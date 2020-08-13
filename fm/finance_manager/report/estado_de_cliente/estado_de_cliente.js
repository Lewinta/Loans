// Copyright (c) 2016, Yefri Tavarez and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Estado de Cliente"] = {
	"filters": [
		{
			"label": "Compañía",
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"reqd": 1,
			"default": frappe.defaults.get_default("company"),
			"hidden": 1,
		},
		{
			"label": "Desde Fecha",
			"fieldname": "from_date",
			"fieldtype": "Date",
			"reqd": 1,
			"default": "2016-01-01"
			//"default": frappe.datetime.year_start()
		},
		{
			"label": "Hasta Fecha",
			"fieldname": "to_date",
			"fieldtype": "Date",
			"reqd": 1,
			"default": frappe.datetime.get_today()
		},
		{
			"label": __("Loan"),
			"fieldname": "loan",
			"fieldtype": "Link",
			"options": "Loan",
		},
		{
			"label": "Cliente",
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer"
		},
		{
			"label": "Estado",
			"fieldname": "status",
			"fieldtype": "Select",
			"options": "\nPENDIENTE\nSALDADA\nABONO\nVENCIDA",
			"default": "VENCIDA"
			
		},
		{
			"label": "Sucursal",
			"fieldname": "sucursal",
			"fieldtype": "Link",
			"options": "Branch Office",
			"default": frappe.boot.sucursal
			
		}
	],
	formatter: function (row, cell, value, columnDef, dataContext, default_formatter) {
		value = default_formatter(row, cell, value, columnDef, dataContext);

		if (cell == 3 || cell == 4) {
			if (flt(value)) {
				value = flt(value).toFixed(2).replace(/(\d)(?=(\d{3})+\.)/g, '$1,');
			}
		}

		return value;
	}
}
