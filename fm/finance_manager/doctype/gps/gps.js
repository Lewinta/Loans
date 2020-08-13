// Copyright (c) 2020, Yefri Tavarez and contributors
// For license information, please see license.txt

frappe.ui.form.on('GPS', {
	refresh: frm => {
		let events = ["set_queries"];
		$.map(events, event => {
			frm.trigger(event);
		});
		frm.add_fetch("loan", "branch_office", "branch_office");
	},
	set_queries: frm => {
		frm.set_query("supplier", function () {
			return {
				"filters": {
					"supplier_type": "GPS Provider"
				}
			}
		});
	}
});
