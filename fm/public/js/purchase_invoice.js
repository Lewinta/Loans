frappe.ui.form.on("Purchase Invoice", {
    onload_post_render: function(frm) {
        if ( !frm.doc.docstatus && frm.doc.poliza_de_seguro){
            frm.set_intro("Valide este documento para confirmar que se ha finalizado con la compra!")
        }
    },
    refresh: function(frm) {
        frm.doc.docstatus < 1 && frm.set_value("branch_office", frappe.boot.sucursal)
    },
    on_submit: function(frm) {
        // create a new Array from the history
        var new_history = Array.from(frappe.route_history)

        // then reversed the new history array
        var reversed_history = new_history.reverse()

        // not found flag to stop the bucle
        var not_found = true

        // iterate the array to find the last Loan visited
        $.each(reversed_history, function(idx, value) {

            // see if there is a Loan that was visited in this
            // section. if found it then redirect the browser to
            // asumming that the user came from that Loan
            if (not_found && "Form" == value[0] && "Loan" == value[1]) {

                // give a timeout before switching the location
                setTimeout(function() {
                    // set the route to the latest opened Loan
                    //frappe.set_route(value)
                }, 1500)

                // set the flag to false to finish
                not_found = false
            }
        })
    }
});