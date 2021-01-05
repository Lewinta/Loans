# -*- encoding: utf-8 -*-

from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "fm"
app_title = "Finance Manager"
app_publisher = "Yefri Tavarez"
app_description = "Una applicacion para la gestion de una financiera."
app_icon = "octicon octicon-flame"
app_color = "#496"
app_email = "yefritavarez@gmail.com"
app_license = "General Public Licence v3"

fixtures = [
	"Role",
	"Print Format",
	"FM Configuration",
	"Translation",
	"Supplier Type"
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = "assets/fm/css/fm.css"
app_include_js = [
	"assets/fm/js/fm.js",
	"assets/fm/js/base_prompt.js",
	"assets/fm/js/payment_entry_prompt.js",
]

# include js, css files in header of web template
# web_include_css = "/assets/fm/css/fm.css"
# web_include_js = "/assets/fm/js/fm.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Journal Entry" : "public/js/journal_entry.js",
	# "Poliza de Seguro" : "public/js/poliza_de_seguro.js",
	"Fiadores" : "public/js/fiadores.js",
	"Customer" : "public/js/customer.js",
	"Customize Form" : "public/js/customize_form.js",
	"Journal Entry" : "public/js/journal_entry.js",
	"Payment Entry" : "public/js/payment_entry.js",
	"Purchase Invoice" : "public/js/purchase_invoice.js",
	"ToDo" : "public/js/todo.js",
	"Translation" : "public/js/translation.js",
	"Vehicle" : "public/js/vehicle.js"
}
doctype_list_js = {"Vehicle" : "public/js/vehicle_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "fm.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "fm.install.before_install"
after_install = "fm.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

notification_config = "fm.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }

doc_events = {
	"Journal Entry": {
		"validate": "fm.accounts.check_duplicate_disbursement",
		"on_submit": "fm.accounts.submit_journal",
		"on_cancel": "fm.accounts.cancel_journal"
	},
	"Customer": {
		"autoname": "fm.api.customer_autoname"
	},
	"Deleted Document": {
		"after_insert": "fm.utilities.after_insert_deleted_doc"
	}
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"fm.scheduler.calculate_fines",
		"fm.scheduler.update_exchange_rates",
		"fm.scheduler.update_insurance_status",
		"fm.scheduler.assign_loans",
		"fm.scheduler.update_client_portfolio",
		"fm.backup.daily"
	]
}

# scheduler_events = {
# 	"all": [
# 		"fm.tasks.all"
# 	],
# 	"daily": [
# 		"fm.tasks.daily"
# 	],
# 	"hourly": [
# 		"fm.tasks.hourly"
# 	],
# 	"weekly": [
# 		"fm.tasks.weekly"
# 	]
# 	"monthly": [
# 		"fm.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "fm.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "fm.event.get_events"
# }

on_session_creation = "fm.api.on_session_creation"

boot_session = "fm.boot.add_insurance_repayments"
