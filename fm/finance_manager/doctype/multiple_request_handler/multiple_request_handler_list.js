frappe.listview_settings['Multiple Request Handler'] = {
	get_indicator: doc => {
		if(doc.status === "Allowed") {
			return ["Allowed", "green", "status,=,Allowed"]
		} else if (doc.status === "Blocked") {
			return ["Blocked", "red", "status,=,Blocked"]
		} 
	}
}