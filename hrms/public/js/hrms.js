// HRMS Global JavaScript Functions

// Set up shortcuts for common pages/reports
frappe.provide('hrms');

$(document).ready(function() {
    // Add custom CSS
    $('<style type="text/css">' +
        '.employee-dashboard-card { border-radius: 8px; margin-bottom: 15px; padding: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }' +
        '.employee-dashboard-card-title { font-size: 16px; font-weight: 600; margin-bottom: 10px; }' +
        '.employee-dashboard-card-value { font-size: 24px; font-weight: 700; margin-bottom: 5px; }' +
        '.employee-dashboard-card-subtitle { font-size: 12px; color: #6c757d; }' +
        '.employee-dashboard-card-icon { font-size: 20px; float: right; margin-top: -35px; opacity: 0.7; }' +
        '.dashboard-list-item { padding: 8px 0; border-bottom: 1px solid #f0f4f7; }' +
        '.dashboard-list-item:last-child { border-bottom: none; }' +
        '.hr-dashboard-section { margin-bottom: 25px; }' +
        '.hr-dashboard-section-title { font-size: 18px; font-weight: 600; margin-bottom: 15px; padding-bottom: 5px; border-bottom: 1px solid #f0f4f7; }' +
    '</style>').appendTo('head');
    
    // Override standard Frappe dialogs with custom styling
    hrms.show_success_message = function(message) {
        frappe.show_alert({
            message: message, 
            indicator: 'green'
        });
    };
    
    hrms.show_error_message = function(message) {
        frappe.show_alert({
            message: message, 
            indicator: 'red'
        });
    };
    
    // Add general utility methods
    hrms.get_current_employee = function(callback) {
        if (frappe.session.user === "Administrator") {
            if (callback) {
                callback(null);
            }
            return;
        }
        
        frappe.db.get_value('Employee', {user_id: frappe.session.user}, 'name', (r) => {
            if (r && r.name) {
                if (callback) {
                    callback(r.name);
                }
            } else {
                if (callback) {
                    callback(null);
                }
            }
        });
    };
    
    // Quick links menu
    hrms.show_quick_links = function() {
        let d = new frappe.ui.Dialog({
            title: __('HR Quick Links'),
            fields: [
                {
                    fieldname: 'section_employee',
                    fieldtype: 'Section Break',
                    label: __('Employee'),
                    collapsible: 0
                },
                {
                    fieldname: 'create_employee',
                    fieldtype: 'Button',
                    label: __('New Employee'),
                    click: function() {
                        d.hide();
                        frappe.new_doc('Employee');
                    }
                },
                {
                    fieldname: 'employee_list',
                    fieldtype: 'Button',
                    label: __('Employee List'),
                    click: function() {
                        d.hide();
                        frappe.set_route('List', 'Employee');
                    }
                },
                {
                    fieldname: 'section_attendance',
                    fieldtype: 'Section Break',
                    label: __('Attendance & Leave'),
                    collapsible: 0
                },
                {
                    fieldname: 'mark_attendance',
                    fieldtype: 'Button',
                    label: __('Mark Attendance'),
                    click: function() {
                        d.hide();
                        frappe.new_doc('Attendance');
                    }
                },
                {
                    fieldname: 'upload_attendance',
                    fieldtype: 'Button',
                    label: __('Upload Attendance'),
                    click: function() {
                        d.hide();
                        frappe.set_route('Form', 'Upload Attendance');
                    }
                },
                {
                    fieldname: 'new_leave_application',
                    fieldtype: 'Button',
                    label: __('New Leave Application'),
                    click: function() {
                        d.hide();
                        frappe.new_doc('Leave Application');
                    }
                },
                {
                    fieldname: 'section_recruitment',
                    fieldtype: 'Section Break',
                    label: __('Recruitment'),
                    collapsible: 0
                },
                {
                    fieldname: 'new_job_opening',
                    fieldtype: 'Button',
                    label: __('New Job Opening'),
                    click: function() {
                        d.hide();
                        frappe.new_doc('Job Opening');
                    }
                },
                {
                    fieldname: 'new_job_applicant',
                    fieldtype: 'Button',
                    label: __('New Job Applicant'),
                    click: function() {
                        d.hide();
                        frappe.new_doc('Job Applicant');
                    }
                },
                {
                    fieldname: 'section_payroll',
                    fieldtype: 'Section Break',
                    label: __('Payroll'),
                    collapsible: 0
                },
                {
                    fieldname: 'new_salary_structure',
                    fieldtype: 'Button',
                    label: __('New Salary Structure'),
                    click: function() {
                        d.hide();
                        frappe.new_doc('Salary Structure');
                    }
                },
                {
                    fieldname: 'new_salary_slip',
                    fieldtype: 'Button',
                    label: __('New Salary Slip'),
                    click: function() {
                        d.hide();
                        frappe.new_doc('Salary Slip');
                    }
                },
                {
                    fieldname: 'section_reports',
                    fieldtype: 'Section Break',
                    label: __('Reports'),
                    collapsible: 0
                },
                {
                    fieldname: 'monthly_attendance_sheet',
                    fieldtype: 'Button',
                    label: __('Monthly Attendance Sheet'),
                    click: function() {
                        d.hide();
                        frappe.set_route('query-report', 'Monthly Attendance Sheet');
                    }
                },
                {
                    fieldname: 'employee_leave_balance',
                    fieldtype: 'Button',
                    label: __('Employee Leave Balance'),
                    click: function() {
                        d.hide();
                        frappe.set_route('query-report', 'Employee Leave Balance');
                    }
                }
            ]
        });
        
        // Custom styling for buttons
        d.wrapper.find('.form-section:not(:first-child)').css({
            'margin-top': '20px'
        });
        
        d.wrapper.find('.frappe-control button').css({
            'margin': '2px',
            'width': '100%'
        });
        
        d.show();
    };
    
    // Add quick links to navbar
    if (frappe.boot.user.roles.includes('HR Manager') || frappe.boot.user.roles.includes('HR User')) {
        $('.navbar-right').prepend(
            '<li class="dropdown"><a class="dropdown-toggle" data-toggle="dropdown" href="#" onclick="hrms.show_quick_links()"> \
                <div><i class="fa fa-users"></i><span class="hidden-xs hidden-sm"> HR Tools</span></div> \
            </a></li>'
        );
    }
});

// Show dashboard links based on role
frappe.provide('hrms.dashboard');

hrms.dashboard.setup_dashboard_links = function() {
    if (frappe.boot.user.roles.includes('HR Manager') || frappe.boot.user.roles.includes('HR User')) {
        frappe.links_info["HR"] = {
            "label": __("Human Resources"),
            "icon": "fa fa-users",
            "color": "#2ecc71",
            "type": "module",
            "doctype": [
                {
                    "label": __("Employee"),
                    "name": "Employee",
                    "onboard": 1,
                },
                {
                    "label": __("Attendance"),
                    "name": "Attendance",
                    "onboard": 1,
                },
                {
                    "label": __("Leave Application"),
                    "name": "Leave Application",
                    "onboard": 1,
                },
                {
                    "label": __("Salary Slip"),
                    "name": "Salary Slip",
                    "onboard": 1,
                }
            ]
        };
    }
};

// Utility functions for HR Dashboard
frappe.provide('hrms.utils');

hrms.utils.format_employee_name = function(employee_name, employee_id) {
    if (!employee_name) return "";
    return employee_name + (employee_id ? ` (${employee_id})` : "");
};

// Filters for various HR reports
hrms.utils.setup_hr_report_filters = function(report_name) {
    if (report_name === "Monthly Attendance Sheet") {
        frappe.query_reports["Monthly Attendance Sheet"] = {
            "filters": [
                {
                    "fieldname": "month",
                    "label": __("Month"),
                    "fieldtype": "Select",
                    "options": [
                        { "value": 1, "label": __("Jan") },
                        { "value": 2, "label": __("Feb") },
                        { "value": 3, "label": __("Mar") },
                        { "value": 4, "label": __("Apr") },
                        { "value": 5, "label": __("May") },
                        { "value": 6, "label": __("Jun") },
                        { "value": 7, "label": __("Jul") },
                        { "value": 8, "label": __("Aug") },
                        { "value": 9, "label": __("Sep") },
                        { "value": 10, "label": __("Oct") },
                        { "value": 11, "label": __("Nov") },
                        { "value": 12, "label": __("Dec") }
                    ],
                    "default": moment().month() + 1
                },
                {
                    "fieldname": "year",
                    "label": __("Year"),
                    "fieldtype": "Select",
                    "options": [
                        { "value": 2020, "label": 2020 },
                        { "value": 2021, "label": 2021 },
                        { "value": 2022, "label": 2022 },
                        { "value": 2023, "label": 2023 },
                        { "value": 2024, "label": 2024 },
                        { "value": 2025, "label": 2025 }
                    ],
                    "default": moment().year()
                },
                {
                    "fieldname": "employee",
                    "label": __("Employee"),
                    "fieldtype": "Link",
                    "options": "Employee"
                },
                {
                    "fieldname": "department",
                    "label": __("Department"),
                    "fieldtype": "Link",
                    "options": "Department"
                },
                {
                    "fieldname": "company",
                    "label": __("Company"),
                    "fieldtype": "Link",
                    "options": "Company",
                    "default": frappe.defaults.get_user_default("Company"),
                    "reqd": 1
                }
            ]
        };
    }
};
