import frappe
import datetime
from math import ceil

def yefris_approach(cur_date, grace_periods):
    cur_date = str(cur_date)
    today = str(datetime.date.today())
    due_date = frappe.utils.add_days(today, grace_periods)
    if  cur_date <= due_date:
        return "Vencido"
    else:
        return "Pendiente"

def old_approach(cur_date, grace_periods):

    today = str(datetime.date.today())
    due_date = str(frappe.utils.add_days(cur_date, grace_periods))
    date_diff = frappe.utils.date_diff(today, due_date)

    due_payments = ceil(date_diff / 30.000)
    if today > due_date:
        return "Vencido"
    else:
        return "Pendiente"

def check_approaches(row):

    conf = frappe.get_single("FM Configuration")
    grace_days = conf.grace_days
    
    info = {
    "prestamo": row.parent,
    "idx": row.idx,
    "fecha": row.fecha,
    "due_date": row.due_date,
    # "estado": row.estado,
    "old": old_approach(row.fecha, grace_days),
    "new": yefris_approach(row.fecha, grace_days),
    }
    info = frappe._dict(info)

    if info.old != info.new:
        print ("""Prestamo: {prestamo} | Cuota: {idx}\t| Fecha: {fecha} | Vencimiento: {due_date} | Old:{old}\t| New:{new}""".format(**info))
        # print ("""Prestamo: {prestamo} | Cuota: {idx}\t| Fecha: {fecha} | Vencimiento: {due_date} | Estado: {estado}\t| Old:{old}\t| New:{new}""".format(**info))