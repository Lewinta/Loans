// Copyright (c) 2017, Yefri Tavarez and contributors
// For license information, please see license.txt

frappe.ui.form.on('Branch Office', {
	"after_save": (frm) => {
		frm.call("refresh_users").done((response) => {
			refresh_field("users")
		}).fail(() => frappe.msgprint("¡Roger We have a problem!"));
	},
	"add_user": (frm) => {
			
		frm.method = "add_user";
		frm.trigger("show_prompt");
	},
	"drop_user": (frm) => {	
		frm.method = "drop_user";
		frm.trigger("show_prompt");
		
	},
	"show_prompt": (frm) => {
		fields = [{
			"fieldname": "usr",
			"fieldtype": "Link",
			"label": __("Seleccione el usuario"),
			"options": "User" 
		}];

		// finishes introducing the values
		let onsubmit = (data) => {

			frappe.confirm("¿Estas seguro de agregar a <b>" + data.usr + "</b> a esta sucursal?", () => {

			 	let args  = { "usr": frm.user_prompt.get_value('usr') };

				frm.call(frm.method, args).done((response) => {
					msg = frm.method == "add_user" ? "Ahora " + response.message + " tiene acceso a esta sucursal" : response.message + " fue removido de esta sucursal";
					frappe.show_alert( msg, 8 );
					frappe.utils.play_sound("submit");
					frm.reload_doc();

				}).fail(() => frappe.msgprint("¡Roger We have a problem!"));
			}, () => frm.user_prompt.show());
		}

		// let's check if object is already set
		if (frm.user_prompt) {

			// it is set at this point
			// let's just make it visible
			frm.user_prompt.show();
		} else {

			// there was not object, so we need to create it
			frm.user_prompt = frappe.prompt(fields, onsubmit, "Usuarios", "Confirmar");
		}

	}


});