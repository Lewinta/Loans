frappe.ui.form.on("Translation", {
    refresh: function(frm) {
        if(frm.doc.__islocal) return
        frm.add_custom_button(__("Duplicate"), function(event){
            frm.doc.source_name = ""
            frm.doc.target_name = ""
            frm.copy_doc()
        })
    }
})