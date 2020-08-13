// Copyright (c) 2019, Yefri Tavarez and contributors
// For license information, please see license.txt

frappe.ui.form.on('Documentation', {
	refresh: frm => {
		let show = eval(frappe.user.has_role("System Manager"));
		
		frm.toggle_enable("enlace", show);
		frm.add_custom_button("Ver Tutorial", event => {
			frm.trigger("ir_al_enlace");
		})
	},
	ir_al_enlace: frm => {
		window.open(frm.doc.enlace, '_blank')
	}
});
