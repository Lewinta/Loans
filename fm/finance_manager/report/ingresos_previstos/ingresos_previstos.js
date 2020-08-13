// Copyright (c) 2016, Yefri Tavarez and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Ingresos previstos"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname":"year",
			"label": __("Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			// "default": frappe.defaults.get_default('fiscal_year'),
			"default": frappe.datetime.year_end().split("-")[0],
			"reqd": 1
		},
		{
			"fieldname":"month",
			"label": __("Month"),
			"fieldtype": "Select",
			"options": [
				{'value': '01', 'label': __("January")},
				{'value': '02', 'label': __("February")},
				{'value': '03', 'label': __("March")},
				{'value': '04', 'label': __("April")},
				{'value': '05', 'label': __("May")},
				{'value': '06', 'label': __("June")},
				{'value': '07', 'label': __("July")},
				{'value': '08', 'label': __("August")},
				{'value': '09', 'label': __("September")},
				{'value': '10', 'label': __("October")},
				{'value': '11', 'label': __("November")},
				{'value': '12', 'label': __("December")},
			],
			"default": frappe.datetime.month_end().split('-')[1],
			"reqd": 1
		},
		{
			"fieldname":"status",
			"label": __("Estado"),
			"fieldtype": "Select",
			"options": "PENDIENTE\nABONO\nSALDADA\nVENCIDA",
		},
	]
}
