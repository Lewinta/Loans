//Copyright (c) 2017, Soldeva, SRL and contributors
// For license information, please see license.txt

frappe.ui.form.on('Loan', {
	"setup": (frm) => frm.add_fetch("customer", "default_currency", "customer_currency"),
	"onload": (frm) => {
		// to filter some link fields
		frm.trigger("set_queries");

		if (!frappe.user.has_role(["System Manager", "Gerente de Operaciones"]))
			frm.set_df_property("branch_office", "read_only", 1);

		if (["Approved", "Linked"].includes(frm.doc.status)) {
			frm.set_value("status", "Sanctioned");
		}

		// let's clear the prompts
		frappe.run_serially([
			() => frm.payment_entry_prompt = undefined,
			() => frm.add_fine_prompt = undefined,
			() => frm.clean_fine_prompt = undefined
		]);

	},
	"onload_post_render": (frm) => {
		frappe.db.get_value("Currency Exchange", {
			"from_currency": "USD",
			"to_currency": "DOP"
		}, "exchange_rate").then(({
			message
		}) => {
			frm.doc.exchange_rate = message.exchange_rate
		}, (exec) => {
			frappe.msgprint("Hubo un problema mientras se cargaba la tasa de conversion de\
				Dolar a Peso.<br>Favor de contactar su administrador de sistema!")
		});

	},
	"refresh": (frm) => {
		// let cur_user = frappe.boot.user.email;
		let cur_user = frappe.session.user;
		frm.doc._dev_hide = 0;
		frappe.db.get_value("FM Configuration", "FM Configuration", "developer_mode")
			.then((data) => {
				frm.doc._dev_hide = eval(data.developer_mode) ? 0 : 1;
			});

		$.map([
			"needs_to_refresh",
			"toggle_fields",
			"add_buttons",
			"beautify_repayment_table",
		], (event) => frm.trigger(event));

		frm.set_df_property("repayment_periods", "read_only", true);
		allowed_users = [
		"keylaali@hotmail.com",
		"Administrator"
		]
		if (!allowed_users.includes(cur_user) ) {
			frm.fields_dict.loan_referral.df.read_only = 1;
			frm.refresh_fields();
		}
	},
	"validate": (frm) => frm.trigger("setup"),
	"needs_to_refresh": (frm) => {
		// check if it's a new doc
		if (frm.is_new()) {
			return 0; // let's just ignore it
		}

		let opts = {
			"method": "frappe.client.get_value"
		};

		opts.args = {
			"doctype": frm.doctype,
			"filters": {
				"name": frm.docname,
			},
			"fieldname": ["modified"]
		};

		// check the last time it was modified in the DB
		// //Was causing issues commented by LV
		// frappe.call(opts).then((response) => {
		// 	if (response && doc)
		// 		frm.doc.modified != response.message.modified && frm.reload_doc();
		// });
	},
	"gross_loan_amount": (frm) => {
		let expense_rate_dec = flt(frm.doc.legal_expense_rate / 100.000);
		frm.set_value("loan_amount", frm.doc.gross_loan_amount * (expense_rate_dec + 1.000));
	},
	"disbursement_date": (frm) => {
		if (frm.doc.disbursement_date) {
			frm.set_value("entrega_voluntaria", frm.doc.disbursement_date);
		}
	},
	"make_jv": (frm) => {
		frm.call("make_jv_entry", "args").then((response) => {
			let doc = response.message;

			doc && frappe.model.sync(doc);

			frappe.set_route(["Form", doc.doctype, doc.name]);
		}, (exec) => frappe.msgprint("¡Ooops... algo salió mal!"));
	},
	"mode_of_payment": (frm) => {

		// check to see if the mode of payment is set
		if (!frm.doc.mode_of_payment) {
			return 0; // let's just ignore it
		}

		let opts = {
			"method": "erpnext.accounts.doctype.sales_invoice.sales_invoice.get_bank_cash_account"
		};

		opts.args = {
			"mode_of_payment": frm.doc.mode_of_payment,
			"company": frm.doc.company
		};

		// ok, now we're ready to send the request
		frappe.call(opts).then((response) => {
			// set the response body to a local letiable
			let data = response.message;

			// let's set the value
			frm.set_value("payment_account", frm.doc.customer_currency == "DOP" ?
				data.account : data.account.replace("DOP", "USD"));
		}, (exec) => frappe.msgprint("¡Hubo un problema mientras se cargaban las cuentas!"));
	},
	"set_account_defaults": (frm) => {
		// this method fetch the default accounts from
		// the FM Configuration panel if it exists


		// the method that we're going to execute in the server
		let opts = {
			"method": "frappe.client.get"
		};

		// and the arguments that it requires
		opts.args = {
			"doctype": "FM Configuration",
			"name": "FM Configuration"
		};

		frappe.call(opts).then((response) => {

			// set the response body to a local letiable
			let conf = response.message;

			// set the response doc object to a local letiable
			let fields = [
				"mode_of_payment",
				"payment_account",
				"expenses_account",
				"customer_loan_account",
				"interest_income_account",
				"disbursement_account"
			];

			// set the values
			$.map(fields, (field) => {
				// check to see if the field has value

				let account = frm.doc.customer_currency != "DOP" ?
					conf[field].replace("DOP", "USD") : conf[field];

				// it has no value, then set it
				frm.set_value(field, account);
			});
		}, (exec) => frappe.msgprint("¡Hubo un problema mientras se cargaban las cuentas!"));
	},
	"loan_application": (frm) => {
		// exit the function and do nothing
		// if loan application is triggered but has not data
		if (!frm.doc.loan_application) {
			return 0; // let's just ignore it
		}

		let opts = {
			"method": "fm.finance_manager.doctype.loan.loan.get_loan_application"
		}

		opts.args = {
			"loan_application": frm.doc.loan_application
		}

		frm.call(opts).then((response) => {
			let loan_application = response.message;

			// exit the callback if no data came from the SV
			if (!loan_application) {
				return 0; // let's just ignore it
			}

			$.map([
				"loan_type",
				"loan_amount",
				"repayment_method",
				"monthly_repayment_amount",
				"repayment_periods",
				"rate_of_interest"
			], (field) => frm.set_value(field, loan_application[field]));
		}, () => frappe.msgprint("¡Hubo un problema mientras se carga la Solicitud de Prestamo!"));
	},
	"customer": (frm) => frm.trigger("set_account_defaults"),
	"repayment_method": (frm) => frm.trigger("toggle_fields"),
	"toggle_fields": (frm) => {
		frm.toggle_enable("monthly_repayment_amount",
			frm.doc.repayment_method == "Repay Fixed Amount per Period");

		frm.toggle_enable("repayment_periods",
			frm.doc.repayment_method == "Repay Over Number of Periods");

		frm.trigger("fix_table_header")
	},
	"update_payment_date": (frm) => {

		let new_disbursement_fields = [{
			"fieldname": "disbursement_date",
			"fieldtype": "Date",
			"label": "Nueva Fecha de Desembolso",
			"bold": 1,
			"default": frm.doc.disbursement_date,
		}, {
			"fieldtype": "HTML",
			"options": "</b>Seleccione la nueva fecha de desembolso y el sistema actualizara las fechas de las cuotas a partir de esa fecha.</b>"
		}];

		let _submit = () => {
			frm.call("update_payment_date", {
				"disbursement_date": frm.update_disbursement_prompt.get_value("disbursement_date")
			}, (data) => {
				//
			});
			frappe.show_alert("Prestamo Actualizado Correctamente!");

			setTimeout(function () {
				frm.reload_doc();
			}, 1500);

		};

		frm.update_disbursement_prompt = frappe.prompt(new_disbursement_fields, _submit, __("Cambiar Fecha Cuotas"), "Cambiar");

	},
	"adjust_repayment_date": (frm) => {
		// old code
		// let found = false;
		// let cur_idx = ""
		// let cur_date = frappe.datetime.get_today().substring(0,7)
		// $.map(frm.doc.repayment_schedule, (value) => {

		// 	// if there's no one found yet
		// 	if ( ! found && value.fecha.substring(0,7) == cur_date) {
		// 		console.log(value.fecha)
		// 		found = true; // set the flag to true
		// 		cur_idx = value.idx; // and set the value
		// 	}
		// });
		let grace_periods = frappe.boot.fm_configuration.grace_days;
		let cur_idx = "";
		let today = frappe.datetime.nowdate();

		$.map(cur_frm.doc.repayment_schedule, ({fecha, idx, estado}) => {
			due_date = frappe.datetime.add_days(fecha, grace_periods);
			if (!cur_idx && due_date >= today && (estado == "ABONO" || estado == "PENDIENTE")) {
				cur_idx = idx;
			}
		})
		let next_date = frm.doc.repayment_schedule[cur_idx - 1].fecha

		let balance_fields = [{
			"fieldname": "next_pagare",
			"fieldtype": "Date",
			"label": "Nueva Fecha",
			"bold": true,
			//"default": next_date,
			"default": "2018-09-28",
		}, {
			"field_name": "idx",
			"fieldtype": "Int",
			"label": "Idx",
			// "hidden": true,
			"default": cur_idx,
			
		}, {
			"fieldtype": "HTML",
			"options": "Esta opción cambiara la fecha de la próxima cuota <u><b>no vencida</b></u> y las cuotas siguientes."
		}];

		let _submit = () => {
			
			_np = frm.new_date_prompt.get_value("next_pagare");
			_idx = frm.new_date_prompt.get_value("idx");
			console.log("309 " + _np + " \n " + _idx);

			let args = {
				"next_date": cur_frm.new_date_prompt.get_value("next_pagare"),
				"idx": cur_frm.new_date_prompt.get_value("idx")
			} 

			frm.call("update_next_payment_date", args, (data) => {
				//
			});

			frappe.show_alert("Fechas Actualizadas Correctamente!");
			setTimeout(function () {
				frm.reload_doc();
			}, 1000);

		};

		frm.new_date_prompt = frappe.prompt(balance_fields, _submit, __("Actualizar Fecha del Proximo Pago"), "Cambiar");


		//balance_prompt.show();

	},
	"clean_fines": (frm) => {

		fields = [{
			"fieldtype": "HTML",
			"options": "Se borraran las moras de todos los Pagares con estado PENDIENTE",
		}];

		let onsubmit = () => {

			frappe.confirm("¿Borrar todas las moras?", () => {

				let opts = {
					"method": "fm.utilities.clean_all_fines"
				}

				opts.args = {
					"loan": frm.docname
				}

				frappe.call(opts).then((response) => {
					// let the user know that it was succesfully created
					frappe.show_alert(__("Mora eliminadas correctamente"), 9);

					// let's play a sound for the user
					frappe.utils.play_sound("submit");

					// clear the prompt
					frm.reload_doc();
				});
			}, () => frm.clean_fine_prompt.show());
		}

		// let's check if object is already set
		if (frm.clean_fine_prompt) {

			// it is set at this point
			// let's just make it visible
			frm.clean_fine_prompt.show()
		} else {

			// there was not object, so we need to create it
			frm.clean_fine_prompt = frappe.prompt(fields, onsubmit, __("Eliminar todas las Moras"), "Eliminar");
		}
	},
	"sync_repayment": (frm) => {
		let cuotas ='';
		
		$.map(cur_frm.doc.repayment_schedule, row =>{
			if (frappe.session.user == 'Administrator'){
				cuotas += row.idx + "\n"
				return
			}
			if(row.estado != "SALDADA")
				cuotas += row.idx + "\n"
		});

		fields = [{
			"fieldname": "repayment",
			"fieldtype": "Select",
			"label": __("Cuota"),
			"reqd": 1,
			"options": cuotas,
			"default": cuotas.split("\n")[0],
			"description": "Ingresar la cuota a sincronizar con el historico."
		},{
			"fieldname": "cb",
			"fieldtype": "Column Break",
		},{
			"fieldname": "date",
			"fieldtype": "Date",
			"label": __("Date"),
			"description": "Colocar una fecha si solo necesita actualizar la cuota a una fecha en especifico, de lo contrario dejelo en blanco."
		}];

		// finishes introducing the values
		let onsubmit = (data) => {

			frappe.confirm("¿Desea continuar?", () => {

				// method to be executed in the server
				let opts = {
					"method": "fm.utilities.sync_row"
				};

				opts.args = {
					"loan": frm.docname,
					"idx": data.repayment,
					"date": data.date,
				};

				frappe.call(opts).then((response) => {
					// let the user know that it was succesfully created
					frappe.show_alert(__("Cuota sincronizada correctamente"), 9);

					// let's play a sound for the user
					frappe.utils.play_sound("submit");

					// clear the prompt
					frm.reload_doc();
				});
			}, () => frm.add_fine_prompt.show());
		}
		
		frappe.prompt(fields, onsubmit, __("Sincronizar Cuota?"), "Sincronizar").show();

	},"add_fines": (frm) => {
		fields = [{
			"fieldname": "repayment",
			"fieldtype": "Int",
			"label": __("Cuota"),
			"reqd": 1
		}, {
			"fieldname": "cb1",
			"fieldtype": "Column Break",
			"label": ""
		}, {
			"fieldname": "fine",
			"fieldtype": "Float",
			"label": "Mora",
			"description": "Ingresar monto con signo negativo para reducir mora.",
			"reqd": "1"
		}, {
			"fieldname": "mora_acumulada",
			"fieldtype": "Float",
			"label": "Mora Acumulada",
			"description": "Ingresar monto con signo negativo para reducir mora.",
			"reqd": "1"
		}];

		// finishes introducing the values
		let onsubmit = (data) => {

			frappe.confirm("¿Desea continuar?", () => {

				// method to be executed in the server
				let opts = {
					"method": "fm.utilities.add_fine"
				};

				opts.args = {
					"loan": frm.docname,
					"cuota": data.repayment,
					"mora": data.fine,
					"mora_acumulada": data.mora_acumulada
				};

				frappe.call(opts).then((response) => {
					// let the user know that it was succesfully created
					frappe.show_alert(__("Mora agregada correctamente"), 9);

					// let's play a sound for the user
					frappe.utils.play_sound("submit");

					// clear the prompt
					frm.reload_doc();
				});
			}, () => frm.add_fine_prompt.show());
		}

		// let's check if object is already set
		if (frm.add_fine_prompt) {

			// it is set at this point
			// let's just make it visible
			frm.add_fine_prompt.show();
		} else {

			// there was not object, so we need to create it
			frm.add_fine_prompt = frappe.prompt(fields, onsubmit, __("Agregar Mora"), "Agregar");
		}
	},
	"conductor_alterno": (frm) =>{
		console.log("clicked");
		if (frm.doc.conductor_alterno == 0){
			frm.set_value("nombre_del_conductor", "");
			frm.set_value("cedula_conductor", "");
		}
		frm.dirty(); 

	},
	"add_buttons": (frm) => {
		if (!frm.is_new()) {
			frm.add_custom_button("Refrescar", () =>{
				frm.call("reload_disbursement_status", () => {
					frappe.show_alert("Prestamo actualizado", [10, "green"]);
					setTimeout(()=>{
						frm.reload_doc()
					},1000) 
				});
			});
		}
		if (frm.doc.docstatus == 1) {
			frm.add_custom_button("Actualizar Info", () =>{
				frm.call("update_customer_info", () => {
					frappe.show_alert("Informacion actualizada", [10, "green"]);
					frm.dirty();
				});
			});
		}

		if (frm.doc.docstatus == 1) {
			frm.add_custom_button(__("Sincronizar"), () => frm.trigger("sync_repayment"));
		}

		// validate that the document is submitted
		if (!frm.doc.docstatus == 1) {
			return 0; // exit code is zero
		}
		status_list = ['Legal', 'Recuperado', 'Pending', "Incautado", "Perdida Total", "Taller", "Detenido", "Disponible", "Intimado"]

		
		if (frm.doc.status == "Fully Disbursed") {
			
			$.map(status_list, st =>{
				frm.add_custom_button(
					__(st),
					() => {

						frm.set_value("old_status", frm.doc.status);
						frm.set_value("status", st);
						frm.set_value("new_status", frm.doc.status);
						frm.save("Update").then(
							() => frm.call("comment_loan_status_changed").then(
								() => frm.call("remove_loan_from_portfolio")
							)
						)
					},
					"Cambiar estado"
				)
			})
		}

		if (["Recuperado", "Legal", "Pending", "Incautado", "Perdida Total", "Taller", "Intimado"].includes(frm.doc.status)) {
			frm.add_custom_button(
				__('Reanudar'),
				() => {
					frm.set_value("old_status", frm.doc.status);
					frm.set_value("status", "Fully Disbursed");
					frm.set_value("new_status", frm.doc.status);
					frm.save("Update");
					frm.call("comment_loan_status_changed");
				},
				"Cambiar estado"
			);
		}

		frm.add_custom_button('Desembolso', () => {
			frappe.db.get_value("Journal Entry", {
				"loan": frm.docname,
				"docstatus": ["!=", 2]
			}, "name").then((data) => {
				frappe.set_route("List", "Journal Entry", {
					"loan": frm.docname,
					"es_un_pagare": "0"
				});
			}, () => frappe.throw("¡No se encontro ningún desembolso para este prestamo!"));
		}, "Ver");

		frm.add_custom_button(__('Payment Entry'), () => {
			frappe.set_route("List", "Journal Entry", {
				"loan": frm.docname,
				"es_un_pagare": "1"
			});
		}, "Ver");

		frm.add_custom_button(__('Balance para saldar'), () => frm.trigger("show_closing_balance"), "Ver");


		frm.add_custom_button('Agregar', () => frm.trigger("add_fines"), "Mora");
		// frm.add_custom_button('Borrar', () => frm.trigger("clean_fines"), "Mora");

		if (frm.doc.status != "Repaid/Closed") {
			frm.add_custom_button('Cambiar Fecha Cuotas', () => frm.trigger("update_payment_date"), "Fecha");
			frm.add_custom_button('Ajustar Proximo Pago', () => frm.trigger("adjust_repayment_date"), "Fecha");

		}

		if (["Partially Disbursed", "Sanctioned"].includes(frm.doc.status)) {
			frm.add_custom_button(__('Disbursement Entry'), () => frm.trigger("make_jv"), "Hacer")
		}

		if ( ["Fully Disbursed", "Legal", "Incautado", "Intimado"].includes(frm.doc.status)) {
			frm.add_custom_button('Entrada de Pago', () => frm.trigger("make_payment_entry"), "Hacer");
		}

		frm.add_custom_button(__('Poliza de Seguro'), () => {
			frappe.set_route("List", "Poliza de Seguro", {
				"loan": frm.docname,
				"status": "Activo"
			});
		}, "Hacer");

		frm.add_custom_button(__('GPS'), () => {
			frappe.set_route("List", "GPS", {
				"loan": frm.docname,
				"vehicle": frm.doc.asset,
				"branch_office": frm.doc.branch_office,
			});
		}, "Hacer");

		frm.page.set_inner_btn_group_as_primary("Hacer");
	},
	"set_queries": (frm) => {
		let root_types = {
			"interest_income_account": "Income",
			"expenses_account": "Income",
			"payment_account": "Asset",
			"customer_loan_account": "Asset"
		};

		let fields = [
			"interest_income_account", "expenses_account",
			"payment_account", "customer_loan_account"
		];

		$.map(fields, function (field) {
			frm.set_query(field, () => {
				return {
					"filters": {
						"company": frm.doc.company,
						"root_type": root_types[field],
						"is_group": 0
					}
				};
			});
		});

		frm.set_query("loan_application", () => {
			return {
				"filters": {
					"docstatus": 1,
					"status": "Approved",
					"status": ["!=", "Linked"]
				}
			};
		});
	},
	"fix_table_header": (frm) => {
		setTimeout(() => {
			$("[data-fieldname=repayment_schedule] \
				[data-fieldname=fecha]")
				.css("width", "14%");

			$("[data-fieldname=repayment_schedule] \
				[data-fieldname=cuota]")
				.css("width", "9%");

			$("[data-fieldname=repayment_schedule] \
				[data-fieldname=balance_capital]")
				.css("width", "9%");

			$("[data-fieldname=repayment_schedule] \
				[data-fieldname=balance_interes]")
				.css("width", "9%");

			$("[data-fieldname=repayment_schedule] \
				[data-fieldname=capital_acumulado]")
				.css("width", "9%");

			$("[data-fieldname=repayment_schedule] \
				[data-fieldname=interes_acumulado]")
				.css("width", "9%");

			$("[data-fieldname=repayment_schedule] \
				[data-fieldname=pagos_acumulados]")
				.css("width", "9%");

			$("[data-fieldname=repayment_schedule] \
				[data-fieldname=estado]")
				.css("width", "14%");

			$("[data-fieldname=repayment_schedule] \
				.close.btn-open-row").parent()
				.css("width", "5%");

			$("[data-fieldname=repayment_schedule] \
				.grid-heading-row .col.col-xs-1")
				.css("height", 60);

			$("[data-fieldname=repayment_schedule] \
				.grid-heading-row .col.col-xs-2")
				.css("height", 60);

			$("[data-fieldname=repayment_schedule] [data-fieldname=fecha] \
				.static-area.ellipsis:first")
				.html("<br>Fecha");

			$("[data-fieldname=repayment_schedule] [data-fieldname=cuota] \
				.static-area.ellipsis:first")
				.html("<br>Cuota");

			$("[data-fieldname=repayment_schedule] [data-fieldname=balance_capital] \
				.static-area.ellipsis:first")
				.html("Bal.<br>Capital");

			$("[data-fieldname=repayment_schedule] [data-fieldname=balance_interes] \
				.static-area.ellipsis:first")
				.html("Bal.<br>Comision");

			$("[data-fieldname=repayment_schedule] [data-fieldname=capital_acumulado] \
				.static-area.ellipsis:first")
				.html("Capital<br>Acum.");

			$("[data-fieldname=repayment_schedule] [data-fieldname=interes_acumulado] \
				.static-area.ellipsis:first")
				.html("Comision<br>Acum.");

			$("[data-fieldname=repayment_schedule] [data-fieldname=pagos_acumulados] \
				.static-area.ellipsis:first")
				.html("Pagos<br>Acum.");

			$("[data-fieldname=repayment_schedule] [data-fieldname=estado] \
				.static-area.ellipsis:first")
				.html("<br>Estado");
		});
	},
	"beautify_repayment_table": (frm) => {
		setTimeout(() => {

			// let's prepare the repayment table's apereance for the customer
			let fields = $("[data-fieldname=repayment_schedule] \
				[data-fieldname=estado] > .static-area.ellipsis");

			// ok, now let's iterate over map row
			$.map(fields, (value) => {

				let color = "grey";
				let field = $(value);

				// let's remove the previous css class
				clear_class(field);

				if ("SALDADA" == field.text()) {
					color = "green";
				} else if ("ABONO" == field.text()) {
					color = "blue";
				} else if ("PENDIENTE" == field.text()) {
					color = "orange";
				} else if ("VENCIDA" == field.text()) {
					color = "red";
				}

				field.addClass(__("indicator {0}", [color]));
			});
		});

		let clear_class = (field) => {
			$.map(["green", "blue", "orange", "red"], (css_class) => {
				field.removeClass(__("indicator {0}", [css_class]));
			});
		}
	},
	"show_closing_balance": (frm) => {

		frm.call("get_balance_to_close", {
			"doctype": frm.doctype
		}, (data) => {
			let _submit = () => {
				frm.trigger("make_payment_entry");
				setTimeout(function () {
					frm.payment_entry_prompt.set_value("paid_amount", frm.balance_prompt.fields_dict.min_payment.value);
					frm.payment_entry_prompt.set_value("other_discounts", frm.balance_prompt.fields_dict.max_discount.value);
				}, 1500)
			}

			if (data && data.message) {
				data = data.message;
				let balance_fields = [{
					"fieldname": "capital",
					"fieldtype": "Currency",
					"label": "Total Capital",
					"default": data.capital.toFixed(2),
					"precision": 2,
					"read_only": 1,
				}, {
					"fieldname": "comision",
					"fieldtype": "Currency",
					"label": "Comision Pendiente",
					"default": data.interes.toFixed(2),
					"precision": 2,
					"read_only": 1
				}, {
					"fieldname": "comision_vencida",
					"fieldtype": "Currency",
					"label": "Comision Vencida Pendiente",
					"default": data.interes_vencido.toFixed(2),
					"precision": 2,
					"read_only": 1
				},
				// {
				// 	"fieldname": "total_pending",
				// 	"fieldtype": "Currency",
				// 	"label": "Total Pendiente",
				// 	"default": data.pendiente.toFixed(2),
				// 	"precision": 2,
				// 	"read_only": 1,
				// },
				 {
					"fieldname": "cb_1",
					"fieldtype": "Column Break",
				}, {
					"fieldname": "fine",
					"fieldtype": "Currency",
					"label": "Mora Pendiente",
					"default": data.fine.toFixed(2),
					"precision": 2,
					"read_only": 1
				}, {
					"fieldname": "insurance",
					"fieldtype": "Currency",
					"label": "Seguro",
					"default": data.insurance.toFixed(2),
					"precision": 2,
					"read_only": 1
				}, {
					"fieldname": "grand_total",
					"fieldtype": "Currency",
					"label": "Total Pendiente",
					"default": data.pendiente.toFixed(2),
					"precision": 2,
					"read_only": 1
				}, {
					"fieldname": "sb_2",
					"fieldtype": "Section Break",
				}, {
					"fieldname": "include_capital",
					"fieldtype": "Check",
					"label": "Capital",
					"default": 1,
					"read_only": 1,
					"onchange": () => frm.trigger("calculate_closing_balance")
				}, {
					"fieldname": "include_expired_interest",
					"fieldtype": "Check",
					"label": "Comision Vencida",
					"default": 1,
					"onchange": () => {
						let fields_data = frm.balance_prompt.fields_dict;
						
						if(fields_data.include_expired_interest.get_input_value() == fields_data.include_interest.get_input_value() && fields_data.include_interest.get_input_value() == 1)
							frm.balance_prompt.set_value("include_expired_interest", 0);

						frm.trigger("calculate_closing_balance");
					}
				},{
					"fieldname": "include_interest",
					"fieldtype": "Check",
					"label": "Comision",
					"default": 0,
					"onchange": () => {
						let fields_data = frm.balance_prompt.fields_dict;
						
						if(fields_data.include_expired_interest.get_input_value() == fields_data.include_interest.get_input_value() && fields_data.include_interest.get_input_value() == 1)
							frm.balance_prompt.set_value("include_interest", 0);
						
						frm.trigger("calculate_closing_balance");
					}
				}, {
					"fieldname": "cb_2",
					"fieldtype": "Column Break",
				},  {
					"fieldname": "include_fine",
					"fieldtype": "Check",
					"label": "Mora",
					"default": 1,
					"onchange": () => frm.trigger("calculate_closing_balance")
				}, {
					"fieldname": "include_insurance",
					"fieldtype": "Check",
					"label": "Seguro",
					"default": 1,
					"read_only": 1,
					"onchange": () => frm.trigger("calculate_closing_balance")
				}, {
					"fieldname": "sb_3",
					"fieldtype": "Section Break",
				}, {
					"fieldname": "min_payment",
					"fieldtype": "Currency",
					"label": "Pago Minimo",
					"default": (data.capital + data.interes_vencido + data.fine + data.insurance).toFixed(2),
					"precision": 2,
					"onchange": () => {
						let min_payment = frm.balance_prompt.fields_dict.min_payment.value
						let pendiente = frm.balance_prompt.fields_dict.grand_total.value

						frm.balance_prompt.set_value("max_discount", pendiente - min_payment)
					}
				}, {
					"fieldname": "cb_3",
					"fieldtype": "Column Break",
				}, {
					"fieldname": "max_discount",
					"fieldtype": "Currency",
					"label": "Descuento Maximo",
					"default": data.interes.toFixed(2),
					"precision": 2,
					"read_only": 1,
					// "onchange": () => {
					// 	let max_discount = frm.balance_prompt.fields_dict.max_discount.value
					// 	let pendiente = frm.balance_prompt.fields_dict.capital.value

					// 	frm.balance_prompt.set_value("min_payment", pendiente - max_discount)

					// }
				}]

				frm.balance_prompt = frappe.prompt(balance_fields, _submit, __("Balance para saldar prestamo"), "Hacer Pago");
			}

			//balance_prompt.show();
		});

	},
	calculate_closing_balance: frm => {
		let min_payment  = 0.00;
		let max_discount = 0.00;

		// if(frm.balance_prompt.fields_dict.include_capital.get_input_value())
		min_payment += flt(frm.balance_prompt.fields_dict.capital.value);
		
		if(frm.balance_prompt.fields_dict.include_expired_interest.get_input_value())
			min_payment += flt(frm.balance_prompt.fields_dict.comision_vencida.value);

		if(frm.balance_prompt.fields_dict.include_interest.get_input_value())
			min_payment += flt(frm.balance_prompt.fields_dict.comision.value);

		if(frm.balance_prompt.fields_dict.include_fine.get_input_value())
			min_payment += flt(frm.balance_prompt.fields_dict.fine.value);

		// if(frm.balance_prompt.fields_dict.include_insurance.get_input_value())
		min_payment += flt(frm.balance_prompt.fields_dict.insurance.value);

						
		frm.balance_prompt.set_value("min_payment", min_payment);
		frm.balance_prompt.set_value("max_discount", frm.balance_prompt.fields_dict.capital.grand_total - min_payment);
	},
	"make_payment_entry": (frm) => {
		let read_only_discount = !!!frappe.user.has_role("Gerente de Operaciones");

		let currency = frm.doc.customer_currency

		// let next_cuota = undefined
		let next_pagare = undefined;

		let total_pending = 0.00;
		let total_fine = 0.00;
		let total_insurance = 0.00;
		$.map(frm.doc.repayment_schedule, (value) => {
			if(!["SALDADA", "PENDIENTE"].includes(value.estado)){
				total_pending += flt(value.monto_pendiente);
				total_fine += flt(value.fine);
				total_insurance += flt(value.insurance);
			}

		});

		// let found = false;
		// $.map(frm.doc.repayment_schedule, (value) => {

		// 	// if there's no one found yet
		// 	if (!found && value.estado != "SALDADA") {
		// 		// means that this is the first one PENDING

		// 		found = true; // set the flag to true
		// 		next_pagare = value; // and set the value
		// 	}
		// });

		// set the fine amount if there is one
		// let fine_amount = !next_pagare.fine ? 0 : next_pagare.fine;
		// let fine_discount = !next_pagare.fine_discount ? 0 : next_pagare.fine_discount;
		// let repayment_amount = !next_pagare.cuota ? frm.doc.monthly_repayment_amount : next_pagare.cuota;

		let get_mode_of_payment_options = () => {
			return [{
					"value": "Cash Entry",
					"label": "Efectivo"
				},
				{
					"value": "Journal Entry",
					"label": "Asiento Contable"
				},
				{
					"value": "Bank Transfer",
					"label": "Transferencia"
				},
				{
					"value": "Cheque",
					"label": "Cheque"
				},
				{
					"value": "Bank Entry",
					"label": "Deposito Bancario"
				},
				{
					"value": "Credit Card Entry",
					"label": "Tarjeta de Credito"
				},
				{
					"value": "Debit Note",
					"label": "Nota de Debito"
				},
				{
					"value": "Credit Note",
					"label": "Nota de Credito"
				},
			];
		};

		// these are the fields to be shown
		let fields = [{
				"fieldname": "paid_amount",
				"fieldtype": "Float",
				"label": "Monto Recibido (DOP)",
				"reqd": 1,
				"precision": 2,
				"description": "Monto recibido por parte del cliente (Incluyendo Gastos Recuperacion)",
				"default": total_pending
				// "default": next_pagare.monto_pendiente
			}, {
				"fieldname": "mode_of_payment",
				"fieldtype": "Select",
				"label": "Modo de Pago",
				"reqd": "1",
				"options": get_mode_of_payment_options(),
				"default": "Cash Entry",
			}, {
				"fieldname": "reference_name",
				"fieldtype": "Data",
				"label": "Referencia",
				"default": frappe.session.user == "marlenliam19@gmail.com" ? "POPULAR SWAT":""
			}, {
				"fieldname": "reference_date",
				"fieldtype": "Date",
				"label": "Fecha de Referencia",
				"default": frappe.datetime.now_date()
			}, {
				"fieldname": "payment_section",
				"fieldtype": "Column Break"
			}, 
			// {
			// 	"fieldname": "repayment_idx",
			// 	"fieldtype": "Int",
			// 	"label": __("Pagare No."),
			// 	"read_only": 1,
			// 	// "default": next_pagare.idx
			// },
			{
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
				"fieldname": "has_intimacion",
				"label": "Agregar Intimacion",
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
				"fieldtype": "Section Break"
			}, {
				"fieldname": "fine",
				"fieldtype": "Currency",
				"label": "Mora (DOP)",
				"precision": 2,
				"read_only": 1,
				"default": total_fine
				// "default": fine_amount ? fine_amount : 0.000
			}, {
				"fieldname": "discount_column",
				"fieldtype": "Column Break"
			}, {
				"fieldname": "fine_discount",
				"fieldtype": "Currency",
				"label": "Descuento a Mora (DOP)",
				"default": "0.000",
				"precision": 2,
				// "default": total_fine_discount,
				// "default": fine_discount ? fine_discount : 0.000,
				"read_only": 1
			}, {
				"fieldname": "other_discounts",
				"fieldtype": "Float",
				"label": "Otros descuentos (DOP)",
				"default": "0.000",
				"precision": 2,
				//"onchange": () => console.log("other_discounts changed")
			}, {
				"label": "Miscelaneos",
				"fieldname": "miscelaneos",
				"fieldtype": "Section Break",
			}, {
				"fieldname": "gastos_intimacion",
				"fieldtype": "Float",
				"label": "Gastos de Intimacion (DOP)",
				"default": "0.000",
				"description": "Debe ser considerado como parte del Monto Recibido",
				"precision": 2,
			}, {
				"fieldname": "expenses_column",
				"fieldtype": "Column Break",
			}, {
				"fieldname": "gastos_recuperacion",
				"fieldtype": "Float",
				"label": "Gastos  de Recuperacion (DOP)",
				"default": "0.000",
				"description": "Debe ser considerado como parte del Monto Recibido",
				"precision": 2,
			}, {
				"fieldname": "gps",
				"fieldtype": "Float",
				"label": "GPS (DOP)",
				"default": "0.000",
				"description": "Debe ser considerado como parte del Monto Recibido",
				"precision": 2,
			},{
				"fieldtype": "Section Break"
			}, {
				"fieldname": "insurance_amount",
				"fieldtype": "Float",
				"label": __("Monto Seguro (DOP)"),
				"default": total_insurance,
				"hidden": !total_insurance || 0,
				"read_only": 1,
				"precision": 2,
			},
			/*{
			"fieldname": "pending_insurance_amount",
			"fieldtype": "Currency",
			"label": __("Pendiente de Seguro (DOP)"),
			"read_only": 1,
			"precision": 2,
			"hidden": ! next_pagare.insurance || 0,
			"default": next_pagare.insurance || 0.000
		}, */
			{
				"fieldname": "repayment_section",
				"fieldtype": "Column Break"
			}, {
				"fieldname": "pending_amount",
				"fieldtype": "Currency",
				"label": "Monto del Pendiente (DOP)",
				"read_only": 1,
				"precision": 2,
				"default": total_pending
			},
			//  {
			// 	"fieldname": "repayment_amount",
			// 	"fieldtype": "Currency",
			// 	"label": "Monto del Pagare (DOP)",
			// 	"read_only": 1,
			// 	"precision": 2,
			// 	// "default": repayment_amount
			// },
			{
				"fieldname": "remarks_section",
				"fieldtype": "Section Break",
				"depends_on": "eval:['Administrator','licda.estrella@gmail.com', 'rosmery2492@hotmail.com', 'jalexpujols@gmail.com'].includes(frappe.session.user)"
			},
			{
				"label": "Nombre del Pago",
				"fieldname": "new_name",
				"fieldtype": "Int",
				"bold": 1,
				"depends_on": "eval:['Administrator','licda.estrella@gmail.com', 'rosmery2492@hotmail.com', 'jalexpujols@gmail.com'].includes(frappe.session.user)"
			},
			{
				"fieldname": "remarks_section",
				"fieldtype": "Section Break"
			},
			{
				"fieldname": "user_remark",
				"fieldtype": "Text",
				"label": "NOTAS DE USUARIO",
			}
		];

		// the callback to execute when user finishes introducing the values
		let onsubmit = (data) => {
			if(!!frm.doc.busy && frm.doc.busy == 1){
				frappe.msgprint("Su solicitud no puede ser completada en este momento intente mas tarde");
				// Estoy Ocupado
				return
			}
			frm.doc.busy = 1;

			if (flt(data.paid_amount) + flt(data.other_discounts) <= 0.000) {
				frappe.msgprint("El monto pagado debe ser mayor que cero!");
				return
			}

			frappe.confirm("¿Desear crear una Entrada de Pago?", () => {

				// method to be executed in the server
				let opts = {
					"method": "fm.accounts.make_payment_entry"
				}

				$.extend(data, {
					"doctype": frm.doctype,
					"docname": frm.docname,
					// "capital_amount": next_pagare.capital,
					// "interest_amount": next_pagare.interes,
					"paid_amount": flt(data.paid_amount) + flt(data.fine_discount),
					"sucursal": frappe.boot.sucursal,
					"validate_payment_entry": data.validate_payment_entry ? true : false,
					"new_name": data.new_name,
				});

				opts.args = {
					"opts": data
				};
				
				frappe.call(opts).then((response) => {
					let name = response.message;

					if (name) {
						// let the user know that it was succesfully created
						frappe.show_alert("Entrada de pago creada", 9.000);

						// let's play a sound for the user
						frappe.utils.play_sound("submit");

						// clear the prompt
						frm.reload_doc();

						setTimeout(() => frappe.hide_msgprint(), 2500.000);
						frm.doc.busy = 0;
						// let's show the user the new payment entry
						frappe.set_route("Form", "Journal Entry", name);
					}
					else{
						frappe.show_alert("Transaccion Bloqueada", 9.000);
						frm.doc.busy = 0;
					}
				}, () => {
					frappe.msgprint("¡Hubo un problema mientras se creaba la Entrada de Pago!");
					frm.doc.busy = 0;
				});
			}, () => frm.payment_entry_prompt.show());
		}

		// let's check if object is already set
		if (frm.payment_entry_prompt) {

			// it is set at this point
			// let's just make it visible
			frm.payment_entry_prompt.show()
		} else {

			// there was not object, so we need to create it
			frm.payment_entry_prompt = frappe.prompt(fields, onsubmit, __("Payment Entry"), "Submit");

			// default status for the wrapper
			frm.payment_entry_prompt.fields_dict.miscelaneos.wrapper.hide();
			frm.payment_entry_prompt.fields_dict.gps.$wrapper.hide();
			frm.payment_entry_prompt.fields_dict.gastos_recuperacion.$wrapper.hide();
			frm.payment_entry_prompt.fields_dict.gastos_intimacion.$wrapper.hide();

			frm.payment_entry_prompt.fields_dict.reference_name.toggle(false);
			frm.payment_entry_prompt.fields_dict.reference_date.toggle(false);

			frm.payment_entry_prompt.fields_dict.user_remark.$input.css({
				"height": "120px"
			});
			frm.payment_entry_prompt.fields_dict.remarks_section.wrapper.hide();


			// frm.payment_entry_prompt.fields_dict.fine_discount.$input.off();

			frm.payment_entry_prompt.fields_dict.fine_discount.change = (event) => {
				let fine_discount = flt(frm.payment_entry_prompt.get_value("fine_discount"));
				let pending_amount = flt(frm.payment_entry_prompt.get_value("pending_amount"));

				frm.payment_entry_prompt.set_value("paid_amount", pending_amount - fine_discount);
			};
			frm.payment_entry_prompt.fields_dict.fine_discount.bind_change_event();

			frm.payment_entry_prompt.fields_dict.has_gps.change = (event) => {
				let checked = frm.payment_entry_prompt.get_value("has_gps");

				if (checked) {

					frm.payment_entry_prompt.set_value("gps", flt(frappe.boot.fm_configuration.gps_amount))
						.then(() => {
							let _gps = frm.payment_entry_prompt.get_value("gps");
							let _recuperacion = frm.payment_entry_prompt.get_value("gastos_recuperacion");
							let _intimacion = frm.payment_entry_prompt.get_value("gastos_intimacion");
							let _paid_amount = frm.payment_entry_prompt.get_value("paid_amount") +
								frm.payment_entry_prompt.get_value("other_discounts");

							if (_intimacion + _gps + _recuperacion > _paid_amount) {
								frm.payment_entry_prompt.set_value("paid_amount", _gps + _paid_amount + _intimacion)
							}

						});

					frm.payment_entry_prompt.fields_dict.gps.$wrapper.show();

					// if checked then let's also show the section break
					frm.payment_entry_prompt.fields_dict.miscelaneos.wrapper.show();


				} else {
					frm.payment_entry_prompt.fields_dict.gps.$wrapper.hide();

					// finally if there's no value in the other one
					if (!frm.payment_entry_prompt.get_value("has_recuperacion")) {
						frm.payment_entry_prompt.fields_dict.miscelaneos.wrapper.hide();
					}
					if (!frm.payment_entry_prompt.get_value("has_intimacion")) {
						frm.payment_entry_prompt.fields_dict.miscelaneos.wrapper.hide();
					}
					_gps = frm.payment_entry_prompt.get_value("gps");
					frm.payment_entry_prompt.set_value("gps", 0.000);
				}
			};
			frm.payment_entry_prompt.fields_dict.has_gps.bind_change_event();

			frm.payment_entry_prompt.fields_dict.has_intimacion.change = (event) => {
				let checked = frm.payment_entry_prompt.get_value("has_intimacion");

				if (checked) {

					frm.payment_entry_prompt.set_value("gastos_intimacion", flt(frappe.boot.fm_configuration.intimation_amount))
						.then(() => {
							let _recuperacion = frm.payment_entry_prompt.get_value("gastos_recuperacion");
							let _intimacion = frm.payment_entry_prompt.get_value("gastos_intimacion");
							let _gps = frm.payment_entry_prompt.get_value("gps");
							let _paid_amount = frm.payment_entry_prompt.get_value("paid_amount") +
								frm.payment_entry_prompt.get_value("other_discounts");

							if (_intimacion + _recuperacion + _gps > _paid_amount) {
								frm.payment_entry_prompt.set_value("paid_amount", _intimacion + _paid_amount)
							}

						});

					frm.payment_entry_prompt.fields_dict.gastos_intimacion.$wrapper.show();

					// if checked then let's also show the section break
					frm.payment_entry_prompt.fields_dict.miscelaneos.wrapper.show();

				} else {
					frm.payment_entry_prompt.fields_dict.gastos_intimacion.$wrapper.hide();

					// finally if there's no value in the other one
					if (!frm.payment_entry_prompt.get_value("has_gps") && !frm.payment_entry_prompt.get_value("has_recuperacion")) {
						frm.payment_entry_prompt.fields_dict.miscelaneos.wrapper.hide();
					}
					
					_intimacion = frm.payment_entry_prompt.get_value("gastos_intimacion");
					frm.payment_entry_prompt.set_value("gastos_intimacion", 0.000);
				}
			};
			frm.payment_entry_prompt.fields_dict.has_intimacion.bind_change_event();

			frm.payment_entry_prompt.fields_dict.has_recuperacion.change = (event) => {
				let checked = frm.payment_entry_prompt.get_value("has_recuperacion");

				if (checked) {

					frm.payment_entry_prompt.set_value("gastos_recuperacion", flt(frappe.boot.fm_configuration.recuperation_amount))
						.then(() => {
							let _recuperacion = frm.payment_entry_prompt.get_value("gastos_recuperacion");
							let _intimacion = frm.payment_entry_prompt.get_value("gastos_intimacion");
							let _gps = frm.payment_entry_prompt.get_value("gps");
							let _paid_amount = frm.payment_entry_prompt.get_value("paid_amount") +
								frm.payment_entry_prompt.get_value("other_discounts");

							if (_recuperacion + _gps > _paid_amount) {
								frm.payment_entry_prompt.set_value("paid_amount", _recuperacion + _paid_amount)
							}

						});

					frm.payment_entry_prompt.fields_dict.gastos_recuperacion.$wrapper.show();

					// if checked then let's also show the section break
					frm.payment_entry_prompt.fields_dict.miscelaneos.wrapper.show();

				} else {
					frm.payment_entry_prompt.fields_dict.gastos_recuperacion.$wrapper.hide();

					// finally if there's no value in the other one
					if (!frm.payment_entry_prompt.get_value("has_gps") && !frm.payment_entry_prompt.get_value("has_intimacion")) {
						frm.payment_entry_prompt.fields_dict.miscelaneos.wrapper.hide();
					}

					_recuperacion = frm.payment_entry_prompt.get_value("gastos_recuperacion");
					frm.payment_entry_prompt.set_value("gastos_recuperacion", 0.000);					
				}
			};
			frm.payment_entry_prompt.fields_dict.has_recuperacion.bind_change_event();

			frm.payment_entry_prompt.fields_dict.insurance_amount.change = (event) => {
				let insurance_amount = frm.payment_entry_prompt.get_value("insurance_amount");

				if (!frm.doc.pending_insurance_amount) {
					frm.doc.pending_insurance_amount = frm.payment_entry_prompt.get_value("pending_insurance_amount");
				}

				if (insurance_amount < 0) {
					frm.payment_entry_prompt.set_value("insurance_amount", 0.000);
					frm.payment_entry_prompt.set_value("pending_insurance_amount", frm.doc.pending_insurance_amount);
					frappe.throw("¡Monto de Seguro invalido!");
				}

				if (insurance_amount > frm.doc.pending_insurance_amount) {
					frm.payment_entry_prompt.set_value("pending_insurance_amount", 0.000);
					frm.payment_entry_prompt.set_value("insurance_amount", frm.doc.pending_insurance_amount);
					frappe.throw("¡Monto de Seguro no puede ser mayor al establecido en la cuota!");
				}

				let new_pending_insurance_amount = frm.doc.pending_insurance_amount - insurance_amount;
				frm.payment_entry_prompt.set_value("pending_insurance_amount", new_pending_insurance_amount);
			};
			frm.payment_entry_prompt.fields_dict.insurance_amount.bind_change_event();

			frm.payment_entry_prompt.fields_dict.mode_of_payment.change = (event) => {
				let mode_of_payment = frm.payment_entry_prompt.get_value("mode_of_payment");

				if (["Credit Card Entry", "Bank Entry", "Bank Transfer", "Cheque"].includes(mode_of_payment)) {
					// make them mandatory then
					frm.payment_entry_prompt.fields_dict.reference_name.df.reqd = true;
					frm.payment_entry_prompt.fields_dict.reference_date.df.reqd = true;

					frm.payment_entry_prompt.fields_dict.reference_name.toggle(true);
					frm.payment_entry_prompt.fields_dict.reference_date.toggle(true);
				} else {
					// make them non mandatory then
					frm.payment_entry_prompt.fields_dict.reference_name.df.reqd = false;
					frm.payment_entry_prompt.fields_dict.reference_date.df.reqd = false;

					frm.payment_entry_prompt.fields_dict.reference_name.toggle(false);
					frm.payment_entry_prompt.fields_dict.reference_date.toggle(false);

				}
			};
			frm.payment_entry_prompt.fields_dict.mode_of_payment.bind_change_event();

			frm.payment_entry_prompt.fields_dict.add_user_remarks.change = (event) => {
				let add_user_remarks = frm.payment_entry_prompt.get_value("add_user_remarks");

				if (add_user_remarks) {
					frm.payment_entry_prompt.fields_dict.remarks_section.wrapper.show();
				} else {
					frm.payment_entry_prompt.fields_dict.remarks_section.wrapper.hide();
				}
			};
			frm.payment_entry_prompt.fields_dict.add_user_remarks.bind_change_event();

			frm.payment_entry_prompt.set_value("gastos_recuperacion", 0.000);
			frm.payment_entry_prompt.set_value("gastos_intimacion", 0.000);
			frm.payment_entry_prompt.set_value("gps", 0.000);
			frm.payment_entry_prompt.set_value("has_gps", 0.000);
			frm.payment_entry_prompt.set_value("has_recuperacion", 0.000);
			frm.payment_entry_prompt.set_value("add_user_remarks", 0.000);
		}
	}
});

frappe.ui.form.on('Tabla Amortizacion', {
	"voucher": (frm, cdt, cdn) => {
		frappe.set_route(["List", "Journal Entry"], {
			"pagare": ["like", __("%{0}%", [cdn])]
		});
	},
	"historical": (frm, cdt, cdn) => {
		row = frappe.model.get_doc(cdt, cdn);
		// frappe.route_options = { "loan": frm.doc.name, "repayment": row.idx };
		// frappe.set_route("query-report/Historico Cuotas");
		window.open(`/#query-report/Historico%20Cuotas?loan=${frm.doc.name}&repayment=${row.idx}`, "_blank");
	},
	"add_fine_discount": (frm, cdt, cdn) => new AddLoanDiscountPrompt(frm, cdt, cdn)
})

class AddLoanDiscountPrompt {
	constructor(frm, cdt, cdn) {
		this.frm = frm;
		this.cdt = cdt;
		this.cdn = cdn;

		this.init();
	}

	init() {
		let fields = [{
			"label": "Monto",
			"fieldname": "fine_discount",
			"fieldtype": "Float",
			"reqd": 1
		}];

		this.prompt = frappe.prompt(fields, (values) => this.process_data(values), "Descuento", "Agregar");
	}

	process_data(values) {
		// frappe.ui.form.close_grid_form();

		let args = {
			"doctype": this.cdt,
			"docname": this.cdn,
			"fine_discount": values.fine_discount
		};

		this.frm.call("add_fine_discount_to_row", args)
			.fail(() => this.prompt && this.prompt.show())
			.done(() => this.frm.refresh_fields());
	}
}