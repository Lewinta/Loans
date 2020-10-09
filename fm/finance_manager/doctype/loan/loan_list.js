frappe.listview_settings['Loan'] = {
	"add_fields": ["status", "docstatus"],
	"onload": (listview) => {
		var filters = {
			"status": ["=","Sanctioned"]
		};

		if (frappe.user.has_role("Gerente de Operaciones")) {
			filters = {
				"status": ["in","Sanctioned,Fully Disbursed,Partially Disbursed"]
			};
		} else if (frappe.user.has_role("Cobros")){
			filters = {
				"status": ["in","Sanctioned,Fully Disbursed,Partially Disbursed"],
				"docstatus": ["=", "1"]
			};
		} else if (frappe.user.has_role("Financiamiento")){
			// $.extend(filters, {
			// 	"owner": frappe.user.name
			// });
		} else if (frappe.user.has_role("Cajera")){
			filters = {
				"status": "Fully Disbursed"
			};
		} else if (frappe.user.has_role("Contador")){
			$.extend(filters, {
				"docstatus": ["=", "1"]
			});
		}

		frappe.route_options = filters;
	},
	"get_indicator": (doc) => {
		if(doc.status === "Sanctioned") {
			return ["Aprobado", "orange", "status,=,Sanctioned"]
		} else if (["Recuperado", "Pending",].includes(doc.status)) {
			return ["Recuperado", "purple", "status,=,Recuperado"]
		} else if (doc.status === "Partially Disbursed") {
			return ["Desembolsado Parcialmente", "darkgrey", "status,=,Partially Disbursed"]
		} else if(doc.status === "Fully Disbursed") {
			return ["Activo", "blue", "status,=,Fully Disbursed"]
		} else if(doc.status === "Repaid/Closed") {
			return ["Completado", "green", "status,=,Repaid/Closed"]
		}else if(doc.status === "Legal") {
			return ["Legal", "red", "status,=,Legal"]
		}else if(doc.status === "Disponible") {
			return ["Disponible", "red", "status,=,Disponible"]
		}else if(doc.status === "Perdida Total") {
			return ["Perdida Total", "red", "status,=,Perdida Total"]
		}else if(doc.status === "Taller") {
			return ["Taller", "purple", "status,=,Taller"]
		}else if(doc.status === "Incautado") {
			return ["Incautado", "purple", "status,=,Incautado"]
		}
	}
}