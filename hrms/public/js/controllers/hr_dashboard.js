frappe.provide('hrms.hr_dashboard');

hrms.hr_dashboard.setup = function(wrapper) {
    let me = this;
    
    // Initialize the dashboard
    me.parent = wrapper;
    me.$parent = $(wrapper);
    
    // Load HR dashboard data
    me.init_dashboard_data();
};

hrms.hr_dashboard.init_dashboard_data = function() {
    let me = this;
    
    // Show loading state
    me.$parent.html(`
        <div class="text-center" style="margin-top: 100px;">
            <i class="fa fa-spinner fa-spin fa-2x"></i>
            <p>${__("Loading HR Dashboard...")}</p>
        </div>
    `);
    
    // Get HR dashboard data
    frappe.call({
        method: "hrms.api.get_hr_dashboard_data",
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
            
            me.dashboard_data = r.message;
            me.render_dashboard();
        }
    });
};

hrms.hr_dashboard.render_dashboard = function() {
    let me = this;
    let data = me.dashboard_data;
    
    // Clear the dashboard
    me.$parent.empty();
    
    // Main dashboard layout
    let dashboard_html = `
        <div class="container hr-dashboard">
            <!-- Header Stats Row -->
            <div class="row" style="margin-top: 20px;">
                <!-- Employee Card -->
                <div class="col-md-3">
                    <div class="employee-dashboard-card" style="background-color: #eaf5fe;">
                        <div class="employee-dashboard-card-title">${__("Employees")}</div>
                        <div class="employee-dashboard-card-icon"><i class="fa fa-users"></i></div>
                        <div class="employee-dashboard-card-value">${data.employee_count || 0}</div>
                        <div class="employee-dashboard-card-subtitle">${__("Total Employees")}</div>
                        <div style="margin-top: 15px;">
                            <button class="btn btn-default btn-xs" onclick="frappe.set_route('List', 'Employee')">
                                ${__("View Employees")}
                            </button>
                        </div>
                    </div>
                </div>
                
                <!-- Attendance Card -->
                <div class="col-md-3">
                    <div class="employee-dashboard-card" style="background-color: #e9f5e9;">
                        <div class="employee-dashboard-card-title">${__("Attendance")}</div>
                        <div class="employee-dashboard-card-icon"><i class="fa fa-calendar-check-o"></i></div>
                        <div class="employee-dashboard-card-value">${data.attendance_today || 0}</div>
                        <div class="employee-dashboard-card-subtitle">${__("Present Today")}</div>
                        <div style="margin-top: 15px;">
                            <button class="btn btn-default btn-xs" onclick="frappe.set_route('List', 'Attendance')">
                                ${__("View Attendance")}
                            </button>
                        </div>
                    </div>
                </div>
                
                <!-- Leave Card -->
                <div class="col-md-3">
                    <div class="employee-dashboard-card" style="background-color: #fef9e6;">
                        <div class="employee-dashboard-card-title">${__("Leave")}</div>
                        <div class="employee-dashboard-card-icon"><i class="fa fa-bed"></i></div>
                        <div class="employee-dashboard-card-value">${data.leave_pending || 0}</div>
                        <div class="employee-dashboard-card-subtitle">${__("Pending Approvals")}</div>
                        <div style="margin-top: 15px;">
                            <button class="btn btn-default btn-xs" onclick="frappe.set_route('List', 'Leave Application')">
                                ${__("View Leave Applications")}
                            </button>
                        </div>
                    </div>
                </div>
                
                <!-- Job Openings Card -->
                <div class="col-md-3">
                    <div class="employee-dashboard-card" style="background-color: #feedf7;">
                        <div class="employee-dashboard-card-title">${__("Job Openings")}</div>
                        <div class="employee-dashboard-card-icon"><i class="fa fa-briefcase"></i></div>
                        <div class="employee-dashboard-card-value">${data.job_openings || 0}</div>
                        <div class="employee-dashboard-card-subtitle">${__("Active Openings")}</div>
                        <div style="margin-top: 15px;">
                            <button class="btn btn-default btn-xs" onclick="frappe.set_route('List', 'Job Opening')">
                                ${__("View Job Openings")}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Department and Attendance Summary -->
            <div class="row" style="margin-top: 20px;">
                <!-- Department Summary -->
                <div class="col-md-6">
                    <div class="employee-dashboard-card">
                        <div class="employee-dashboard-card-title">${__("Department Summary")}</div>
                        <div id="department-chart" style="height: 250px;"></div>
                    </div>
                </div>
                
                <!-- Attendance Summary -->
                <div class="col-md-6">
                    <div class="employee-dashboard-card">
                        <div class="employee-dashboard-card-title">${__("Attendance Summary")}</div>
                        <div id="attendance-chart" style="height: 250px;"></div>
                    </div>
                </div>
            </div>
            
            <!-- Pending Actions and Recent Hires -->
            <div class="row" style="margin-top: 20px;">
                <!-- Pending Actions -->
                <div class="col-md-6">
                    <div class="employee-dashboard-card">
                        <div class="employee-dashboard-card-title">${__("Pending Actions")}</div>
                        <div id="pending-actions">
                            ${me.get_pending_actions_html(data.pending_actions)}
                        </div>
                    </div>
                </div>
                
                <!-- Recent Hires -->
                <div class="col-md-6">
                    <div class="employee-dashboard-card">
                        <div class="employee-dashboard-card-title">${__("Recent Hires")}</div>
                        <div id="recent-hires">
                            ${me.get_recent_hires_html(data.recent_hires)}
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Upcoming Reviews and Birthdays -->
            <div class="row" style="margin-top: 20px;">
                <!-- Upcoming Reviews -->
                <div class="col-md-6">
                    <div class="employee-dashboard-card">
                        <div class="employee-dashboard-card-title">${__("Upcoming Appraisals")}</div>
                        <div id="upcoming-reviews">
                            ${me.get_upcoming_reviews_html(data.upcoming_reviews)}
                        </div>
                    </div>
                </div>
                
                <!-- Upcoming Birthdays -->
                <div class="col-md-6">
                    <div class="employee-dashboard-card">
                        <div class="employee-dashboard-card-title">${__("Upcoming Birthdays")}</div>
                        <div id="upcoming-birthdays">
                            ${me.get_upcoming_birthdays_html(data.upcoming_birthdays)}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    me.$parent.html(dashboard_html);
    
    // Render charts after the DOM is ready
    me.render_department_chart(data.department_data);
    me.render_attendance_chart(data.attendance_data);
};

hrms.hr_dashboard.render_department_chart = function(department_data) {
    if (!department_data || department_data.length === 0) {
        $('#department-chart').html(`<div class="text-muted">${__("No department data available")}</div>`);
        return;
    }
    
    // Prepare data for chart
    let labels = [];
    let values = [];
    
    department_data.forEach(function(dept) {
        labels.push(dept.department);
        values.push(dept.count);
    });
    
    // Create chart
    let chart = new Chart(document.getElementById('department-chart'), {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: __("Employees"),
                data: values,
                backgroundColor: 'rgba(54, 162, 235, 0.6)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                yAxes: [{
                    ticks: {
                        beginAtZero: true,
                        callback: function(value) {if (value % 1 === 0) {return value;}}
                    }
                }]
            }
        }
    });
};

hrms.hr_dashboard.render_attendance_chart = function(attendance_data) {
    if (!attendance_data) {
        $('#attendance-chart').html(`<div class="text-muted">${__("No attendance data available")}</div>`);
        return;
    }
    
    // Create chart
    let chart = new Chart(document.getElementById('attendance-chart'), {
        type: 'pie',
        data: {
            labels: [__("Present"), __("Absent"), __("On Leave"), __("Half Day")],
            datasets: [{
                data: [
                    attendance_data.present || 0,
                    attendance_data.absent || 0,
                    attendance_data.on_leave || 0,
                    attendance_data.half_day || 0
                ],
                backgroundColor: [
                    'rgba(75, 192, 192, 0.6)',
                    'rgba(255, 99, 132, 0.6)',
                    'rgba(54, 162, 235, 0.6)',
                    'rgba(255, 206, 86, 0.6)'
                ],
                borderColor: [
                    'rgba(75, 192, 192, 1)',
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            legend: {
                position: 'right'
            }
        }
    });
};

hrms.hr_dashboard.get_pending_actions_html = function(pending_actions) {
    if (!pending_actions || pending_actions.length === 0) {
        return `<div class="text-muted">${__("No pending actions")}</div>`;
    }
    
    let html = '<div class="dashboard-list">';
    
    pending_actions.forEach(function(action) {
        html += `
            <div class="dashboard-list-item">
                <div>
                    <a href="#${action.route}">${action.title}</a>
                    <span class="pull-right">
                        <span class="indicator ${action.indicator}"></span>
                    </span>
                </div>
                <div class="text-muted">${action.description}</div>
            </div>
        `;
    });
    
    html += '</div>';
    return html;
};

hrms.hr_dashboard.get_recent_hires_html = function(recent_hires) {
    if (!recent_hires || recent_hires.length === 0) {
        return `<div class="text-muted">${__("No recent hires")}</div>`;
    }
    
    let html = '<div class="dashboard-list">';
    
    recent_hires.forEach(function(employee) {
        html += `
            <div class="dashboard-list-item">
                <div>
                    <a href="#Form/Employee/${employee.name}">${employee.employee_name}</a>
                    <span class="pull-right text-muted">
                        ${frappe.datetime.str_to_user(employee.date_of_joining)}
                    </span>
                </div>
                <div class="text-muted">${employee.designation} - ${employee.department}</div>
            </div>
        `;
    });
    
    html += '</div>';
    return html;
};

hrms.hr_dashboard.get_upcoming_reviews_html = function(upcoming_reviews) {
    if (!upcoming_reviews || upcoming_reviews.length === 0) {
        return `<div class="text-muted">${__("No upcoming appraisals")}</div>`;
    }
    
    let html = '<div class="dashboard-list">';
    
    upcoming_reviews.forEach(function(review) {
        html += `
            <div class="dashboard-list-item">
                <div>
                    <a href="#Form/Appraisal/${review.name}">${review.employee_name}</a>
                    <span class="pull-right text-muted">
                        ${frappe.datetime.str_to_user(review.end_date)}
                    </span>
                </div>
                <div class="text-muted">${review.designation} - ${review.department}</div>
            </div>
        `;
    });
    
    html += '</div>';
    return html;
};

hrms.hr_dashboard.get_upcoming_birthdays_html = function(upcoming_birthdays) {
    if (!upcoming_birthdays || upcoming_birthdays.length === 0) {
        return `<div class="text-muted">${__("No upcoming birthdays")}</div>`;
    }
    
    let html = '<div class="dashboard-list">';
    
    upcoming_birthdays.forEach(function(employee) {
        let birthday_date = frappe.datetime.str_to_obj(employee.date_of_birth);
        let today = frappe.datetime.get_today();
        
        // Get this year's birthday date (same month and day, current year)
        let current_year = moment(today).year();
        let birthday_this_year = moment(birthday_date).year(current_year);
        
        // Calculate days until birthday
        let days_until = moment(birthday_this_year).diff(moment(today), 'days');
        
        // If birthday already passed this year, show next year's birthday
        if (days_until < 0) {
            birthday_this_year = moment(birthday_date).year(current_year + 1);
            days_until = moment(birthday_this_year).diff(moment(today), 'days');
        }
        
        // Format the birthday date string
        let birthday_str = frappe.datetime.str_to_user(employee.date_of_birth).split('-');
        birthday_str = birthday_str[0] + '-' + birthday_str[1]; // Only show day and month
        
        html += `
            <div class="dashboard-list-item">
                <div>
                    <a href="#Form/Employee/${employee.name}">${employee.employee_name}</a>
                    <span class="pull-right text-muted">
                        ${birthday_str}
                    </span>
                </div>
                <div class="text-muted">
                    ${days_until === 0 ? __("Today") : __('{0} days from now', [days_until])}
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    return html;
};
