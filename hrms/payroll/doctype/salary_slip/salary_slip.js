frappe.ui.form.on('Salary Slip', {
    refresh: function(frm) {
        // Custom buttons
        if(frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Create Bank Entry'), function() {
                // Create bank entry for salary payment
                frappe.model.open_mapped_doc({
                    method: "hrms.payroll.doctype.salary_slip.salary_slip.make_bank_entry",
                    frm: frm
                });
            }, __("Actions"));
            
            frm.add_custom_button(__('Print'), function() {
                // Print salary slip
                frappe.set_route("print", frm.doctype, frm.docname);
            }, __("Actions"));
            
            frm.add_custom_button(__('Send Email'), function() {
                // Send salary slip via email
                frappe.call({
                    method: "hrms.payroll.doctype.salary_slip.salary_slip.send_salary_slip_email",
                    args: {
                        "salary_slip": frm.doc.name
                    },
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.show_alert({message: __("Email sent to employee"), indicator: 'green'});
                        }
                    }
                });
            }, __("Actions"));
        }
        
        // Show and set indicator colors
        if (frm.doc.status === "Submitted") {
            frm.set_indicator_formatter('status',
                function(doc) { return "green"; });
        } else if (frm.doc.status === "Cancelled") {
            frm.set_indicator_formatter('status',
                function(doc) { return "red"; });
        } else {
            frm.set_indicator_formatter('status',
                function(doc) { return "orange"; });
        }
        
        // Enable/disable fields
        frm.toggle_enable(['employee', 'salary_structure', 'start_date', 'end_date'], frm.doc.docstatus === 0);
    },
    
    onload: function(frm) {
        // Set filter for employee field
        frm.set_query("employee", function() {
            return {
                filters: {
                    'status': 'Active'
                }
            };
        });
        
        // Default values for new document
        if (frm.doc.__islocal) {
            frm.set_value('posting_date', frappe.datetime.get_today());
            frm.set_value('start_date', frappe.datetime.month_start());
            frm.set_value('end_date', frappe.datetime.month_end());
            
            // Set current user as employee if applicable
            if (frappe.session.user !== "Administrator") {
                frappe.db.get_value('Employee', {'user_id': frappe.session.user}, 'name', (r) => {
                    if (r && r.name) {
                        frm.set_value("employee", r.name);
                    }
                });
            }
        }
    },
    
    employee: function(frm) {
        if (frm.doc.employee) {
            // Get employee details
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Employee",
                    name: frm.doc.employee,
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value("employee_name", r.message.employee_name);
                        frm.set_value("department", r.message.department);
                        frm.set_value("designation", r.message.designation);
                        frm.set_value("branch", r.message.branch);
                        
                        // Get salary structure
                        if (r.message.salary_structure) {
                            frm.set_value("salary_structure", r.message.salary_structure);
                        } else {
                            frappe.call({
                                method: "frappe.client.get_value",
                                args: {
                                    doctype: "Salary Structure Assignment",
                                    filters: {
                                        employee: frm.doc.employee,
                                        docstatus: 1
                                    },
                                    fieldname: ["salary_structure"]
                                },
                                callback: function(r) {
                                    if (r.message && r.message.salary_structure) {
                                        frm.set_value("salary_structure", r.message.salary_structure);
                                    } else {
                                        frappe.msgprint(__("No active Salary Structure found for this employee"));
                                    }
                                }
                            });
                        }
                    }
                }
            });
        }
    },
    
    salary_structure: function(frm) {
        if (frm.doc.employee && frm.doc.salary_structure) {
            frm.trigger("calculate_salary_details");
        }
    },
    
    start_date: function(frm) {
        if (frm.doc.employee && frm.doc.salary_structure && frm.doc.start_date && frm.doc.end_date) {
            frm.trigger("calculate_salary_details");
        }
    },
    
    end_date: function(frm) {
        if (frm.doc.employee && frm.doc.salary_structure && frm.doc.start_date && frm.doc.end_date) {
            frm.trigger("calculate_salary_details");
        }
    },
    
    calculate_salary_details: function(frm) {
        frappe.call({
            method: "make_salary_slip_from_salary_structure",
            doc: frm.doc,
            callback: function(r) {
                if (r.message) {
                    frappe.show_alert({message: __("Salary details calculated"), indicator: 'green'});
                    frm.refresh();
                }
            }
        });
    }
});

// Child table event handlers
frappe.ui.form.on('Salary Detail', {
    amount: function(frm) {
        frm.trigger("calculate_totals");
    },
    earnings_remove: function(frm) {
        frm.trigger("calculate_totals");
    },
    deductions_remove: function(frm) {
        frm.trigger("calculate_totals");
    },
    calculate_totals: function(frm) {
        let total_earnings = 0;
        let total_deductions = 0;
        
        // Calculate total earnings
        (frm.doc.earnings || []).forEach(function(d) {
            if (d.amount) {
                total_earnings += flt(d.amount);
            }
        });
        
        // Calculate total deductions
        (frm.doc.deductions || []).forEach(function(d) {
            if (d.amount) {
                total_deductions += flt(d.amount);
            }
        });
        
        frm.set_value('total_earning', total_earnings);
        frm.set_value('total_deduction', total_deductions);
        frm.set_value('net_pay', total_earnings - total_deductions);
    }
});
