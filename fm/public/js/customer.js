frappe.ui.form.on("Customer", {
    validate: function(frm) {
        if (!frm.doc.telefonos || frm.doc.telefonos.length < 1) {
            frappe.msgprint("No puede guardar un cliente sin por lo menos dos numeros telefonicos")
            validated = false
        }
        if (!frm.doc.references || frm.doc.references.length < 1) {
            frappe.msgprint("No puede guardar un cliente sin por lo menos dos referencias personales")
            validated = false
        }
    /*if (!frm.doc.empresas|| frm.doc.empresas.length < 1) {
            frappe.msgprint("No puede guardar un cliente sin por lo menos un lugar de trabajo")
            validated = false
        }*/

    },
    tipo_de_documento: function(frm) {
        frm.set_value("cedula", "");
    },
    cedula: function(frm) {
        if(frm.doc.tipo_de_documento == "Cedula")
            frm.set_value("cedula",mask_ced_pas_rnc(frm.doc.cedula))

        if(frm.doc.tipo_de_documento == "Pasaporte")
            frm.set_value("cedula", frm.doc.cedula.replace("-", ""));            
    },
    customer_name: function(frm) {
        frm.set_value("customer_name", frm.doc.customer_name.toUpperCase())
    },
    direccion: function(frm) {
        frm.set_value("direccion", frm.doc.direccion.toUpperCase())
    },
    ocupacion: function(frm) {
        frm.set_value("ocupacion", frm.doc.ocupacion.toUpperCase())
    }
})  

frappe.ui.form.on("Phone Number", "number", function(frm, cdt, cdn){
    var row = locals[cdt][cdn]; 
    frappe.model.set_value(cdt,cdn,"number",mask_phone(row.number));
})

frappe.ui.form.on("Referencia", {
    first_name: function(frm, cdt, cdn){
        var row = locals[cdt][cdn]; 
        frappe.model.set_value(cdt, cdn, "first_name", row.first_name.trim().toUpperCase());
    },
    last_name: function(frm, cdt, cdn){
        var row = locals[cdt][cdn]; 
        frappe.model.set_value(cdt, cdn, "last_name", row.last_name.trim().toUpperCase());
    },
    address: function(frm, cdt, cdn){
        var row = locals[cdt][cdn]; 
        frappe.model.set_value(cdt, cdn, "address", row.address.trim().toUpperCase());
    },
    cedula: function(frm, cdt, cdn){
        var row = locals[cdt][cdn]; 
        frappe.model.set_value(cdt, cdn, "cedula", mask_ced_pas_rnc(row.cedula));
    },
    phone: function(frm, cdt, cdn){
        var row = locals[cdt][cdn]; 
        frappe.model.set_value(cdt, cdn, "phone", mask_phone(row.phone));
    }
})

frappe.ui.form.on("Empresa",{
	telefono:function(frm, cdt, cdn){
    	var row = locals[cdt][cdn]; 
    	frappe.model.set_value(cdt, cdn, "telefono", mask_phone(row.telefono));
	},
	address: function(frm, cdt, cdn){
        var row = locals[cdt][cdn]; 
        frappe.model.set_value(cdt, cdn, "address", row.address.trim().toUpperCase());
    },
	empresa: function(frm, cdt, cdn){
        var row = locals[cdt][cdn]; 
        frappe.model.set_value(cdt, cdn, "empresa", row.empresa.trim().toUpperCase());
    },
	posicion: function(frm, cdt, cdn){
        var row = locals[cdt][cdn]; 
        frappe.model.set_value(cdt, cdn, "posicion", row.posicion.trim().toUpperCase());
    },
	supervisor: function(frm, cdt, cdn){
        var row = locals[cdt][cdn]; 
        frappe.model.set_value(cdt, cdn, "supervisor", row.supervisor.trim().toUpperCase());
    }

})

function valida_cedula(ced) {
    var c = ced.replace(/-/g, '');
    var Cedula = c.substr(0, c.length - 1);
    var Verificador = c.substr(c.length - 1, 1);
    var suma = 0;

    if (c.length < 11) {
        frappe.msgprint("La Cedula ingresada no es valida!")
        return undefined
    }

    for (i = 0; i < Cedula.length; i++) {
        mod = "";
        /*
            se evaluan la posicion en la que esta cada digito, si esta en una
            posicion par el multiplicador sera 1 de lo contrario el 
            multiplicador sera 2
            Ex. 12121212121
            223-0087201-1
        */
        if ((i % 2) == 0) {
            mod = 1
        } else {
            mod = 2
        }
        //luego se multiplica el valor de la posicion con su multiplicador
        res = Cedula.substr(i, 1) * mod;
        /* en caso de que el multiplicador sea mayor que 9 se suman ambos 
            digitos
            Ex. res = 14 entonces sumamos 1 + 4 = 5
            luego acumulamos el reultado
         */
        if (res > 9) {
            res = res.toString();
            uno = res.substr(0, 1);
            dos = res.substr(1, 1);
            res = eval(uno) + eval(dos);
        }
        suma += eval(res);
    }
    /*
        luego a 10 le restamos el modulo del acumulativo, 
    */
    el_numero = (10 - (suma % 10)) % 10;
    if (el_numero == Verificador && Cedula.substr(0, 3) != "000") {
        return "{0}{1}{2}-{3}{4}{5}{6}{7}{8}{9}-{10}".format(c)
    } else {
        frappe.msgprint("La Cedula ingresada no es valida!")
        return undefined
    }
}

function mask_ced_pas_rnc(input)
{
    input = input.trim().replace(/-/g,"")
    
    if (input.length == 11)
        return ("{0}{1}{2}-{3}{4}{5}{6}{7}{8}{9}-{10}".format(input));

    if (input.length == 9)
        return ("{0}-{1}{2}-{3}{4}{5}{6}{7}-{8}".format(input));
    
    return input
}

function mask_phone(phone)
{
    temp = phone.trim().replace(/-/g,"")

    if (temp.length == 10)
        return ("({0}{1}{2}) {3}{4}{5}-{6}{7}{8}{9}".format(temp));
    else
        return phone;

    /*var pattern = new RegExp("((^[0-9]{3})[0-9]{3}[0-9]{4})$");
    var pattern1 = new RegExp("([(][0-9]{3}[)] [0-9]{3}-[0-9]{4})$");
    var pattern2 = new RegExp("([(][0-9]{3}[)][0-9]{3}-[0-9]{4})$");

    if(pattern.test(phone))
        return ("({0}{1}{2}) {3}{4}{5}-{6}{7}{8}{9}".format(phone));
    else if(pattern1.test(phone))
        return phone;
    else if(pattern2.test(phone))
        return ("{0}{1}{2}{3}{4} {5}{6}{7}{8}{9}{10}{11}{12}".format(phone));*/
}

String.prototype.format = function () {
    "use strict";

    var formatted = this;
    for (var prop in arguments[0]) {
        if (arguments[0].hasOwnProperty(prop)) {
            var regexp = new RegExp("\\{" + prop + "\\}", "gi");
            formatted = formatted.replace(regexp, arguments[0][prop]);
        }
    }
    return formatted;
};