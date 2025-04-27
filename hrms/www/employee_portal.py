# Copyright (c) 2023, Your Company and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, formatdate, add_months, add_days, date_diff, get_first_day, get_last_day, nowdate, get_month_name

def get_context(context):
    """Add data to context object for rendering the employee portal page"""
    if not frappe.session.user or frappe.session.user == "Guest":
        frappe.throw(_("You need to be logged in to access this page"), frappe.PermissionError)
    
    # Get employee info for current user
    employee = get_employee_for_user(frappe.session.user)
    if not employee:
        frappe.throw(_("You don't have an associated Employee record"), frappe.PermissionError)
    
    # Add employee info to context
    context.employee = employee
    context.employee_id = employee.name
    context.employee_name = employee.employee_name
    
    # Get reports_to information
    if employee.reports_to:
        reports_to = frappe.db.get_value("Employee", employee.reports_to, "employee_name")
        context.reports_to_name = reports_to
    else:
        context.reports_to_name = None
    
    # Get leave balance
    context.leave_balances = get_leave_balances(employee.name)
    
    # Get recent leave applications
    context.leave_applications = get_leave_applications(employee.name)
    
    # Get attendance summary for current month
    today = getdate()
    first_day = get_first_day(today)
    last_day = get_last_day(today)
    context.month_year = get_month_name(today.month) + " " + str(today.year)
    context.attendance_summary = get_attendance_summary(employee.name, first_day, last_day)
    
    # Get upcoming holidays
    context.holidays = get_upcoming_holidays(employee.company)
    
    # Get recent salary slips
    context.salary_slips = get_salary_slips(employee.name)
    
    # Get performance appraisals
    context.appraisals = get_appraisals(employee.name)
    
    # Set page title and breadcrumbs
    context.title = _("Employee Portal")
    context.parents = [{"name": _("Home"), "route": "/"}]
    
    return context

def get_employee_for_user(user):
    """Get employee record for the current user"""
    employee_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if employee_id:
        return frappe.get_doc("Employee", employee_id)
    return None

def get_leave_balances(employee):
    """Get leave balances for the employee"""
    leave_balances = []
    
    # Get leave allocations
    allocations = frappe.db.sql("""
        SELECT leave_type, total_leaves_allocated, total_leaves_taken
        FROM `tabLeave Allocation`
        WHERE employee = %s AND docstatus = 1
        AND %s BETWEEN from_date AND to_date
    """, (employee, getdate()), as_dict=True)
    
    for allocation in allocations:
        balance_leaves = allocation.total_leaves_allocated - allocation.total_leaves_taken
        leave_balances.append({
            "leave_type": allocation.leave_type,
            "balance_leaves": balance_leaves
        })
    
    return leave_balances

def get_leave_applications(employee, limit=5):
    """Get recent leave applications for the employee"""
    leave_applications = frappe.db.sql("""
        SELECT name, leave_type, from_date, to_date, total_leave_days, status
        FROM `tabLeave Application`
        WHERE employee = %s
        ORDER BY creation DESC
        LIMIT %s
    """, (employee, limit), as_dict=True)
    
    # Add indicator colors
    for leave in leave_applications:
        if leave.status == "Approved":
            leave.indicator = "green"
        elif leave.status == "Rejected":
            leave.indicator = "red"
        elif leave.status == "Open":
            leave.indicator = "orange"
        else:
            leave.indicator = "blue"
    
    return leave_applications

def get_attendance_summary(employee, start_date, end_date):
    """Get attendance summary for the given period"""
    # Get all attendance records for the period
    attendance = frappe.db.sql("""
        SELECT status, COUNT(*) as count
        FROM `tabAttendance`
        WHERE employee = %s
        AND attendance_date BETWEEN %s AND %s
        AND docstatus = 1
        GROUP BY status
    """, (employee, start_date, end_date), as_dict=True)
    
    # Create summary dictionary
    summary = {
        "present": 0,
        "absent": 0,
        "half_day": 0,
        "on_leave": 0
    }
    
    # Fill in the summary
    for status in attendance:
        if status.status in summary:
            summary[status.status] = status.count
    
    return summary

def get_upcoming_holidays(company, limit=5):
    """Get upcoming holidays for the company"""
    # Get holiday list for the company
    holiday_list = frappe.db.get_value("Company", company, "default_holiday_list")
    if not holiday_list:
        return []
    
    # Get upcoming holidays
    today = getdate()
    holidays = frappe.db.sql("""
        SELECT holiday_date, description
        FROM `tabHoliday`
        WHERE parent = %s
        AND holiday_date >= %s
        ORDER BY holiday_date
        LIMIT %s
    """, (holiday_list, today, limit), as_dict=True)
    
    # Add days away information
    for holiday in holidays:
        holiday.days_away = date_diff(holiday.holiday_date, today)
        holiday.is_today = holiday.days_away == 0
    
    return holidays

def get_salary_slips(employee, limit=3):
    """Get recent salary slips for the employee"""
    salary_slips = frappe.db.sql("""
        SELECT name, posting_date, start_date, end_date, net_pay, status, docstatus
        FROM `tabSalary Slip`
        WHERE employee = %s
        ORDER BY creation DESC
        LIMIT %s
    """, (employee, limit), as_dict=True)
    
    # Add month and year info
    for slip in salary_slips:
        slip.month = get_month_name(getdate(slip.start_date).month)
        slip.year = getdate(slip.start_date).year
        
        # Add indicator colors
        if slip.docstatus == 1:
            slip.indicator = "green"
            slip.status = "Submitted"
        elif slip.docstatus == 2:
            slip.indicator = "red"
            slip.status = "Cancelled"
        else:
            slip.indicator = "orange"
            slip.status = "Draft"
    
    return salary_slips

def get_appraisals(employee, limit=3):
    """Get recent performance appraisals for the employee"""
    appraisals = frappe.db.sql("""
        SELECT name, start_date, end_date, score, total_score, status
        FROM `tabAppraisal`
        WHERE employee = %s
        ORDER BY creation DESC
        LIMIT %s
    """, (employee, limit), as_dict=True)
    
    # Add indicator colors
    for appraisal in appraisals:
        if appraisal.status == "Completed":
            appraisal.indicator = "green"
        elif appraisal.status == "Cancelled":
            appraisal.indicator = "red"
        else:
            appraisal.indicator = "blue"
    
    return appraisals
