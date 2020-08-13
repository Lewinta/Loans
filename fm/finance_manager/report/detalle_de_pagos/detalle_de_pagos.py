# Copyright (c) 2013, Lewin Villar and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt

def execute(filters=None):
	return get_columns(), get_data(filters)

def get_columns():
	return [
		"Pago:Link/Journal Entry:90",
		"Fecha No:Date:90",
		"Prestamo:Link/Loan:70",
		"Cuotas No:Data:90",
		"Tipo de Pago:Data:90",
		"Monto Pagado:Currency:120",
		"Seguro:Currency:120",
		"Capital/Comision:Currency:120",
		"Descuento:Currency:120",
		"Mora:Currency:120",
		"Gastos Rec.:Currency:120",
	]

def get_data(filters):
	data, name = [], ""

	result = frappe.db.sql("""
		SELECT
			parent.name,
			parent.posting_date,
			parent.loan,
			parent.repayment_no,
			parent.voucher_type,
			parent.total_debit,
			SUM( IF( child.repayment_field  = 'insurance' , child.credit, 0 )) as insurance,
			SUM( IF( child.repayment_field  = 'capital' , child.credit, 0 )) + SUM( IF( child.repayment_field  = 'interes' , child.credit, 0 )) - SUM( IF( child.repayment_field  = 'other_discounts' , child.debit, 0 ))as capital,
			SUM( IF( child.repayment_field  = 'fine' , child.credit, 0 )) as fine,
			SUM( IF( child.repayment_field  = 'gastos_recuperacion' , child.credit, 0 )) as expenses,
			SUM( IF( child.repayment_field  = 'other_discounts' , child.debit, 0 )) as discount

		FROM
			`tabJournal Entry` AS parent 
			JOIN
				`tabJournal Entry Account` AS child 
				ON child.parent = parent.name 
		WHERE
			%(filters)s

		GROUP BY
			parent.name

	""" % { "filters": get_filters(filters) }, filters, as_dict=True, debug=True)

	for row in result:
	# 	if row.name != name:
	# 		name = row.name
	# 	# 	add_total_amounts(row)
	# 	else: 
	# 		row.name = ""
	# 	# 	row.loan = ""
	# 	# 	# row.monthly_repayment_amount = ""
	# 	# 	row.total_paid = ""
	# 	# 	row.total_pending = ""
	# 	# 	row.total_payment = ""
		
	# 	# if row.monto_pagado <= 0:
	# 	# 	continue
	# 	name = row.name
		append_to_data(data, row)

	return data

def get_filters(filters):
	query = ["parent.docstatus = 1  and es_un_pagare = 1 and repayment_field != 'paid_amount'"]

	if filters.get("loan"):
		query.append("parent.loan = %(loan)s")

	return " AND ".join(query)
		
def append_to_data(data, row):
	# mora = row.fine
	# extras = mora + row.insurance
	# insurance = row.monto_pagado - mora
	# cuota = row.monto_pagado - extras
	data.append([
		row.name,
		row.posting_date,
		row.loan,
		row.repayment_no,
		row.voucher_type,
		row.total_debit,
		row.insurance,
		row.capital,
		row.discount,
		row.fine,
		row.expenses,

	])
