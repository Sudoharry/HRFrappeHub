# Copyright (c) 2023, Your Company and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, flt, add_days, date_diff, add_months, get_first_day, get_last_day, nowdate, get_datetime

@frappe.whitelist()
def get_employee_dashboard_data(employee=None):
    """Get data for employee dashboard"""
    if not employee:
        # Get employee for current user
        employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
        if not employee:
            return {"error": "No employee record found"}
    
    # Get employee details
    employee_doc = frappe.get_doc("Employee", employee)
    
    # Get leave balance
    leave_balance = get_leave_balance_for_dashboard(employee)
    
    # Get attendance summary
    attendance_summary = get_attendance_summary_for_dashboard(employee)
    
    # Get recent activities
    activities = get_recent_activities(employee)
    
    # Get leave applications
    leave_applications = get_leave_applications(employee)
    
    # Get salary slips
    salary_slips = get_salary_slips(employee)
    
    # Get upcoming holidays
    holidays = get_upcoming_holidays(employee_doc.company)
    
    # Return consolidated data
    return {
        "employee": {
            "name": employee_doc.name,
            "employee_name": employee_doc.employee_name,
            "designation": employee_doc.designation,
            "department": employee_doc.department,
            "company_email": employee_doc.company_email,
            "personal_email": employee_doc.personal_email,
            "date_of_joining": employee_doc.date_of_joining
        },
        "leave_balance": leave_balance,
        "attendance_summary": attendance_summary,
        "activities": activities,
        "leave_applications": leave_applications,
        "salary_slips": salary_slips,
        "holidays": holidays
    }

@frappe.whitelist()
def get_hr_dashboard_data(filters=None):
    """Get data for HR Dashboard"""
    if not filters:
        filters = {}
    
    # Check if user has HR permissions
    if not frappe.has_permission("Employee", "read"):
        frappe.throw(_("You don't have permission to access this data"), frappe.PermissionError)
    
    # Get basic counts
    employee_count = get_employee_count(filters)
    attendance_today = get_attendance_today(filters)
    leave_pending = get_pending_leave_count(filters)
    job_openings = get_job_openings_count(filters)
    
    # Get department-wise data
    department_data = get_department_employee_count(filters)
    
    # Get attendance data
    attendance_data = get_attendance_data(filters)
    
    # Get pending actions
    pending_actions = get_pending_actions()
    
    # Get recent hires
    recent_hires = get_recent_hires(filters)
    
    # Get upcoming reviews
    upcoming_reviews = get_upcoming_reviews(filters)
    
    # Get upcoming birthdays
    upcoming_birthdays = get_upcoming_birthdays(filters)
    
    # Return consolidated data
    return {
        "employee_count": employee_count,
        "attendance_today": attendance_today,
        "leave_pending": leave_pending,
        "job_openings": job_openings,
        "department_data": department_data,
        "attendance_data": attendance_data,
        "pending_actions": pending_actions,
        "recent_hires": recent_hires,
        "upcoming_reviews": upcoming_reviews,
        "upcoming_birthdays": upcoming_birthdays
    }

def get_leave_balance_for_dashboard(employee):
    """Get leave balance for dashboard"""
    # Get leave allocations
    leave_allocations = frappe.db.sql("""
        SELECT leave_type, total_leaves_allocated, total_leaves_taken
        FROM `tabLeave Allocation`
        WHERE employee = %s AND docstatus = 1
        AND %s BETWEEN from_date AND to_date
    """, (employee, getdate()), as_dict=True)
    
    total_balance = 0
    leave_types = []
    
    for allocation in leave_allocations:
        balance = flt(allocation.total_leaves_allocated) - flt(allocation.total_leaves_taken)
        total_balance += balance
        leave_types.append({
            "leave_type": allocation.leave_type,
            "balance": balance
        })
    
    return {
        "total": total_balance,
        "leave_types": leave_types
    }

def get_attendance_summary_for_dashboard(employee):
    """Get attendance summary for dashboard"""
    # Get month's attendance
    today = getdate()
    first_day = get_first_day(today)
    last_day = get_last_day(today)
    
    # Get attendance records
    attendance = frappe.db.sql("""
        SELECT status, COUNT(*) as count
        FROM `tabAttendance`
        WHERE employee = %s 
        AND attendance_date BETWEEN %s AND %s
        AND docstatus = 1
        GROUP BY status
    """, (employee, first_day, last_day), as_dict=True)
    
    # Create summary
    summary = {
        "present": 0,
        "absent": 0,
        "half_day": 0,
        "on_leave": 0,
        "total": date_diff(today, first_day) + 1  # Days so far in the month
    }
    
    # Fill in actual values
    for entry in attendance:
        if entry.status in summary:
            summary[entry.status] = entry.count
    
    return summary

def get_recent_activities(employee, limit=5):
    """Get recent activities for the employee"""
    activities = []
    
    # Get recent leave applications
    leave_applications = frappe.get_all("Leave Application",
        fields=["name", "leave_type", "from_date", "status", "creation"],
        filters={
            "employee": employee
        },
        order_by="creation desc",
        limit=limit
    )
    
    for application in leave_applications:
        indicator = "blue"
        if application.status == "Approved":
            indicator = "green"
        elif application.status == "Rejected":
            indicator = "red"
        
        activities.append({
            "date": application.creation,
            "description": _("Leave Application: {0} ({1})").format(application.leave_type, application.status),
            "reference_type": "Leave Application",
            "reference_name": application.name,
            "indicator": indicator
        })
    
    # Get recent attendance
    attendance = frappe.get_all("Attendance",
        fields=["name", "attendance_date", "status", "creation"],
        filters={
            "employee": employee
        },
        order_by="creation desc",
        limit=limit
    )
    
    for entry in attendance:
        indicator = "blue"
        if entry.status == "Present":
            indicator = "green"
        elif entry.status == "Absent":
            indicator = "red"
        elif entry.status == "Half Day":
            indicator = "orange"
        
        activities.append({
            "date": entry.creation,
            "description": _("Attendance: {0} on {1}").format(entry.status, frappe.format(entry.attendance_date, {"fieldtype": "Date"})),
            "reference_type": "Attendance",
            "reference_name": entry.name,
            "indicator": indicator
        })
    
    # Sort by date
    activities.sort(key=lambda x: x["date"], reverse=True)
    
    return activities[:limit]

def get_leave_applications(employee, limit=5):
    """Get recent leave applications for employee dashboard"""
    leave_applications = frappe.get_all("Leave Application",
        fields=["name", "leave_type", "from_date", "to_date", "total_leave_days", "status"],
        filters={
            "employee": employee
        },
        order_by="creation desc",
        limit=limit
    )
    
    return leave_applications

def get_salary_slips(employee, limit=5):
    """Get recent salary slips for employee dashboard"""
    salary_slips = frappe.get_all("Salary Slip",
        fields=["name", "start_date", "end_date", "total_working_days", "net_pay", "docstatus"],
        filters={
            "employee": employee
        },
        order_by="creation desc",
        limit=limit
    )
    
    return salary_slips

def get_upcoming_holidays(company, limit=5):
    """Get upcoming holidays"""
    # Get holiday list for the company
    holiday_list = frappe.db.get_value("Company", company, "default_holiday_list")
    if not holiday_list:
        return []
    
    # Get upcoming holidays
    today = getdate()
    holidays = frappe.get_all("Holiday",
        fields=["name", "holiday_date", "description"],
        filters={
            "parent": holiday_list,
            "holiday_date": [">=", today]
        },
        order_by="holiday_date",
        limit=limit
    )
    
    return holidays

def get_employee_count(filters=None):
    """Get total employee count with optional filters"""
    if not filters:
        filters = {}
    
    conditions = ["status = 'Active'"]
    
    if filters.get("department"):
        conditions.append("department = '{}'".format(filters["department"]))
    
    if filters.get("branch"):
        conditions.append("branch = '{}'".format(filters["branch"]))
    
    condition_str = " AND ".join(conditions)
    
    count = frappe.db.sql("""
        SELECT COUNT(*) as count
        FROM `tabEmployee`
        WHERE {0}
    """.format(condition_str))[0][0]
    
    return count

def get_attendance_today(filters=None):
    """Get attendance count for today"""
    if not filters:
        filters = {}
    
    conditions = ["status = 'Present'", "attendance_date = %s"]
    values = [nowdate()]
    
    if filters.get("department"):
        conditions.append("department = %s")
        values.append(filters["department"])
    
    condition_str = " AND ".join(conditions)
    
    count = frappe.db.sql("""
        SELECT COUNT(*) as count
        FROM `tabAttendance`
        WHERE {0}
    """.format(condition_str), values)[0][0]
    
    return count

def get_pending_leave_count(filters=None):
    """Get count of pending leave applications"""
    if not filters:
        filters = {}
    
    conditions = ["status = 'Open'", "docstatus = 0"]
    values = []
    
    if filters.get("department"):
        conditions.append("department = %s")
        values.append(filters["department"])
    
    condition_str = " AND ".join(conditions)
    
    count = frappe.db.sql("""
        SELECT COUNT(*) as count
        FROM `tabLeave Application`
        WHERE {0}
    """.format(condition_str), values)[0][0]
    
    return count

def get_job_openings_count(filters=None):
    """Get count of active job openings"""
    count = frappe.db.count("Job Opening", {"status": "Open"})
    return count

def get_department_employee_count(filters=None):
    """Get department-wise employee count"""
    if not filters:
        filters = {}
    
    conditions = ["e.status = 'Active'"]
    values = []
    
    if filters.get("department"):
        conditions.append("e.department = %s")
        values.append(filters["department"])
    
    condition_str = " AND ".join(conditions)
    
    data = frappe.db.sql("""
        SELECT e.department as department, COUNT(*) as count
        FROM `tabEmployee` e
        WHERE {0}
        GROUP BY e.department
        ORDER BY count DESC
        LIMIT 10
    """.format(condition_str), values, as_dict=True)
    
    return data

def get_attendance_data(filters=None):
    """Get attendance summary data for today"""
    if not filters:
        filters = {}
    
    conditions = ["attendance_date = %s"]
    values = [nowdate()]
    
    if filters.get("department"):
        conditions.append("department = %s")
        values.append(filters["department"])
    
    condition_str = " AND ".join(conditions)
    
    data = frappe.db.sql("""
        SELECT status, COUNT(*) as count
        FROM `tabAttendance`
        WHERE {0}
        GROUP BY status
    """.format(condition_str), values, as_dict=True)
    
    # Create summary
    summary = {
        "present": 0,
        "absent": 0,
        "on_leave": 0,
        "half_day": 0
    }
    
    # Fill in actual values
    for entry in data:
        if entry.status in summary:
            summary[entry.status] = entry.count
    
    return summary

def get_pending_actions():
    """Get pending actions for the HR dashboard"""
    actions = []
    
    # Get pending leave applications
    leave_count = frappe.db.count("Leave Application", {"status": "Open", "docstatus": 0})
    if leave_count > 0:
        actions.append({
            "title": _("Leave Applications"),
            "route": "List/Leave Application/List?status=Open&docstatus=0",
            "indicator": "blue",
            "description": _("{0} applications pending approval").format(leave_count)
        })
    
    # Get pending job applications
    job_applicants_count = frappe.db.count("Job Applicant", {"status": "Open"})
    if job_applicants_count > 0:
        actions.append({
            "title": _("Job Applications"),
            "route": "List/Job Applicant/List?status=Open",
            "indicator": "blue",
            "description": _("{0} applications to review").format(job_applicants_count)
        })
    
    # Get employees with missing information
    incomplete_employees = frappe.db.sql("""
        SELECT COUNT(*) as count
        FROM `tabEmployee`
        WHERE status = 'Active'
        AND (
            IFNULL(personal_email, '') = '' OR
            IFNULL(company_email, '') = '' OR
            IFNULL(emergency_contact_name, '') = '' OR
            IFNULL(emergency_phone, '') = ''
        )
    """)[0][0]
    
    if incomplete_employees > 0:
        actions.append({
            "title": _("Incomplete Profiles"),
            "route": "List/Employee/List?status=Active",
            "indicator": "orange",
            "description": _("{0} employees with incomplete information").format(incomplete_employees)
        })
    
    # Get employees with upcoming contract end
    today = getdate()
    thirty_days_later = add_days(today, 30)
    
    contracts_ending = frappe.db.sql("""
        SELECT COUNT(*) as count
        FROM `tabEmployee`
        WHERE status = 'Active'
        AND employment_type = 'Contract'
        AND IFNULL(relieving_date, '2199-12-31') BETWEEN %s AND %s
    """, (today, thirty_days_later))[0][0]
    
    if contracts_ending > 0:
        actions.append({
            "title": _("Contracts Ending"),
            "route": "List/Employee/List?status=Active&employment_type=Contract",
            "indicator": "red",
            "description": _("{0} contracts ending within 30 days").format(contracts_ending)
        })
    
    return actions

def get_recent_hires(filters=None, limit=5):
    """Get recently hired employees"""
    if not filters:
        filters = {}
    
    conditions = ["status = 'Active'"]
    values = []
    
    if filters.get("department"):
        conditions.append("department = %s")
        values.append(filters["department"])
    
    condition_str = " AND ".join(conditions)
    
    employees = frappe.db.sql("""
        SELECT name, employee_name, designation, department, date_of_joining
        FROM `tabEmployee`
        WHERE {0}
        ORDER BY date_of_joining DESC
        LIMIT %s
    """.format(condition_str), values + [limit], as_dict=True)
    
    return employees

def get_upcoming_reviews(filters=None, limit=5):
    """Get upcoming performance reviews"""
    if not filters:
        filters = {}
    
    conditions = ["docstatus = 0"]
    values = []
    
    if filters.get("department"):
        conditions.append("department = %s")
        values.append(filters["department"])
    
    condition_str = " AND ".join(conditions)
    
    appraisals = frappe.db.sql("""
        SELECT name, employee, employee_name, designation, department, end_date
        FROM `tabAppraisal`
        WHERE {0}
        ORDER BY end_date
        LIMIT %s
    """.format(condition_str), values + [limit], as_dict=True)
    
    return appraisals

def get_upcoming_birthdays(filters=None, limit=5):
    """Get upcoming employee birthdays"""
    if not filters:
        filters = {}
    
    # Filter conditions
    conditions = ["status = 'Active'", "date_of_birth IS NOT NULL"]
    values = []
    
    if filters.get("department"):
        conditions.append("department = %s")
        values.append(filters["department"])
    
    condition_str = " AND ".join(conditions)
    
    # Get all employees with birthdays
    employees = frappe.db.sql("""
        SELECT name, employee_name, date_of_birth, department, designation
        FROM `tabEmployee`
        WHERE {0}
    """.format(condition_str), values, as_dict=True)
    
    # Calculate days until next birthday
    today = getdate()
    current_year = today.year
    
    for employee in employees:
        dob = getdate(employee.date_of_birth)
        
        # Set birthday to current year
        birthday_this_year = getdate(f"{current_year}-{dob.month:02d}-{dob.day:02d}")
        
        # If birthday has passed this year, look at next year's birthday
        if birthday_this_year < today:
            birthday_this_year = getdate(f"{current_year + 1}-{dob.month:02d}-{dob.day:02d}")
        
        # Calculate days until birthday
        employee.days_until_birthday = date_diff(birthday_this_year, today)
    
    # Sort by days until birthday and limit
    employees.sort(key=lambda x: x.days_until_birthday)
    return employees[:limit]
