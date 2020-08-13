import frappe

def get_payments(repayment_name):
	import json

	filters = {"repayments_dict":["like", "%%{}%%".format(repayment_name)]}
	fields  =  ["name", "repayments_dict", "posting_date"]
	result  = []

	for je in frappe.get_list("Journal Entry", filters, fields, order_by='posting_date'):
		repayments = json.loads(
			je.repayments_dict.replace("u'", "'").replace("'", "\"")
		)
		detail = filter(lambda x, name=repayment_name: x.get('name') == name, repayments )
		# print("{}\t{}".format(je.posting_date, detail[0].get('monto_pagado')))
		result.append({
			"posting_date": str(je.posting_date),
			"paid_amount": detail[0].get('monto_pagado')
		})

	return result

def calc_pending_amount(rpmt):
	monto_pendiente = (
		rpmt.cuota + \
		rpmt.insurance + \
		rpmt.mora_acumulada -\
		rpmt.monto_pagado
	)

	rpmt.update({
		"monto_pendiente": monto_pendiente
	})
	
def calculate_fine(rpmt, payment_date):
	from frappe.utils import date_diff, nowdate, add_days, flt
	from math import ceil
	fine_rate = frappe.db.get_value("Loan", rpmt.parent, "fine") / 100.0

	if payment_date > rpmt.fecha:
		due_date = add_days(rpmt.fecha, 5)
		date_difference = date_diff(payment_date, due_date)
		due_payments = ceil(date_difference / 30.000)
		# new_fine = flt(fine_rate) * flt(rpmt.monto_pendiente - rpmt.fine) * due_payments
		new_fine = flt(fine_rate) * flt(rpmt.cuota + rpmt.insurance + rpmt.mora_acumulada - rpmt.monto_pagado) * due_payments
		monthly_fine = flt(fine_rate) * flt(rpmt.cuota + rpmt.insurance + rpmt.mora_acumulada - rpmt.monto_pagado)
		
		rpmt.update({
			"fine": new_fine if rpmt.monto_pagado == .00 else monthly_fine,
			"mora_acumulada": new_fine if rpmt.monto_pagado == .00 else rpmt.mora_acumulada + monthly_fine
		})
	calc_pending_amount(rpmt)
	print(
		"{} | {} | {} ({}) \n\tcuota:{}\n\tsegur:{}\n\tmo_ac:{}\n\tpagad:{}\n\tpendi:{}".format(
			rpmt.fecha, due_date, payment_date, due_payments, rpmt.cuota, rpmt.insurance, rpmt.mora_acumulada,
			rpmt.monto_pagado, rpmt.monto_pendiente
		)
	)

def validate_repayment(repayment_name):
	from frappe.utils import date_diff, nowdate, flt

	doc = frappe.get_doc("Tabla Amortizacion", repayment_name)
	
	rpmt = frappe._dict({
		"cuota": doc.cuota,
		"insurance": doc.insurance,
		"fecha": str(doc.fecha),
		"parent": doc.parent,
		"fine": .000,
		"mora_acumulada": .000,
		"monto_pagado": .000,
		"monto_pendiente": doc.cuota + doc.insurance,
	})

	for paymt in get_payments(repayment_name):
		calculate_fine(rpmt, str(paymt.get('posting_date')))
		# Make Payment
		rpmt.monto_pagado += flt(paymt.get('paid_amount'))
		calc_pending_amount(rpmt)
		print(
			" \n\tafter_payment\n\t{}\n\tsegur:{}\n\tmo_ac:{}\n\tpagad:{}\n\tpendi:{}".format(
				rpmt.cuota, rpmt.insurance, rpmt.mora_acumulada,
				rpmt.monto_pagado, rpmt.monto_pendiente
			)
		)
		calculate_fine(rpmt, nowdate())
