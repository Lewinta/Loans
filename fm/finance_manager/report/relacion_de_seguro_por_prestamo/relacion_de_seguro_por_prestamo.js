// Copyright (c) 2016, Yefri Tavarez and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Relacion de Seguro por Prestamo"] = {
	"filters": [
		{
			"fieldname":"branch_office",
			"label": __("Sucursal"),
			"fieldtype": "Link",
			"options": "Branch Office",
			"bold": 1,
		},
	]
}
