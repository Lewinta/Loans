frappe.ui.form.on("Fiador", {
	fiador: function(frm){
		frappe.model.get_value(
			"Phone Number",{ 
				"idx":1,
				"parenttype":"Fiador",
				"parent":frm.doc.fiador
			},
			"number",
			function(response){
				if(response)
					frm.set_value("telefono",response.number)
			})
	}
})  
