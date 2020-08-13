// Copyright (c) 2016, Yefri Tavarez and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Polizas Emitidas"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"fieldtype": "Date",
			"label": "From Date",
			"reqd":1
		},
		{
			"fieldname": "to_date",
			"fieldtype": "Date",
			"label": __("To Date"),
			"reqd":1
		},
		{
			"fieldname": "branch_office",
			"fieldtype": "Link",
			"options": "Branch Office",
			"label": __("Branch Office"),
			"reqd":1
		}
	]
}
