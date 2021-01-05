// Copyright (c) 2016, Yefri Tavarez and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Recibo Seguros"] = {
	"filters": [
		{
			"label": __("From Date"),
			"fieldtype": "Date",
			"fielname": "from_date",
			"bold": 1
		},
		{
			"label": __("To Date"),
			"fieldtype": "Date",
			"fielname": "to_date",
			"bold": 1
		},
		{
			"label": __("Branch Office"),
			"fieldtype": "Link",
			"fielname": "branch_office",
			"options": "Branch Office",
			"bold": 1
		}
	]
}
