// Copyright (c) 2016, Yefri Tavarez and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Detalle de Pagos"] = {
	"filters": [
		{
			"label": __("Loan"),
			"fieldname": "loan",
			"fieldtype": "Link",
			"reqd": 1,
			"options": "Loan"
		}
	]
}
