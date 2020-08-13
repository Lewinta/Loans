import frappe
import json

def before_print(doc, event):
	r = json.dumps(doc.repayments_dict)
	
	loaded_r = json.loads(r)
	
	doc.repayments = loaded_r
