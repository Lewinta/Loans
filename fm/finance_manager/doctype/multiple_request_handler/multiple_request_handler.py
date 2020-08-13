# -*- coding: utf-8 -*-
# Copyright (c) 2019, Yefri Tavarez and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from fm.api import get_time_based_name
from frappe.utils import now, time_diff

class MultipleRequestHandler(Document):
	def validate(self):
		self.check_request()
		
	def before_insert(self):
		self.identifier = get_time_based_name()

	def check_request(self):
		too_soon = self.is_too_soon()
		
		self.update({
			"user":frappe.session.user,
			"status": "Blocked" if too_soon else "Allowed"
		})

		return too_soon

	def get_last_request(self):
		return frappe.db.get_value(
			"Multiple Request Handler",
			{'status':'Allowed'},
			['MAX(identifier)']
		)
	
	def is_too_soon(self):
		# Min Seconds allowed before another request
		min_allowed = 20
		req = self.get_last_request()
		if not req:
			return False

		last = frappe.get_doc("Multiple Request Handler", req)

		self.last_request = time_diff(now(), last.timestamp).seconds
		same_user = last.user == frappe.session.user


		return True if self.last_request <= min_allowed and same_user else False
			


