# -*- encoding: utf-8 -*-

import frappe
from math import ceil
from frappe.desk.tags import DocTags
from fm.api import FULLY_PAID
from frappe.utils import cstr, flt, nowdate, add_months, add_days

def calculate_fines():
	# if frappe.conf.get("developer_mode"):
	# 	return # as we are in development yet
	print("def calculate_fines")

	# global defaults
	conf = frappe.get_single("FM Configuration")

	# fine = conf.vehicle_fine
	grace_days = conf.grace_days
	pending_or_monthly_amount = conf.pending_or_monthly_amount

	# today as string to operate with other dates
	today = str(nowdate())

	# let's begin
	for loan in frappe.get_list("Loan", { "docstatus": "1", "status": ["in", "Fully Disbursed, Recuperado, Legal, Incautado"] }):

		due_repayment_list = []

		doc = frappe.get_doc("Loan", loan.name) # load from db
		
		fine_rate = flt(doc.fine) / 100.000
		
		doc.overdue_amount = 0
		
		for row in doc.get("repayment_schedule"):
			row.calculate_fine()
			# due_repayment_list.append(row)
					
		# if due_repayment_list:
		# 	create_todo(doc, due_repayment_list)

def create_todo(doc, due_rows):
	# payments that are already due
	due_payments = len(due_rows)

	# load from db the default email for ToDos
	allocated_to = frappe.db.get_single_value("FM Configuration" , "allocated_to_email")

	customer_currency = frappe.db.get_value("Customer", doc.customer, "default_currency")

	# load defaults
	description_tmp = ""
	description = get_description()

	total_debt = 0

	for idx, row in enumerate(due_rows):
		# calculated values
		total_overdue_amount = flt(row.fine) + flt(doc.monthly_repayment_amount)
		description_tmp += """<br/><li> Para el pagare vencido No. {0} de fecha <i>{1}</i> el cargo por mora asciende 
			a <i>{5} ${2} {6}</i> ademas de <i>{5} ${3} {6} </i> pendientes por la cuota de dicho pagare para una deuda total 
			de <i>{5} ${4}</i> {6} solo por ese pagare.</li>""".encode('utf-8').strip()
		
		description_tmp = description_tmp.format(
			idx +1, # add 1 to make it natural
			row.due_date,
			"{0}{1}".format(str(row.fine), ".00" if not "." in str(row.fine) else ""),
			"{0}{1}".format(str(row.monto_pendiente - row.fine), ".00" if not "." in str(row.monto_pendiente - row.fine) else ""),
			"{0}{1}".format(str(row.monto_pendiente), ".00" if not "." in str(row.monto_pendiente) else ""),
			"RD" if customer_currency == "DOP" else "US",
			"Pesos" if customer_currency == "DOP" else "Dolares"
		)

		total_debt += total_overdue_amount

	# ok, let's begin
	t = frappe.new_doc("ToDo")

	allocated_to = frappe.get_value("User Branch Office", {
		"parent": doc.branch_office,
		"collection_user": 1
	}, ["user"])

	t.assigned_by = allocated_to
	t.owner = allocated_to
	t.reference_type = doc.doctype
	t.reference_name = doc.name
	t.branch_office = doc.branch_office

	t.description = description.encode("utf-8").format(
		doc.customer.encode("utf-8"), 
		due_payments, 
		nowdate(),
		description_tmp.encode("utf-8"),
		doc.name.encode("utf-8"),
		"{0}{1}".format(str(doc.overdue_amount), ".00" if not "." in str(doc.overdue_amount) else ""),
		"RD" if customer_currency == "DOP" else "US",
		"Pesos" if customer_currency == "DOP" else "Dolares"
	)

	t.insert()

def get_description():
	# the ToDo description
	description = """El cliente <b>{0}</b> tiene <b style="color:#ff5858">{1}</b> pagares vencidos a la fecha de hoy 
		<i>{2}</i>: <ol>{3}</ol><br/> <span style="margin-left: 3.5em"> Para una deuda total <b>{6}$ {5}</b> {7}, 
		mas informacion en el enlace debajo.</span>"""

	return description.encode('utf-8')

def get_expired_insurance():
	days_to_expire = frappe.db.get_single_value("FM Configuration", "renew_insurance")

	insurance_list = frappe.db.sql("""SELECT loan.customer, loan.asset
		FROM `tabPoliza de Seguro` AS poliza 
		JOIN tabLoan AS loan 
		ON loan.name = poliza.loan 
		WHERE DATEDIFF(poliza.end_date, NOW()) <= %s""" % days_to_expire, 
	as_dict=True)

	for vehicle in insurance_list:

		create_expired_insurance_todo(
			frappe.get_doc("Vehicle", vehicle.name), 
			vehicle.days
		)

def create_expired_insurance_todo(doc, days):

	# load from db the default email for ToDos
	allocated_to = frappe.db.get_single_value("FM Configuration", "allocated_to_email")
	description = get_expired_insurance_description()
	# ok, let's begin
	t = frappe.new_doc("ToDo")

	t.assigned_by = "Administrator"
	t.owner = allocated_to
	t.reference_type = doc.doctype
	t.reference_name = doc.name

	t.description = description.format(
		doc.make, 
		doc.model, 
		doc.license_plate, 
		days
	)

	t.insert()

def get_expired_insurance_description():

	# the ToDo description
	description = """El vehiculo <b>{0} {1}</b> placa <b>{2}</b>  le faltan <b style="color:#ff5858">{3}</b> dias para 
		vencer por favor renovar, mas informacion en el enlace debajo.""".encode('utf-8').strip()

	return description

def update_insurance_status():
	# if frappe.conf.get("developer_mode"):
	# 	return # as we are in development yet

	current_date = frappe.utils.nowdate()

	insurance_list = frappe.get_list("Poliza de Seguro", {
		"end_date": ["<=", current_date],
		"status": "Activo",
		"docstatus": "1"
	})

	for insurance in insurance_list:
		doc = frappe.get_doc("Poliza de Seguro", insurance.name)
		print("{} has expired".format(insurance.name))
		doc.status = "Inactivo"
		doc.db_update()

def update_exchange_rates():
	from fm.api import exchange_rate_USD

	today = nowdate()

	# load the Currency Exchange docs that were created when installing
	# the app and update them in a daily basis
	usddop = frappe.get_doc("Currency Exchange", {"from_currency": "USD", "to_currency": "DOP" })
	dopusd = frappe.get_doc("Currency Exchange", {"from_currency": "DOP", "to_currency": "USD" })

	# update the date field to let the user
	# know that it's up to date
	usddop.date = today
	dopusd.date = today

	# fetch the exchange rate from USD to DOP
	dop = exchange_rate_USD('DOP')

	if dop:
		usddop.exchange_rate = round(dop)
		usddop.save()

		dopusd.exchange_rate = round(dop)
		dopusd.save()
		 
def remove_loan_tags():
	for name, in frappe.get_list("Loan", as_list=True):
		DocTags("Loan").remove_all(name)
		 
def clean_portfolios():
	for name, in frappe.get_list("Client Portfolio", as_list=True):
		doc = frappe.get_doc("Client Portfolio", name)
		doc.customer_portfolio = []
		doc.save()

def assign_loans():
	remove_loan_tags()
	clean_portfolios()
	# MXT
	# ------------------------

	filters = {
		"branch_office": "MXT",
		"docstatus": 1,
		"status": ["!=", "Recuperado"],
	}

	doc = frappe.get_doc("Client Portfolio", "CART-00001")

	doc.customer_portfolio = []
	for loan, customer in frappe.get_list("Loan", filters, ["name", "customer_name"], as_list=True):
		doc.append("customer_portfolio", {"loan": loan, "customer": customer})
	doc.save()
	frappe.db.commit()

	# SANTIAGO
	# ------------------------

	filters = {
		"branch_office": "SANTIAGO",
		"docstatus": 1,
		"status": ["!=", "Recuperado"],
	}

	doc = frappe.get_doc("Client Portfolio", "CART-00005")

	doc.customer_portfolio = []
	for loan, customer in frappe.get_list("Loan", filters, ["name", "customer_name"], as_list=True):
		doc.append("customer_portfolio", {"loan": loan, "customer": customer})
	doc.save()
	frappe.db.commit()

	# SANTO DOMINGO 4
	# ------------------------

	doc = frappe.get_doc("Client Portfolio", "CART-00004")
	lst = frappe.db.sql("""
	select 
	 	`tabTabla Amortizacion`.parent,
	 	`tabLoan`.customer,
	 	count(1) qty 
	from 
	 	`tabTabla Amortizacion` 
	JOIN
		`tabLoan`
	ON
		`tabLoan`.name = `tabTabla Amortizacion`.parent

	where
		`tabTabla Amortizacion`.estado = 'VENCIDA'
	and
		`tabLoan`.docstatus = 1
	and
		`tabLoan`.status not in ('Recuperado', 'Legal')
	and 
		`tabLoan`.branch_office = 'SANTO DOMINGO'
	group by 
		`tabTabla Amortizacion`.parent 
	having 
		qty >= 5 

	union 

	select 
		`tabLoan`.name, `tabLoan`.customer, 100
	from 
		`tabLoan`
	where 
		`tabLoan`.docstatus = 1
	and
		`tabLoan`.status = 'Legal'
	and 
		`tabLoan`.branch_office = 'SANTO DOMINGO'
	""")
	doc.customer_portfolio = []
	for loan, customer, qty in lst:
		doc.append("customer_portfolio", {"loan": loan, "customer": customer})
	doc.save()
	frappe.db.commit()


	# SANTO DOMINGO 2-3 
	# ------------------------

	doc1 = frappe.get_doc("Client Portfolio", "CART-00002")
	doc2 = frappe.get_doc("Client Portfolio", "CART-00003")
	lst = frappe.db.sql("""
	select 
	 	`tabTabla Amortizacion`.parent,
	 	`tabLoan`.customer,
	 	count(1) qty 
	from 
	 	`tabTabla Amortizacion` 
	JOIN
		`tabLoan`
	ON
		`tabLoan`.name = `tabTabla Amortizacion`.parent

	where
		`tabTabla Amortizacion`.estado = 'VENCIDA'
	and
		`tabLoan`.docstatus = 1
	and
		`tabLoan`.status not in ('Recuperado')
	and 
		`tabLoan`.branch_office = 'SANTO DOMINGO'
	group by 
		`tabTabla Amortizacion`.parent 
	having 
		qty < 5 

	""")

	doc1.customer_portfolio = []
	doc2.customer_portfolio = []
	idx = 0
	for loan, customer, qty in lst:
		if idx % 2 == 0:
			doc1.append("customer_portfolio", {"loan": loan, "customer": customer})
		else:
			doc2.append("customer_portfolio", {"loan": loan, "customer": customer})
		idx +=1

	doc1.save()
	doc2.save()
	frappe.db.commit()

def update_client_portfolio():
	for name, in frappe.get_list("Client Portfolio", as_list=True):
		doc = frappe.get_doc("Client Portfolio", name)
		print("{name} {employee_name} updated".format(**doc.as_dict()))
		doc.save()