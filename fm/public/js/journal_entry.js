// Copyright (c) 2017, Soldeva, SRL and contributors
// For license information, please see license.txt

frappe.ui.form.on("Journal Entry", {
    onload_post_render: function(frm) {
        frm.doc.create_jv = true
        var doctype = docname = "FM Configuration"

        frappe.db.get_value(doctype, docname, "interest_on_loans", function(data) {
            frm.doc._interest_account = data.interest_on_loans
        })
    },
    refresh: function(frm) {
        var callback = function(response) {
            if (frm.doc.__islocal || !response.message) 
                return 0 // exit code is zero

            var list = response.message
            var cur_route, prev_route, next_route
            var index = 0, prev_index = 0, next_index = 0

            for ( ; index < list.length; index++) {
                prev_index = index - 1 < 0 ? 0 : index - 1
                next_index = index + 1 >= list.length ? list.length - 1 : index + 1

                if (frm.doc.name == list[index].name) {
                    prev_route = list[prev_index].name
                    next_route = list[next_index].name
                    cur_route = list[index].name

                    break
                }
            }

            var route_next = function(res) {
                set_emp_route(next_route)
            }

            var route_prev = function(res) {
                set_emp_route(prev_route)
            }

            var set_emp_route = function(docname) {
                frappe.set_route(["Form", frm.doctype, docname])
            }

            if (prev_route != cur_route) 
                frm.add_custom_button("<< Prev", route_prev)

            if (next_route != cur_route) 
                frm.add_custom_button("Next >>", route_next)
        }

        frappe.call({
            "method": "frappe.client.get_list",
            "args": {
                "doctype": frm.doctype,
                "limit_page_lentgh": 0,
                "filters": {
                    "loan": frm.doc.loan,
                    "es_un_pagare": frm.doc.es_un_pagare
                }
            }, "callback": callback
        })
        setTimeout(function() {
            frappe.hide_msgprint()
        },1500)

        frm.doc.docstatus < 1 && frm.set_value("branch_office", frappe.boot.sucursal)
        if (frm.doc.loan){
            frm.add_custom_button("Prestamo", () => frappe.set_route(["Form", "Loan", frm.doc.loan]))
        }  
    },
    "validate": (frm) => {
        setTimeout(function() {
           frappe.hide_msgprint()
        },1500) 
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
            // section. if found it the redirects the browser to
            // asumming that the user came from that Loan
            if (not_found && "Form" == value[0] && "Loan" == value[1]) {

                // give a timeout before switching the location
                setTimeout(function() {
                    // set the route to the latest opened Loan
                    // frappe.set_route(value)
                }, 1500)

                // set the flag to false to finish
                not_found = false
            }
        })
        setTimeout(function() {
           frappe.hide_msgprint()
        },2000)
        // Let's clear the prompt  
        frm.p = undefined  
    },
    repayment: function(frm){
        var read_only_discount = !!!frappe.user.has_role("Gerente de Operaciones")

        if ( !frm.doc.repayment){
            frm.set_value("loan", "")
            frm.set_value("es_un_pagare", "0")
            frm.set_value("repayment_no", "")

            return 0 // the exit is zero
        }

        var fields = [
            {
                "fieldname": "prestamo",
                "fieldtype": "Link",
                "options": "Loan",
                "label": "Prestamo",
                "filters": { "status": "Fully Disbursed"}//, "customer_currency": "USD" }
            }, {
                "fieldname": "paid_amount",
                "fieldtype": "Float",
                "label": "Monto Recibido",
                "reqd": "1",
                "default": "0"
            }, {
                "fieldname": "mode_of_payment",
                "fieldtype": "Select",
                "label": "Modo de Pago",
                "reqd": "1",
                "options": "Cash Entry\nJournal Entry\nBank Entry\nCredit Card Entry\nDebit Note\nCredit Note\nContra Entry\nExcise Entry\nWrite Off Entry\nOpening Entry\nDepreciation Entry",
                "default": "Cash Entry"
            }, {
                "fieldname": "payment_section",
                "fieldtype": "Column Break"
            }, {
                "fieldname": "repayment_idx",
                "fieldtype": "Int",
                "label": "Pagare No.",
                "read_only": "1",
                "default": "0"
            }, {
                "fieldname": "customer_currency",
                "label": "Currency",
                "fieldtype": "Read Only",
                "read_only": "1",
                "default": "DOP"
            }, {
                "fieldname": "has_gps",
                "label": "GPS?",
                "fieldtype": "Check",
                "default": "0"
            },{
                "fieldname": "has_recuperacion",
                "label": "Recuperacion?",
                "fieldtype": "Check",
                "default": "0"
            }, {
                "label": "Seccion de Mora",
                "fieldname": "fine_section",
                "fieldtype": "Section Break"
            }, {
                "fieldname": "fine",
                "fieldtype": "Float",
                "label": "Mora", 
                "read_only": "1",
                "default": "0.00"
            }, {
                "fieldname": "discount_column",
                "fieldtype": "Column Break"
            }, {
                "fieldname": "fine_discount",
                "fieldtype": "Float",
                "label": "Descuento a Mora",
                "default": "0.0",
                "precision": "2",
                "read_only": read_only_discount
            },  {
                "label": "Miscelaneos",
                "fieldname": "miscelaneos",
                "fieldtype": "Section Break",
            }, {
                "fieldname": "gps",
                "fieldtype": "Float",
                "label": "GPS", 
                "default": "0.00",
            }, {
                "fieldname": "discount_column",
                "fieldtype": "Column Break"
            }, {
                "fieldname": "gastos_recuperacion",
                "fieldtype": "Float",
                "label": "Gastos  de Recuperacion",
                "default": "0.0",
                "precision": "2",
            }, {
                "fieldname": "insurance_section",
                "fieldtype": "Section Break"
            }, {
                "fieldname": "insurance",
                "fieldtype": "Float",
                "label": "Seguro",
                "read_only": "1",
                "default": "0.00"
            }, {
                "fieldname": "repayment_section",
                "fieldtype": "Column Break"
            }, {
                "fieldname": "pending_amount",
                "fieldtype": "Float",
                "label": "Monto del Pendiente",
                "read_only": "1",
                "default": "0.00"
            }, {
                "fieldname": "repayment_amount",
                "fieldtype": "Float",
                "label": "Monto del Pagare",
                "read_only": "1",
                "default": "0.00"
            }
        ]
        
        if ( !frm.p){
            frm.p = frappe.prompt(fields, function(data){
                frm.doc._pdata = data
                frm.trigger("set_values")

            }, "Seleccione el prestamo", "Continuar")
        } else {
            frm.p.show()
        }

        var calculate_duty_amount = function() {
            var recuperacion = frm.p.get_value("has_recuperacion")? frm.p.get_value("gastos_recuperacion"): 0.000
            var gps = frm.p.get_value("has_gps")? frm.p.get_value("gps"): 0.000
            var pending_amount = frm.p.get_value("pending_amount")
            var exchange_rate = 1.000

            frm.p.set_value("paid_amount", pending_amount)
        }

        // default status for the wrapper
        frm.p.fields_dict.miscelaneos.wrapper.hide()
        frm.p.fields_dict.gps.$wrapper.hide()
        frm.p.fields_dict.gastos_recuperacion.$wrapper.hide()
        
        frm.p.set_value("has_gps", 0.000)
        frm.p.set_value("has_recuperacion", 0.000)

        frm.p.fields_dict.has_gps.$input.on("change", function(event){
            var checked = frm.p.get_value("has_gps")
            
            if (checked) {
                // ok, let's get ready
                var doctype = docname = "FM Configuration"
                
                frappe.db.get_value(doctype, docname, "gps_amount", function(data) {
                    var default_amount = data.gps_amount

                    // set the default amount for the user
                    frm.p.set_value("gps", default_amount)
                })

                frm.p.fields_dict.gps.$wrapper.show()

                // if checked then let's also show the section break
                frm.p.fields_dict.miscelaneos.wrapper.show()
            } else {
                frm.p.fields_dict.gps.$wrapper.hide()

                // finally if there's no value in the other one
                if ( !frm.p.get_value("has_recuperacion")) {
                    frm.p.fields_dict.miscelaneos.wrapper.hide()
                }
            }
        })

        frm.p.fields_dict.has_recuperacion.$input.on("change", function(event){
            var checked = frm.p.get_value("has_recuperacion")
            
            if (checked) {
                // ok, let's get ready
                var doctype = docname = "FM Configuration"
                
                frappe.db.get_value(doctype, docname, "recuperation_amount", function(data) {
                    
                    var default_amount = data.recuperation_amount 

                    // set the default amount for the user
                    frm.p.set_value("gastos_recuperacion", default_amount)
                })

                frm.p.fields_dict.gastos_recuperacion.$wrapper.show()

                // if checked then let's also show the section break
                frm.p.fields_dict.miscelaneos.wrapper.show()
            } else {
                frm.p.fields_dict.gastos_recuperacion.$wrapper.hide()

                // finally if there's no value in the other one
                if ( !frm.p.get_value("has_gps")) {
                    frm.p.fields_dict.miscelaneos.wrapper.hide()
                }
            } 
        })

        if (frm.p.fields_dict.fine_discount.$input) {
        frm.p.fields_dict.fine_discount.$input.on("change", function(event){
            var fine_discount = flt(frm.p.get_value("fine_discount"))
            var pending_amount = flt(frm.p.get_value("pending_amount"))
           

            frm.p.set_value("paid_amount", pending_amount - fine_discount )

        })}

        frm.p.fields_dict.prestamo.$input.on("change", function(event){

            var prestamo = $(this).val()
            var currency = "DOP"

            frappe.model.get_value("Loan", prestamo, "customer_currency", function(data){
                if (data) {
                    currency = data.customer_currency
                } else {
                    currency = "DOP" 
                }
            })

            if ( !prestamo) {
                var prm = frm.p
                prm.set_value("repayment_idx", "")
                prm.set_value("paid_amount", 0.000)
                prm.set_value("fine", 0.000)
                prm.set_value("insurance", 0.000)
                prm.set_value("pending_amount", 0.000)
                prm.set_value("repayment_amount", 0.000)
                prm.set_value("customer_currency", "DOP")

                return 0.000
            }

            var method = "fm.api.next_repayment"
            var args = { 
                loan: prestamo 
            }

            var callback = function(response){
                var prm = frm.p
                var repayment = response.message

                if ( !repayment){

                    // then we got some serious issues
                    frappe.throw(__("El prestamo {0} no tiene ningun pagare pendiente!", [prestamo]))
                }
                
                prm.set_value("repayment_idx", repayment.idx)
                prm.set_value("paid_amount", repayment.monto_pendiente)
                prm.set_value("fine", repayment.fine)
                prm.set_value("insurance", repayment.insurance)
                prm.set_value("pending_amount", repayment.monto_pendiente)
                prm.set_value("repayment_amount", repayment.cuota)
                prm.set_value("customer_currency", currency)

                frm._repayment = repayment
            }

            frappe.call({ method: method, args: args, callback: callback })
        })
    },
    set_values: function(frm) {
        var doc = frm.doc._pdata
        var repayment = frm._repayment
        var fine_account = doc.customer_currency == "DOP" ?
                frm.doc._interest_account : frm.doc._interest_account.replace("DOP", "USD")
        var acct_goods_received_nb = ""
        var payment_account_dop = ""
        var interest_income_account = ""
        frappe.model.get_value(
            "FM Configuration", 
            "FM Configuration", 
            ["goods_received_but_not_billed", "payment_account", "disbursement_account", "interest_income_account"],
            function(data){
                if(data){
                    acct_goods_received_nb = data.goods_received_but_not_billed
                    if (doc.mode_of_payment == "Cash Entry")
                        payment_account_dop = data.payment_account
                    else
                        payment_account_dop = data.disbursement_account

                interest_income_account = doc.customer_currency == "DOP" ?
                data.interest_income_account : data.interest_income_account.replace("DOP", "USD")                    

                }
            }
        )      
        frm.set_value("loan", repayment.parent)
        frm.set_value("pagare", repayment.name)
        frm.set_value("es_un_pagare", "1")
        
        frm.doc._capital = repayment.capital
        frm.doc._interes = repayment.interes
        doc.fecha_de_vencimiento = repayment.fecha

        var fields = {
            "due_date": "fecha_de_vencimiento",
            "dutty_amount": "paid_amount",
            "partially_paid": "paid_amount",
            "amount_paid": "paid_amount",
            "fine_discount": "fine_discount",
            "pending_amount": "pending_amount",
            "insurance_amount": "insurance",
            "mode_of_payment": "mode_of_payment",
            "fine": "fine",
            "repayment_no": "repayment_idx",
            "currency": "customer_currency",
            "gps": "gps",
            "gastos_recuperacion": "gastos_recuperacion",
        }

        frm.set_value("multi_currency", doc.customer_currency == "DOP" ? 0 : 1)
        $.each(fields, function(key, field) {
            frm.set_value(key, doc[field])
        })

        var fields = ["payment_account", "customer_loan_account", "disbursement_account", "customer"]
        frappe.db.get_value(repayment.parenttype, repayment.parent, fields, function(data) {
            
            var payment_account = doc.mode_of_payment == "Cash Entry" ? 
                data.payment_account: data.disbursment_account

            frm.doc.accounts = []
            frm.add_child("accounts", {
                "account": payment_account,
                "debit_in_account_currency": doc.paid_amount,
                "account_currency": doc.customer_currency,
                "reference_type": repayment.parenttype,
                "reference_name": repayment.parent
            })
            if (doc.gastos_recuperacion || doc.gps){
                doc.gps = doc.gps || 0.00
                doc.gastos_recuperacion = doc.gastos_recuperacion || 0.00

                frm.add_child("accounts", {
                    "account": payment_account_dop,
                    "debit_in_account_currency": doc.gastos_recuperacion + doc.gps,
                    "account_currency": "DOP",
                    "reference_type": repayment.parenttype,
                    "reference_name": repayment.parent
                })
            }
            if (doc.fine_discount){

                frm.add_child("accounts", {
                    "account": interest_income_account,
                    "debit_in_account_currency": doc.fine_discount,
                })
            }
            var credit_amounts = [
                repayment.capital, 
                repayment.interes,
                repayment.insurance 
            ]

            $.each(credit_amounts, function(idx, amount) {

                if (amount){ // This is to avoid create a row with 0 when the amount is not available

                    frm.add_child("accounts", {
                        "account": data.customer_loan_account,
                        "credit_in_account_currency": amount,
                        "party": data.customer,
                        "party_type": "Customer",
                        "account_currency": doc.customer_currency,
                    })
                }
            })
            if (doc.fine) {
                frm.add_child("accounts", {
                    "account": fine_account,
                    "credit_in_account_currency": doc.fine,
                    "account_currency": doc.customer_currency,
                    "reference_type": repayment.parenttype,
                    "reference_name": repayment.parent
                })
            }
            if (doc.gps) {
                frm.add_child("accounts", {
                    "account": acct_goods_received_nb,
                    "credit_in_account_currency": doc.gps,
                    "account_currency": doc.customer_currency,
                    "reference_type": repayment.parenttype,
                    "reference_name": repayment.parent
                })
            }
            if (doc.gastos_recuperacion ) {
                frm.add_child("accounts", {
                    "account": acct_goods_received_nb,
                    "credit_in_account_currency": doc.gastos_recuperacion,
                    "account_currency": doc.customer_currency,
                    "reference_type": repayment.parenttype,
                    "reference_name": repayment.parent
                })
            }
            
            refresh_field("accounts")
        })
    },
})