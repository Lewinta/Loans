# Copyright (c) 2013, Yefri Tavarez and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import date_diff
from frappe.utils import date_diff, nowdate, flt, add_days, add_months
from math import ceil

def execute(filters=None):
	if not filters.get('repayment'):
		return [], []
	else:
		return get_columns(), get_data(filters)

def get_columns():
	return [
		# "Prestamo:Link/Loan:75",
		"Fecha:Date:80",
		"Fecha Trans:Date:80",
		"Cuota:Currency:100",
		"Venc.:Data:50",
		"Mora:Data:100",
		"Mora Acum.:Data:100",
		"Mora Gen.:Currency:90",
		"Seguro:Currency:100",
		"Pagado:Currency:100",
		"Pendiente:Data:100",
		"Trans.:Data:60",
		"Ref.:Link/Journal Entry:75",
	]

def get_data(filters):
	fltrs = {
		"parent": filters.get("loan"),
		"idx": filters.get("repayment")
	}
	row = frappe.get_doc("Tabla Amortizacion", fltrs)
	results = []
	today = nowdate() if not filters.get('date') else filters.get('date')

	# Let's append the first row
	results.append(
		(
			# row.parent,
			row.fecha,
			row.fecha,
			row.cuota,
			'',
			'',
			'',
			'',
			row.insurance,
			'',
			row.cuota + row.insurance,
			'CUOTA',
			'',
		)
	)

	rpmt = frappe._dict(get_base_rpmt(row))
	due_date = from_date = curdate = str(add_days(row.fecha, 5))
	vencimientos = int(ceil(date_diff(today, row.fecha)/30)) + 1
	# Pagos antes del vencimiento
	last_trans = ''
	last_ref = ''
	for pymt in has_payments(rpmt, add_days(due_date, 1)):
		pymt = frappe._dict(pymt)
		# frappe.errprint("1 pymet to {} ".format(due_date))
		if pymt.posting_date > today:
			continue
		frappe.errprint("1. {} < {} ".format(pymt.posting_date, today))
		rpmt = apply_payment(rpmt, pymt)
		results.append(
			(
				# '',
				'',
				pymt.posting_date,
				'',
				0 if curdate < str(row.fecha) else ceil(date_diff(curdate, row.fecha)/30.0),
				'',
				'',
				'',
				'',
				pymt.paid_amount,
				rpmt.monto_pendiente,
				'ABONO',
				pymt.name

			)
		)
		last_trans = 'ABONO'
		last_ref = pymt.name 

	for v in range(0, vencimientos):
		# frappe.errprint("{} - {}".format(add_days(curdate, 1), add_days(from_date, 1)))
		for pymt in has_payments(rpmt, add_days(curdate, 1), add_days(from_date, 1)):
			pymt = frappe._dict(pymt)
			# frappe.errprint("2-) {} venc. pymet from {} to {} paid {}".format(v ,from_date, curdate, pymt.paid_amount))
			if pymt.posting_date > today:
				continue
			frappe.errprint("2. {} {} ".format(pymt.posting_date, today))
			if pymt.name == last_ref :
				continue
			rpmt = apply_payment(rpmt, pymt)
			results.append(
				(
					# '',
					'',
					pymt.posting_date,
					'',
					0 if curdate < str(row.fecha) else ceil(date_diff(curdate, row.fecha)/30.0),
					'',
					'',
					'',
					'',
					pymt.paid_amount,
					rpmt.monto_pendiente,
					'ABONO',
					pymt.name

				)
			)
			last_trans = 'ABONO'
			last_ref = pymt.name 

		if rpmt.monto_pendiente <= 1:
			from_date = curdate
			curdate = add_months(curdate, 1)
			continue

		if curdate > today:
			continue
		frappe.errprint("3. {} {} ".format(rpmt.due_date, today))
		rpmt = calculate_fine(rpmt, curdate)
		results.append(
			(
				# '',
				'',
				curdate,
				'',
				0 if curdate < str(row.fecha) else ceil(date_diff(curdate, row.fecha)/30.0),
				rpmt.fine,
				rpmt.mora_acumulada,
				rpmt.new_fine,
				'',
				'',
				rpmt.monto_pendiente,
				'MORA',
				''
			)
		)
		
		if add_months(curdate, 1) > today:
			from_date = curdate
			curdate = add_months(curdate, 1)
			continue

		from_date = curdate
		curdate = add_months(curdate, 1)	
	# Pagos despues del Vencimiento
	# print(has_payments(rpmt, add_days(today, 2), add_months(curdate, -1)))
	for pymt in has_payments(rpmt, add_days(today, 2), add_months(curdate, -1)):
			pymt = frappe._dict(pymt)
			# frappe.errprint("3 pymet to {} ".format(due_date))
			if pymt.posting_date > today:
				continue
			rpmt = apply_payment(rpmt, pymt)
			if pymt.name == last_ref:
				continue
			results.append(
				(
					# '',
					'',
					pymt.posting_date,
					'',
					0 if curdate < str(row.fecha) else ceil(date_diff(curdate, row.fecha)/30.0),
					'',
					'',
					'',
					'',
					pymt.paid_amount,
					rpmt.monto_pendiente,
					'ABONO',
					pymt.name

				)
			)
	return results

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
	due_date  = str(add_days(rpmt.fecha, 5))
	print("Calculating {} {}".format(curdate, due_date))
	if str(curdate) > str(rpmt.fecha):
		print("Calculando {} {}".format(curdate, due_date))
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
	})
	rpmt = calc_pending_amount(rpmt)
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
