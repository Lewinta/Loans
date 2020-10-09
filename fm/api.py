# -*- encoding: utf-8 -*-

import frappe
import requests
from frappe.utils import add_to_date

PENDING = "PENDIENTE"
FULLY_PAID = "SALDADA"
PARTIALLY_PAID = "ABONO"
OVERDUE = "VENCIDA"

# Loans with these statuses are not allowed on Client Portfolio

DISALLOWED_STATUSES = ['Legal', 'Recuperado', 'Incautado', 'Perdida Total', 'Repaid/Closed', 'Disponible']


def get_repayment(loan, repayment):
	for row in loan.repayment_schedule:
		if row.name == repayment:
			return row

def get_paid_amount(account, journal_entry, fieldname):

	result = 0.000
	for current in get_accounts_and_amounts(journal_entry):

		if account == current.account and fieldname == current.fieldname:
			return current.amount

	return result

def get_paid_amount2(account, journal_entry):

	result = 0.000
	for current in get_accounts_and_amounts2(journal_entry):

		if account == current.account:
			return current.amount

	return result

def get_accounts_and_amounts(journal_entry):
	return frappe.db.sql("""SELECT child.account, 
		child.credit_in_account_currency AS amount, child.repayment_field AS fieldname
	FROM 
		`tabJournal Entry` AS parent 
	JOIN 
		`tabJournal Entry Account` AS child 
	ON 
		parent.name = child.parent 
	WHERE 
		parent.name = '%s' 
	ORDER BY 
		child.idx""" 
	% journal_entry, as_dict=True)

def get_accounts_and_amounts2(journal_entry):
	return frappe.db.sql("""SELECT child.account, 
		child.credit_in_account_currency + child.debit_in_account_currency AS amount, child.repayment_field AS fieldname
	FROM 
		`tabJournal Entry` AS parent 
	JOIN 
		`tabJournal Entry Account` AS child 
	ON 
		parent.name = child.parent 
	WHERE 
		parent.name = '%s' 
	ORDER BY 
		child.idx""" 
	% journal_entry, as_dict=True)

def update_insurance_status(new_status, row_name):
	if frappe.get_value("Insurance Repayment Schedule", { "name": row_name }, "name"):
		insurance_row = frappe.get_doc("Insurance Repayment Schedule", row_name)

		insurance_row.status = new_status
		insurance_row.db_update()

def from_en_to_es(string):
	return {
		# days of the week
		"Sunday": "Domingo",
		"Monday": "Lunes",
		"Tuesday": "Martes",
		"Wednesday": "Miercoles",
		"Thursday": "Jueves",
		"Friday": "Viernes",
		"Saturday": "Sabado",

		# months of the year
		"January": "Enero",
		"February": "Febrero",
		"March": "Marzo",
		"April": "Abril",
		"May": "Mayo",
		"June": "Junio",
		"July": "Julio",
		"August": "Agosto",
		"September": "Septiembre",
		"October": "Octubre",
		"November": "Noviembre",
		"December": "Diciembre" 
	}[string]

def add_months(date, months):
	return add_to_date(date, months=months, as_datetime=True)

def get_time_based_name(serie=None):
	from datetime import datetime
	key = "%Y%m%d%H%M%S%f"
	if serie:
		key = "{}{}".format(serie, key)
	return datetime.now().strftime(key)

def get_voucher_type(mode_of_payment):
	# fetch the mode of payment type
	_type = frappe.db.get_value("Mode of Payment", mode_of_payment, "type")

	return {
		"General": "Journal Entry",
		"Bank": "Bank Entry",
		"Cash": "Cash Entry"
	}[_type]

@frappe.whitelist()
def next_repayment(loan):
	doc = frappe.get_doc("Loan", loan)
	return doc.next_repayment()

def get_exchange_rates(base):
	from frappe.email.queue import send

	URL = "http://openexchangerates.org/api/latest.json"

	ARGS = {
		# my app id for the service
		"app_id": frappe.db.get_single_value("FM Configuration", "app_id"), 
		# base currency that we are going to be working with
		"base": base
	}

	if not ARGS.get("app_id"):
		return 0 # exit code is zero
		
	# sending the request
	response = requests.get(url=URL, params=ARGS)

	# convert to json the response
	obj = response.json()

	rates = obj["rates"]

	if not rates:
		send(
			recipients=["yefritavarez@gmail.com"],
			sender="yefritavarez@gmail.com",
			subject="No rates when requesting to openexchangerates.org",
			message="There was an error while fetching today's rates",
			now=True
		)

	return rates


@frappe.whitelist()
def exchange_rate_USD(currency):
	from frappe.email.queue import send
	
	rates = get_exchange_rates('USD')

	exchange_rate = rates[currency]

	if not exchange_rate:
		send(
			recipients=['yefri@soldeva.com'],
			sender='yefritavarez@gmail.com',
			subject='Failed to find {currency} Currency'.format(currency=currency),
			message='We were unable to find the {currency} Currency in the rates list'.format(currency=currency),
			now=True
		)

		return 0.000

	return exchange_rate

@frappe.whitelist()
def get(doctype, name=None, filters=None):
	import frappe.client
	
	try:
		frappe.client.get(doctype, name, filters)
	except:
		pass
	
@frappe.whitelist()
def authorize(usr, pwd, reqd_level):
	from frappe.auth import check_password

	validated = False

	try:
		validated = not not check_password(usr, pwd)
	except:
		pass

	if validated:
		doc = frappe.get_doc("User", usr)

		role_list = [ row.role for row in doc.user_roles ]

		return reqd_level in role_list
	else: return False

@frappe.whitelist()
def get_currency(loan, account):
	return account if loan.customer_currency == "DOP" \
		else account.replace("DOP", "USD")

@frappe.whitelist()
def get_pending_repayments(loan_name):
	repayments = []
	pending = []

	if not loan_name:
		return False
	
	loan = frappe.get_doc("Loan", loan_name)

	pending = filter(
		lambda x: x.estado != "SALDADA",
		loan.repayment_schedule
	)
	repayments = [str(p.idx) for p in pending]
	
	return "\n".join(repayments)

def get_paid_amount_for_loan(customer, posting_date):
	result = frappe.db.sql("""SELECT IFNULL(SUM(child.credit_in_account_currency), 0.000) AS amount
		FROM `tabJournal Entry` AS parent 
		JOIN `tabJournal Entry Account` AS child 
		ON parent.name = child.parent 
		WHERE child.party = '%(customer)s'
		AND parent.posting_date >= '%(posting_date)s'""" % {
			"customer": customer, "posting_date": posting_date })

	return result[0][0]

def get_pending_amount_for_loan(customer, posting_date):
	result = frappe.db.sql("""SELECT (IFNULL(SUM(child.debit_in_account_currency), 0.000) # what he was given
			- IFNULL(SUM(child.credit_in_account_currency), 0.000)) AS amount  # vs. what's he's already paid
		FROM `tabJournal Entry` AS parent 
		JOIN `tabJournal Entry Account` AS child 
		ON parent.name = child.parent 
		WHERE child.party = '%(customer)s'
		AND parent.posting_date >= '%(posting_date)s'""" % { 
			"customer": customer, "posting_date": posting_date })

	return result[0][0]

def create_purchase_invoice( amount, item_type, docname, is_paid=1.00 ):
	import erpnext 
	company = frappe.get_doc("Company", erpnext.get_default_company())
	#Let's get the default supplier for the PINV
	supplier = frappe.db.get_single_value("FM Configuration", "default_{0}_supplier".format(item_type.lower()))

	if not supplier:
		frappe.throw("No se Encontro Ningun Suplidor para {0}".format(item_type))

	item = frappe.new_doc("Item")
	item_name = frappe.get_value("Item", { "item_group": item_type })

	# let's see if it exists
	if item_name:
		item = frappe.get_doc("Item", item_name)
	else:
		# ok, let's create it 
		item.item_group = item_type
		item.item_code = item.item_name = "%s Services" % item_type
		item.insert()

	if not supplier:
		frappe.throw("No se ha seleccionado un suplidor de {0}".format(item_type))

	pinv = frappe.new_doc("Purchase Invoice")

	pinv.supplier = supplier
	pinv.is_paid = 1.000
	pinv.company = company.name
	pinv.mode_of_payment = frappe.db.get_single_value("FM Configuration", "mode_of_payment")
	pinv.cash_bank_account = company.default_bank_account
	pinv.paid_amount = amount
	pinv.base_paid_amount = amount

	# ensure this doc is linked to the new purchase
	pinv.linked_doc = docname

	pinv.append("items", {
		"item_code": item.item_code,
		"is_fixed_item": 1,
		"item_name": item.item_name,
		"qty": 1,
		"rate": amount
	})

	pinv.flags.ignore_permissions = True
	pinv.submit()

	return pinv.name

def customer_autoname(doc, event):
	from fm.utilities import s_sanitize
	doc.name = s_sanitize(doc.customer_name)

def on_session_creation():
	msg = "User {} has now logged in at {}".format(frappe.session.user, frappe.utils.now_datetime())

	users = ["lewin.villar@gmail.com", "yefritavarez@gmail.com"]
	for user in users:
		frappe.publish_realtime(event="msgprint", message=msg, user=user)

def remove_fines_to_row(row):
	row.fine = row.mora_acumulada = .000
	row.monto_pendiente = row.get_pending_amount()
	row.db_update()
	return row.monto_pendiente

def add_fines_to_row(row, due_payments=1):
	from math import ceil
	remove_fines_to_row(row)
	row.fine = row.mora_acumulada = ceil(row.monto_pendiente * 0.1 * due_payments)
	row.db_update()
	return row.fine

def validate_repayment(repayment_name, ff=False):
	from frappe.utils import date_diff
	from frappe.utils import date_diff, nowdate, flt, add_days
	from math import ceil
	def get_payments(repayment_name):
		import json

		filters = {"docstatus":1, "repayments_dict":["like", "%%{}%%".format(repayment_name)]}
		fields  =  ["name", "repayments_dict", "posting_date"]
		result  = []

		for je in frappe.get_list("Journal Entry", filters, fields, order_by='posting_date'):
			repayments = json.loads(
				je.repayments_dict.replace("u'", "'").replace("'", "\"")
			)
			detail = filter(lambda x, name=repayment_name: x.get('name') == name, repayments )
			# print("{}\t{}".format(je.posting_date, detail[0].get('monto_pagado')))
			result.append({
				"name": str(je.name),
				"posting_date": str(je.posting_date),
				"paid_amount": detail[0].get('monto_pagado')
			})

		return result
	# End get_payments
	def calc_pending_amount(rpmt):
		monto_pendiente = (
			flt(rpmt.cuota) + \
			flt(rpmt.insurance) + \
			flt(rpmt.mora_acumulada) -\
			flt(rpmt.monto_pagado)
		)

		rpmt.update({
			"monto_pendiente": monto_pendiente
		})
		return rpmt
	# End calc_pending_amount	
	def apply_payment(rpmt, pymt):
		pymt = frappe._dict(pymt)
		if rpmt.payment_ref == pymt.name:
			return rpmt
		rpmt.update({
			"fine": .000 if pymt.paid_amount >= rpmt.fine else rpmt.fine - pymt.paid_amount,
			"monto_pagado":  rpmt.monto_pagado + pymt.paid_amount,
			"last_payment":  pymt.posting_date if str(pymt.posting_date) > str(rpmt.fecha) else 0,
			"payment_ref":  pymt.name,
		})
		rpmt = calc_pending_amount(rpmt)
		print("""\n***apply_payment***\nfine: {fine}\nmora_acumulada: {mora_acumulada}\nPagado: {monto_pagado}\nPendiente: {monto_pendiente}""".format(**rpmt))
		return rpmt
	# End apply_payment
	def calculate_fine(rpmt, payment):
		rpmt = frappe._dict(rpmt)
		pymt = frappe._dict(payment)
		fine_rate = frappe.db.get_value("Loan", rpmt.parent, "fine") / 100.0

		if str(pymt.posting_date) < str(rpmt.fecha):
			# Es un abono y solo hay que aplicar el pago
			# rpmt.update({
			# 	"monto_pagado": pymt.paid_amount,
			# })

			calc_pending_amount(pymt)
		else:
			# Debemos calcular la mora
			payment_date = rpmt.last_payment if rpmt.last_payment else add_days(rpmt.fecha, 5)
			due_date = add_days(rpmt.fecha, 5)
			date_difference = date_diff(pymt.posting_date, due_date)
			due_payments = ceil(date_difference / 30.000)
			new_fine = ceil(flt(fine_rate) * flt(rpmt.monto_pendiente) * due_payments)
			print("\npayment_date:{}\ndiff: {}\ndue: {}\nfine: {}\n".format(pymt.posting_date, date_difference, due_payments, new_fine))
			rpmt.update({
				"fine": new_fine,
				"mora_acumulada": new_fine,
				"subtotal": flt(rpmt.cuota) + flt(rpmt.insurance),
				"due_date": due_date,
				"last_payment": pymt.posting_date if str(pymt.posting_date) > str(rpmt.fecha) else 0,
			})
			
		calc_pending_amount(rpmt)

		print("""\n***calculate_fine***\nFecha: {fecha}\nDue Date: {due_date}\nCuota: {cuota}\nSeguro:{insurance}\nSubtotal:{subtotal}\nfine: {fine}\nmora_acumulada: {mora_acumulada}\nPagado: {monto_pagado}\nPendiente: {monto_pendiente}""".format(**rpmt))
			
		return rpmt
	# End calculate_fine
	def final_fine(rpmt):
		rpmt = frappe._dict(rpmt)
		fine_rate = frappe.db.get_value("Loan", rpmt.parent, "fine") / 100.0
		
		if str(rpmt.fecha) > nowdate():
			return rpmt
		date = rpmt.last_payment  if rpmt.last_payment else add_days(rpmt.fecha, 5)

		date_difference = date_diff(nowdate(), date)
		due_payments = ceil(date_difference / 30.000)
		new_fine = ceil(flt(fine_rate) * flt(rpmt.monto_pendiente) * due_payments)
		
		print("\ndiff: {}\ndue: {}\nfine: {}\n".format(date_difference, due_payments, new_fine))

		if new_fine < 0:
			frappe.throw("New fine for {parent} {idx} cannot be less than 0 ".format(**rpmt))

		
		rpmt.update({
			"fine": rpmt.fine + new_fine,
			"mora_acumulada":  rpmt.mora_acumulada + new_fine,
		})

		rpmt = calc_pending_amount(rpmt)
		print("""\n***final_fine***\nFecha: {fecha}\nFecha: {due_date}\nCuota: {cuota}\nSeguro:{insurance}\nfine: {fine}\nmora_acumulada: {mora_acumulada}\nPagado: {monto_pagado}\nPendiente: {monto_pendiente}""".format(**rpmt))
		return rpmt
	# End Final fine
	doc = frappe.get_doc("Tabla Amortizacion", repayment_name)
	
	rpmt = {
		"cuota": doc.cuota,
		"insurance": doc.insurance,
		"fecha": doc.fecha,
		"due_date": doc.due_date,
		"parent": doc.parent,
		"idx": doc.idx,
		"fine": .000,
		"mora_acumulada": .000,
		"monto_pagado": .000,
		"monto_pendiente": doc.cuota + doc.insurance,
		"last_payment": 0,
	}
	
	last_ref = ''
	last_trans = ''
	for paymt in get_payments(repayment_name):
		print("\n_____________")
		print("{parent}->{idx}".format(**doc.as_dict()))
		print("_____________")
		frappe.throw("before cal_fine".format(rpmt.monto_pagado))
		rpmt = calculate_fine(rpmt, paymt)
		rpmt = apply_payment(rpmt, paymt)
		rpmt = frappe._dict(rpmt)
		paymt = frappe._dict(paymt)
		if str(paymt.posting_date) < str(rpmt.fecha) or ff:
			rpmt = final_fine(rpmt)
		doc.update({
			"fine": rpmt.fine,
			"mora_acumulada": rpmt.mora_acumulada,
			"monto_pagado": rpmt.monto_pagado,
		})
		doc.monto_pendiente = doc.get_pending_amount()

		if doc.fine < 0 or doc.mora_acumulada < 0:
			frappe.throw("New fine for {parent} {idx} cannot be less than 0 ".format(**rpmt))
		doc.update_status()
		doc.db_update()
		# rpmt = calculate_fine(rpmt, paymt, today=True)
		# print("""\n***end***\nFecha: {fecha}\nCuota: {cuota}\nSeguro:{insurance}\nfine: {fine}\nmora_acumulada: {mora_acumulada}\nPagado: {monto_pagado}\nPendiente: {monto_pendiente}""".format(**rpmt))