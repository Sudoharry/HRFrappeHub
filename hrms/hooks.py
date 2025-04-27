# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "hrms"
app_title = "HRMS"
app_publisher = "Your Company"
app_description = "Human Resource Management System"
app_icon = "octicon octicon-organization"
app_color = "#3498db"
app_email = "your@example.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = "/assets/hrms/css/hrms.css"
app_include_js = "/assets/hrms/js/hrms.js"

# include js, css files in header of web template
web_include_css = "/assets/hrms/css/hrms_web.css"
web_include_js = "/assets/hrms/js/hrms_web.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "hrms/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Employee": "public/js/employee.js",
    "Attendance": "public/js/attendance.js",
    "Leave Application": "public/js/leave_application.js"
}

# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
home_page = "login"

# website user home page (by Role)
role_home_page = {
    "HR Manager": "hr_dashboard",
    "Employee": "employee_portal"
}

# Generators
# ----------

# automatically create page for each record of this doctype
website_generators = []

# Installation
# ------------

# before_install = "hrms.install.before_install"
# after_install = "hrms.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

notification_config = "hrms.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
    "Employee": "hrms.hr.doctype.employee.employee.get_permission_query_conditions",
    "Attendance": "hrms.hr.doctype.attendance.attendance.get_permission_query_conditions",
    "Leave Application": "hrms.hr.doctype.leave_application.leave_application.get_permission_query_conditions",
}

has_permission = {
    "Employee": "hrms.hr.doctype.employee.employee.has_permission",
    "Attendance": "hrms.hr.doctype.attendance.attendance.has_permission",
    "Leave Application": "hrms.hr.doctype.leave_application.leave_application.has_permission",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "User": {
        "after_insert": "hrms.hrms_controller.create_employee_for_user"
    },
    "Employee": {
        "on_update": "hrms.hrms_controller.update_employee_details"
    },
    "Leave Application": {
        "on_submit": "hrms.notifications.notify_leave_approval",
        "on_cancel": "hrms.notifications.notify_leave_cancellation"
    },
    "Attendance": {
        "on_submit": "hrms.hr.doctype.attendance.attendance.process_auto_attendance"
    },
    "Salary Slip": {
        "on_submit": "hrms.notifications.notify_salary_slip_creation"
    }
}

# Scheduled Tasks
# ---------------
scheduler_events = {
    "daily": [
        "hrms.hr.doctype.attendance.attendance.mark_absent_for_unmarked_employees",
        "hrms.hr.doctype.leave_application.leave_application.update_leave_status"
    ],
    "monthly": [
        "hrms.payroll.doctype.salary_slip.salary_slip.process_scheduled_salary_slips"
    ]
}

# Testing
# -------

# before_tests = "hrms.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#     "frappe.desk.doctype.event.event.get_events": "hrms.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#     "Task": "hrms.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# REST API Endpoints
# ----------------
api_version = 1

# API endpoints for specific doctype
api_endpoints = {
    "Employee": "hrms/api/employee",
    "Leave Application": "hrms/api/leave",
    "Attendance": "hrms/api/attendance",
    "Job Opening": "hrms/api/job_opening",
    "Job Applicant": "hrms/api/job_applicant"
}

# Authentication
# -------------
website_context = {
    "splash_image": "/assets/hrms/images/splash.svg"
}

# Role Based Permissions
role_permissions = {
    "HR Manager": [
        ["Employee", "read", "write", "create", "delete", "submit", "cancel", "amend"],
        ["Attendance", "read", "write", "create", "delete", "submit", "cancel", "amend"],
        ["Leave Application", "read", "write", "create", "delete", "submit", "cancel", "amend"],
        ["Salary Slip", "read", "write", "create", "delete", "submit", "cancel", "amend"],
        ["Job Opening", "read", "write", "create", "delete", "submit", "cancel", "amend"],
        ["Job Applicant", "read", "write", "create", "delete", "submit", "cancel", "amend"],
        ["Appraisal", "read", "write", "create", "delete", "submit", "cancel", "amend"]
    ],
    "HR User": [
        ["Employee", "read", "write", "create"],
        ["Attendance", "read", "write", "create", "submit"],
        ["Leave Application", "read", "write", "create", "submit"],
        ["Salary Slip", "read"],
        ["Job Opening", "read", "write", "create"],
        ["Job Applicant", "read", "write", "create"],
        ["Appraisal", "read", "write", "create"]
    ],
    "Employee": [
        ["Employee", "read", {"user": "owner"}],
        ["Attendance", "read", "write", "create", {"user": "owner"}],
        ["Leave Application", "read", "write", "create", {"user": "owner"}],
        ["Salary Slip", "read", {"user": "owner"}],
        ["Appraisal", "read", {"user": "owner"}]
    ]
}
