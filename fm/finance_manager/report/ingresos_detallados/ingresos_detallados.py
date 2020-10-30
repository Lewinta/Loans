	# Copyright (c) 2013, TZCODE SRL and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cstr, flt

def execute(filters=None):
	return get_columns(), get_data(filters)

def get_columns():
	columns = (
		("Pago", "Link/Journal Entry", 90),
		("Sucursal", "Link/Branch Office", 120),
		("Prestamo", "Link/Loan", 90),
		("Cliente", "Data", 200),
		("Capital", "Currency", 100),
		("Mora", "Currency", 100),
		("Seguro", "Currency", 100),
		("Descuentos", "Currency", 100),
		("Intimaciones", "Currency", 120),
		("Gastos Legal", "Currency", 120),
		("Total", "Currency", 120),
	)

	formatted_columns = []
	
	for label, fieldtype, width in columns:
		formatted_columns.append(
			get_formatted_column(label, fieldtype, width)
		)

	return formatted_columns

def get_formatted_column(label, fieldtype, width):
	# [label]:[fieldtype/Options]:width
	parts = (
		_(label),
		fieldtype,
		cstr(width)
	)
	return ":".join(parts)

def get_conditions(filters):
	"""
	Return sql conditions ready to use in query

	NOTE: Value is mandatory if condition_type == value
	"""
	conditions = []

	if filters.get('from_date'):
		conditions.append(
			("Journal Entry", "posting_date", ">=", filters.get('from_date'))
		)

	if filters.get('to_date'):
		conditions.append(
			("Journal Entry", "posting_date", "<=", filters.get('to_date'))
		)

	if filters.get('branch'):
		conditions.append(
			("Journal Entry", "branch_office", "=", filters.get('branch'))
		)

	if filters.get('mode_of_payment'):
		conditions.append(
			("Journal Entry", "voucher_type", "=", filters.get('mode_of_payment'))
		)

	sql_conditions = []

	if not conditions:
		return sql_conditions
	
	for doctype, fieldname, compare, value in conditions:

		if not value:
			continue
		if value == "NULL":
			sql_condition = "`tab{doctype}`.`{fieldname}` {compare} {value}" \
				.format(doctype=doctype, fieldname=fieldname, compare=compare,
					value=value)
		else:
			sql_condition = "`tab{doctype}`.`{fieldname}` {compare} '{value}'" \
				.format(doctype=doctype, fieldname=fieldname, compare=compare,
					value=value)

		sql_conditions.append(sql_condition)

	# frappe.errprint(conditions)

	return " And ".join(sql_conditions)


def get_fields(filters):
	"""
	Return sql fields ready to be used on query
	"""
	fields = (
		("Journal Entry", "name", "jv"),
		("Journal Entry", "branch_office"),
		("Journal Entry", "loan"),
		("Journal Entry", "pay_to_recd_from"),
		("Loan", "customer"),
		("""SUM(
				IF(
					`tabJournal Entry Account`.repayment_field = 'capital',
					`tabJournal Entry Account`.credit_in_account_currency,
					0
				)
			) capital"""
		),
		("""SUM(
				IF(
					`tabJournal Entry Account`.repayment_field = 'fine',
					`tabJournal Entry Account`.credit_in_account_currency,
					0
				)
			) fine"""
		),
		("""SUM(
				IF(
					`tabJournal Entry Account`.repayment_field = 'insurance',
					`tabJournal Entry Account`.credit_in_account_currency,
					0
				)
			) insurance"""
		),
		("""SUM(
				IF(
					`tabJournal Entry Account`.repayment_field = 'other_discounts',
					`tabJournal Entry Account`.debit_in_account_currency,
					0
				)
			) other_discounts"""
		),
		("""SUM(
				IF(
					`tabJournal Entry Account`.repayment_field = 'gastos_intimacion',
					`tabJournal Entry Account`.credit_in_account_currency,
					0
				)
			) gastos_intimacion"""
		),
		("""SUM(
				IF(
					`tabJournal Entry Account`.repayment_field = 'gastos_recuperacion',
					`tabJournal Entry Account`.credit_in_account_currency,
					0
				)
			) gastos_recuperacion"""
		),
	)
		
	sql_fields = []

	for args in fields:
		sql_field = get_field(args)

		sql_fields.append(sql_field)

	return ", ".join(sql_fields)

def get_field(args):

	if len(args) == 2:
		doctype, fieldname = args
		alias = fieldname
	elif len(args) == 3:
		doctype, fieldname, alias = args
	else:
		return args if isinstance(args, basestring) \
			else " ".join(args)

	sql_field = "`tab{doctype}`.`{fieldname}` as {alias}" \
		.format(doctype=doctype, fieldname=fieldname, alias=alias)

	return sql_field

def get_data(filters):
	"""
	Return the data that needs to be rendered
	"""
	fields = get_fields(filters)
	conditions = get_conditions(filters)
	results = []
	data =  frappe.db.sql("""
		Select
			{fields}
			
		From
			`tabJournal Entry`
		Inner Join 
				`tabJournal Entry Account`
			On
				`tabJournal Entry`.name = `tabJournal Entry Account`.parent
			And 
				`tabJournal Entry`.docstatus = 1
		Left Join
			`tabLoan`
			On
			`tabJournal Entry`.loan = `tabLoan`.name
			And 
				`tabLoan`.docstatus = 1
		Where
			{conditions}
		Group By 
			`tabJournal Entry`.name

		""".format(fields=fields, conditions=conditions or "1 = 1"),
	filters, debug=False, as_dict=True)
	for row in data:
		results.append(
			(
				row.jv,
				row.branch_office,
				row.loan,
				row.customer or row.pay_to_recd_from,
				row.capital,
				row.fine,
				row.insurance,
				row.other_discounts,
				row.gastos_intimacion,
				row.gastos_recuperacion,
				row.capital + row.fine + row.insurance - row.other_discounts + row.gastos_recuperacion + row.gastos_intimacion
			) 
		)
	return results
