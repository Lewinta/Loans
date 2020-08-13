# Copyright (c) 2013, Yefri Tavarez and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt

def execute(filters=None):
	return get_columns(), get_data(filters)

def get_columns():
	return [
		"Cliente:Link/Customer:200",
		"Prestamo:Link/Loan:70",
		"Cuota Mensual:Data:95",
		#"Total Pendiente:Float:100",
		"Cuota No:Int:40",
		"Fecha No:Data:90",
		"Monto Pagado:Float:90",
		"Capital:Float:90",
		"Comision:Float:90",
		"Seguro:Float:75",
		"Mora:Float:70",
		"Monto Pendiente:Float:100",
		"Estado:Data:80",
		"Sucursal:Data:120",
	]

def get_data(filters):
	data, loan = [], ""
	if not filters.get("customer"):
		result = frappe.db.sql("""
			SELECT
				parent.customer,
				parent.name as loan,
				parent.monthly_repayment_amount,
				child.idx as repayment_no,
				child.estado as status,
				parent.total_payment,
				child.pagos_acumulados,
				child.monto_pagado,
				child.capital,
				child.interes,
				child.fecha,
				child.insurance,
				child.mora_acumulada,
				child.monto_pendiente,
				parent.branch_office
			FROM
				`tabLoan` AS parent 
				JOIN
					`tabTabla Amortizacion` AS child 
					ON child.parent = parent.name AND parent.status <> "Recuperado"
			WHERE
				%(filters)s
			ORDER BY
				child.fecha ASC

		""" % { "filters": get_filters(filters) }, filters, as_dict=True, debug=False)
	else:
		result = frappe.db.sql("""
			SELECT
				parent.customer,
				parent.name as loan,
				parent.monthly_repayment_amount,
				child.idx as repayment_no,
				child.estado as status,
				parent.total_payment,
				child.pagos_acumulados,
				child.monto_pagado,
				child.capital,
				child.interes,
				child.fecha,
				child.insurance,
				child.mora_acumulada,
				child.monto_pendiente,
				parent.branch_office
			FROM
				`tabLoan` AS parent 
				JOIN
					`tabTabla Amortizacion` AS child 
					ON child.parent = parent.name AND parent.status <> "Recuperado"
			WHERE
				%(filters)s
			ORDER BY
				parent.customer,
				child.idx

		""" % { "filters": get_filters(filters) }, filters, as_dict=True)


	for row in result:
		if not row.loan == loan:
			loan = row.loan
			add_total_amounts(row)
		else: 
			row.customer = ""
			row.loan = ""
			row.monthly_repayment_amount = ""
			row.total_paid = ""
			row.total_pending = ""
			row.total_payment = ""

		append_to_data(data, row)

	return data

def get_filters(filters):
	query = ["parent.status = 'Fully Disbursed'"]

	if filters.get("company"):
		query.append("parent.company = %(company)s")
		
	if filters.get("from_date"):
		query.append("child.fecha >= %(from_date)s")	

	if filters.get("to_date"):
		query.append("child.fecha <= %(to_date)s")	

	if filters.get("customer"):
		query.append("parent.customer = %(customer)s")

	if filters.get("status"):
		query.append("child.estado = %(status)s")

	if filters.get("loan"):
		query.append("child.parent = %(loan)s")

	if filters.get("sucursal"):
		query.append("parent.branch_office = %(sucursal)s")

	return " AND ".join(query)
		
def append_to_data(data, row):
	data.append([
		row.customer,
		row.loan,
		row.monthly_repayment_amount,
		#row.total_payment,
		#row.total_pending,
		row.repayment_no,
		row.fecha,
		row.monto_pagado,
		row.capital,
		row.interes,
		row.insurance,
		row.mora_acumulada,
		row.monto_pendiente,
		row.status,
		row.branch_office,
	])

def add_total_amounts(row):
	row.total_paid = frappe.get_value("Tabla Amortizacion", {
		"parent": row.loan,
		"docstatus": "1"
	}, ["sum(monto_pagado)"])

	row.total_pending = frappe.get_value("Tabla Amortizacion", {
		"parent": row.loan
	}, ["sum(monto_pendiente)"])	
