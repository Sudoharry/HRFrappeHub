frappe.ui.form.on('Attendance', {
    refresh: function(frm) {
        // Add custom buttons
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Mark Attendance'), function() {
                frappe.route_options = {
                    "employee": frm.doc.employee,
                    "attendance_date": frappe.datetime.add_days(frm.doc.attendance_date, 1)
                };
                frappe.set_route("Form", "Attendance", "New Attendance");
            });
        }
        
        // Set indicator color based on status
        if (frm.doc.status === "Present") {
            frm.set_indicator_formatter('status', function(doc) {
                return "Present" === doc.status ? "green" : "red";
            });
        } else if (frm.doc.status === "Absent") {
            frm.set_indicator_formatter('status', function(doc) {
                return "Absent" === doc.status ? "red" : "green";
            });
        } else if (frm.doc.status === "Half Day") {
            frm.set_indicator_formatter('status', function(doc) {
                return "Half Day" === doc.status ? "orange" : "red";
            });
        } else if (frm.doc.status === "On Leave") {
            frm.set_indicator_formatter('status', function(doc) {
                return "On Leave" === doc.status ? "blue" : "red";
            });
        }
    },
    
    onload: function(frm) {
        // Set query for Employee
        frm.set_query("employee", function() {
            return {
                "filters": {
                    "status": "Active"
                }
            };
        });
        
        // Default values for new document
        if (frm.doc.__islocal) {
            frm.set_value("attendance_date", frappe.datetime.get_today());
        }
    },
    
    attendance_date: function(frm) {
        // Check if attendance date is in the future
        if (frm.doc.attendance_date) {
            if (frappe.datetime.get_day_diff(frm.doc.attendance_date, frappe.datetime.get_today()) > 0) {
                frappe.msgprint(__("Attendance cannot be marked for future dates"));
                frm.set_value("attendance_date", frappe.datetime.get_today());
            }
        }
        
        // Check if there's a holiday
        if (frm.doc.employee && frm.doc.attendance_date) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Employee",
                    filters: { name: frm.doc.employee },
                    fieldname: ["holiday_list", "company"]
                },
                callback: function(r) {
                    if (r.message && r.message.holiday_list) {
                        frappe.call({
                            method: "frappe.client.get_list",
                            args: {
                                doctype: "Holiday",
                                filters: [
                                    ["parent", "=", r.message.holiday_list],
                                    ["holiday_date", "=", frm.doc.attendance_date]
                                ],
                                fields: ["name", "description"]
                            },
                            callback: function(r) {
                                if (r.message && r.message.length > 0) {
                                    frappe.msgprint(__("This day is a holiday: {0}", [r.message[0].description]));
                                }
                            }
                        });
                    }
                }
            });
        }
        
        // Check if there's an existing leave application for this date
        if (frm.doc.employee && frm.doc.attendance_date) {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Leave Application",
                    filters: [
                        ["employee", "=", frm.doc.employee],
                        ["from_date", "<=", frm.doc.attendance_date],
                        ["to_date", ">=", frm.doc.attendance_date],
                        ["docstatus", "=", 1]
                    ],
                    fields: ["name", "leave_type"]
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        frappe.msgprint(__("There is an approved leave application for this day for {0}", [r.message[0].leave_type]));
                        frm.set_value("status", "On Leave");
                    }
                }
            });
        }
    },
    
    employee: function(frm) {
        // Get and set employee name
        if (frm.doc.employee) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Employee",
                    filters: { name: frm.doc.employee },
                    fieldname: ["employee_name", "company"]
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value("employee_name", r.message.employee_name);
                        frm.set_value("company", r.message.company);
                    }
                }
            });
            
            // Check status
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Employee",
                    filters: { name: frm.doc.employee },
                    fieldname: ["status", "date_of_joining", "relieving_date"]
                },
                callback: function(r) {
                    if (r.message) {
                        if (r.message.status === "Inactive") {
                            frappe.msgprint(__("Employee is not active"));
                        } else if (r.message.status === "Left") {
                            frappe.msgprint(__("Employee has left the organization"));
                        } else if (frm.doc.attendance_date && r.message.date_of_joining) {
                            if (frappe.datetime.get_day_diff(frm.doc.attendance_date, r.message.date_of_joining) < 0) {
                                frappe.msgprint(__("Attendance date cannot be less than employee's joining date"));
                                frm.set_value("attendance_date", r.message.date_of_joining);
                            }
                        }
                    }
                }
            });
        }
    },
    
    status: function(frm) {
        // Set working hours based on status
        if (frm.doc.status === "Present") {
            // Get default shift for the employee
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Employee",
                    filters: { name: frm.doc.employee },
                    fieldname: ["default_shift"]
                },
                callback: function(r) {
                    if (r.message && r.message.default_shift) {
                        frappe.call({
                            method: "frappe.client.get_value",
                            args: {
                                doctype: "Shift Type",
                                filters: { name: r.message.default_shift },
                                fieldname: ["start_time", "end_time"]
                            },
                            callback: function(r) {
                                if (r.message) {
                                    frm.set_value("working_hours", 8); // Default to 8 hours
                                }
                            }
                        });
                    } else {
                        frm.set_value("working_hours", 8); // Default to 8 hours
                    }
                }
            });
        } else if (frm.doc.status === "Half Day") {
            frm.set_value("working_hours", 4); // Half day is 4 hours
        } else {
            frm.set_value("working_hours", 0);
        }
    }
});
