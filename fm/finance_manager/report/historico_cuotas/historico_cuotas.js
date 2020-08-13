// Copyright (c) 2016, Yefri Tavarez and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Historico Cuotas"] = {
	"filters": [
		{
			"label": __("Loan"),
			"fieldtype": "Link",
			"fieldname": "loan",
			"options": "Loan",
			"reqd":1
		},
		{
			"label": __("Repayment"),
			"fieldtype": "Int",
			"fieldname": "repayment",
			"reqd":1
		},
		{
			"label": __("Date"),
			"fieldtype": "Date",
			"fieldname": "date",
			"bold":1,
			"default": frappe.datetime.nowdate()
		},
	],
	formatter: function(row, cell, value, columnDef, dataContext) {

			
			if (new Array(3,5,6,7,8,9,10).includes(cell)) {
				value = frappe.format(value, {
					fieldtype: "Currency",
					precision: 2,
				});
			} else if(new Array(1, 12).includes(cell)){
				route = value.split(":")[0]
				return `<a class="grey" href="#Form/${columnDef.df.options}/${route}" data-doctype="${columnDef.df.options}">${value}</a>`;
			}

			return this.left_align(row, cell, value, columnDef, dataContext);
	},
	left_align: function(row, cell, value, columnDef, dataContext) {
		const stylesheet = [
			"text-align: right !important;",
			"display: block;",
		].join(" ");

		return `<span style="${stylesheet}">${value || ""}</span>`;
	},
	
}
