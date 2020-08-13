frappe.ui.form.on("Poliza de Seguro", {
    "refresh": (frm) => {
        frm.is_new() && frm.set_value("repayments", frappe.boot.insurance_repayments);
        frm.is_new() && ! frm.doc.loan && frm.trigger("fetch_loan");
        // frm.doc.docstatus < 1 && frm.set_value("branch_office", frappe.boot.sucursal);
    },
    "repayments": (frm) => frm.trigger("total_amount"),
    "fetch_loan": (frm) => {
        let field = {"label": "Prestamo", "fieldtype": "Link", "fieldname": "loan", "options": "Loan"};
        frappe.prompt(field, (values) => {
            frm.set_value("loan", values["loan"]);
            frm.refresh();
        }, "Seleccione el Prestamo", "Continuar");
    },
    "validate": (frm) => {
        ! frm.doc.loan && frm.trigger("fetch_loan");
    },
    "loan": (frm) => frm.trigger("fetch_customer_details"),
    "fetch_customer_details": (frm) => {
        frappe.db.get_value("Loan", frm.doc.loan, ["customer", "customer_name", "asset", "branch_office"])
            .then((response) => $.each(response.message, (key, value) => {console.log(value);frm.set_value(key, value)}));
    }
});