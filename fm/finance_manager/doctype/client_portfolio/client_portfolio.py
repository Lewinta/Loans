# -*- coding: utf-8 -*-
# Copyright (c) 2020, Yefri Tavarez and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.desk.tags import DocTags
from frappe.utils import flt
from frappe import _

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
				loan,
				customer,
				parent,
				SUM(1) qty
			FROM 
				`tabCustomer Portfolio`
			WHERE
				loan in ('%s')
			AND 
				parent != '%s'
			GROUP BY 
				loan
			HAVING
				qty >= 1

		""" % (loans, self.name), as_dict=True)

		if duplicates:
			msg = ""
			for r in duplicates:
				msg +="<tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(r.get("loan"),r.get("customer"), r.get("parent"))

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

	def calculate_pending_amount(self):
		if not self.customer_portfolio:
			return
		
		self.total_pending = .000
		self.total_received = .000
		self.customer_qty = 0
		
		for row in self.customer_portfolio:
			loan = frappe.get_doc("Loan", row.loan)
			row.pending_amount = loan.get_past_due_balance(self.end_date)
			row.received_amount = loan.get_paid_amount(self.start_date, self.end_date)
			self.total_pending += row.pending_amount
			self.total_received += row.received_amount
			self.add_tag(loan.name)

		self.customer_qty = len(self.customer_portfolio)
		self.percentage_received = flt(self.total_received / self.total_pending * 100, 2) if self.total_pending > 0 else .000


