# Copyright (c) 2013, Yefri Tavarez and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

import frappe
from frappe.utils import flt
from frappe import msgprint, _

def execute(filters=None):
	return get_columns(), get_data(filters)


def get_columns():
	"""return columns based on filters"""
	columns = [
		_("Loan") + ":Link/Loan:90",
		_("Cuotas Pend.") + ":Int:90",
		_("Status") + ":Data:100",
		_("Cedula") + ":Data:110",
		_("Cliente") + ":Data:300",
		_("Sucursal") + ":Data:120",
		_("Marca") + ":Data:100",
		_("Model") + ":Data:100",
		_("Ano") + ":Data:80",
		_("Chassis") + ":Data:120",
		_("Precio Venta") + ":Currency:100",
		_("Poliza") + ":Link/Poliza de Seguro:120",
		_("Status") + ":Data:100",
		_("Aseguradora") + ":Data:120",
		_("Poliza No.") + ":Data:120",
		_("Co-Conductor") + ":Data:200",
		_("Cedula Co-Conductor") + ":Data:120",
		_("F. Inicio") + ":Date:100",
		_("Prima") + ":Currency:110",
		_("Monto Asegurado") + ":Currency:110",
	]

	return columns

def get_conditions(filters):

	conditions = "`tabLoan`.docstatus = 1"

	if filters.get("branch_office"):
		conditions += " and `tabLoan`.branch_office = %(branch_office)s"

	return conditions

def get_data(filters):

	conditions = get_conditions(filters)
	
	return frappe.db.sql("""
		SELECT
			`tabLoan`.name,
			(SELECT COUNT(1) FROM `tabTabla Amortizacion` WHERE `tabTabla Amortizacion`.parent =`tabLoan`.name AND `tabTabla Amortizacion`.estado = 'VENCIDA' ) as pend,
			`tabLoan`.status,
			`tabLoan`.customer_cedula,
			`tabLoan`.customer_name,
			`tabLoan`.branch_office,
			`tabVehicle`.make,
			`tabVehicle`.model,
			`tabVehicle`.year,
			`tabVehicle`.chassis_no,
			`tabVehicle`.price,
			`tabPoliza de Seguro`.name,
			`tabPoliza de Seguro`.status,
			`tabPoliza de Seguro`.insurance_company,
			`tabPoliza de Seguro`.policy_no,
			`tabPoliza de Seguro`.nombre_del_conductor,
			`tabPoliza de Seguro`.cedula_conductor,
			`tabPoliza de Seguro`.start_date,
			`tabPoliza de Seguro`.total_amount,
			`tabPoliza de Seguro`.monto_asegurado
		FROM 
			`tabLoan`
		JOIN
			`tabVehicle`
		ON
			`tabVehicle`.name = `tabLoan`.asset
		LEFT JOIN
			`tabPoliza de Seguro`
		ON
			`tabPoliza de Seguro`.docstatus = 1
		AND
			`tabPoliza de Seguro`.status = 'Activo'
		AND
			`tabPoliza de Seguro`.loan = `tabLoan`.name

		WHERE
			%s

	""" % conditions, filters, debug=True)
