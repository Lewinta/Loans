# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, cint
import calendar

def execute(filters=None):
	# key yyyy-mm
	new_clients = {}
	payments = {}
	rows = []
	company_condition = ""
	totals = []

	if filters.get("company"):
		company_condition = 'AND company=%(company)s'

	result = frappe.db.sql("""
		SELECT
			parent.posting_date,
			MONTH(parent.posting_date) mo,
			YEAR(parent.posting_date) yr,
			EXTRACT(YEAR_MONTH FROM parent.posting_date) AS yearmonth,
			SUM(IF(child.repayment_field = 'paid_amount' AND  parent.es_un_pagare = 1, child.debit, 0)) AS total,
			SUM(IF(child.repayment_field = 'capital' AND  parent.es_un_pagare = 1, child.credit, 0)) AS capital,
			SUM(IF(child.repayment_field = 'fine' AND  parent.es_un_pagare = 1, child.credit, 0)) AS fine,
			SUM(IF(child.repayment_field = 'insurance' AND  parent.es_un_pagare = 1, child.credit, 0)) AS insurance,
			SUM(IF(child.repayment_field = 'other_discounts' AND parent.es_un_pagare = 1, child.debit, 0)) AS discount,
			SUM(IF(parent.es_un_pagare   = 0 AND parent.voucher_type = "Bank Entry", child.debit, 0)) AS total_disbursed,


			COUNT(parent.name) AS records
		FROM
			`tabJournal Entry` AS parent
				INNER JOIN
			`tabJournal Entry Account` AS child
				ON child.parent = parent.name
		WHERE
			parent.docstatus = 1
			AND posting_date BETWEEN %(from_date)s AND %(to_date)s
		GROUP BY yearmonth
		ORDER BY
			parent.posting_date""".format(company_condition=company_condition),
	filters, as_dict=True)

	loan_result = frappe.db.sql("""
		SELECT
			l.posting_date,
			MONTH(l.posting_date) mo,
			YEAR(l.posting_date) yr,
			EXTRACT(YEAR_MONTH FROM l.posting_date) AS yearmonth,
			SUM(l.gross_loan_amount) AS total
		FROM
			`tabLoan` l
		WHERE
			l.docstatus = 1
			AND
				posting_date BETWEEN %(from_date)s AND %(to_date)s
		GROUP BY yearmonth
		ORDER BY
			l.posting_date""".format(company_condition=company_condition),
	filters, as_dict=True)

	for row in result:
		key = row.posting_date.strftime("%Y-%m")
		# rows.append([row.yr, row.mo, row.total, row.records])
		payments.setdefault(key, [0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000])
		# payments[key][0] += 1
		payments[key][0] += row.records
		payments[key][1] += row.discount
		# payments[key][2] += row.total
		payments[key][2] += row.capital + row.fine
		payments[key][3] += row.total_disbursed
		payments[key][4] += row.capital
		payments[key][5] += row.fine
		payments[key][6] += row.insurance
		payments[key][7] += row.capital + row.fine + row.insurance

	# time series
	from_year, from_month, temp = filters.get("from_date").split("-")
	to_year, to_month, temp = filters.get("to_date").split("-")

	from_year, from_month, to_year, to_month = \
		cint(from_year), cint(from_month), cint(to_year), cint(to_month)

	out = []
	idx = 0
	for year in xrange(from_year, to_year +1):
		for month in xrange(from_month if year==from_year else 1, (to_month+1) if year==to_year else 13):
			key = "{year}-{month:02d}".format(year=year, month=month)

			jv = payments.get(key, [0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 100, 0.000])
			prestado = filter(lambda x: x.mo == month and x.yr == year, loan_result)
			# frappe.errprint("{} {}".format(idx, prestado))
			prestado_total = prestado[0].total if len(prestado) > 0 else .00
			out.append([year, calendar.month_name[month], jv[0], jv[4], jv[5], jv[6], jv[1], jv[7], jv[2], prestado_total, jv[3]])
			idx += 1

	# for i in range(0, len(out)):
	# 	out[i][8] = loan_result[i].total if loan_result[i] and loan_result[i].total else 0.00

	return [
		_("Ano"),
		_("Mes"),
		_("Pagos") + ":Int:70",
		_("Capital/Comision") + ":Currency:150",
		_("Mora") + ":Currency:110",
		_("Seguro") + ":Currency:110",
		_("Descuentos") + ":Currency:110",
		_("Ingreso Bruto") + ":Currency:110",
		_("Ingreso Neto") + ":Currency:110",
		_("Prestado") + ":Currency:110",
		_("Desembolsado") + ":Currency:110",
	], out


