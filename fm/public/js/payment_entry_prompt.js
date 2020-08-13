// import BasePrompt from assets.fm.js.base_prompt

class PaymentEntryPrompt extends BasePrompt {
	constructor(opts) {
		super(opts) && frappe.run_serially([
			() => this.init(opts),
			() => this.find_next_pagare(),
			() => this.setup(opts),
			() => this.setup_parent(this.args)
		]) 
	}

	init(opts) {
		this.doc = opts.frm.doc;
	}

	find_next_pagare() {
		this.next_pagare = $.grep(cur_frm.doc.repayment_schedule, (value) => {
			return value.estado != "SALDADA"; 
		})[0];
	}

	setup(opts) {
		this.args = {
			"title": this.get_title(),
			"fields": this.setup_fields(),
			"callback": this.callback,
			"primary_label": this.get_primary_label(),
			"hide_after_request": this.hide_prompt_after_request(),
			"autoshow": true
		};

		$.extend(this.args, opts);
	}

	setup_parent(args) {
		super.init(args);
	}

	get_title() {
		return "Formulario de Recibo de Ingreso";
	}

	get_primary_label() {
		return "Enviar";
	}

	hide_prompt_after_request() {
		return true;
	}

	callback(data) {
		frappe.confirm("¿Desear crear una Entrada de Pago?", () => {

			// method to be executed in the server
			let opts = {
				"method": "fm.accounts.make_payment_entry"
			}

			$.extend(data, {
				"doctype": this.frm.doctype,
				"docname": this.frm.docname,
				"capital_amount": this.next_pagare.capital,
				"interest_amount": this.next_pagare.interes,
				"paid_amount": flt(data.paid_amount) + flt(data.fine_discount),
			});

			opts.args = { "opts": data };

			frappe.call(opts).then(() => {
				frappe.run_serially([
					() => frappe.show_alert("Entrada de pago creada", 9),
					() => frappe.utils.play_sound("submit"),
					() => this.frm.reload_doc(),
					() => frappe.timeout(2.5),
					() => frappe.hide_msgprint()
				]);
				
				frappe.set_route("List", "Journal Entry", { 
					"loan": this.frm.docname,
					"es_un_pagare": "1"
				});
			}, () => frappe.msgprint("¡Hubo un problema mientras se creaba la Entrada de Pago!"));
		}, () => this.show());
	}

	setup_fields() {
		return [{
			"fieldname": "paid_amount",
			"fieldtype": "Float",
			"label": __("Monto Recibido ({0})", [this.customer_currency]),
			"reqd": 1,
			"precision": 2,
			"default": this.next_pagare.monto_pendiente
		}, {
			"fieldname": "mode_of_payment",
			"fieldtype": "Select",
			"label": "Modo de Pago",
			"reqd": "1",
			"options": this.get_mode_of_payment_options(),
			"default": "Cash Entry"
		}, {
			"fieldname": "reference_name",
			"fieldtype": "Data",
			"label": "Referencia",
		}, {
			"fieldname": "reference_date",
			"fieldtype": "Date",
			"label": "Fecha de Referencia",
			"default": frappe.datetime.now_date()
		}, {
			"fieldname": "payment_section",
			"fieldtype": "Column Break"
		}, {
			"fieldname": "repayment_idx",
			"fieldtype": "Int",
			"label": __("Pagare No."),
			"read_only": 1,
			"default": this.next_pagare.idx
		}, {
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"label": "Fecha de Posteo",
			"default": frappe.datetime.get_today()
		}, {
			"fieldname": "has_gps",
			"label": "Agregar GPS",
			"fieldtype": "Check",
			"default": 0
		}, {
			"fieldname": "has_recuperacion",
			"label": "Agregar Recuperacion",
			"fieldtype": "Check",
			"default": 0
		}, {	
			"fieldname": "add_user_remarks",
			"label": "Agregar Notas",
			"fieldtype": "Check",
			"default": 0
		}, {	
			"fieldname": "validate_payment_entry",
			"label": "Validar Entrada de Pago",
			"fieldtype": "Check",
			"default": 1
		}, {
			"fieldname": "fine_section",
			"hidden": ! flt(this.next_pagare.fine_amount),
			"fieldtype": "Section Break"
		}, {
			"fieldname": "fine",
			"fieldtype": "Currency",
			"label": __("Mora ({0})", [this.customer_currency]),
			"precision": 2,
			"read_only": 1,
			"default": this.next_pagare.fine_amount || 0.000
		}, {
			"fieldname": "discount_column",
			"fieldtype": "Column Break"
		}, {
			"fieldname": "fine_discount",
			"fieldtype": "Currency",
			"label": __("Descuento a Mora ({0})", [this.doc.customer_currency]),
			"default": 0.000,
			"precision": 2,
			"default": this.next_pagare.fine_discount || 0.000,
			"read_only": 1
		}, {
			"label": "Miscelaneos",
			"fieldname": "miscelaneos",
			"fieldtype": "Section Break",
		}, {
			"fieldname": "gps",
			"fieldtype": "Float",
			"label": "GPS (DOP)", 
			"default": 0.000,
			"precision": 2,
		}, {
			"fieldname": "expenses_column",
			"fieldtype": "Column Break",
		}, {
			"fieldname": "gastos_recuperacion",
			"fieldtype": "Float",
			"label": "Gastos  de Recuperacion (DOP)",
			"default": 0.000,
			"precision": 2,
		}, {
			"fieldtype": "Section Break"
		}, {
			"fieldname": "insurance_amount",
			"fieldtype": "Float",
			"label": __("Monto Seguro (DOP)"),
			"default": this.next_pagare.insurance || 0.000,
			"hidden": ! this.next_pagare.insurance || 0,
			"precision": 2,
		}, {
			"fieldname": "pending_insurance_amount",
			"fieldtype": "Currency",
			"label": __("Pendiente de Seguro (DOP)"),
			"read_only": 1,
			"precision": 2,
			"hidden": ! this.next_pagare.insurance || 0,
			"default": this.next_pagare.insurance || 0.000
		}, 
		{
			"fieldname": "repayment_section",
			"fieldtype": "Column Break"
		}, {
			"fieldname": "pending_amount",
			"fieldtype": "Currency",
			"label": __("Monto del Pendiente ({0})", [this.customer_currency]),
			"read_only": 1,
			"precision": 2,
			"default": this.next_pagare.monto_pendiente
		}, {
			"fieldname": "repayment_amount",
			"fieldtype": "Currency",
			"label": __("Monto del Pagare ({0})", [this.customer_currency]),
			"read_only": 1,
			"precision": 2,
			"default": this.next_pagare.cuota
		},
		{
			"fieldname": "remarks_section",
			"fieldtype": "Section Break"
		},
		{
			"fieldname": "user_remark",
			"fieldtype": "Text",
			"label": "NOTAS DE USUARIO",
		}];
	}

	get_mode_of_payment_options() {
		return [
			{ "value": "Cash Entry", "label": "Efectivo" },
			{ "value": "Journal Entry", "label": "Asiento Contable" },
			{ "value": "Bank Entry", "label": "Transferencia" },
			{ "value": "Bank Entry", "label": "Cheque" },
			{ "value": "Bank Entry", "label": "Deposito Bancario" },
			{ "value": "Credit Card Entry", "label": "Tarjeta de Credito" },
			{ "value": "Debit Note", "label": "Nota de Debito" },
			{ "value": "Credit Note", "label": "Nota de Credito" },
		];
	}
}