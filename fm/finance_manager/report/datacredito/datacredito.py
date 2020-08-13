# Copyright (c) 2013, Yefri Tavarez and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import nowdate, date_diff
from math import ceil

def execute(filters=None):
	return get_columns(), get_data(filters)

def get_columns():
	return [
		"PRESTAMO:Link/Loan:100",
		"CUSTOMER NAME:Link/Customer:250",
		"CEDULA:Data:120",
		"DIRRECCION:Data:200",
		"TEL1:Data:120",
		"TEL2:Data:120",
		"MONTO PRESTAMO:Currency:100",
		"CREATION:Date:100",
		"FECHA VENC.:Date:100",
		"BALANCE AL DIA:Currency:130",
		"MONTO ATRASO:Currency:120",
		"STATU:Data:80",
		"ULTIMO PAGO:Date:100",
		"CUOTA MENSUAL:Currency:120",
		"TIPO PRESTAMO:Data:80"
	]
def get_data(filters):
	data = []
	filters = get_filters(filters)

	result = frappe.db.sql("""
		SELECT 
			l.name,
			l.customer,
			l.customer_cedula,
			c.direccion,
			COALESCE((SELECT number FROM `tabPhone Number` WHERE parent = l.customer AND idx = 1), "-") AS tel_1,
			COALESCE((SELECT number FROM `tabPhone Number` WHERE parent = l.customer AND idx = 2), "-") AS tel_2,
			l.loan_amount,
			CAST(l.creation AS DATE) AS creation,
			l.closing_date,
			(SELECT SUM(capital) AS 'Monto Pendiente' FROM `tabTabla Amortizacion` WHERE parent = l.name AND estado !='SALDADA' GROUP BY parent) AS current_balance,
			(SELECT SUM(IF(due_date  < CURDATE(), monto_pendiente, 0)) AS 'Monto Pendiente' FROM `tabTabla Amortizacion` WHERE parent = l.name AND estado IN ('ABONO', 'VENCIDA') GROUP BY parent) AS due_date,
			l.status,  
			(SELECT MAX(posting_date) 'Fecha Ultimo Pago' FROM `tabJournal Entry` WHERE es_un_pagare = 1 AND docstatus = 1 AND loan = l.name) AS last_payment,
			l.monthly_repayment_amount,
			t.expired_payments,
			'N' AS loan_type 
		FROM 
			`tabLoan` l 
		JOIN 
			`tabCustomer` c 
		ON 
			l.customer = c.name
		LEFT JOIN
			`viewExpired Loans` t
		ON
			l.name = t.loan

		WHERE 
			l.docstatus = 1
		AND
			l.status NOT IN ('Perdida Total', 'Recuperado')
		{}

	""".format(filters),  as_dict=True, debug=True)
	
	for row in result:
		append_to_data(data, row)

	return data

def get_filters(filters):
	if filters.get("branch_office"): 
		return "AND l.branch_office = '{}'".format(
			filters.get("branch_office")
		)
	else: 
		return" " 


def append_to_data(data, row):
	days_diff = date_diff(nowdate(), row.last_payment)

	# if days_diff <= 30:
	# 	status = 'N'
	# if days_diff > 30:
	# 	status = 'A'
	# if days_diff > 61:
	# 	status = 'L'
	# if days_diff > 61:
	# 	status = 'C'
	if row.expired_payments > 3:
		status = 'C'
	if row.expired_payments == 3:
		status = 'L'
	if row.expired_payments <= 2:
		status = 'A'
	if row.expired_payments == 0:
		status = 'N'

	if row.status == "Repaid/Closed" and status == 'N':
		status = 'S' 
	
	data.append([
		row.name,
		row.customer,
		row.customer_cedula,
		row.direccion,
		row.tel_1,
		row.tel_2,
		row.loan_amount,
		row.creation,
		row.closing_date,
		row.current_balance,
		row.due_date,
		status,
		row.last_payment,
		row.monthly_repayment_amount,
		row.loan_type,
	])