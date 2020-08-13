# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
import fm.api

from frappe import _
from datetime import datetime
from fm.api import *
from frappe.utils import flt

from fm.finance_manager.doctype.loan.loan import get_monthly_repayment_amount

def submit_journal(doc, event):
	if doc.loan and not doc.es_un_pagare:

		# load the loan from the database
		loan = frappe.get_doc("Loan", doc.loan)

		curex = frappe.get_doc("Currency Exchange", {
			"from_currency": "USD",
			"to_currency": "DOP"
		})

		if not loan.total_payment == doc.total_debit:
			frappe.throw("¡El monto desembolsado difiere del monto del prestamo!")

		# call the update status function 
		loan.update_disbursement_status()

		# update the database
		loan.db_update()
	elif doc.loan and doc.es_un_pagare and doc.get("create_jv"):
		
		# let's create a purchase invoice
		if flt(doc.gps):
			fm.api.create_purchase_invoice( doc.gps, "GPS", doc.name)
		
		if flt(doc.gastos_recuperacion):
			fm.api.create_purchase_invoice( doc.gastos_recuperacion, "Recuperacion", doc.name)

		loan = frappe.get_doc("Loan", doc.loan)

		row = loan.next_repayment() or\
			frappe.throw("""<h4>Parece que este prestamo no tiene mas pagares.</h4>
				<b>Si esta pagando multiples cuotas, es probable que el monto que este digitando
				sea mayor al monto total pendiente del prestamo.</b>""")

		capital = row.capital
		interes = row.interes

		make_payment_entry({
			"doctype": "Loan",
			"docname": doc.loan,
			"paid_amount": doc.total_debit,
			"capital_amount": capital,
			"interest_amount": interes,
			"fine": doc.fine,
			"fine_discount": doc.fine_discount,
			"insurance": doc.insurance_amount,
			"validate_payment_entry": True,
			"create_jv": False
		})

		# let's update the status if necessary
		# call the update status function
		loan.update_disbursement_status()
		# update the database

		loan.db_update() 

def generate_repayment_breakup(doc, event=None):
	import json

	if not doc.repayments_dict:
		return

	titles = ['Prestamo', 'Pagare', 'Monto Pagado', 'Mora', 'Seguro']

	headers = ''
	rows = ''
	repayment_details =  json.loads(
		doc.repayments_dict.replace("u'", "'").replace("'", "\"")
	)

	for title in titles:
		headers += add_el('th', title)

	headers = add_el('tr', headers)
	for row in repayment_details:
		tr = ''
		fine = .00
		idx = frappe.db.get_value("Tabla Amortizacion", row.get('name'), "idx")
		if row.get('fine_before'):
			fine = row.get('fine_before') if row.get('fine_before') <= row.get('monto_pagado') else row.get('monto_pagado')
		tr += add_el('td', doc.loan)
		tr += add_el('td', idx)
		tr += add_el('td', row.get('monto_pagado'))
		tr += add_el('td', fine)
		tr += add_el('td', row.get('insurance_paid') or .000)
		
		rows += add_el('tr', tr)

	doc.repayment_breakup = add_el(
		'table',
		headers + rows,
		'table table-bordered'
	)

def check_duplicate_disbursement(doc, event):
	# Prevenir recibos mientras trabajo
	working = 0
	if working and frappe.session.user != "Administrator":
		frappe.throw("El administrador esta trabajando en el sistema, favor esperar algunos minutos")

	# Prevenir  desembolsos duplicados
	if doc.es_un_pagare:
		return 

	response = frappe.db.sql("""
		SELECT
			count(1)
		FROM
			`tabJournal Entry`
		WHERE 
			loan = %s
		AND	
			es_un_pagare = 0
		AND
			docstatus = 1
	""", doc.loan)[0][0]

	if not response:
		return

	frappe.throw("""El prestamo {} ya tiene un desembolso,
		vaya al prestamo y presione el boton de refrescar
	""".format(doc.loan))


def add_el(element, data, cls=''):
	return "<{0}>{1}</{0}>".format(element, data) if not cls else \
		"<{0}  class='{2}'>{1}</{0}>".format(element, data, cls)

def check_previous_jv(doc, event):
	sub_entries = frappe.db.sql("""
		SELECT 
			count(1)
		FROM
			`tabJournal Entry`
		WHERE
			loan = %s
		AND
			docstatus = 1
		AND
			name > %s
	""", (doc.loan, doc.name), debug=False)[0][0]

	if sub_entries > 0:
		frappe.throw("""
			Debes cancelar los {} pagos validados anteriores a este!
		""".format(sub_entries))

def cancel_journal(doc, event):
	if not doc.loan:
		return 0.000 # exit code is zero
	# let's make sure this is the last journal entry
	if doc.es_un_pagare == 1:
		check_previous_jv(doc, event)

	# let's check if it has any linked purchase invoice 
	pinv_list = frappe.get_list("Purchase Invoice", { "linked_doc": doc.name })

	for current in pinv_list:
		pinv = frappe.get_doc("Purchase Invoice", current.name)

		if pinv.docstatus == 1:
			pinv.cancel()
			
		pinv.delete()

	filters = { 
		"loan": doc.loan,
		"es_un_pagare": "1",
		"docstatus": "1",

	}

	if not doc.es_un_pagare:

		if frappe.get_list("Journal Entry", filters):
			frappe.throw("No puede cancelar este desembolso con pagares hechos!")
	
		# load the loan from the database
		loan = frappe.get_doc("Loan", doc.loan)

		# call the update status function
		loan.update_disbursement_status()

		# update the database
		loan.db_update()

		return 0.000 # to exit the function
			
	else: 
		update_repayment_amount(doc)

	refresh_loan_totals(doc.loan)
	return 0.000 # to exit the function
	
	
def update_repayment_amount(doc):
	import json

	dt = "Tabla Amortizacion"
	ins_dt = "Insurance Repayment Schedule"
	loan = frappe.get_doc("Loan", doc.loan)

	repayment_details =  json.loads(doc.repayments_dict.replace("u'", "'").replace("'", "\"")) if doc.repayments_dict else ""

	for current in repayment_details:
		row = frappe.get_doc(dt, current.get("name"))
		
		insurance = ''
		if frappe.db.exists(ins_dt, current.get("insurance_name")):
			insurance = frappe.get_doc(ins_dt, current.get("insurance_name"))
		
		# let see if we're canceling the jv
		if doc.docstatus == 2.000:
			row.monto_pendiente = flt(current.get("monto_pendiente_before"))
			row.monto_pagado = flt(current.get("monto_pagado_before"))
			row.fine = flt(current.get("fine_before"))

			if insurance:
				insurance.paid_amount = flt(current.get("insurance_before"))
				insurance.calculate_pending_amount()
				insurance.update_status()
				insurance.db_update()

			# let's make sure we update the status to the corresponding
			# row in the insurance doc
			# fm.api.update_insurance_status("PENDIENTE", row.insurance_doc)
		row.update_status()

		# save to the database
		row.db_update()

	loan.update_disbursement_status()
	loan.db_update()

def get_repayment_details(self):

	# validate that the interest type is simple
	if self.interest_type == "Simple":
		return get_simple_repayment_details(self)

	elif self.interest_type == "Composite":
		return get_compound_repayment_details(self)		

def get_simple_repayment_details(self):
	# if there's not rate set
	if not self.rate_of_interest: 	
		# now let's fetch from the db the default rate for interest simple
		self.rate_of_interest = frappe.db.get_single_value("FM Configuration", "simple_rate_of_interest")

	# convert the rate of interest to decimal
	self.rate = flt(self.rate_of_interest) / 100.000

	# total interest using the simple interest formula
	self.total_payable_interest = self.loan_amount * self.rate * self.repayment_periods

	# calculate the monthly interest
	self.monthly_interest = flt(self.loan_amount * self.rate)

	# calculate the monthly capital
	self.monthly_capital = flt(self.loan_amount) / flt(self.repayment_periods)

	# get the monthly repayment amount
	self.monthly_repayment_amount = self.monthly_interest + self.monthly_capital

	# calculate the total payment
	self.total_payable_amount = self.loan_amount + self.total_payable_interest

def get_compound_repayment_details(self):
	# if there's not rate set
	if not self.rate_of_interest: 
		# now let's fetch from the db the default rate for interest compound
		self.rate_of_interest = frappe.db.get_single_value("FM Configuration", "composite_rate_of_interest")
	
	if self.repayment_method == "Repay Over Number of Periods":
		self.repayment_amount = get_monthly_repayment_amount(
				self.interest_type,
				self.repayment_method, 
				self.loan_amount, 
				self.rate_of_interest,
				self.repayment_periods
			)

	self.calculate_payable_amount()

def make_simple_repayment_schedule(self):
	from fm.api import from_en_to_es
	
	# let's get the loan details
	get_repayment_details(self)
	
	# let's clear the table
	self.repayment_schedule = []

	# set defaults for this variables
	capital_balance = self.loan_amount
	interest_balance = self.total_payable_interest

	pagos_acumulados = interes_acumulado = 0.000
	capital_acumulado = 0.000

	# payment_date = self.get("disbursement_date") or self.get("posting_date")
	initial_date = self.get("disbursement_date") or self.get("posting_date")

	# map the values from the old variables
	self.total_payment = self.total_payable_amount
	self.total_interest_payable = self.total_payable_interest

	# fetch from the db the maximun pending amount for a loan
	maximum_pending_amount = frappe.db.get_single_value("FM Configuration", "maximum_pending_amount")
	# numero de la cuota
	idx = 1
	# ok, now let's add the records to the table
	while(capital_balance > flt(maximum_pending_amount)):

		monthly_repayment_amount = self.monthly_repayment_amount

		cuota =  round(self.monthly_capital + self.monthly_interest)
			
		capital_balance -= round(self.monthly_capital)
		interest_balance -= cuota - round(self.monthly_capital)
		pagos_acumulados += round(monthly_repayment_amount)
		interes_acumulado += cuota - round(self.monthly_capital)
		capital_acumulado += round(self.monthly_capital)

		# start running the dates
		payment_date = frappe.utils.add_months(initial_date, idx)
		payment_date_obj = payment_date
		idx += 1
		if isinstance(payment_date, basestring):
			payment_date_obj = datetime.strptime(payment_date, frappe.utils.DATE_FORMAT)

		payment_date_str = payment_date_obj.strftime(frappe.utils.DATE_FORMAT)

		if capital_balance < 0.000 or interest_balance < 0.000:
			capital_balance = interest_balance = 0.000

			if len(self.repayment_schedule) >= int(self.repayment_periods):
				self.repayment_periods += 1
		
		self.append("repayment_schedule", {
			"fecha": payment_date_str,
			"cuota": cuota,
			"monto_pendiente": cuota,
			"show_capital": round(self.monthly_capital),
			"capital": round(self.monthly_capital),
			"interes": cuota - round(self.monthly_capital),
			"show_interes": cuota - round(self.monthly_capital),
			"balance_capital": round(capital_balance),
			"balance_interes": round(interest_balance),
			"capital_acumulado": round(capital_acumulado),
			"interes_acumulado": round(interes_acumulado),
			"pagos_acumulados": pagos_acumulados,
			"fecha_mes": from_en_to_es("{0:%B}".format(payment_date_obj)),
			"estado": PENDING
		})

	# round the amounts
	self.monthly_repayment_amount = round(self.monthly_repayment_amount)
	self.total_payment = round(self.total_payable_amount)
	self.total_payable_amount = round(self.total_payable_amount)
	self.total_interest_payable = round(self.total_payable_interest)
	self.total_payable_interest = round(self.total_payable_interest)

@frappe.whitelist()
def loan_disbursed_amount(loan):
	return frappe.db.sql("""SELECT IFNULL(SUM(debit_in_account_currency), 0.000) AS disbursed_amount 
		FROM `tabGL Entry` 
		WHERE against_voucher_type = 'Loan' 
		AND against_voucher = %s""", 
		(loan), as_dict=1)[0]

@frappe.whitelist()
def make_payment_entry(opts, create_jv=True):
	from erpnext.accounts.utils import get_account_currency
	# Let's check multiple request

	request = frappe.new_doc("Multiple Request Handler")
	too_soon = request.check_request()
	
	request.update({
		"method": "make_payment_entry",
		"reference_doctype": "Journal Entry",
	})
	request.save(ignore_permissions=True)
	
	if too_soon:
		return

	if isinstance(opts, basestring):
		import json
		opts = json.loads(opts)

	opts = frappe._dict(opts)

	if not opts.posting_date:
		opts.posting_date = frappe.utils.nowdate()

	opts.update({
		"idxs": [],
		"pagares": [],
		"repayment_details": []
	})

	# load the loan from the database to make the requests more
	# efficients as the browser won't have to send everything back
	loan = frappe.get_doc(opts.doctype, opts.docname)

	curex = frappe.get_value("Currency Exchange", 
		{"from_currency": "USD", "to_currency": "DOP"}, "exchange_rate")

	exchange_rate = curex if loan.customer_currency == "USD" else 0.000
	
	def update_series(new_name=None):
		
		last = frappe.db.sql("""
			SELECT 
				replace(max(name), 'JV-', '') as max 
			FROM 
				`tabJournal Entry`
		""")[0][0]
		
		current = last if not new_name else new_name

		frappe.db.sql("""
			UPDATE
				`tabSeries`
			SET
				`tabSeries`.current = %s
			WHERE
				`tabSeries`.name = 'JV-'
		"""% current, debug=False)

	def make(options):
		options = frappe._dict(options)
		party_type = "Customer"
		party_account_currency = get_account_currency(loan.customer_loan_account)
		today = frappe.utils.nowdate()
		# Variables for the print format
		ttl_paid = ttl_recuperacion = 0.00

		conf = frappe.get_single("FM Configuration")
		if loan.customer_currency == "USD":
			default_discount_account = conf.default_discount_account.replace("DOP","USD")

		insurance_supplier = frappe.get_value("Poliza de Seguro", { 
			"loan": loan.name,
			"docstatus": "1",
			"start_date": ["<=", today],
			"end_date": [">=", today] 
		}, "insurance_company") or\
		conf.default_insurance_supplier

		options.jv.update({
			"voucher_type": opts.mode_of_payment,
			"cheque_date": opts.reference_name and opts.reference_date,
			"cheque_no": opts.reference_name or "",
			"user_remark": opts.user_remark or 'Pagare de Prestamo: %s' % loan.name,
			"company": loan.company,
			"branch_office": loan.branch_office,
			"posting_date": opts.posting_date,
			"es_un_pagare": 1,
			"ttl_discounts": flt(opts.ttl_fine_discount) + flt(opts.other_discounts) ,
			"ttl_capital": opts.ttl_capital,
			"ttl_interest": opts.ttl_interest,
			"ttl_insurance": opts.ttl_insurance,
			"ttl_fine": opts.ttl_fine,
			"gastos_recuperacion": opts.gastos_recuperacion,
			"loan": loan.name
		})
		if options.paid_amount:
			add(options.jv, loan.payment_account, options.paid_amount, True, "paid_amount")

		if flt(options.gps) or flt(options.gastos_recuperacion):
			options.gps = flt(options.gps)
			options.gastos_recuperacion = flt(options.gastos_recuperacion)

		if flt(options.fine_discount):
			add(options.jv, conf.default_discount_account, options.fine_discount, True, "fine_discount")
		
		if flt(options.other_discounts):
			add(options.jv, conf.default_discount_account, options.other_discounts, True, "other_discounts")

		if flt(options.paid_amount or options.other_discounts):
			capital_amount = flt(options.paid_amount) - flt(options.gps) - flt(options.gastos_recuperacion)\
				- flt(options.jv.ttl_fine) - flt(opts.ttl_insurance) + flt(options.fine_discount) + flt(options.other_discounts)
			
			if capital_amount > 0:
				add(options.jv, loan.customer_loan_account, capital_amount, False, "capital", "Customer", loan.customer)
		
		if flt(opts.ttl_insurance):
			add(options.jv, conf.account_of_suppliers, opts.ttl_insurance, False, "insurance", "Supplier", opts.supplier)
			
		if flt(options.gps):
			add(options.jv, conf.goods_received_but_not_billed, options.gps, False, "gps")

		if flt(options.gastos_recuperacion):
			add(options.jv, conf.goods_received_but_not_billed, options.gastos_recuperacion, False, "gastos_recuperacion")

		if flt(options.ttl_fine):
			add(options.jv, conf.interest_on_loans, options.jv.ttl_fine, False, "fine")

		options.jv.repayments_dict = str(options.repayment_details)

		# frappe.errprint(options.jv.as_dict())
		
		if options.new_name:
			update_series(options.new_name - 1)
		
		try:
			options.jv.insert()
		except Exception as e:
			raise e
		finally:
			update_series()
		
		generate_repayment_breakup(opts.jv)

		if opts.validate_payment_entry:
			options.jv.submit()

		return options.jv

	received_amount_and_others = flt(opts.paid_amount) + flt(opts.other_discounts) \
		- (flt(opts.gps) + flt(opts.gastos_recuperacion))

	opts.ttl_fine = opts.ttl_fine_discount = opts.ttl_insurance = opts.ttl_capital = opts.ttl_interest = 0.00

	while received_amount_and_others > 0.000 and opts.validate_payment_entry:
		row = loan.next_repayment() or\
			frappe.throw("""<h4>Parece que este prestamo no tiene mas pagares.</h4>
				<b>Si esta pagando multiples cuotas, es probable que el monto que este digitando
				sea mayor al monto total pendiente del prestamo!</b>""")

		total_fine = frappe.get_value("Tabla Amortizacion", {
			"parent": row.parent, 
			"parenttype": row.parenttype,
			"parentfield": row.parentfield
		}, ["sum(fine)"]) or 0.000

		if flt(opts.fine_discount) and not total_fine:
			frappe.throw("¡No puede hacerle descuento a la mora si el cliente no tiene mora!")

		frappe.errprint("{} {}".format(opts.fine_discount,total_fine))
		if flt(opts.fine_discount) > total_fine:
			frappe.throw("¡No es posible hacer descuentos mayores a la mora! -> cuota {} discount:{} - total_fine:{}".format(row.idx, opts.fine_discount, total_fine) )
		
		# Si el monto pagado es menor a la mora
		if 	received_amount_and_others <= row.fine:
			paid_capital = paid_interest = dutty_without_capital = 0
			temp_monto_pagado = opts.fine = received_amount_and_others
			opts.ttl_fine += received_amount_and_others
			opts.ttl_fine_discount += row.fine_discount
			opts.ttl_interest = opts.ttl_capital = 0
			temp_fine = row.fine

			row.fine -= received_amount_and_others
			insurance_doc = ""
		else:
			dutty_amount = row.get_dutty_amount() 
			insurance_doc = ""
			insurance = .00
			
			if row.insurance_doc:
				insurance_doc = frappe.get_doc("Insurance Repayment Schedule", row.insurance_doc) 
				insurance_doc.calculate_pending_amount()
				opts.supplier = insurance_doc.get_supplier()
				
				if received_amount_and_others >= insurance_doc.pending_amount + row.fine:
					insurance = insurance_doc.pending_amount 
				else:
					insurance = received_amount_and_others - row.fine
			
			paid_capital  = received_amount_and_others - row.fine - insurance + row.fine_discount - row.interes
			paid_interest = received_amount_and_others - row.fine - insurance + row.fine_discount - paid_capital
			dutty_without_capital = insurance + row.fine + row.interes - row.fine_discount
			

			opts.ttl_fine += row.fine
			opts.ttl_fine_discount += row.fine_discount
			opts.ttl_insurance += insurance
			opts.ttl_interest += row.interes if received_amount_and_others >= dutty_without_capital else paid_interest
			opts.ttl_capital  +=  paid_capital

			temp_monto_pagado = row.monto_pendiente if received_amount_and_others > row.monto_pendiente else received_amount_and_others

			opts.partially_paid = received_amount_and_others if received_amount_and_others < dutty_amount else 0.000
			temp_fine = row.fine
		
			row.fine = 0.000 if received_amount_and_others >= row.fine  else row.fine - received_amount_and_others		
			# frappe.throw("Before: {} After: {} Received {} ".format(temp_fine, row.fine, received_amount_and_others))
		
		received_amount_and_others -= temp_monto_pagado
		
		opts.idxs += [str(row.idx)]
		opts.pagares += [str(row.name)]

		insurance_paid = ins_paid_before = .00
		
		if row.insurance_doc and insurance_doc:
			ins_paid_before = insurance_doc.paid_amount
			ins_pending = insurance_doc.pending_amount
			unallocated_amt = temp_monto_pagado - temp_fine
			if unallocated_amt > 0:
				insurance_paid = insurance_doc.make_payment(unallocated_amt)

		opts.repayment_details += [{
			"name": row.name,
			"insurance_name": row.insurance_doc or "-",
			"monto_pagado": temp_monto_pagado,
			"monto_pendiente_before": row.monto_pendiente,
			"monto_pagado_before": row.monto_pagado,
			"fine_before": temp_fine,
			"insurance_before": ins_paid_before,
			"insurance_paid": insurance_paid or .00,
		}]
		row.monto_pagado += temp_monto_pagado
		row.monto_pendiente -= temp_monto_pagado

		# if row.monto_pendiente:
		# 	fm.api.update_insurance_status("ABONO", row.insurance_doc)
		# else:
		# 	fm.api.update_insurance_status("SALDADO", row.insurance_doc)

		row.update_status()
		row.db_update()

	cuotas = ", ".join(opts.idxs) if len(", ".join(opts.idxs)) <= 15 else "-".join([opts.idxs[0],opts.idxs[-1]])
	pagares = ", ".join(opts.pagares)

	if create_jv:
		payment_entry = frappe.new_doc("Journal Entry")
		payment_entry.update({
			"pagare": pagares,
			"loan": loan.name,
			"branch_office": loan.branch_office,
			"partially_paid": opts.partially_paid,
			"amount_paid": fm.api.get_paid_amount_for_loan(loan.customer, loan.posting_date),
			"fine_discount": opts.fine_discount,
			"gps": opts.gps,
			"gastos_recuperacion": opts.recuperacion,
			"loan_amount": loan.total_payment,
			"pending_amount": fm.api.get_pending_amount_for_loan(loan.customer, loan.posting_date),
			"mode_of_payment": opts.mode_of_payment,
			"fine": opts.fine,
			"document": "PAGARE",
			"repayment_no": cuotas,
			"currency": loan.customer_currency,
			"ttl_discounts": opts.ttl_fine_discount,
			"ttl_insurance": opts.ttl_insurance,
			"ttl_capital": opts.ttl_capital,
			"ttl_interest": opts.ttl_interest,
			"ttl_fine": opts.ttl_fine,
		})

		# frappe.throw(str(opts))
		opts.jv = payment_entry
		payment_entry = make(opts)

	loan.update_disbursement_status()

	loan.db_update()
	refresh_loan_totals(loan.name)

	return payment_entry.name

@frappe.whitelist() # deprecated by Yefri 
def cashier_control(frm, data):
	import json
	# validate if the user has permissions to do this
	frappe.has_permission('Journal Entry', throw=True)

	# i received frm and data as string, let's decode and make it a dict 
	data = frappe._dict(json.loads(data))
	frm = frappe._dict(json.loads(frm))
	
	dop = flt(data.get("amount_dop")) if flt(data.get("amount_dop")) else 0.000    
	usd = flt(data.get("amount_usd")) if flt(data.get("amount_usd")) else 0.000    

	journal_entry = frappe.new_doc("Journal Entry")
	journal_entry.voucher_type = "Journal Entry"
	journal_entry.user_remark = _("{}".format(data.get("type")))
	journal_entry.company = data.get("company")
	journal_entry.posting_date = frappe.utils.nowdate()
	journal_entry.multi_currency = 1.000 if usd  else 0.000
	journal_entry.is_cashier_closing = 1
	journal_entry.document = "CIERREDECAJA"

	if dop:
		debit_account = frm.cashier_account if data.get("type") == "OPEN" else frm.bank_account
		credit_account = frm.bank_account if data.get("type") == "OPEN" else frm.cashier_account

		journal_entry.append("accounts", {
			"account": debit_account,
			"debit_in_account_currency": dop,
		})
		journal_entry.append("accounts", {
			"account": credit_account,
			"credit_in_account_currency": dop,
		})

	if usd:
		debit_account_usd = frm.cashier_account_usd if data.get("type") == "OPEN" else frm.bank_account_usd
		credit_account_usd = frm.bank_account_usd if data.get("type") == "OPEN" else frm.cashier_account_usd

		journal_entry.append("accounts", {
			"account": debit_account_usd,
			"debit_in_account_currency": usd,
		})
		journal_entry.append("accounts", {
			"account": credit_account_usd,
			"credit_in_account_currency": usd,
		})
	
	journal_entry.submit()
	
	frm.entries.insert(0, {
		"idx": 0,
		"date": frappe.utils.nowdate(),
		"user": frappe.session.user,
		"type": data.get("type"),
		"amount": dop,
		"amount_usd": usd,
		"reference": journal_entry.name
	})

	entries = []
	for idx, current in enumerate(frm.entries):
		current = frappe._dict(current)
		current.idx = idx + 1

		entries.append(current)

	frm.entries = entries
	return frm

def add(doc, account, amount, debit=True, repayment_field=None, party_type=None, party=None):
	row = doc.append("accounts", {
		"account": account,
		"credit_in_account_currency": 0.000 if debit else amount,
		"debit_in_account_currency":  amount if debit else 0.000,
		"party_type": party_type,
		"party": party,
		"repayment_field": repayment_field
	})

def refresh_loan_totals(loan):
	total_fine = total_pagado = total_pendiente = 0
	loan = frappe.get_doc("Loan", loan)
	for r in frappe.get_list("Tabla Amortizacion", {"parent":loan.name}):
		row = frappe.get_doc("Tabla Amortizacion", r.name)
		total_fine += row.fine
		total_pendiente += row.monto_pendiente
		total_pagado += row.monto_pagado
	loan.total_paid_fine = total_fine
	loan.total_paid_amount = total_pagado
	loan.db_update()
	
	
