frappe.ui.form.on('Leave Application', {
    refresh: function(frm) {
        // Custom buttons
        if (frm.doc.status === "Approved" && frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Cancel Leave Application'), function() {
                // Cancel the leave application
                frappe.confirm(
                    __('Are you sure you want to cancel this leave application?'),
                    function() {
                        frm.set_value("status", "Cancelled");
                        frm.savecancel(function() {
                            frappe.show_alert({message: __("Leave Application cancelled"), indicator: 'green'});
                        });
                    }
                );
            }).addClass("btn-danger");
        }
        
        // Set indicator colors based on status
        if (frm.doc.status) {
            frm.set_indicator_formatter('status',
                function(doc) {
                    let indicator = 'blue';
                    if (doc.status === 'Approved') indicator = 'green';
                    else if (doc.status === 'Rejected') indicator = 'red';
                    else if (doc.status === 'Cancelled') indicator = 'darkgrey';
                    else if (doc.status === 'Active') indicator = 'blue';
                    else if (doc.status === 'Completed') indicator = 'green';
                    return indicator;
                }
            );
        }
        
        // Enable/disable form fields based on document state
        frm.toggle_enable(['leave_type', 'from_date', 'to_date', 'half_day', 'half_day_date'], frm.doc.docstatus === 0);
        
        // Show Leave Balance
        if (frm.doc.employee && frm.doc.leave_type && frm.doc.from_date) {
            frm.trigger('calculate_total_days');
        }
    },
    
    onload: function(frm) {
        // Set query for leave approver
        frm.set_query('leave_approver', function() {
            return {
                query: "frappe.core.doctype.user.user.user_query",
                filters: {
                    "role": "Leave Approver"
                }
            }
        });
        
        // Set employee field filters
        frm.set_query('employee', function() {
            return {
                filters: {
                    'status': 'Active'
                }
            };
        });
        
        // Default values for new document
        if (frm.doc.__islocal) {
            frm.set_value("from_date", frappe.datetime.get_today());
            frm.set_value("to_date", frappe.datetime.get_today());
            
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
    
    validate: function(frm) {
        frm.trigger('calculate_total_days');
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
                        frm.set_value("leave_approver", r.message.leave_approver);
                        frm.set_value("department", r.message.department);
                        
                        // Refresh leave details if leave type exists
                        if (frm.doc.leave_type) {
                            frm.trigger("leave_type");
                        }
                    }
                }
            });
        }
    },
    
    leave_type: function(frm) {
        if (frm.doc.employee && frm.doc.leave_type) {
            // Get leave balance
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Leave Allocation",
                    filters: {
                        employee: frm.doc.employee,
                        leave_type: frm.doc.leave_type,
                        docstatus: 1
                    },
                    fieldname: ["total_leaves_allocated", "total_leaves_taken"]
                },
                callback: function(r) {
                    if (r.message) {
                        let allocated = r.message.total_leaves_allocated || 0;
                        let taken = r.message.total_leaves_taken || 0;
                        let balance = allocated - taken;
                        
                        frm.set_value("leave_balance", balance);
                        
                        if (balance <= 0) {
                            frappe.msgprint(__("The employee has insufficient leave balance for this leave type"));
                        }
                    } else {
                        frappe.msgprint(__("No leave allocation found for this employee and leave type"));
                        frm.set_value("leave_balance", 0);
                    }
                }
            });
            
            // Get leave type details
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Leave Type",
                    name: frm.doc.leave_type,
                },
                callback: function(r) {
                    if (r.message) {
                        if (r.message.max_continuous_days) {
                            let max_days = r.message.max_continuous_days;
                            if (frm.doc.total_leave_days > max_days) {
                                frappe.msgprint(__("This leave type can only be applied for {0} days at a time.", [max_days]));
                            }
                        }
                        
                        if (r.message.is_lwp) {
                            frappe.msgprint(__("This Leave Type is a Leave Without Pay type. Salary will be deducted accordingly."));
                        }
                    }
                }
            });
        }
    },
    
    from_date: function(frm) {
        frm.trigger("calculate_total_days");
        frm.trigger("set_half_day_date");
    },
    
    to_date: function(frm) {
        frm.trigger("calculate_total_days");
        frm.trigger("set_half_day_date");
    },
    
    half_day: function(frm) {
        frm.trigger("calculate_total_days");
        frm.trigger("set_half_day_date");
    },
    
    set_half_day_date: function(frm) {
        if (frm.doc.from_date && frm.doc.half_day) {
            if (!frm.doc.half_day_date) {
                frm.set_value("half_day_date", frm.doc.from_date);
            } else {
                // Validate that half day date is within the leave period
                let half_day_date = frappe.datetime.str_to_obj(frm.doc.half_day_date);
                let from_date = frappe.datetime.str_to_obj(frm.doc.from_date);
                let to_date = frappe.datetime.str_to_obj(frm.doc.to_date);
                
                if (half_day_date < from_date || half_day_date > to_date) {
                    frm.set_value("half_day_date", frm.doc.from_date);
                }
            }
        }
    },
    
    calculate_total_days: function(frm) {
        if (frm.doc.from_date && frm.doc.to_date) {
            // Calculate the total leave days
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Employee",
                    filters: { name: frm.doc.employee },
                    fieldname: "holiday_list"
                },
                callback: function(r) {
                    if (r.message && r.message.holiday_list) {
                        let holiday_list = r.message.holiday_list;
                        
                        frappe.call({
                            method: "frappe.client.get_list",
                            args: {
                                doctype: "Holiday",
                                parent: "Holiday List",
                                filters: [
                                    ["parent", "=", holiday_list],
                                    ["holiday_date", ">=", frm.doc.from_date],
                                    ["holiday_date", "<=", frm.doc.to_date]
                                ],
                                fields: ["holiday_date", "description"]
                            },
                            callback: function(r) {
                                let holidays = r.message || [];
                                
                                let from_date = frappe.datetime.str_to_obj(frm.doc.from_date);
                                let to_date = frappe.datetime.str_to_obj(frm.doc.to_date);
                                let days = frappe.datetime.get_day_diff(to_date, from_date) + 1;
                                
                                // Adjust for holidays
                                let exclude_holidays = true; // Assuming holidays are excluded by default
                                frappe.call({
                                    method: "frappe.client.get_value",
                                    args: {
                                        doctype: "Leave Type",
                                        filters: { name: frm.doc.leave_type },
                                        fieldname: "include_holiday"
                                    },
                                    callback: function(r) {
                                        if (r.message) {
                                            exclude_holidays = !r.message.include_holiday;
                                        }
                                        
                                        if (exclude_holidays) {
                                            days -= holidays.length;
                                        }
                                        
                                        if (frm.doc.half_day) {
                                            days -= 0.5;
                                        }
                                        
                                        if (days < 0) days = 0;
                                        
                                        frm.set_value("total_leave_days", days);
                                        
                                        // Display holidays for user information
                                        if (holidays.length > 0) {
                                            let holiday_names = holidays.map(h => 
                                                `${frappe.datetime.str_to_user(h.holiday_date)}: ${h.description}`).join("\n");
                                            
                                            frm.set_df_property("total_leave_days", "description", 
                                                __("Holidays within leave period:\n{0}", [holiday_names]));
                                        } else {
                                            frm.set_df_property("total_leave_days", "description", "");
                                        }
                                    }
                                });
                            }
                        });
                    } else {
                        // No holiday list, just calculate day difference
                        let from_date = frappe.datetime.str_to_obj(frm.doc.from_date);
                        let to_date = frappe.datetime.str_to_obj(frm.doc.to_date);
                        let days = frappe.datetime.get_day_diff(to_date, from_date) + 1;
                        
                        if (frm.doc.half_day) {
                            days -= 0.5;
                        }
                        
                        frm.set_value("total_leave_days", days);
                    }
                }
            });
        }
    }
});
