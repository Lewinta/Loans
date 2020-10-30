// Copyright (c) 2020, Yefri Tavarez and contributors
// For license information, please see license.txt

frappe.ui.form.on('Client Portfolio', {
	refresh: frm => {
		frm.trigger("add_custom_button");
		frm.trigger("set_queries");
	},
	set_queries: frm => {
		frm.set_query("loan", "customer_portfolio", function () {
			return {
				"filters": {
					"status": ["!=", "Repaid/Closed"],
					"branch_office": frm.doc.branch_office,
					"docstatus": ["=", "1"],
				}
			}
		});
	},
	add_custom_button: frm =>{
		if (frm.is_new())
			return

		frm.add_custom_button(__("Move Customer"), () => {
			frm.trigger("show_move_cust_prompt");
		});

		frm.add_custom_button(__("Payments"), () => {
			frappe.set_route(
				'query-report',
				'Payments by Portfolio', 
				{
					client_portfolio: frm.doc.name,
				}
			);
		}, __("View"));

		frm.add_custom_button(__("Customers"), () => {
			frappe.set_route(
				'query-report',
				'Customers by Portfolio', 
				{
					client_portfolio: frm.doc.name,
				}
			);
		}, __("View"));
	},
	description: frm => {
		if (!frm.doc.description)
			return
		frm.set_value("description", frm.doc.description.toUpperCase().trim());
	},
	update_customer_qty: frm => {
		frm.set_value("customer_qty", frm.doc.customer_portfolio.length);
	},
	get_pending_amount: frm => {
		frm.call("calculate_pending_amount").then(() => {
			frm.refresh();
		});
		frm.trigger("update_customer_qty");
	},
	show_move_cust_prompt: frm => {
		let fields =[
			{
				"label": __("Loan"),
				"fieldname": "loan",
				"fieldtype": "Link",
				"options": "Loan",
				"reqd": 1,
			},
			{
				"label": __("Customer"),
				"fieldname": "customer",
				"fieldtype": "Read Only",
			},
			{
				"fieldtype": "Column Break"
			},
			{
				"label": __("Client Portfolio"),
				"fieldname": "client_portfolio",
				"fieldtype": "Link",
				"options": "Client Portfolio",
				"reqd": 1,
			},
		]
		let _cb = (data) => {
			frm.doc.loan_to_move = data.loan;
			frm.doc.new_portfolio = data.client_portfolio;
			frappe.run_serially([
				() => frappe.dom.freeze(`Moviendo <b>${data.loan}</b> a <b>${data.client_portfolio}</b>, por favor espere...`),
				() => frm.call("move_loan"),
				() => frappe.dom.unfreeze(),
				() => frappe.show_alert(`El Prestamo ${data.loan} fue movido exitosamente!`),
				() => frm.reload_doc(),
			])
		}

		frappe.prompt(fields, _cb, "Move Customer", "Mover");
	}

});

frappe.ui.form.on('Customer Portfolio', {
	loan: (frm, cdt, cdn) =>{
		row = frappe.model.get_doc(cdt,cdn);
		if (row.loan){
			frm.trigger("calculate_pending_amount");
		}
		frm.doc.customer_portfolio.filter(r => {
			if (r.loan == row.loan && r.idx != row.idx ){
				frappe.show_alert(`${row.loan} ya existe en la linea ${r.idx}`, 5);
				frm.get_field("customer_portfolio").grid.grid_rows[
					cur_frm.doc.customer_portfolio.length-1
				].remove();
				return
			}

		});
	},
	customer_portfolio_remove: (frm, cdt, cdn) => {
		frm.trigger("calculate_pending_amount");
	},
	view_statement: (frm, cdt, cdn) => {
		row = frappe.model.get_doc(cdt,cdn);
		frappe.set_route(
			'query-report',
			'Estado de Cliente', 
			{
				customer: row.customer,
				sucursal: row.branch_office, 
				loan: row.loan, 
				to_date: frm.doc.end_date, 
				status: "", 
			}
		);
	},
});
