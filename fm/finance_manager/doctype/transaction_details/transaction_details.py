# -*- coding: utf-8 -*-
# Copyright (c) 2019, Yefri Tavarez and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class TransactionDetails(Document):

	def validate(self):
		self.validate_amount()

	def after_insert(self):
		self.idx = frappe.db.sql("""
			SELECT 
				COUNT(1) 
			FROM
				`tabTransaction Details`
			WHERE
				`tabTransaction Details`.loan = '{loan}'
			AND
				`tabTransaction Details`.repayment = '{repayment}'
			""".format(**self.as_dict())
		)[0][0]

		self.get_pending_amount()
		self.db_update()

	def get_pending_amount(self):
		self.pending_amount = frappe.db.sql("""
			SELECT 
				SUM(amount) 
			FROM
				`tabTransaction Details`
			WHERE
				`tabTransaction Details`.loan = '{loan}'
			AND
				`tabTransaction Details`.repayment = '{repayment}'
			""".format(**self.as_dict())
		)[0][0]

	def validate_amount(self):
		# Payments must be <0 
		# Everything else must be >0
		if self.description == "Pago" and self.amount > 0:
			frappe.throw(
				_("Amount {} must be < 0 for Payments".format(self.amount))
			)
		
		if self.description != "Pago" and self.amount < 0:
			frappe.throw(
				_("Amount {0} must be > 0 for {1}".format(
					self.amount, self.description
				)
			)
		)

