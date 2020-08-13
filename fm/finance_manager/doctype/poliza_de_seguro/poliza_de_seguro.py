# -*- coding: utf-8 -*-
# Copyright (c) 2015, Soldeva, SRL and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe.model.document import Document
from frappe import _
from math import ceil
from frappe.utils import flt, nowdate
from fm.api import FULLY_PAID, PENDING, OVERDUE


class PolizadeSeguro(Document):
	def validate(self):
		if not self.loan:
			return

		if self.financiamiento and not self.cuotas:
			frappe.throw("""
				No es posible financiar a cero cuotas, desmarque 
				la casilla de financiamiento si el cliente pago completo
			""")

		self.branch_office = frappe.db.get_value("Loan", self.loan, "branch_office")

		if self.loan and not self.insurance_starts_on:
			frappe.throw(_("Favor seleccionar en la cuota que inicia la poliza"))

		if self.payment_date > nowdate():
			frappe.throw("La fecha de pago no debe ser posterior a la fecha de hoy")

		if self.financiamiento and self.initial_payment == .000:
			return 
		
		if not self.payment_date:
			frappe.throw("Favor especificar la fecha en la que se recibe el inicial")
		if not self.mode_of_payment:
			frappe.throw("Favor especificar el metodo de pago del inicial")



	def before_submit(self):
		"""Automate the Purchase Invoice creation against a Poliza de Seguro"""
		# validate if exists a purchase invoice against the current document
		pinv_asdict = frappe.get_value("Purchase Invoice", 
			{ "poliza_de_seguro": self.name, "docstatus": ["!=", "2"] }, "*")

		if pinv_asdict:
			# let's return the purchase invoice name
			return pinv_asdict

		# ok, let's continue as there is not an existing PINV

		item = frappe.new_doc("Item")
		company = frappe.get_doc("Company", erpnext.get_default_company())

		item_was_found = not not frappe.get_value("Item", { "item_group": "Insurances" })

		# let's see if it exists
		if item_was_found:

			item = frappe.get_doc("Item", { "item_group": "Insurances" })
		else:
			# ok, let's create it
			item.item_group = "Insurances"
			item.item_code = "Vehicle Insurance"
			item.item_name = item.item_code

			item.insert()

		pinv = frappe.new_doc("Purchase Invoice")

		pinv.supplier = self.insurance_company
		pinv.is_paid = 1.000
		pinv.company = company.name
		pinv.branch_office = self.branch_office
		pinv.mode_of_payment = frappe.db.get_single_value("FM Configuration", "mode_of_payment")
		pinv.cash_bank_account = company.default_bank_account
		pinv.paid_amount = self.amount
		pinv.sucursal = frappe.get_value("User Branch Office",{"user":frappe.session.user},["parent"]) or "SANTO DOMINGO"
		pinv.base_paid_amount = self.amount

		# ensure this doc is linked to the new purchase
		pinv.poliza_de_seguro = self.name

		pinv.append("items", {
			"item_code": item.item_code,
			"is_fixed_item": 1,
			"item_name": item.item_name,
			"qty": 1,
			"price_list_rate": self.amount,
			"rate": self.amount
		})

		pinv.flags.ignore_permissions = True
		pinv.submit()

		return pinv.as_dict()

	def on_submit(self):
		"""Run after submission"""

		self.create_event()
		self.create_first_payment()
		# self.create_initial_payment()

		# let's check if this insurance was term financed
		# if not self.get("financiamiento"):
			# return 0 # let's just ignore and do nothing else

		if not self.loan:
			return 0

		loan = frappe.get_doc("Loan", self.loan)

		stock_received = frappe.db.get_single_value("FM Configuration", "goods_received_but_not_billed")
        
		for insurance in self.cuotas:
			insurance.amount = flt(self.amount / self.repayments, 2)
			insurance.db_update()

		# to persist the changes to the db
		self.db_update()		
				
		idx = int(self.insurance_starts_on)

		# iterate every insurance repayment to map it and add its amount
		# to the insurance field in the repayment table
		# get the first repayment that has not insurance and its payment date
		# is very first one after the start date of the insurance coverage
		
		for index, insurance in enumerate(self.cuotas):

			loan_row = frappe.get_doc(
				"Tabla Amortizacion",
				{
					"parent": self.loan,
					"idx": idx,
				},
			)

			if loan_row.estado == FULLY_PAID:
				frappe.throw("El pagare No. {0} ya se ha saldado, por lo que no sera posible \
					cobrarle a cliente en este pagare!".format(loan_row.idx))

			loan_row.insurance = insurance.amount

			# pending_amount will be what the customer has to pay for this repayment
			pending_amount = flt(loan_row.capital) + flt(loan_row.interes) + flt(loan_row.fine) + flt(loan_row.insurance)

			loan_row.monto_pendiente = pending_amount
		
			# ensures this repayment knows about this child
			loan_row.insurance_doc = insurance.name
			
			loan_row.db_update()

			idx += 1

		# return first_jv

	def create_first_payment(self):
		# Pagos completos de seguro
		from fm.accounts import add
		
		amount = self.initial_payment if self.get("financiamiento") else self.get("total_amount")
		
		if not self.get("financiamiento") and not self.get("total_amount"):
			frappe.throw("No es posible hacer una poliza en cero")

		if self.get("financiamiento") and not self.get("loan"):
			frappe.throw("No es posible hacer una poliza financiada sin un prestamo")

		if not amount: return 0.000

		conf = frappe.get_single("FM Configuration")
		branch_office = self.branch_office
		if self.loan:
			loan = frappe.get_doc("Loan", self.loan)
			branch_office = loan.branch_office
		
		jv = frappe.new_doc("Journal Entry")

		jv.update({
			"voucher_type":  self.mode_of_payment,
			"document":'POLIZA',
			"es_un_pagare": 1,
			"loan": self.loan or "",
			"company": frappe.db.get_single_value("Global Defaults", "default_company"),
			"branch_office": branch_office,
			# "posting_date": frappe.utils.nowdate(),
			"posting_date": self.payment_date,
			"cheque_no": "Cash Entry" if self.mode_of_payment == "Cash Entry" else self.payment_reference,
			"cheque_date": self.payment_date,
			"insurance": self.name,
			"poliza_de_seguro": self.name,
			"ttl_insurance": amount,
			"user_remark": "Pago inicial del seguro para poliza {0}".format(self.name)
		})		
		
		if self.financiamiento:
			add(jv, conf.payment_account, amount, True, "paid_amount")
			add(jv, conf.account_of_suppliers, amount, False, "insurance", "Supplier", self.insurance_company)
		else:
			add(jv, conf.payment_account, amount, True)
			add(jv, conf.customer_loan_account, amount, False, "insurance", "Customer", self.customer)
	
		jv.flags.ignore_permissions = True
		jv.submit()

		return jv.as_dict()	

	
	# def create_initial_payment(self):
	# 	from fm.accounts import add
		
	# 	conf = frappe.get_single("FM Configuration")
	# 	if self.get("financiamiento") and self.initial_payment == 0.00:
	# 		# no need to create any jv if no initial payment
	# 		return
	# 	amount = self.initial_payment if self.get("financiamiento") else self.get("total_amount")
	# 	# We need to register a full payment towards the supplier
	# 	jv = frappe.new_doc("Journal Entry")
	# 	jv.update({
	# 		"voucher_type": self.mode_of_payment,
	# 		"user_remark": "Pago Inicial Poliza de seguro",
	# 		"es_un_pagare": 1,
	# 		"loan": self.loan,
	# 		"company": frappe.db.get_value("Loan", self.loan, "company"),
	# 		# "posting_date": self.start_date,
	# 		# "posting_date": nowdate(),
	# 		"posting_date": self.payment_date,
	# 		"branch_office": self.branch_office,
	# 		"poliza_de_seguro": self.name,
	# 		"ttl_insurance": amount,
	# 	})
	# 	add(jv, conf.payment_account, amount, True, "paid_amount")
	# 	add(jv, conf.account_of_suppliers, amount, False, "insurance", "Supplier", self.insurance_company)
	# 	jv.save()
	# 	jv.submit()

	def on_cancel(self):
		"""Run after cancelation"""

		self.delete_event()
		self.delete_initial_payment()

		# let's check if this insurance was term financed
		if not self.get("financiamiento"):
			return 0 # let's just ignore and do nothing else

		# self.delete_payment()
		for index, insurance in enumerate(self.cuotas):
			# now, let's fetch from the database the corresponding repayment
			if frappe.db.exists("Tabla Amortizacion", { "insurance_doc": insurance.name }):
			
				loan_row = frappe.get_doc("Tabla Amortizacion", 
					{ "insurance_doc": insurance.name })

				# if by any chance the repayment status is not pending
				if not loan_row.estado in [PENDING, OVERDUE]:
					frappe.throw("No puede cancelar este seguro porque ya se ha efectuado en {} un pago en contra del mismo!".format(loan_row.idx))

				# unlink this insurance row from the repayment
				loan_row.insurance_doc = ""

				# clear any other amount
				loan_row.insurance = 0.000

				# Let's make sure we change paid amount only if was paid 
				if loan_row.monto_pagado > insurance.amount:
					loan_row.monto_pagado -= insurance.amount

				# pending amount will be what the customer has to pay for this repayment
				loan_row.monto_pendiente = loan_row.get_pending_amount()
				
				loan_row.db_update()		
		# self.delete_payment()
		self.delete_purchase_invoice()
		# finally let's update the status 
		self.status = "Inactivo"
	
	def delete_initial_payment(self):
		filters = {
			"poliza_de_seguro": self.name,
			"docstatus": 1,
		}
		if not frappe.db.exists("Journal Entry", filters):
			return
		
		doc = frappe.get_doc("Journal Entry", filters)
		doc.cancel()
		doc.delete()

	def is_paid(self):
		return True if not self.financiamiento or \
			not self.has_pending_payments() else False
		
	def has_pending_payments(self):
		return False if not self.cuotas or \
			not filter(lambda x: x.status != "SALDADO", self.cuotas) else True
		

	def delete_purchase_invoice(self):
		"""Delete the Purchase Invoice after cancelation of the Poliza de Seguro"""

		filters = { "poliza_de_seguro": self.name }

		for current in frappe.get_list("Purchase Invoice", filters):
			
			pinv = frappe.get_doc("Purchase Invoice", current.name)

			# check to see if it was submitted
			if pinv.docstatus == 1.000:

				# let's cancel it first
				pinv.cancel()

			pinv.delete()

	def create_event(self):
		event_exist = frappe.get_value("Event", 
			{ "starts_on": [">=", self.end_date], "ref_name": self.name })

		if event_exist:
			frappe.throw("Ya existe un evento creado para esta fecha para esta Poliza de Seguro!")

		customer_name = frappe.get_value("Loan", self.loan, "customer_name")

		event = frappe.new_doc("Event")

		event.all_day = 1L
		event.ref_type = self.doctype
		event.ref_name = self.name

		event.starts_on = self.end_date

		# set the subject for the event
		event.subject = "Vencimiento de seguro No. {0}".format(self.policy_no)

		# set the description for the event
		event.description = "El seguro de poliza No. {0} para el cliente {1} vence en esta fecha {2}.\
			El monto por el cual fue vendido es de {3} ${4} e inicio su vigencia el {5}. \
			Es un seguro {6} y esta relacionado con el vehiculo cuyo chasis es {7}.".format(
				self.policy_no, customer_name, self.end_date, self.currency, self.amount,
				self.start_date, self.tipo_seguro, self.asset
			)

		# append the roles that are going to be able to see this events 
		# in the calendar and in the doctype's view
		# event.append("roles", {
		# 	"role": "Cobros"
		# })

		# event.append("roles", {
		# 	"role": "Gerente de Operaciones"
		# })

		event.flags.ignore_permissions = True
		event.insert()

		return event

	def delete_payment(self):
		filters = { "insurance": self.name }
		if frappe.get_value("Journal Entry", filters):
			jv = frappe.get_doc("Journal Entry", filters)

			if jv.docstatus == 1.000:
				jv.cancel()

			jv.delete()

	def delete_event(self):
		for current in frappe.get_list("Event", { "ref_name": self.name }):
			event = frappe.get_doc("Event", current.name)
			event.delete()
