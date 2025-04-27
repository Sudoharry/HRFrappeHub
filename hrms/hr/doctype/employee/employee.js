frappe.ui.form.on('Employee', {
    setup: function(frm) {
        frm.set_query("department", function() {
            return {
                "filters": {
                    "company": frm.doc.company
                }
            };
        });
        
        frm.set_query("reports_to", function() {
            return {
                "filters": {
                    "company": frm.doc.company
                }
            };
        });
        
        frm.set_query("leave_policy", function() {
            return {
                "filters": {
                    "company": frm.doc.company
                }
            };
        });
        
        frm.set_query("salary_structure", function() {
            return {
                "filters": {
                    "company": frm.doc.company,
                    "docstatus": 1
                }
            };
        });
    },
    
    refresh: function(frm) {
        // Custom buttons for creating related documents
        if(frm.doc.status == "Active") {
            frm.add_custom_button(__("Attendance"), function() {
                frappe.route_options = {
                    "employee": frm.doc.name,
                    "attendance_date": frappe.datetime.get_today()
                };
                frappe.set_route("Form", "Attendance", "New Attendance");
            }, __("Create"));
            
            frm.add_custom_button(__("Leave Application"), function() {
                frappe.route_options = {
                    "employee": frm.doc.name
                };
                frappe.set_route("Form", "Leave Application", "New Leave Application");
            }, __("Create"));
            
            frm.add_custom_button(__("Salary Slip"), function() {
                frappe.route_options = {
                    "employee": frm.doc.name
                };
                frappe.set_route("Form", "Salary Slip", "New Salary Slip");
            }, __("Create"));
            
            frm.add_custom_button(__("Appraisal"), function() {
                frappe.route_options = {
                    "employee": frm.doc.name
                };
                frappe.set_route("Form", "Appraisal", "New Appraisal");
            }, __("Create"));
        }
        
        // View related records
        frm.add_custom_button(__("Leave Balance"), function() {
            frappe.route_options = {
                "employee": frm.doc.name
            };
            frappe.set_route("query-report", "Employee Leave Balance");
        }, __("View"));
        
        frm.add_custom_button(__("Attendance"), function() {
            frappe.route_options = {
                "employee": frm.doc.name
            };
            frappe.set_route("List", "Attendance", "List");
        }, __("View"));
        
        frm.add_custom_button(__("Leave Applications"), function() {
            frappe.route_options = {
                "employee": frm.doc.name
            };
            frappe.set_route("List", "Leave Application", "List");
        }, __("View"));
        
        frm.add_custom_button(__("Salary Slips"), function() {
            frappe.route_options = {
                "employee": frm.doc.name
            };
            frappe.set_route("List", "Salary Slip", "List");
        }, __("View"));
        
        // Dashboard
        frm.add_custom_button(__("Dashboard"), function() {
            frappe.set_route("employee-dashboard", frm.doc.name);
        });
        
        // Emergency Contact and Personal Details sections
        if (frm.doc.__islocal) {
            hide_field(["emergency_contact_details", "personal_details"]);
        } else {
            unhide_field(["emergency_contact_details", "personal_details"]);
        }
    },
    
    status: function(frm) {
        // Show/hide relieving_date based on status
        frm.toggle_reqd("relieving_date", frm.doc.status === "Left");
        
        // Warn if trying to set inactive employee as a reports_to
        if (frm.doc.status == "Left") {
            frappe.msgprint(__("This employee has left the organization. Please make sure to reassign their subordinates to another manager."));
        }
    },
    
    date_of_birth: function(frm) {
        if (frm.doc.date_of_birth) {
            // Calculate age
            var today = new Date();
            var birthDate = new Date(frm.doc.date_of_birth);
            var age = today.getFullYear() - birthDate.getFullYear();
            frm.set_value('age', age);
            
            // Warning for employees under 18
            if (age < 18) {
                frappe.msgprint(__("Warning: Employee is under 18 years old."));
            }
        }
    },
    
    company: function(frm) {
        // Clear fields that depend on company
        frm.set_value('department', '');
        frm.set_value('branch', '');
        frm.set_value('reports_to', '');
        frm.set_value('leave_policy', '');
        frm.set_value('salary_structure', '');
    },
    
    user_id: function(frm) {
        // Auto-populate related user fields
        if (frm.doc.user_id) {
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "User",
                    name: frm.doc.user_id
                },
                callback: function(data) {
                    if (data.message) {
                        frm.set_value('company_email', data.message.email);
                        frm.set_value('first_name', data.message.first_name);
                        frm.set_value('last_name', data.message.last_name);
                    }
                }
            });
        }
    }
});
