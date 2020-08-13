# Copyright (c) 2013, Lewin Villar and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt

def execute(filters=None):
	return get_columns(), get_data(filters)

def get_columns():
	return [
		"Pago:Link/Journal Entry:100",
		"Fecha No:Date:90",
		"Cliente:Data:250",
		"Prestamo:Link/Loan:90",
		"Pagare:Data:80",
		"Monto Pagado:Currency:110",
		"Tipo de Pago:Data:100",
		"Referencia:Data:150",
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
			`tabJournal Entry`.name,
			`tabJournal Entry`.posting_date,
			`tabLoan`.customer,
			`tabJournal Entry`.loan,
			`tabJournal Entry`.repayment_no,
			`tabJournal Entry`.total_debit,
			`tabJournal Entry`.voucher_type,
			`tabJournal Entry`.cheque_no,
			`tabJournal Entry`.branch_office
		FROM 
			`tabJournal Entry`
		LEFT JOIN
			`tabLoan`
		ON
			`tabJournal Entry`.loan = `tabLoan`.name
		WHERE
			`tabLoan`.name in ('%s')
		AND
			`tabJournal Entry`.es_un_pagare = 1
		AND
			`tabJournal Entry`.posting_date >= '%s'
		AND
			`tabJournal Entry`.posting_date <= '%s'
		AND
			`tabJournal Entry`.docstatus = 1
		
		

	""" % (loans, portfolio.start_date, portfolio.end_date), debug=False)
