frappe.ui.form.on('Salary Structure', {
    refresh: function(frm) {
        // Custom buttons
        if(frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Create Salary Slip'), function() {
                frappe.route_options = {
                    'salary_structure': frm.doc.name
                };
                frappe.set_route("Form", "Salary Slip", "New Salary Slip");
            }, __("Actions"));
            
            frm.add_custom_button(__('Assign to Employees'), function() {
                frm.trigger('assign_to_employees');
            }, __("Actions"));
        }
        
        // Enable/disable fields based on document state
        frm.toggle_enable(['from_date', 'to_date', 'company', 'is_active', 'payroll_frequency'], frm.doc.docstatus === 0);
    },
    
    onload: function(frm) {
        // Set company query filter for salary components
        frm.set_query("salary_component", "earnings", function() {
            return {
                filters: {
                    type: "Earning"
                }
            };
        });
        
        frm.set_query("salary_component", "deductions", function() {
            return {
                filters: {
                    type: "Deduction"
                }
            };
        });
        
        // Set company query filter for employee table
        frm.set_query("employee", "employees", function() {
            return {
                filters: {
                    company: frm.doc.company,
                    status: "Active"
                }
            };
        });
        
        // Default values for new document
        if (frm.doc.__islocal) {
            frm.set_value("from_date", frappe.datetime.get_today());
            frm.set_value("payroll_frequency", "Monthly");
        }
    },
    
    assign_to_employees: function(frm) {
        // Dialog to select employees to assign this salary structure
        var d = new frappe.ui.Dialog({
            title: __("Assign to Employees"),
            fields: [
                {
                    fieldname: "get_employees_by",
                    fieldtype: "Select",
                    label: __("Get Employees By"),
                    options: "Company\nDepartment\nDesignation\nBranch",
                    default: "Company"
                },
                {
                    fieldname: "company",
                    fieldtype: "Link",
                    label: __("Company"),
                    options: "Company",
                    reqd: 1,
                    default: frm.doc.company,
                    depends_on: "eval:doc.get_employees_by=='Company'"
                },
                {
                    fieldname: "department",
                    fieldtype: "Link",
                    label: __("Department"),
                    options: "Department",
                    depends_on: "eval:doc.get_employees_by=='Department'"
                },
                {
                    fieldname: "designation",
                    fieldtype: "Link",
                    label: __("Designation"),
                    options: "Designation",
                    depends_on: "eval:doc.get_employees_by=='Designation'"
                },
                {
                    fieldname: "branch",
                    fieldtype: "Link",
                    label: __("Branch"),
                    options: "Branch",
                    depends_on: "eval:doc.get_employees_by=='Branch'"
                }
            ],
            primary_action: function() {
                var data = d.get_values();
                
                // Get employees based on the filter
                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Employee",
                        filters: get_employee_filters(data),
                        fields: ["name", "employee_name", "department", "designation"]
                    },
                    callback: function(r) {
                        if (r.message) {
                            // Clear and add new employees
                            frm.clear_table("employees");
                            r.message.forEach(function(employee) {
                                var row = frm.add_child("employees");
                                row.employee = employee.name;
                                row.employee_name = employee.employee_name;
                                row.base = 0; // Default values
                                row.variable = 0;
                            });
                            frm.refresh_field("employees");
                            frm.save();
                            frappe.show_alert({message: __("Employees added successfully"), indicator: 'green'});
                        } else {
                            frappe.show_alert({message: __("No employees found with the selected criteria"), indicator: 'red'});
                        }
                    }
                });
                d.hide();
            },
            primary_action_label: __("Add Employees")
        });
        
        function get_employee_filters(data) {
            var filters = {};
            filters.status = "Active";
            
            if (data.get_employees_by === "Company") {
                filters.company = data.company;
            } else if (data.get_employees_by === "Department") {
                filters.department = data.department;
            } else if (data.get_employees_by === "Designation") {
                filters.designation = data.designation;
            } else if (data.get_employees_by === "Branch") {
                filters.branch = data.branch;
            }
            
            return filters;
        }
        
        d.show();
    },
    
    calculate_totals: function(frm) {
        let total_earnings = 0;
        let total_deductions = 0;
        
        // Calculate total earnings
        frm.doc.earnings.forEach(function(d) {
            if (d.amount) {
                total_earnings += flt(d.amount);
            }
        });
        
        // Calculate total deductions
        frm.doc.deductions.forEach(function(d) {
            if (d.amount) {
                total_deductions += flt(d.amount);
            }
        });
        
        frm.set_value('total_earning', total_earnings);
        frm.set_value('total_deduction', total_deductions);
        frm.set_value('net_pay', total_earnings - total_deductions);
    }
});

// Child table event handler for Salary Structure Earning
frappe.ui.form.on('Salary Detail', {
    earnings_remove: function(frm) {
        frm.trigger("calculate_totals");
    },
    deductions_remove: function(frm) {
        frm.trigger("calculate_totals");
    },
    amount: function(frm) {
        frm.trigger("calculate_totals");
    },
    earnings_add: function(frm) {
        frm.trigger("calculate_totals");
    },
    deductions_add: function(frm) {
        frm.trigger("calculate_totals");
    }
});
