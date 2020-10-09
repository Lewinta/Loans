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
		_("Poliza") + ":Link/Poliza de Seguro:90",
		_("Cliente") + ":Data:300",
		_("Aseguradora") + ":Data:120",
		_("Externo") + ":Check:80",
		_("F. Inicio") + ":Date:100",
		_("Poliza No.") + ":Data:120",
		_("Prima") + ":Currency:110",
		_("Pagado") + ":Currency:110",
		_("Status") + ":Data:100",
		_("Sucursal") + ":Data:120",
	]

	return columns

def get_conditions(filters):

	conditions = ["`tabJournal Entry`.docstatus = 1"]

	if filters.get("branch_office"):
		conditions.append("`tabPoliza de Seguro`.branch_office = %(branch_office)s")
	
	if filters.get("from_date"):
		conditions.append("`tabJournal Entry`.posting_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("`tabJournal Entry`.posting_date <= %(to_date)s")


	return " AND ".join(conditions)

def get_data(filters):

	conditions = get_conditions(filters)
	
	return frappe.db.sql("""
		SELECT
			`tabPoliza de Seguro`.name,
			`tabPoliza de Seguro`.customer,
			`tabPoliza de Seguro`.insurance_company,
			`tabPoliza de Seguro`.endoso_externo,
			`tabPoliza de Seguro`.start_date,
			`tabPoliza de Seguro`.policy_no,
			`tabPoliza de Seguro`.total_amount,
			SUM( 
				IF (
					`tabJournal Entry Account`.repayment_field = 'insurance',
					`tabJournal Entry Account`.credit_in_account_currency,
					0
				)
			) as paid,
			`tabPoliza de Seguro`.status,
			`tabPoliza de Seguro`.branch_office

		FROM
			`tabJournal Entry`
		JOIN 
			`tabJournal Entry Account`
		ON
			`tabJournal Entry`.name = `tabJournal Entry Account`.parent
		AND 
			`tabJournal Entry`.docstatus = 1
		JOIN
			`tabPoliza de Seguro`
		ON
			`tabPoliza de Seguro`.docstatus = 1
		AND
			`tabPoliza de Seguro`.status = 'Activo'
		AND
			`tabPoliza de Seguro`.loan = `tabJournal Entry`.loan
		WHERE
			%s
		GROUP BY 
			`tabPoliza de Seguro`.name
		ORDER BY
			`tabPoliza de Seguro`.name desc
	""" % conditions, filters, debug=True)
