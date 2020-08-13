# -*- coding: utf-8 -*-
# Copyright (c) 2017, Yefri Tavarez and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe.model.document import Document

class BranchOffice(Document):

	def add_user(self, usr):

		if not frappe.db.exists("User Permission", { "user": usr, "allow": "Branch Office", "for_value": self.name}):
			user = frappe.get_doc("User", usr)
			permission = frappe.new_doc("User Permission")
			permission.user = usr
			permission.allow = "Branch Office"
			permission.for_value = self.name
			permission.full_name = user.full_name
			permission.save()
			self.add_comment("Updated", "<span> agregó el usuario {} a esta sucursal! </span>".format(user.name), frappe.session.user)
			self.refresh_users()
			
		return usr

	def drop_user(self, usr):

		if  frappe.db.exists("User Permission", { "user": usr, "allow": "Branch Office", "for_value": self.name}):
			user = frappe.get_doc("User", usr)
			permission = frappe.get_doc("User Permission", { "user": usr, "allow": "Branch Office", "for_value": self.name})
			permission.delete()
			self.add_comment("Updated", "<span> Eliminó el usuario {} a esta sucursal! </span>".format(user.name), frappe.session.user)
			self.refresh_users()
			
		return usr

	def refresh_users(self):
		collection_user = [d for d in self.users if d.collection_user]
		self.users = []
		users = frappe.get_list("User Permission", { "allow": "Branch Office", "for_value": self.name}, ["user", "full_name"])
		for user in users:
			if collection_user and user.user == collection_user[0].user:
				user.collection_user = 1
			self.append("users",user)
		self.save()



		