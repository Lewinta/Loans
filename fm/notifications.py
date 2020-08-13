import frappe

def get_notification_config():
	return {
		"for_doctype": {
			"Loan": {"status": ["=", "Sanctioned"]}
		}
	}
