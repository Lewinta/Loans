// Copyright (c) 2018, TZ CODE, SRL and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Datacredito"] = {
	"filters": [
		{
			"fieldtype": "Link",
			"fieldname": "branch_office",
			"label": __("Sucursal"),
			"options": "Branch Office",
			"bold": 1,
			"reqd": 1
		},
		// {
		// 	"fieldtype": "Date",
		// 	"fieldname": "to_date",
		// 	"label": __("To"),
		// 	"default": frappe.datetime.month_end(),
		// 	"reqd": true
		// },
		// {
		// 	"fieldtype": "Link",
		// 	"fieldname": "customer",
		// 	"options": "Customer",
		// 	"label": __("Customer"),
		// 	"reqd": false
		// },
		// {
		// 	"fieldtype": "Select",
		// 	"fieldname": "statu",
		// 	"options": [
		// 		{"label": "Normal", "value": "N"},
		// 		{"label": "Abono", "value": "A"},
		// 		{"label": "Legal", "value": "L"},
		// 	],
		// 	"label": __("Status"),
		// 	"reqd": false
		// },
	]
}
