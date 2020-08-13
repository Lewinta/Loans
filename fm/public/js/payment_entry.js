frappe.ui.form.on("Payment Entry", {
    
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
            // section. if found it the redirects the browser to
            // asumming that the user came from that Loan
            if (not_found && "Form" == value[0] && "Loan" == value[1]) {

                // give a timeout before switching the location
                setTimeout(function() {
                    // set the route to the latest opened Loan
                    frappe.set_route(value)
                }, 1500)

                // set the flag to false to finish
                not_found = false
            }
        })
    },
    refresh: function(frm) {
        frm.doc.docstatus < 1 && frm.set_value("branch_office", frappe.boot.sucursal)
    },
    es_un_pagare: function(frm){

        // validate is the checkbox is checked first
        if ( !frm.doc.es_un_pagare ){

            // let's clear the pagare
            frm.set_value("pagare", 0)

            // let's clear the loan
            frm.set_value("loan", undefined)

            return 0 // exit is zero
        }
            
        var callback = function(data){
            frm.set_value("loan", data.loan)

            var _method = "fm.api.next_repayment"

            var _args = {
                "loan": frm.doc.loan
            }

            var _callback = function(response){

                // set the response the repayment variable
                var repayment = response.message

                // set the index value to the pagare number
                frm.set_value("pagare", repayment.idx)
            }

            frappe.call({ "method": _method, "args": _args, "callback": _callback })
        }

        // link field to Loan List
        var link_field = { "label": "Prestamo", "fieldname": "loan", "fieldtype": "Link", "options": "Loan" }

        if ( !frm.doc.prompt ){

            // let's show the prompt
            frm.doc.prompt = frappe.prompt(link_field, callback, "Seleccione el Prestamo", "Continuar")
        } else {
            // let's just make it visible
            var p = frm.doc.prompt

            p.show()
        }
    }
})