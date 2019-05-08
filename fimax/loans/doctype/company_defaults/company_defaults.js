// Copyright (c) 2018, Yefri Tavarez and contributors
// For license information, please see license.txt

frappe.ui.form.on('Company Defaults', {
	refresh: frm => {
		frm.trigger("set_queries")
	},
	"set_queries": (frm) => {
		let event_list = [
			"set_party_account_query",
			"set_income_account_query", 
			"set_disbursement_account_query", 
			
		];

		$.map(event_list, (event) => frm.trigger(event));
	},
	set_party_account_query: frm => {
		frm.set_query("party_account", () => {
			return {
				"filters": {
					"is_group": 0,
					"company": frm.doc.company,
					"account_type": "Receivable"
				}
			};
		});
	},
	set_income_account_query: frm =>{
		frm.set_query("income_account", () => {
			return {
				"filters": {
					"is_group": 0,
					"company": frm.doc.company,
					"account_type": "Income Account"
				}
			};
		});
	},
	set_disbursement_account_query: frm => {
		frm.set_query("disbursement_account", () => {
			return {
				"filters": {
					"is_group": 0,
					"company": frm.doc.company,
					"account_type": ["in", "Bank, Cash"]
				}
			};
		});
	},
});
