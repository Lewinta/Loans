// Copyright (c) 2016, Yefri Tavarez and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Customers by Portfolio"] = {
	"filters": [
		{
			"label": __("Client Portfolio"),
			"fieldname": "client_portfolio",
			"fieldtype": "Link",
			"options": "Client Portfolio",
			"reqd": 1,
		},
	]
}
