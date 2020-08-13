frappe.ui.form.on('Vehicle', {
	refresh: function(frm) {
		if(frm.doc.__islocal){
			frm.set_value("employee", frappe.session.user)
			frm.set_value("branch_office", frappe.boot.sucursal)
		}
	},
	validate: function(frm) {
		cuotas = frm.doc.cuotas
		if (cuotas && cuotas.length > 0) {
			total_insurance = 0

			cuotas.forEach(function(row) {
				total_insurance += row.amount
			})

			frappe.call({
				method: "fm.utilities.add_insurance_to_loan",
				args: {
					"chasis_no": frm.doc.license_plate,
					"total_insurance": total_insurance
				},
				callback: function(response) {
					var name = response.message

					frappe.show_alert(
						repl("Loan %(loan)s was updated", {
							"loan": name
						}),
					10)
				}
			})
		}
	},
	make: function(frm) {
		frm.set_value("make", frm.doc.make.trim().toUpperCase())
		frm.set_value("title", set_title(frm))
	},
	model: function(frm) {
		frm.set_value("model", frm.doc.model.trim().toUpperCase())
		frm.set_value("title", set_title(frm))
	},
	location: function(frm) {
		frm.set_value("location", frm.doc.location.trim().toUpperCase())
	},
	color: function(frm) {
		frm.set_value("color", frm.doc.color.trim().toUpperCase())
		frm.set_value("title", set_title(frm))
	},
	year: function(frm) {
		frm.set_value("title", set_title(frm))
	},
	renew: function(frm) {
		if ( !frm.doc.insurance_company )
			frappe.throw("Debe ingresar el nombre de la aseguradora")

		if ( !frm.doc.policy_no )
			frappe.throw("Debe ingresar el numero de poliza del cliente")

		if (frm.doc.financiamiento) {
			if (frm.doc.amount > 0) {
				amount = Math.ceil(frm.doc.amount / 3)
				var today = frappe.datetime.get_today()
				date = frappe.datetime.add_months(today, 1)

				frm.clear_table("cuotas")

				for (i = 0; i < 3; i++) {
					frm.add_child("cuotas", { "date": date, "amount": amount, "status": "PENDING" })

					date = frappe.datetime.add_months(date, 1)
				}

				refresh_field("cuotas")
				frm.save()
			} else {
				frappe.msgprint("Si opta por el financiamiento el monto de la poliza debe ser mayor que cero")
			}
		} else {
			frm.set_value("amount", 0)
		}
		frappe.show_alert("Vehiculo guardado")
	}
})

function set_title(frm){
	var name =""
		
	if(frm.doc.make)
		name = frm.doc.make
	
	if(frm.doc.model)
		name += " " + frm.doc.model
	
	if(frm.doc.year)
		name += " " + frm.doc.year

	if(frm.doc.color)
		name += " " + frm.doc.color

	return name.trim() 
}