frappe.ui.form.on("Customize Form", {
    refresh: function(frm) {
         frm.set_query("default_print_format", function() {
             return {
                  "filters": {
                      "doc_type": frm.doc.doc_type
                  }
             }
         })
    }
})