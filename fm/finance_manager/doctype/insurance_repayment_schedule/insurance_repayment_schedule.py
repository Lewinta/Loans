# -*- coding: utf-8 -*-
# Copyright (c) 2015, Soldeva, SRL and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt

class InsuranceRepaymentSchedule(Document):
	def update_status(self):
		if self.paid_amount  == .000:
			self.status = "PENDIENTE"
		
		if self.paid_amount  > .000:
			self.status = "ABONO"
		
		if self.pending_amount  < 1.5:
			self.status = "SALDADA"
		self.db_update()
		return self.status

	def calculate_pending_amount(self):
		self.pending_amount = self.amount - self.paid_amount
		self.db_update()
		return self.pending_amount
	
	def make_payment(self, amount):
		self.calculate_pending_amount()
		if not amount:
			return details
		if amount < .00:
			frappe.throw("No es posible agregar un pago negativo a esta cuota de la poliza")
		
		used  = self.pending_amount if amount > self.pending_amount else amount
		
		self.paid_amount += used
		self.calculate_pending_amount()
		self.update_status()
		self.db_update()
		return used 
	def get_supplier(self):
		return frappe.db.get_value("Poliza de Seguro", self.parent, "insurance_company")


