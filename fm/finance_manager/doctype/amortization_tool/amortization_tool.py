# -*- coding: utf-8 -*-
# Copyright (c) 2017, Soldeva, SRL and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
import fm.accounts

class AmortizationTool(Document):
	def calculate_everything(self):
		from fm.accounts import make_simple_repayment_schedule

		make_simple_repayment_schedule(self)
		self.save()

		return self

@frappe.whitelist()
def make_loan_application(source_name, target_doc = None):
	amort = frappe.get_doc("Amortization Tool", source_name)
	appl = get_mapped_doc("Amortization Tool", source_name, {
		"Amortization Tool": {
			"doctype": "Loan Application",
		}
	}, target_doc)

	# loan.status = "Sanctioned" # status = [Approved] is not valid in Loan DocType
	# loan.disbursement_date = appl.required_by_date
	# loan.posting_date = appl.posting_date

	# # set account defaults for Loan
	# if loan.customer_currency == "DOP":
	# 	loan.mode_of_payment = frappe.db.get_single_value("FM Configuration", "mode_of_payment")
	# 	loan.payment_account = frappe.db.get_single_value("FM Configuration", "payment_account")
	# 	loan.customer_loan_account = frappe.db.get_single_value("FM Configuration", "customer_loan_account")
	# 	loan.disbursement_account = frappe.db.get_single_value("FM Configuration", "disbursement_account")
	# 	loan.interest_income_account = frappe.db.get_single_value("FM Configuration", "interest_income_account")
	# 	loan.expenses_account = frappe.db.get_single_value("FM Configuration", "expenses_account")
	# else:
	# 	loan.mode_of_payment = frappe.db.get_single_value("FM Configuration", "mode_of_payment").replace("DOP", "USD")
	# 	loan.payment_account = frappe.db.get_single_value("FM Configuration", "payment_account").replace("DOP", "USD")
	# 	loan.customer_loan_account = frappe.db.get_single_value("FM Configuration", "customer_loan_account").replace("DOP", "USD")
	# 	loan.disbursement_account = frappe.db.get_single_value("FM Configuration", "disbursement_account").replace("DOP", "USD")
	# 	loan.interest_income_account = frappe.db.get_single_value("FM Configuration", "interest_income_account").replace("DOP", "USD")
	# 	loan.expenses_account = frappe.db.get_single_value("FM Configuration", "expenses_account").replace("DOP", "USD")
	
    
	# loan.validate()
	return appl
