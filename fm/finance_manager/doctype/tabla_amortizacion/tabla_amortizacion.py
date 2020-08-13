# -*- coding: utf-8 -*-
# Copyright (c) 2017, Soldeva, SRL and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from fm.api import PENDING, FULLY_PAID, PARTIALLY_PAID, OVERDUE
from frappe.utils import flt, cstr,nowdate, add_months, add_days, date_diff
from math import ceil

class TablaAmortizacion(Document):
	def update_status(self):
		orignal_duty = self.get_dutty_amount()

		today = nowdate()
		grace_days = frappe.get_single("FM Configuration").grace_days
		due_date = add_days(self.fecha, grace_days ) 
		# # ok, let's see if the repayment has been fully paid
		# if orignal_duty == self.monto_pendiente and str(due_date) < today:

		# 	self.estado = OVERDUE
		# elif  orignal_duty == self.monto_pendiente:

		# 	self.estado = PENDING
		# elif self.monto_pendiente <= 0.5:

		# 	self.estado = FULLY_PAID
		# elif self.monto_pendiente < orignal_duty and self.monto_pendiente > 0:

		# 	self.estado = PARTIALLY_PAID

		# it's pending if repayment date is in the future and has nothing paid
		if cstr(due_date) >= today and self.monto_pendiente > 0.000:
			self.estado = PENDING

		# it's partially paid if repayment date is in the future and has something paid
		if cstr(due_date) > today and self.monto_pagado > 0.000:
			self.estado = PARTIALLY_PAID

		# it's overdue if repayment date is in the past and is not fully paid
		if cstr(due_date) <= today and self.monto_pendiente > 0.000:
			self.estado = OVERDUE

		# it's paid if paid and total amount are equal hence there's not outstanding amount
		if flt(self.monto_pagado, 2) == flt(orignal_duty, 2)\
			or not flt(self.monto_pendiente, 0):
			self.estado = FULLY_PAID

		return self.estado

	def get_dutty_amount(self):
		return round(flt(self.cuota) + flt(self.insurance) + flt(self.mora_acumulada)\
			- flt(self.fine_discount), 2)

	def get_pending_amount(self):
		return round(self.get_dutty_amount() - flt(self.monto_pagado), 2)

	def get_paid_in_others_vouchers(self, voucher):
		result = frappe.db.sql("""
			SELECT
				SUM(debit) 
			FROM
				`tabJournal Entry` AS parent 
				JOIN
					`tabJournal Entry Account` AS child 
					ON parent.name = child.parent 
			WHERE
				parent.pagare LIKE "%{0}%"
				AND repayment_field = "paid_amount" 
				AND parent.name != "{1}"
		""".format(self.name, voucher), as_list=True)

		return len(result) and result[0][0]
	
	def get_sibilings_paid_amount(self, voucher):
		result = frappe.db.sql("""
			SELECT
				SUM(monto_pagado) 
			FROM
				`tabTabla Amortizacion` AS parent 
			WHERE
				parent.name in "{}"
		""".format(self.name, voucher), as_list=True)

		return len(result) and result[0][0]

	def get_paid_amount_until(self, date):
		result = frappe.db.sql("""
			SELECT
				SUM(debit) AS paid_amount
			FROM
				`tabJournal Entry` AS parent 
				JOIN
					`tabJournal Entry Account` AS child 
					ON parent.name = child.parent 
			WHERE
				parent.pagare LIKE "%{0}%"
				AND repayment_field in ("capital","paid_amount")
				AND posting_date < "{1}" 

		""".format(self.name, date), as_list=True)

		return len(result) and result[0][0]

	def get_paid_in_sibilings(voucher, sibilings):
		result = frappe.db.sql("""
			SELECT
				SUM()
			
			""")

	def check_fine(self):
		import datetime
		conf = frappe.get_single("FM Configuration")
		fine_rate = flt(conf.vehicle_fine)/100
		grace_days = conf.grace_days
		# self.fine = 0
		tmp_fine = 0
		due_date = add_days(self.fecha, grace_days)
		today = datetime.date.today()

		while self.monto_pendiente > 0 and due_date < today:
			dutty = self.get_dutty_amount()
			# dutty = flt(self.cuota) + flt(self.insurance) 
			paid_amount = flt(self.get_paid_amount_until(due_date))
			new_fine = (dutty - paid_amount) * fine_rate
			print("dutty {} paid_amount {} new fine {} due_date {}".format(dutty, paid_amount, new_fine, due_date))
			tmp_fine += new_fine
			due_date = add_months(due_date, 1)

		return tmp_fine
	
	def calculate_fine(self):
		conf = frappe.get_single("FM Configuration")
		fine = frappe.get_value(self.parenttype, self.parent, "fine")
		fine_rate = fine / 100.0
		grace_days = conf.grace_days
		today = nowdate()
		updated_fine_on = add_months(cstr(self.updated_fine_on or self.fecha), 1)
		due_date = str(add_days(self.fecha, int(grace_days)))
		
		# date diff in days
		date_difference = date_diff(today, due_date)
		due_payments = ceil(date_difference / 30.000)
		new_fine = flt(fine_rate) * flt(self.monto_pendiente - self.fine) * due_payments
		monthly_fine = flt(fine_rate) * flt(self.cuota + self.insurance + self.mora_acumulada - self.monto_pagado)

		if self.estado != FULLY_PAID and today > due_date:
			# this repayment is due
			# print("repayment is due")
			if not self.updated_fine_on or today > updated_fine_on:
				# print("let's calc fine")
				fine_log = frappe.new_doc("Fine Log")
				print("{parent} {idx}".format(**self.as_dict()))
				fine_log.update({
					"loan": self.parent,
					"repayment": self.idx,
					"interest_rate": fine,
					"due_days": due_payments,
					"interest_generated": ceil(monthly_fine),
					"posting_date": today,
					"repayment_date": self.fecha,
					"due_date": due_date,
					"mora_acumulada_b": self.mora_acumulada,
					"fine_b": self.fine,
					"pending_amount_b": self.monto_pendiente,
				})
				
				if self.monto_pagado == .00:
					self.fine = ceil(due_payments * (self.cuota + self.insurance) * fine_rate)
					self.mora_acumulada = self.fine
				else:
					self.fine += ceil(monthly_fine) # adding th new fine
					self.mora_acumulada += ceil(monthly_fine)

				self.due_date = due_date 
				self.due_payments = due_payments 
				self.updated_fine_on = today
				self.monto_pendiente = self.get_pending_amount() 
				
				fine_log.update({
					"mora_acumulada_a": self.mora_acumulada,
					"fine_a": self.fine,
					"pending_amount_a": self.monto_pendiente,

				})

				fine_log.save()
				self.update_status()

				self.db_update()