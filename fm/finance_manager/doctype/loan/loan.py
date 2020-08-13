# -*- coding: utf-8 -*-
# Copyright (c) 2017, Soldeva, SRL and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import erpnext
from frappe import _
from frappe.utils import nowdate, flt
from erpnext.controllers.accounts_controller import AccountsController
from datetime import datetime
from fm.api import add_months
from frappe.utils import add_months
from frappe.desk.tags import DocTags
from frappe.utils.background_jobs import enqueue_doc

class Loan(AccountsController):
	def before_insert(self):
		existing_loan = frappe.get_value("Loan", {
			"loan_application": self.loan_application,
			"docstatus": ["!=", "2"]
		})

		self.closing_date = add_months(self.disbursement_date, self.repayment_periods)

		if existing_loan:
			frappe.throw(
				_("There is already a Loan against the Loan Application: %s" % self.loan_application)
			)

	def after_insert(self):
		self.update_application_status()

	def on_update_after_submit(self):
		if self.status in ['Recuperado', 'Incautado', 'Perdida Total', 'Legal']:
			
			if frappe.db.exists("Customer Portfolio", {"loan": self.name}):
				child = frappe.get_doc("Customer Portfolio", {"loan": self.name})
				enqueue_doc("Client Portfolio", child.parent, "remove_loan_from_portfolio")
			

	def validate(self):

		# let's validate that the user has filled up the required fields
		check_repayment_method(
			self.repayment_method, 
			self.loan_amount, 
			self.monthly_repayment_amount, 
			self.repayment_periods
		)

		# set missing values for hidden fields
		self.set_missing_values()

		# now let's fetch from the DB the maximum loan amount limit depending on the Loan Type
		maximum_loan_limit = frappe.db.get_single_value("FM Configuration", 'max_loan_amount_vehic' 
			if self.loan_type == "Vehicle" else 'max_loan_amount_vivienda')

		# throw an error if the loan amount is greater than what it should be
		if self.loan_amount > flt(maximum_loan_limit):
			frappe.throw(_("Loan Amount cannot exceed Maximum Loan Amount of {0}").format(maximum_loan_limit))

		if not self.company:
			self.company = erpnext.get_default_company()

		if not self.posting_date:
			self.posting_date = nowdate()

		self.validate_loan_amount()
		self.set_missing_values()

	def comment_loan_status_changed(self):
		msg = """
			<span>Cambió el estado de {} a {}.</span>
		""".format(self.old_status, self.new_status)

		self.add_comment("Updated", msg, frappe.session.user)

	def update_customer_info(self):
		customer_name, cedula = frappe.get_value("Customer", self.customer, ["customer_name", "cedula"])
		self.customer_name = customer_name
		self.customer_cedula = cedula

	def validate_loan_amount(self):

		if self.interest_type == "Simple":
			if not self.rate_of_interest: 	
				self.rate_of_interest = frappe.db.get_single_value("FM Configuration", "simple_rate_of_interest")

			self.make_simple_repayment_schedule()

		elif self.interest_type == "Composite":
			if not self.rate_of_interest:
				self.rate_of_interest = frappe.db.get_single_value("FM Configuration", "composite_rate_of_interest")

			self.set_repayment_period()
			self.make_repayment_schedule()

	def make_jv_entry(self):
		self.check_permission('write')
		journal_entry = frappe.new_doc('Journal Entry')
		curex = frappe.get_doc("Currency Exchange", {"from_currency": "USD", "to_currency": "DOP"})

		exchange_rate = curex.exchange_rate if self.customer_currency == "USD" else 0.000
		
		journal_entry.voucher_type = 'Bank Entry'
		journal_entry.user_remark = _('Desembolso de Prestamo: {0}').format(self.name)
		journal_entry.company = self.company
		journal_entry.loan = self.name
		journal_entry.branch_office = self.branch_office
		journal_entry.cheque_no = self.asset
		# journal_entry.posting_date = journal_entry.cheque_date = nowdate()
		journal_entry.posting_date = journal_entry.cheque_date = self.posting_date
		# journal_entry.cheque_date = nowdate()
		journal_entry.document = "DESEMBOLSO"

		journal_entry.multi_currency = 1.000 if self.customer_currency == "USD" else 0.000

		account_amt_list = []

		# let's calculate some values
		legal_expenses_amount = self.loan_amount - self.gross_loan_amount
		total_payable_interest = self.total_payment - self.loan_amount

		account_amt_list.append({
			"account": self.customer_loan_account,
			"party_type": "Customer",
			"party": self.customer,
			"debit_in_account_currency": self.total_payment,
			"reference_type": "Loan",
			"reference_name": self.name,
			"exchange_rate": exchange_rate,
			"debit": self.total_payment * exchange_rate
		})

		account_amt_list.append({
			"account": self.disbursement_account,
			"credit_in_account_currency": self.gross_loan_amount,
			"exchange_rate": exchange_rate,
			"debit": self.total_payment * exchange_rate
		})

		account_amt_list.append({
			"account": self.expenses_account,
			"credit_in_account_currency": legal_expenses_amount,
			"exchange_rate": exchange_rate,
			"debit": self.total_payment * exchange_rate
		})

		account_amt_list.append({
			"account": self.interest_income_account,
			"credit_in_account_currency": total_payable_interest,
			"exchange_rate": exchange_rate,
			"debit": self.total_payment * exchange_rate
		})

		# let's put the totals too
		journal_entry.total_debit = self.total_payment
		journal_entry.total_credit = legal_expenses_amount \
			+ total_payable_interest \
			+ self.gross_loan_amount

		journal_entry.set("accounts", account_amt_list)
		return journal_entry.as_dict()

	def add_fine_discount_to_row(self, doctype, docname, fine_discount):

		if not frappe.db.exists(doctype, docname):
			frappe.throw("¡No se encontro el pagare buscado!")
			
		row = frappe.get_doc(doctype, docname)

		if row.estado == "SALDADA":
			frappe.throw("¡No es posible agregar descuentos a un pagare saldado!")
			
		if row.fine < fine_discount: 
			frappe.throw("¡El descuento a mora no debe ser mayor a la mora!")

		row.monto_pendiente -= fine_discount
		row.fine_discount += fine_discount

		if row.monto_pendiente < 0:
			frappe.throw("¡El monto pendiente no puede quedar negativo!")

		if row.fine_discount < 0:
			frappe.throw("¡El descuento en mora no puede quedar negativo!")
		self.add_comment("Updated", "<span> agregó ${} de descuento a la mora del pagare No. {} </span>".format(fine_discount, row.idx), frappe.session.user)
		row.db_update()
		self.reload()

	def make_payment_entry(self):
		self.check_permission('write')
		return make_payment_entry(self.doctype, self.name, self.monthly_repayment_amount)

	def get_balance_to_close(self):
		
		capital = interes = fine = pendiente = insurance = 0

		for rows in frappe.get_list("Tabla Amortizacion", {"parent":self.name, "estado":["!=", "SALDADA"]}):
			row = frappe.get_doc("Tabla Amortizacion", rows.name)

			pendiente += row.monto_pendiente
			capital += row.capital
			interes += row.interes
			fine += row.fine
			insurance += row.insurance

		return {"capital": capital, "interes": interes, "fine": fine, "insurance": insurance, "pendiente": pendiente}

	def make_simple_repayment_schedule(self):
		import fm.accounts
		fm.accounts.make_simple_repayment_schedule(self)
		
	def make_fake_repayment_schedule(self, capital, interes):
		capital_acumulado = capital = flt(capital)
		interes_acumulado = interes = flt(interes)
		repayment_amount = self.monthly_repayment_amount = capital + interes 
		balance_capital = capital * self.repayment_periods
		balance_interes = self.total_interest_payable = interes * self.repayment_periods
		pagos_acumulados = repayment_amount
		self.total_payment	=  repayment_amount	* self.repayment_periods

		rows = frappe.get_list('Tabla Amortizacion', {'parent': self.name}, ['name', 'idx'] )
		# No se como estan guardados en la base de datos, dejame organizarlos por idx
		rows = sorted(rows,  key = lambda k: k['idx'])
		for pago in rows:
			row = frappe.get_doc('Tabla Amortizacion', pago.name)
			row.cuota = repayment_amount  
			row.capital = capital  
			row.interes = interes
			row.balance_capital = balance_capital   
			row.balance_interes = balance_interes
			row.capital_acumulado = capital_acumulado   
			row.interes_acumulado = interes_acumulado 
			row.pagos_acumulados  = pagos_acumulados
			# Calculo de nuevo el monto pendiente, te recomiento que corras el scheduler para recalcular la mora
			row.monto_pendiente	  = repayment_amount
			row.fine = 0
			balance_capital -= capital
			balance_interes -= interes
			capital_acumulado += capital
			interes_acumulado += interes
			pagos_acumulados  += repayment_amount

			row.db_update()
		self.db_update()
		print("Success!, I strongly suggest you to run the scheduler again to calculate fines")

	def make_repayment_schedule(self):
		self.repayment_schedule = []
		payment_date = self.disbursement_date
		balance_amount = self.loan_amount
		counter = 0
		while(balance_amount > 0.000):
			interest_amount = balance_amount * flt(self.rate_of_interest) / (12.000 * 100.000)
			principal_amount = self.monthly_repayment_amount - interest_amount
			balance_amount = balance_amount + interest_amount - self.monthly_repayment_amount

			if balance_amount < 0.000:
				principal_amount += balance_amount
				balance_amount = 0.000

			total_payment = principal_amount + interest_amount

			self.append("repayment_schedule", {
				"payment_date": payment_date,
				"principal_amount": principal_amount,
				"interest_amount": round(interest_amount),
				"total_payment": total_payment,
				"balance_loan_amount": round(balance_amount)
			})

			payment_date = add_months(self.disbursement_date, counter)
			counter += 1

	def set_missing_values(self):
		from fm.api import from_en_to_es

		if not self.customer_cedula:
			self.customer_cedula = frappe.db.get_value("Customer", self.customer, "cedula")

		for row in self.repayment_schedule:
			if isinstance(row.fecha, basestring):
				row.fecha_day = row.fecha.split("-")[2]
				row.fecha_year = row.fecha.split("-")[0]
			else:
				row.fecha_day = row.fecha.day
				row.fecha_year = row.fecha.year

		if not self.posting_date_str:
			# ok, let's validate if the posting date is a string
			if isinstance(self.posting_date, basestring):
				# it is a string, so let's convert to a datetime object
				self.posting_date = datetime.strptime(self.posting_date, "%Y-%m-%d")

			self.posting_date_str = '{0}, {4} ({1:%d}) del mes de {2} del año {3} ({1:%Y})'.format(
				from_en_to_es("{0:%A}".format(self.posting_date)),
				self.posting_date,
				from_en_to_es("{0:%B}".format(self.posting_date)),
				frappe.utils.num2words(self.posting_date.year, lang='es').upper(),
				frappe.utils.num2words(self.posting_date.day, lang='es').upper()
			)

			self.end_date = add_months(self.posting_date, self.repayment_periods)

			self.end_date_str = '{0}, {4} ({1:%d}) del mes de {2} del año {3} ({1:%Y})'.format(
				from_en_to_es("{0:%A}".format(self.end_date)),
				self.end_date,
				from_en_to_es("{0:%B}".format(self.end_date)),
				frappe.utils.num2words(self.end_date.year, lang='es').upper(),
				frappe.utils.num2words(self.end_date.day, lang='es').upper()
			)

			self.posting_date = self.posting_date.strftime("%Y-%m-%d")

	def set_repayment_period(self):
		if self.repayment_method == "Repay Fixed Amount per Period":
			repayment_periods = len(self.repayment_schedule)

			self.repayment_periods = repayment_periods

	def next_repayment(self, by_insurance=False, with_date=None):
		if by_insurance and not with_date:
			frappe.throw("<i>With Date</i> argument is mandatory if <i>By Insurance</i> is provided")

		for repayment in self.repayment_schedule:
			if (by_insurance and not repayment.insurance and str(repayment.fecha) >= with_date) \
				or (not by_insurance and repayment.monto_pendiente):

				# the first found in the table
				return repayment

	# to update the loan application status
	def update_application_status(self):
		appl = frappe.get_doc("Loan Application", self.loan_application)

		if not self.docstatus == 2:
			# if loan is in draft or submitted, change the status of the appl
			appl.status = "Linked"
			appl.parent = "Linked"

		else:
			# if loan is cancelled then change the status application
			appl.status = "Approved"
			appl.parent = None

			# also, unlink the loan application
			self.loan_application = None

		# finally update the database
		appl.db_update()

	def on_cancel(self):
		self.update_application_status()
		
	def on_trash(self):
		if self.loan_application:
			appl = frappe.get_doc("Loan Application", self.loan_application)
			appl.status = "Approved"
			
			# finally update the database
			appl.db_update()

	def update_disbursement_status(self):
		disbursement = get_disbursed_amount(self.name)

		if disbursement.disbursed_amount == self.total_payment:
			self.status = "Fully Disbursed"
			# frappe.msgprint("Status is Fully Disbursed")
			
		if disbursement.disbursed_amount == 0.000:
			self.status = "Sanctioned"
			# frappe.msgprint("Status is Sanctioned")

		if disbursement.disbursed_amount < self.total_payment and not disbursement.disbursed_amount == 0.000:
			self.status = "Partially Disbursed"
			# frappe.msgprint("Status is Partially Disbursed")

		total_outstanding_amount = get_total_outstanding_amount(self.name)

		if total_outstanding_amount == 0.000:
			self.status = "Repaid/Closed"
			if not self.closed_date:
				self.closed_date = frappe.utils.today()
			# frappe.msgprint("Status is Repaid/Closed")
	
	def reload_disbursement_status(self):
		self = frappe.get_doc(self.doctype, self.name)
		
		self.update_disbursement_status()
		
		for row in self.repayment_schedule:
			if row.estado == "SALDADA":
				continue
			row.monto_pendiente = row.get_pending_amount()
			row.update_status()
			row.db_update()
		
		self.db_update()

		frappe.db.commit()
		
	def update_payment_date(self, disbursement_date):
		#this function allows the user to change the payment date for all repayments so the customer can pay on-time
		self.disbursement_date = disbursement_date
		self.db_update()
		for i in frappe.get_list("Tabla Amortizacion", {"parent":self.name}):
			row = frappe.get_doc("Tabla Amortizacion", i.name)
			tmp = frappe.utils.add_months(self.disbursement_date, row.idx)
			print("Loan:{} idx:{} fecha:{} updated to:{} ".format(row.parent, row.idx, row.fecha, tmp))
			row.fecha = tmp
			row.db_update()

		self.add_comment("Updated", "<span> cambió la fecha de pago de los dias {} de cada mes. </span>".format(str(self.disbursement_date)[-2:]), frappe.session.user)
		self.reload()	

	def update_next_payment_date(self, next_date, idx):
		
		next_repayment = frappe.get_doc("Tabla Amortizacion", {"parent": self.name, "idx": idx})

		#Let's make sure the new date is greater than the existing one
		# if str(next_repayment.fecha) > next_date:
		# 	frappe.msgprint(_("New date must be after current repayment date"))
		# 	return

		next_repayment.fecha = next_date
		next_repayment.db_update()

		for name, in frappe.get_list("Tabla Amortizacion", {"parent": self.name, "idx": [">", next_repayment.idx]}, as_list=True):
			repayment = frappe.get_doc("Tabla Amortizacion", name)
			repayment.fecha = add_months(str(next_date), repayment.idx - next_repayment.idx)
			repayment.db_update()

		self.add_comment("Updated", "<span> cambió las fecha de la cuota {} a {} y todas las cuotas siguientes. </span>".format(next_repayment.idx, next_date), frappe.session.user)
		self.reload()	

	def get_past_due_balance(self, date=None):
		if not date:
			date = nowdate()

		return frappe.db.sql("""
			SELECT 
				IFNULL(SUM(monto_pendiente), 0)
			FROM 
				`tabTabla Amortizacion`
			WHERE
				`tabTabla Amortizacion`.parent = %s
			AND
				`tabTabla Amortizacion`.fecha < %s
		""", (self.name, date), debug=False)[0][0]
	
	def get_paid_amount(self, from_date=None, to_date=None):
		
		if not from_date:
			from_date = "1900-01-01"

		if not to_date:
			to_date = nowdate()
			
		return frappe.db.sql("""
			SELECT 
				IFNULL(SUM(total_debit), 0)
			FROM 
				`tabJournal Entry`
			WHERE
				`tabJournal Entry`.es_un_pagare = 1
			AND
				`tabJournal Entry`.docstatus = 1
			AND
				`tabJournal Entry`.loan = %s
			AND
				`tabJournal Entry`.posting_date >= %s
			AND
				`tabJournal Entry`.posting_date <= %s
		""", (self.name, from_date, to_date), debug=False)[0][0]


def check_repayment_method(repayment_method, loan_amount, monthly_repayment_amount, repayment_periods):
	if repayment_method == "Repay Over Number of Periods" and not repayment_periods:
		frappe.throw(_("Please enter Repayment Periods"))
		
	if repayment_method == "Repay Fixed Amount per Period":
		if not monthly_repayment_amount:
			frappe.throw(_("Please enter repayment Amount"))

		if monthly_repayment_amount > loan_amount:
			frappe.throw(_("Monthly Repayment Amount cannot be greater than Loan Amount"))

def get_monthly_repayment_amount(interest_type, repayment_method, loan_amount, rate_of_interest, repayment_periods):
	if interest_type == "Composite": 	
		if rate_of_interest:
			monthly_interest_rate = flt(rate_of_interest) / 100.0
			return round((loan_amount * monthly_interest_rate *
				(1 + monthly_interest_rate)**repayment_periods) \
				/ ((1 + monthly_interest_rate)**repayment_periods - 1))
	elif rate_of_interest == "Simple":
		return round(flt(loan_amount) / repayment_periods)

def get_disbursed_amount(loan, es_pagare=False):
	return frappe.db.sql("""SELECT journal.posting_date, 
		IFNULL(SUM(general.credit_in_account_currency), 0.000) AS  disbursed_amount
		FROM `tabGL Entry` AS general 
		JOIN `tabJournal Entry` AS journal 
		ON journal.name = general.voucher_no 
		WHERE journal.loan = '{0}'
		AND journal.es_un_pagare = {1}""".format(loan, 1.000 if es_pagare else 0.000),
		as_dict=True)[0]

def get_total_outstanding_amount(loan):
	return frappe.db.sql("""SELECT IFNULL(SUM(monto_pendiente), 0) AS total_oustanding_amount
		FROM `tabTabla Amortizacion` 
		WHERE parent = '%s'""" % loan, 
	as_dict=False)[0][0]

@frappe.whitelist()
def get_loan_application(loan_application):
	return frappe.get_doc("Loan Application", loan_application)

@frappe.whitelist()
def make_jv_entry(customer_loan, company, customer_loan_account, customer, loan_amount, payment_account):
	journal_entry = frappe.new_doc('Journal Entry')
	journal_entry.voucher_type = 'Bank Entry'
	journal_entry.user_remark = _('Desembolso de Prestamo: {0}').format(customer_loan)
	journal_entry.company = company
	journal_entry.posting_date = nowdate()

	account_amt_list = []

	account_amt_list.append({
		"account": customer_loan_account,
		"debit_in_account_currency": loan_amount,
		"reference_type": "Loan",
		"reference_name": customer_loan,
		})
	account_amt_list.append({
		"account": payment_account,
		"credit_in_account_currency": loan_amount,
		"reference_type": "Loan",
		"reference_name": customer_loan,
		})
	journal_entry.set("accounts", account_amt_list)
	return journal_entry.as_dict()

@frappe.whitelist()
def make_payment_entry(doctype, docname, paid_amount):
	from erpnext.accounts.utils import get_account_currency
	frappe.has_permission('Payment Entry', throw=True)

	loan = frappe.get_doc(doctype, docname)

	party_type = "Customer"

	party_account_currency = get_account_currency(loan.customer_loan_account)
	customer_currency = frappe.db.get_value("Customer", loan.customer, "default_currency")
	
	# amounts
	grand_total = loan.monthly_repayment_amount

	outstanding_amount = grand_total - paid_amount
	row = loan.next_repayment()

	payment = frappe.new_doc("Payment Entry")
	payment.payment_type = "Receive"
	payment.company = loan.company
	payment.loan = loan.name
	payment.insurance = loan.vehicle_insurance
	payment.posting_date = nowdate()
	payment.mode_of_payment = loan.mode_of_payment
	payment.party_type = party_type
	payment.party = loan.customer
	payment.paid_from = loan.customer_loan_account
	payment.paid_to = loan.payment_account
	payment.paid_from_account_currency = party_account_currency
	payment.paid_to_account_currency = party_account_currency
	payment.paid_amount = paid_amount + row.fine
	payment.mora = row.fine
	payment.pagare = row.idx
	payment.received_amount = paid_amount
	payment.allocate_payment_amount = 1

	# payment.es_un_pagare = 1

	if not customer_currency == frappe.defaults.get_global_default("currency"):
		payment.multi_currency = 1

	# cuotas
	payment.append("references", {
		"reference_doctype": doctype,
		"reference_name": docname,
		"due_date": row.fecha,
		"total_amount": grand_total,
		"outstanding_amount": outstanding_amount,
		"allocated_amount": outstanding_amount
	})
	
	return payment
