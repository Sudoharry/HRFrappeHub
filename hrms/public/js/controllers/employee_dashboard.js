frappe.provide('hrms.employee_dashboard');

hrms.employee_dashboard.setup = function(wrapper) {
    let me = this;
    
    // Initialize the dashboard
    me.parent = wrapper;
    me.$parent = $(wrapper);
    
    // Load employee info
    me.init_employee_data();
};

hrms.employee_dashboard.init_employee_data = function() {
    let me = this;
    
    // Get current employee
    hrms.get_current_employee(function(employee_id) {
        if (!employee_id) {
            me.$parent.html(`
                <div class="page-card">
                    <div class="page-card-head">
                        <span class="indicator red">
                            ${__("Error")}
                        </span>
                    </div>
                    <p>${__("You are not linked to an Employee record. Please contact your HR Manager.")}</p>
                </div>
            `);
            return;
        }
        
        // Show loading state
        me.$parent.html(`
            <div class="text-center" style="margin-top: 100px;">
                <i class="fa fa-spinner fa-spin fa-2x"></i>
                <p>${__("Loading Employee Dashboard...")}</p>
            </div>
        `);
        
        // Get employee data
        frappe.call({
            method: "hrms.api.get_employee_dashboard_data",
            args: {
                employee: employee_id
            },
            callback: function(r) {
                if (r.exc) {
                    me.$parent.html(`
                        <div class="page-card">
                            <div class="page-card-head">
                                <span class="indicator red">
                                    ${__("Error")}
                                </span>
                            </div>
                            <p>${__("Failed to load dashboard data. Please contact your system administrator.")}</p>
                        </div>
                    `);
                    return;
                }
                
                me.employee_data = r.message;
                me.render_dashboard();
            }
        });
    });
};

hrms.employee_dashboard.render_dashboard = function() {
    let me = this;
    let data = me.employee_data;
    
    // Clear the dashboard
    me.$parent.empty();
    
    // Main dashboard layout
    let dashboard_html = `
        <div class="container employee-dashboard">
            <!-- Profile section -->
            <div class="row">
                <div class="col-md-12">
                    <div class="employee-dashboard-card" style="background-color: #f8f9fa;">
                        <div class="row">
                            <div class="col-md-2">
                                <div style="width: 100px; height: 100px; border-radius: 50%; overflow: hidden; margin: auto;">
                                    <i class="fa fa-user-circle-o" style="font-size: 100px; color: #c0c0c0;"></i>
                                </div>
                            </div>
                            <div class="col-md-5">
                                <h3 style="margin-top: 10px;">${data.employee.employee_name}</h3>
                                <div>${data.employee.designation} - ${data.employee.department}</div>
                                <div style="margin-top: 10px;">
                                    <div><i class="fa fa-envelope-o"></i> ${data.employee.company_email || data.employee.personal_email || 'N/A'}</div>
                                    <div><i class="fa fa-clock-o"></i> ${__("Joined")} ${frappe.datetime.str_to_user(data.employee.date_of_joining)}</div>
                                </div>
                            </div>
                            <div class="col-md-5 text-right">
                                <div style="display: inline-block; text-align: center; margin: 0 15px;">
                                    <div style="font-size: 24px; font-weight: bold;">${data.leave_balance.total || 0}</div>
                                    <div>${__("Leave Balance")}</div>
                                </div>
                                <div style="display: inline-block; text-align: center; margin: 0 15px;">
                                    <div style="font-size: 24px; font-weight: bold;">${data.attendance_summary.present || 0}</div>
                                    <div>${__("Days Present")}</div>
                                </div>
                                <br>
                                <button class="btn btn-primary btn-sm" onclick="frappe.set_route('Form', 'Leave Application', 'New Leave Application')">
                                    ${__("Apply for Leave")}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Quick Stats Row -->
            <div class="row" style="margin-top: 20px;">
                <!-- Attendance Card -->
                <div class="col-md-4">
                    <div class="employee-dashboard-card">
                        <div class="employee-dashboard-card-title">${__("Attendance")}</div>
                        <div class="employee-dashboard-card-icon"><i class="fa fa-calendar-check-o"></i></div>
                        <div class="employee-dashboard-card-value">${data.attendance_summary.present || 0} / ${data.attendance_summary.total || 0}</div>
                        <div class="employee-dashboard-card-subtitle">${__("Days Present / Working Days")}</div>
                        <div style="margin-top: 15px;">
                            <button class="btn btn-default btn-xs" onclick="frappe.set_route('Form', 'Attendance', 'New Attendance')">
                                ${__("Mark Attendance")}
                            </button>
                        </div>
                    </div>
                </div>
                
                <!-- Leave Card -->
                <div class="col-md-4">
                    <div class="employee-dashboard-card">
                        <div class="employee-dashboard-card-title">${__("Leave")}</div>
                        <div class="employee-dashboard-card-icon"><i class="fa fa-bed"></i></div>
                        <div class="employee-dashboard-card-value">${data.leave_balance.total || 0}</div>
                        <div class="employee-dashboard-card-subtitle">${__("Available Leave Balance")}</div>
                        <div style="margin-top: 15px;">
                            <button class="btn btn-default btn-xs" onclick="frappe.set_route('Form', 'Leave Application', 'New Leave Application')">
                                ${__("Apply Leave")}
                            </button>
                        </div>
                    </div>
                </div>
                
                <!-- Payroll Card -->
                <div class="col-md-4">
                    <div class="employee-dashboard-card">
                        <div class="employee-dashboard-card-title">${__("Payroll")}</div>
                        <div class="employee-dashboard-card-icon"><i class="fa fa-money"></i></div>
                        <div class="employee-dashboard-card-value">${data.salary_slips.length || 0}</div>
                        <div class="employee-dashboard-card-subtitle">${__("Salary Slips Generated")}</div>
                        <div style="margin-top: 15px;">
                            <button class="btn btn-default btn-xs" onclick="frappe.set_route('List', 'Salary Slip', {employee: '${data.employee.name}'})">
                                ${__("View Salary Slips")}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Recent Activities and Leave Applications -->
            <div class="row" style="margin-top: 20px;">
                <!-- Recent Activities -->
                <div class="col-md-6">
                    <div class="employee-dashboard-card">
                        <div class="employee-dashboard-card-title">${__("Recent Activities")}</div>
                        <div id="recent-activities">
                            ${me.get_recent_activities_html(data.activities)}
                        </div>
                    </div>
                </div>
                
                <!-- Recent Leave Applications -->
                <div class="col-md-6">
                    <div class="employee-dashboard-card">
                        <div class="employee-dashboard-card-title">${__("Leave Applications")}</div>
                        <div id="recent-leave-applications">
                            ${me.get_leave_applications_html(data.leave_applications)}
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Upcoming Events and Holidays -->
            <div class="row" style="margin-top: 20px;">
                <div class="col-md-12">
                    <div class="employee-dashboard-card">
                        <div class="employee-dashboard-card-title">${__("Upcoming Holidays")}</div>
                        <div id="upcoming-holidays">
                            ${me.get_holidays_html(data.holidays)}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    me.$parent.html(dashboard_html);
};

hrms.employee_dashboard.get_recent_activities_html = function(activities) {
    if (!activities || activities.length === 0) {
        return `<div class="text-muted">${__("No recent activities")}</div>`;
    }
    
    let html = '<div class="dashboard-list">';
    
    activities.forEach(function(activity) {
        html += `
            <div class="dashboard-list-item">
                <div>
                    <span class="small text-muted">${frappe.datetime.prettyDate(activity.date)}</span>
                    <span class="pull-right">
                        <span class="indicator ${activity.indicator || 'blue'}"></span>
                    </span>
                </div>
                <div>${activity.description}</div>
            </div>
        `;
    });
    
    html += '</div>';
    return html;
};

hrms.employee_dashboard.get_leave_applications_html = function(leave_applications) {
    if (!leave_applications || leave_applications.length === 0) {
        return `<div class="text-muted">${__("No leave applications")}</div>`;
    }
    
    let html = '<div class="dashboard-list">';
    
    leave_applications.forEach(function(leave) {
        let status_color = 'blue';
        if (leave.status === 'Approved') status_color = 'green';
        if (leave.status === 'Rejected') status_color = 'red';
        
        html += `
            <div class="dashboard-list-item">
                <div>
                    <a href="#Form/Leave Application/${leave.name}">${leave.name}</a>
                    <span class="pull-right">
                        <span class="indicator ${status_color}">${leave.status}</span>
                    </span>
                </div>
                <div>${leave.leave_type}: ${frappe.datetime.str_to_user(leave.from_date)} to ${frappe.datetime.str_to_user(leave.to_date)}</div>
            </div>
        `;
    });
    
    html += '</div>';
    return html;
};

hrms.employee_dashboard.get_holidays_html = function(holidays) {
    if (!holidays || holidays.length === 0) {
        return `<div class="text-muted">${__("No upcoming holidays")}</div>`;
    }
    
    let html = '<div class="row">';
    
    holidays.forEach(function(holiday) {
        // Calculate days remaining
        let holiday_date = frappe.datetime.str_to_obj(holiday.holiday_date);
        let today = frappe.datetime.get_today();
        let days_remaining = frappe.datetime.get_day_diff(holiday_date, today);
        
        html += `
            <div class="col-md-4" style="margin-bottom: 15px;">
                <div style="border: 1px solid #f0f4f7; border-radius: 5px; padding: 10px;">
                    <div style="font-size: 16px; font-weight: 600;">${holiday.description}</div>
                    <div style="font-size: 14px; color: #6c757d;">${frappe.datetime.str_to_user(holiday.holiday_date)}</div>
                    <div style="font-size: 12px; margin-top: 5px;">
                        ${days_remaining > 0 ? `${days_remaining} ${__("days remaining")}` : __("Today")}
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    return html;
};
