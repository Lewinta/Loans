# Copyright (c) 2013, Lewin Villar and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt

def execute(filters=None):
	return get_columns(), get_data(filters)

def get_columns():
	return [
		"Prestamo:Link/Loan:70",
		"Fecha:Date:90",
		"Cliente:Link/Customer:200",
		"Vehiculo:Data:150",
		"Poliza:Link/Poliza de Seguro:90",
		"Aseguradora:Data:150",
		"Poliza no.:Data:100",
		"Monto Total:Currency:90",
		"Expiracion:Date:90",
	]

def get_field(args):

	if len(args) == 3:
		doctype, fieldname, alias = args
	elif len(args) == 2:
		doctype, fieldname = args
		alias = fieldname
	else:
		return args if isinstance(args, basestring) \
			else " ".join(args)

	sql_field = "`tab{doctype}`.`{fieldname}` as {alias}" \
		.format(doctype=doctype, fieldname=fieldname, alias=alias)

	return sql_field

def get_fields(filters):
	"""
	Return sql fields ready to be used on query
	"""
	fields = (
		("Loan", "name", "loan"),
		("Loan", "disbursement_date"),
		("Loan", "customer"),
		("Loan", "asset"),
		("Poliza de Seguro", "name", "poliza"),
		("Poliza de Seguro", "insurance_company"),
		("Poliza de Seguro", "policy_no", "poliza"),
		("Poliza de Seguro", "total_amount"),
		("Poliza de Seguro", "end_date"),
	)

	sql_fields = []

	for args in fields:
		sql_field = get_field(args)

		sql_fields.append(sql_field)

	return ", ".join(sql_fields)

def get_data(filters):
	filters = get_filters(filters)
	fields = get_fields(filters)

	return frappe.db.sql("""
		SELECT
			{fields}
		FROM
			`tabLoan`
		JOIN
			`tabPoliza de Seguro`
		ON
			`tabLoan`.asset = `tabPoliza de Seguro`.vehicle
		AND
			`tabPoliza de Seguro`.status = 'Activo'
		WHERE
			{filters}
		GROUP BY
			`tabLoan`.`disbursement_date`

	""".format(fields=fields, filters=filters), debug=True)

def get_filters(filters):
	query = ['`tabLoan`.docstatus = 1 AND `tabPoliza de Seguro`.docstatus = 1']

	if filters.get("from_date"):
		query.append(
			"`tabLoan`.disbursement_date >= '{}'".format(
				filters.get('from_date')
			)
		)
	
	if filters.get("from_date"):
		query.append(
			"`tabLoan`.disbursement_date >= '{}'".format(
				filters.get('from_date')
			)
		)

	return " AND ".join(query)
