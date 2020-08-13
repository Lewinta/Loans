# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	return get_columns(), get_data(filters)

def get_columns():
	return [
		"Prestamo:Link/Loan:100",
		"Nombre del Cliente:Data:300",
		"Fecha de Pago:Date:120",
		"Capital:Currency:120",
		"Comision:Currency:120",
		"Mora:Currency:120",
		"Seguro:Currency:120",
		"Monto a Pagar:Currency:120",
		"Monto Pagado:Currency:120",
		"Estado:Data:100"
	]

def get_data(filters=None):
	conditions = get_conditions(filters)
	results = []
	data =  frappe.db.sql("""
		SELECT 
			parent.name,
			parent.customer_name,
			child.fecha,
			child.capital,
			child.interes,
			child.fine,
			child.mora_acumulada,
			child.insurance,
			child.monto_pagado,
			child.monto_pendiente,
			child.estado
		FROM
			`tabLoan` AS parent
		JOIN
			`tabTabla Amortizacion` AS child ON parent.name = child.parent
		WHERE 
			{conditions}
		ORDER BY fecha""".format(conditions=conditions),
	filters, as_dict=True)

	for row in data:
		results.append(
			(
				row.name,
				row.customer_name,
				row.fecha,
				row.capital,
				row.interes,
				row.fine,
				row.insurance,
				row.monto_pagado,
				row.monto_pendiente,
				row.estado,
			)
		)
	return results

def get_conditions(filters=None):
	conditions = []

	if not filters.get("year") or not filters.get("month"):
		frappe.throw("Formato de fecha incompleto")

	if filters.get("status"):
		conditions.append("child.estado = %(status)s")

	if filters.get("company"):
		conditions.append("parent.company = %(company)s")

	conditions.append("DATE_FORMAT(child.fecha, '%%Y%%m') = '{year}{month}'".format(**filters))

	return " AND ".join(conditions)