frappe.provide("fm.utils")

function developer_mode(){
	var doctype = docname = "FM Configuration"
	var dev_mode = 0
		frappe.db.get_value(doctype, docname, "developer_mode", function(data) {
		dev_mode = data.developer_mode
	})
}

class JavaScriptFile {
	fetch(src) {
		this.new_script_tag() && frappe.run_serially([
			() => this.validate_source(src),
			() => this.set_source(src),
			() => this.append_to_page(),
		]);
	}

	new_script_tag() {
		return this.script = document.createElement("script");
	}

	set_source(src) {
    	this.script.src = src;
	}

	append_to_page(src) {
		document.head.appendChild(this.script);
	}

	validate_source(src) {
		$.ajax(src).fail(() => frappe.throw("¡Archivo no encontrado!"));
	}
}

$(document).ready(function(event) {
    // hide the help menu
    $(".dropdown.dropdown-help.dropdown-mobile").hide();

    $.extend(frappe.app, {
        refresh_notifications: refresh_notifications
    })
})

var refresh_notifications = function() {
    var me = this;
    if (frappe.session_alive) {
        return frappe.call({
            method: "frappe.desk.notifications.get_notifications",
            callback: function callback(r) {
                if (r.message) {
                    $.extend(frappe.boot.notification_info, r.message);
                    $(document).trigger("notification-update");

                    me.update_notification_count_in_modules();

                    if (frappe.get_route()[0] != "messages") {
                        if (r.message.new_messages.length) {
                            frappe.utils.set_title_prefix("(" + r.message.new_messages.length + ")");
                        }
                    }
                }
            },
            freeze: false,
            type: "GET", // to fix the invalid request bug
            args: {
                // to identify requests in the server
                "user": frappe.boot.user_info[frappe.session.user].username
            }
        });
    }
}

// fix the unload bug
_f.Frm.prototype.is_new = () => {
    return this.doc && this.doc.__islocal
}

