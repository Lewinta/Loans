# -*- coding: utf-8 -*-
# Copyright (c) 2020, Yefri Tavarez and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.desk.tags import DocTags
from frappe.utils import flt
from frappe import _
from fm.api import DISALLOWED_STATUSES

class ClientPortfolio(Document):
	def validate(self):
		self.calculate_pending_amount()
		self.validate_duplicates()
		self.validate_date()

	def validate_duplicates(self):
		if not self.customer_portfolio:
			return

		loans = [x.loan for x in self.customer_portfolio]
		loans = "','".join(loans)

		duplicates = frappe.db.sql("""
			SELECT 
				`tabCustomer Portfolio`.loan,
				`tabCustomer Portfolio`.customer,
				`tabClient Portfolio`.employee_name,
				`tabCustomer Portfolio`.parent,
				SUM(1) qty
			FROM 
				`tabCustomer Portfolio`
			JOIN
				`tabClient Portfolio`
			ON
				`tabClient Portfolio`.name = `tabCustomer Portfolio`.parent
			WHERE
				`tabCustomer Portfolio`.loan in ('%s')
			AND 
				`tabCustomer Portfolio`.parent != '%s'
			GROUP BY 
				`tabCustomer Portfolio`.loan
			HAVING
				qty >= 1

		""" % (loans, self.name), as_dict=True)

		if duplicates:
			msg = ""
			for r in duplicates:
				msg +="<tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(r.get("loan"),r.get("customer"), r.get("employee_name"))

			frappe.throw("""<h3 class='text-center'>Los siguientes prestamos ya pertenecen a otra cartera:</h3><br>
				<table class='table table-bordered'>
					<thead>
						<tr>
							<th class='active text-center'>Prestamo</th>
							<th class='active text-center'>Cliente</th>
							<th class='active text-center'>Agente</th>
						</tr>
					</thead>
					<tbody>
					{}
					</tbody>
				</table>""".format(msg))

	def validate_date(self):
		if self.start_date > self.end_date:
			frappe.throw(_("End Date must be greater than Start Date"))
	def add_tag(self, loan):
		DocTags("Loan").remove_all(loan)
		DocTags("Loan").add(loan, self.employee_name)

	def remove_loan_from_portfolio(self):
		for row in self.customer_portfolio:
			status = frappe.db.get_value("Loan", row.loan, "status")
			if status in ['Recuperado', 'Incautado', 'Perdida Total', 'Legal']:
				DocTags("Loan").remove_all(row.loan)
				self.remove(row)
				self.save(ignore_permissions=True)

	def remove_paid_loans(self):
		for row in self.customer_portfolio:
			status = frappe.db.get_value("Loan", row.loan, "status")
			if status == 'Repaid/Closed' and row.received_amount == .000:
				DocTags("Loan").remove_all(row.loan)
				self.remove(row)
				self.save(ignore_permissions=True)

	def show_invalid_loans(self):
		for l in self.customer_portfolio:
			status = frappe.db.get_value("Loan", l.loan, "status")
			if status  in DISALLOWED_STATUSES:
				print("{} {} {} {} {}".format(l.idx, self.employee_name, l.loan, status, l.received_amount))

	def calculate_pending_amount(self):
		if not self.customer_portfolio:
			return
		
		self.total_pending = self.total_received = self.net_received = self.total_discounts = .000
		self.customer_qty = 0
		
		for row in self.customer_portfolio:
			loan = frappe.get_doc("Loan", row.loan)
			row.pending_amount = loan.get_past_due_balance(self.end_date)
			row.received_amount, row.total_discount, row.total_paid = loan.get_paid_amount(self.start_date, self.end_date)

			self.total_discounts += row.total_discount
			self.net_received    += row.received_amount
			self.total_received  += row.total_paid
			self.total_pending   += row.pending_amount
			self.add_tag(loan.name)

		self.customer_qty = len(self.customer_portfolio)
		self.percentage_received = flt(self.net_received / self.total_pending * 100, 2) if self.net_received > 0 else .000
	
	def move_loan(self):
		frappe.errprint("Let's move {} to {}".format(self.loan_to_move, self.new_portfolio))
		if not self.loan_to_move or not self.new_portfolio:
			return
		result = filter(lambda r, loan_to_move=self.loan_to_move: r.loan == loan_to_move, self.customer_portfolio)
		frappe.errprint("Found {}".format(result))
		if not result:
			frappe.throw("El prestamo <b>{}</b> no pertenece a esta cartera".format(self.loan_to_move))

		self.customer_portfolio.remove(result[0])
		self.save()
		frappe.errprint("Saved")

		new_portfolio = frappe.get_doc("Client Portfolio", self.new_portfolio)
		new_portfolio.append("customer_portfolio", {"loan": result[0].loan})
		new_portfolio.save()
		frappe.errprint("NEw SAved")


