# Copyright (c) 2013, Lewin Villar and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt

def execute(filters=None):
	return get_columns(), get_data(filters)

def get_columns():
	return [
		"Prestamo:Link/Loan:90",
		"Cliente:Data:250",
		"Fecha No:Date:90",
		"Cuotas:Int:80",
		"Monto Pendiente:Currency:150",
		"Sucursal:Data:120",
	]

def get_data(filters):
	if not filters.get("client_portfolio"):
		return []
	portfolio = frappe.get_doc("Client Portfolio", filters.get("client_portfolio"))

	loans = [x.loan for x in portfolio.customer_portfolio]
	loans = "','".join(loans)

	return  frappe.db.sql("""
		SELECT
			`tabTabla Amortizacion`.parent,
			`tabLoan`.customer,
			MIN(CASE WHEN `tabTabla Amortizacion`.monto_pendiente > 0 THEN `tabTabla Amortizacion`.fecha END),
			SUM(IF(`tabTabla Amortizacion`.monto_pendiente > 0, 1, 0)) as qty,
			SUM(`tabTabla Amortizacion`.monto_pendiente),
			`tabLoan`.branch_office
		FROM 
			`tabTabla Amortizacion`
		LEFT JOIN
			`tabLoan`
		ON
			`tabTabla Amortizacion`.parent = `tabLoan`.name
		WHERE
			`tabLoan`.name in ('%s')
		AND
			`tabTabla Amortizacion`.fecha >= '%s'
		AND
			`tabTabla Amortizacion`.fecha <= '%s'
		GROUP BY 
			`tabTabla Amortizacion`.parent
		

	""" % (loans, portfolio.start_date, portfolio.end_date), debug=True)
