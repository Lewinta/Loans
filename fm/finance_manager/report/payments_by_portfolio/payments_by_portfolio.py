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
		"Capital:Currency:100",
		"Mora:Currency:100",
		"Seguro:Currency:100",
		"Descuentos:Currency:100",
		"Gastos Legal:Currency:120",
		"Total:Currency:120",
		"Tipo de Pago:Data:100",
		"Referencia:Data:200",
		"Sucursal:Data:120",
	]

def get_data(filters):
	if not filters.get("client_portfolio"):
		return []
	portfolio = frappe.get_doc("Client Portfolio", filters.get("client_portfolio"))

	loans = [x.loan for x in portfolio.customer_portfolio]
	loans = "','".join(loans)
	results = []
	data =  frappe.db.sql("""
		SELECT
			`tabJournal Entry`.name,
			`tabJournal Entry`.posting_date,
			`tabLoan`.customer,
			`tabJournal Entry`.loan,
			`tabJournal Entry`.repayment_no,
			SUM(
				IF(
					`tabJournal Entry Account`.repayment_field = 'capital',
					`tabJournal Entry Account`.credit_in_account_currency,
					0
				)
			) capital,
			SUM(
				IF(
					`tabJournal Entry Account`.repayment_field = 'fine',
					`tabJournal Entry Account`.credit_in_account_currency,
					0
				)
			) fine,
			SUM(
				IF(
					`tabJournal Entry Account`.repayment_field = 'insurance',
					`tabJournal Entry Account`.credit_in_account_currency,
					0
				)
			) insurance,
			SUM(
				IF(
					`tabJournal Entry Account`.repayment_field = 'other_discounts',
					`tabJournal Entry Account`.debit_in_account_currency,
					0
				)
			) other_discounts,
			SUM(
				IF(
					`tabJournal Entry Account`.repayment_field = 'gastos_recuperacion',
					`tabJournal Entry Account`.credit_in_account_currency,
					0
				)
			) gastos_recuperacion,
			`tabJournal Entry`.total_debit,
			`tabJournal Entry`.voucher_type,
			`tabJournal Entry`.cheque_no,
			`tabJournal Entry`.branch_office
		FROM 
			`tabJournal Entry`
		JOIN
			`tabJournal Entry Account`
		ON
			`tabJournal Entry`.name = `tabJournal Entry Account`.parent
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
		GROUP BY 
			`tabJournal Entry`.name
	""" % (loans, portfolio.start_date, portfolio.end_date), as_dict=True, debug=False)
	for row in data:
		results.append(
			(
				row.name,
				row.posting_date,
				row.customer,
				row.loan,
				row.repayment_no,
				row.capital - row.other_discounts,
				row.fine,
				row.insurance,
				row.other_discounts,
				row.gastos_recuperacion,
				row.total_debit,
				row.voucher_type,
				row.cheque_no,
				row.branch_office
			)
		)
	return results
