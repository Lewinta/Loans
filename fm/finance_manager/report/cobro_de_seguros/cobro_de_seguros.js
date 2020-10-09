// Copyright (c) 2016, Yefri Tavarez and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Cobro de Seguros"] = {
	"filters": [
		{
			"label": __("From Date"),
			"fieldname": "from_date",
			"fieldtype": "Date",
			"default": frappe.datetime.month_start(),
			"bold":1,
		},
		{
			"label": __("To Date"),
			"fieldname": "to_date",
			"fieldtype": "Date",
			"default": frappe.datetime.month_end(),
			"bold":1,
		},
		{
			"label": __("Branch Office"),
			"fieldname": "branch_office",
			"fieldtype": "Link",
			"options": "Branch Office",
			"bold":1,
		}
	]
}
