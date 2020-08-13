// Copyright (c) 2016, Yefri Tavarez and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Payments by Portfolio"] = {
	"filters": [
		{
			"label": __("Client Portfolio"),
			"fieldname": "client_portfolio",
			"fieldtype": "Link",
			"options": "Client Portfolio",
			"reqd": 1,
		},
		// {
		// 	"label": __("From Fecha"),
		// 	"fieldname": "from_date",
		// 	"fieldtype": "Date",
		// 	"readonly": 1,
		// },
		// {
		// 	"label": __("To Fecha"),
		// 	"fieldname": "to_date",
		// 	"fieldtype": "Date",
		// 	"readonly": 1,
		// },
	]
}
