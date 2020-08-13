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
	update_customer_qty: frm => {
		frm.set_value("customer_qty", frm.doc.customer_portfolio.length);
	},
	get_pending_amount: frm => {
		frm.call("calculate_pending_amount").then(() => {
			frm.refresh();
		});
		frm.trigger("update_customer_qty");
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
