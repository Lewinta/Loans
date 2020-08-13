// Copyright (c) 2016, Yefri Tavarez and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Ingresos Detallados"] = {
	"filters": [
		{
			"label": __("From Date"),
			"fieldtype": "Date",
			"fieldname": "from_date",
			"reqd": 1,
			"default": frappe.datetime.get_today()
		},
		{
			"label": __("To Date"),
			"fieldtype": "Date",
			"fieldname": "to_date",
			"reqd": 1,
			"default": frappe.datetime.get_today()
		},
		{
			"label": __("Sucursal"),
			"fieldtype": "Link",
			"fieldname": "branch",
			"options": "Branch Office",
		},
		{
			"label": __("Metodo de Pago"),
			"fieldtype": "Select",
			"fieldname": "mode_of_payment",
			"options": "Journal Entry\nBank Entry\nCash Entry\nCredit Card Entry\nCheque\nDebit Note\nCredit Note\nContra Entry\nExcise Entry\nWrite Off Entry\nOpening Entry\nDepreciation Entry",
			"default": "Cash Entry"
		}
	]
}
