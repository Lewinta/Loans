frappe.ui.form.on("ToDo", {
	onload: function(frm){
  		frm.set_df_property("reference_name", "read_only", frm.doc.reference_type=="Loan")
	}
})