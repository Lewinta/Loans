# -*- encoding: utf-8 -*-
import frappe
from datetime import date
from frappe.utils import flt

from fm.api import PENDING

@frappe.whitelist()
def get_next_repayment_schedule(chasis_no):
	loan_id = frappe.get_value("Loan", { "asset": chasis_no }, "name")

	if not loan_id:
		next_month = frappe.utils.add_months(date.today(), 1)

		return next_month.strftime("%Y-%m-%d")

	loan = frappe.get_doc("Loan", loan_id)

	pagos_vencidos = [ row for row in loan.repayment_schedule if row.estado == PENDING ]

	pagare = pagos_vencidos[0]

	fecha_pagare = pagare.fecha

	return fecha_pagare.strftime('%Y-%m-%d')

@frappe.whitelist()
def add_insurance_to_loan(chasis_no, total_insurance):
	doc = frappe.get_doc("Loan", { "asset": chasis_no, "status": "Fully Disbursed" })
	doc.vehicle_insurance = total_insurance

	doc.save()

	return doc.name

def s_sanitize(string):
	"""Remove the most common special caracters"""

	special_cars = [
		(u"á", "a"), (u"Á", "A"),
		(u"é", "e"), (u"É", "E"),
		(u"í", "i"), (u"Í", "I"),
		(u"ó", "o"), (u"Ó", "O"),
		(u"ú", "u"), (u"Ú", "U"),
		(u"ü", "u"), (u"Ü", "U"),
		(u"ñ", "n"), (u"Ñ", "N")
	]

	s_sanitized = string

	for pair in special_cars:
		s_sanitized = s_sanitized.replace(pair[0], pair[1])

	return s_sanitized.upper()

@frappe.whitelist()
def clean_all_fines(loan):
	_log = 'done'
	doc = frappe.get_doc('Loan',loan)
	for r in frappe.get_list('Tabla Amortizacion', {'parent':loan}, 'name'):
		row = frappe.get_doc('Tabla Amortizacion', r.name)
		if not row.estado == "SALDADA":
			row.monto_pendiente = row.monto_pendiente - row.fine
			row.fine = 0
			row.db_update()

	#Let's leave some trace
	doc.add_comment("Updated", "<span>Eliminó todas las moras de este prestamo.</span>", frappe.session.user)			
	return _log

@frappe.whitelist()
def add_fine(loan, cuota, mora, mora_acumulada):
	doc = frappe.get_doc('Loan',loan)
	mora = flt(mora)
	mora_acumulada = flt(mora_acumulada)
	row = frappe.get_doc('Tabla Amortizacion', {'parent': loan, 'idx': cuota})
	row.fine += mora
	row.mora_acumulada += mora_acumulada
	row.monto_pendiente = row.get_pending_amount()
	row.db_update()

	#Let's leave some trace
	if mora:
		doc.add_comment("Updated", "<span>Agregó  ${} de mora a la cuota No. {}.</span>".format(mora, cuota), frappe.session.user)

	if mora_acumulada:
		doc.add_comment("Updated", "<span>Agregó  ${} de mora acumulada a la cuota No. {}.</span>".format(mora, cuota), frappe.session.user)	

@frappe.whitelist()
def sync_row(loan, idx, date=None):
	repayment_name = frappe.db.get_value("Tabla Amortizacion", {"parent":loan, "idx":idx})
	from frappe.utils import date_diff
	from frappe.utils import date_diff, nowdate, flt, add_days, add_months
	from math import ceil

	def get_base_rpmt(row):
		return {
			"name": row.name,
			"cuota": row.cuota,
			"insurance": row.insurance,
			"fecha": row.fecha,
			"due_date": row.due_date,
			"parent": row.parent,
			"idx": row.idx,
			"fine": .000,
			"mora_acumulada": .000,
			"monto_pagado": .000,
			"monto_pendiente": row.cuota + row.insurance,
			"last_payment": 0,
		}

	def get_payments(repayment_name):
		import json

		filters = {"docstatus":1, "repayments_dict":["like", "%%{}%%".format(repayment_name)]}
		fields  = ["name", "repayments_dict", "posting_date"]
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

	def has_payments(rpmt, to_date, from_date=False):
		payments = get_payments(rpmt.name)
		if from_date:
			return filter(
				lambda x, from_date=from_date, to_date=to_date: x.get('posting_date') < to_date and x.get('posting_date') >= from_date , 
				payments
			)
		else:
			return filter(
				lambda x, from_date=from_date, to_date=to_date: x.get('posting_date') < to_date, 
				payments
			)

	def calculate_fine(rpmt, curdate):
		rpmt = frappe._dict(rpmt)
		fine_rate = frappe.db.get_value("Loan", rpmt.parent, "fine") / 100.0
		grace_days = frappe.db.get_single_value("FM Configuration", "grace_days")
		due_date = str(add_days(rpmt.fecha, int(grace_days)))
		if curdate > nowdate():
			return rpmt
		print("{} {}".format(curdate, rpmt.fecha))
		if str(curdate) > str(rpmt.fecha):
			# Debemos calcular la mora
			date_difference = date_diff(curdate, due_date)
			due_payments = ceil(date_difference / 29.99) if curdate != due_date else 1
			new_fine = ceil(flt(fine_rate) * flt(rpmt.monto_pendiente) * due_payments)
			monthly_fine = ceil(flt(fine_rate) * flt(rpmt.monto_pendiente))
			mon_reg_fine = ceil(flt(fine_rate) * flt(rpmt.cuota + rpmt.insurance))
			reg_fine = ceil(flt(fine_rate) * flt(rpmt.cuota + rpmt.insurance) * flt(due_payments))
			# frappe.errprint("cur:{}\ndiff:{}\ndue:{}\nnf:{}\nmf:{}\n\n".format(curdate,date_difference, due_payments, new_fine, monthly_fine))
			rpmt.update({
				"fine": reg_fine if flt(rpmt.monto_pagado == 0) else rpmt.fine + monthly_fine,
				"mora_acumulada": reg_fine if flt(rpmt.monto_pagado == 0) else rpmt.mora_acumulada + monthly_fine,
				"subtotal": flt(rpmt.cuota) + flt(rpmt.insurance),
				"due_date": due_date,
				"new_fine": mon_reg_fine if flt(rpmt.monto_pagado == 0) else monthly_fine,
				"last_updated_on": curdate,
			})
			
		calc_pending_amount(rpmt)		
		return rpmt

	def apply_payment(rpmt, pymt):
		pymt = frappe._dict(pymt)
		rpmt.update({
			"fine": .000 if pymt.paid_amount >= rpmt.fine else rpmt.fine - pymt.paid_amount,
			"monto_pagado":  rpmt.monto_pagado + pymt.paid_amount,
			"last_payment":  pymt.posting_date if str(pymt.posting_date) > str(rpmt.fecha) else 0,
			"last_ref":  pymt.name,
		})
		rpmt = calc_pending_amount(rpmt)
		# frappe.errprint("Payment:\n\t")
		# frappe.errprint(rpmt)
		# print("""\n***apply_payment***\nfine: {fine}\nmora_acumulada: {mora_acumulada}\nPagado: {monto_pagado}\nPendiente: {monto_pendiente}""".format(**rpmt))
		return rpmt

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

	row = frappe.get_doc("Tabla Amortizacion", repayment_name)
	today = nowdate() if not date else date

	rpmt = frappe._dict(get_base_rpmt(row))
	grace_days = frappe.db.get_single_value("FM Configuration", "grace_days")
	due_date = from_date = curdate = str(add_days(row.fecha, int(grace_days)))
	vencimientos = int(ceil(date_diff(today, row.fecha)/30)) + 1

	# frappe.errprint("Initial:\n\t")
	# frappe.errprint(rpmt)
	last_trans = ''
	last_ref = ''
	# Pagos antes del vencimiento
	for pymt in has_payments(rpmt, add_days(due_date, 1)):
		pymt = frappe._dict(pymt)
		# frappe.errprint("0. {} == {} => {}".format(pymt.name, last_ref, rpmt.monto_pagado))
		if pymt.posting_date > today:
			continue
		rpmt = apply_payment(rpmt, pymt)
		last_trans = 'ABONO'
		last_ref = rpmt.last_ref 
		frappe.errprint("Pagos Antes del vencimiento:\n\t")
		frappe.errprint("1.  {name} {paid_amount} ABONO".format(**pymt))
	for v in range(0, vencimientos):
		frappe.errprint("{} - {}".format(add_days(curdate, 1), add_days(from_date, 1)))
		for pymt in has_payments(rpmt, add_days(curdate, 1), add_days(from_date, 1)):
			pymt = frappe._dict(pymt)
			frappe.errprint("1.5 {} == {} => {}".format(rpmt.last_ref, last_ref, pymt.paid_amount))
			if pymt.posting_date > today:
				continue
			if last_ref == pymt.name:
				continue
			rpmt = apply_payment(rpmt, pymt)
			frappe.errprint("Pagos en vencimientos:\n\t")
			frappe.errprint("2.  {name} {paid_amount} ABONO".format(**pymt))
		
		if rpmt.monto_pendiente <= 1:
			from_date = curdate
			curdate = add_months(curdate, 1)
			continue

		if curdate > today:
			continue
		rpmt = calculate_fine(rpmt, curdate)
		frappe.errprint("Calculo Moras:\n\t")
		# frappe.errprint(rpmt)
		frappe.errprint("2. {last_updated_on} {fine} {new_fine} {mora_acumulada} MORA".format(**rpmt))
		if add_months(curdate, 1) > today:
			from_date = curdate
			curdate = add_months(curdate, 1)
			continue

		from_date = curdate
		curdate = add_months(curdate, 1)
	
	for pymt in has_payments(rpmt, add_days(today, 2), add_months(curdate, -1)):
		pymt = frappe._dict(pymt)
		frappe.errprint("3. {} == {} => {}".format(pymt.name, last_ref, rpmt.monto_pagado))
		if last_ref == pymt.name or last_ref == rpmt.last_ref:
			continue
		
		if pymt.posting_date > today:
			continue
		rpmt = apply_payment(rpmt, pymt)
		frappe.errprint("Final pay:\n\t")
		# frappe.errprint(rpmt)
		frappe.errprint("3. {name} {paid_amount} ABONO".format(**pymt))

	row.update({
		"fine": rpmt.fine,
		"mora_acumulada": rpmt.mora_acumulada,
		"monto_pagado": rpmt.monto_pagado,
	})
	if rpmt.monto_pendiente < 0:
		frappe.throw(
			"""Monto pendiente en {parent} -> {idx}no puede ser menor que 0, 
			comuniquese con su administrador""".format(**row.as_dict())
		)
		# print("*******************************************")
		# print("\t\t{parent} - {idx}".format(**rpmt))
		# print("                 Not updated              ")
		# print("*******************************************")
		return
	
	row.monto_pendiente = row.get_pending_amount()
	row.update_status()
	row.db_update()
	frappe.db.commit()

def get_month_end(date):
	from datetime import datetime
	from calendar import monthrange

	return date.replace(day = monthrange(date.year, date.month)[1])

def get_month_start(date):
	from datetime import datetime
	from calendar import monthrange

	return date.replace(day = monthrange(date.year, date.month)[0])

def after_insert_deleted_doc(doc, event):
	doc.responsible = frappe.session.user
	doc.db_update()
	frappe.db.commit()