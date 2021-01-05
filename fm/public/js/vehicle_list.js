frappe.listview_settings['Vehicle'] = {
	"get_indicator": (doc) => {
		if(doc.status === "Financiado") {
			return ["Financiado", "blue", "status,=,Financiado"]
		} else if (doc.status === "Disponible") {
			return ["Disponible", "green", "status,=,Disponible"]
		} else if (doc.status === "Vendido") {
			return ["Vendido", "green", "status,=,Vendido"]
		}
	}
}