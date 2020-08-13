class BasePrompt {
	constructor(args) {
		if (args) {
			this.init(args);
		}
	}

	init(args) {
		frappe.run_serially([
			() => this.setup_args(args),
			() => this.setup_fields(),
			() => this.make(),
			() => this.set_primary_action(),
			() => this.set_onhide_action(),
		]);
	}

	setup_args(args) {
		return $.each(args, (key, value) => this[key] = value);
	}

	setup_fields() {
		if (typeof this.fields === "string") {
			this.fields = [{
				"label": this.fields,
				"fieldname": "value",
				"fieldtype": "Data",
				"reqd": 1
			}];
		} else if ($.isPlainObject(this.fields)) {
			this.fields = [this.fields];
		}
	}

	make() {
		this.prompt = new frappe.ui.Dialog({
			"fields": this.fields,
			"title": this.title || "Introduzca el valor"
		});

		this.autoshow && this.prompt.show();
	}

	set_primary_action() {
		this.prompt.set_primary_action(this.primary_label || "Enviar", () => {
			let values = this.prompt.get_values();
			if ( ! values) {
				frappe.throw("¡No hay data para enviar!");
			}


			this.hide_after_request || this.prompt.hide();
			this.callback && this.callback(values);
		});
	}

	set_onhide_action() {
		this.prompt.onhide = () => {
			this.onhide && this.onhide();
			console.log("hidden")
		}
	}

	show() {
		this.before_show && this.before_show();
		this.prompt && this.prompt.show();
		this.after_show && this.after_show();
	}

	hide() {
		this.before_hide && this.before_hide();
		this.prompt && this.prompt.hide();
		this.after_hide && this.after_hide();
	}
}
