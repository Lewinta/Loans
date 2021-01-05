// Copyright (c) 2021, Yefri Tavarez and contributors
// For license information, please see license.txt

frappe.ui.form.on('Portfolio Log', {
	refresh: function(frm) {
		let fields = [
			"loan",
			"amount_to_collect",
			"start_date",
			"end_date",
		]

		$.map(fields, field => {
			frm.set_df_property(field, read_only, !frappe.user.has_role("System Manager"));
		});
	}
});
