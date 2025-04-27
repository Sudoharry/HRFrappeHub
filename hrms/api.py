"""
HRMS API Module

This module contains the API endpoints for HRMS modules.
APIs follow the Frappe-style and are designed to provide
consistent interfaces for the front-end and third-party integrations.
"""

import frappe
from frappe import _
from frappe.utils import getdate, flt, cint, today
import json
from datetime import datetime, timedelta

# ------------------------------------------------------
# Employee APIs
# ------------------------------------------------------

@frappe.whitelist()
def get_employee_details(employee_id=None, user=None):
    """
    Get employee details by employee_id or user
    
    Args:
        employee_id (str, optional): Employee ID
        user (str, optional): User ID
        
    Returns:
        dict: Employee details
    """
    if not (employee_id or user):
        frappe.throw(_("Either employee_id or user is required"))
    
    filters = {}
    if employee_id:
        filters["name"] = employee_id
    elif user:
        filters["user_id"] = user
    
    # Check permissions
    if not frappe.has_permission("Employee", "read", filters):
        frappe.throw(_("Not permitted to access employee details"), frappe.PermissionError)
    
    fields = [
        "name", "employee_id", "employee_name", "first_name", "last_name", 
        "status", "gender", "date_of_birth", "date_of_joining",
        "department", "designation", "company", "reports_to", "user_id"
    ]
    
    employee = frappe.get_value("Employee", filters, fields, as_dict=True)
    
    if not employee:
        frappe.throw(_("Employee not found"))
    
    # Add additional data
    if employee.get("reports_to"):
        employee["reports_to_name"] = frappe.get_value("Employee", 
            employee.reports_to, "employee_name")
    
    return employee

@frappe.whitelist()
def get_organization_chart(company=None, department=None):
    """
    Get organization chart
    
    Args:
        company (str, optional): Company
        department (str, optional): Department
        
    Returns:
        dict: Organization chart data
    """
    if not frappe.has_permission("Employee", "read"):
        frappe.throw(_("Not permitted to access organization chart"), frappe.PermissionError)
    
    filters = {"status": "Active"}
    if company:
        filters["company"] = company
    if department:
        filters["department"] = department
    
    employees = frappe.get_all("Employee", 
        filters=filters,
        fields=["name", "employee_name", "reports_to", "department", "designation", "user_id"],
        order_by="reports_to asc, name asc"
    )
    
    # Build the org chart
    org_chart = {}
    for emp in employees:
        emp_id = emp.get("name")
        org_chart[emp_id] = {
            "id": emp_id,
            "name": emp.get("employee_name"),
            "designation": emp.get("designation"),
            "department": emp.get("department"),
            "children": []
        }
    
    # Second pass to build the tree
    root_nodes = []
    for emp_id, emp_data in org_chart.items():
        reports_to = frappe.get_value("Employee", emp_id, "reports_to")
        
        if reports_to and reports_to in org_chart:
            org_chart[reports_to]["children"].append(emp_data)
        else:
            root_nodes.append(emp_data)
    
    return {"root_nodes": root_nodes}

# ------------------------------------------------------
# Attendance APIs
# ------------------------------------------------------

@frappe.whitelist()
def mark_attendance(employee_id, attendance_date, status, check_in=None, check_out=None):
    """
    Mark attendance for an employee
    
    Args:
        employee_id (str): Employee ID
        attendance_date (str): Attendance date
        status (str): Status (Present, Absent, Half Day, On Leave)
        check_in (str, optional): Check-in time
        check_out (str, optional): Check-out time
        
    Returns:
        dict: Attendance details
    """
    if not frappe.has_permission("Attendance", "write"):
        frappe.throw(_("Not permitted to mark attendance"), frappe.PermissionError)
    
    # Check if employee exists
    if not frappe.db.exists("Employee", employee_id):
        frappe.throw(_("Employee {0} does not exist").format(employee_id))
    
    # Convert date string to date object
    attendance_date = getdate(attendance_date)
    
    # Check if attendance for this date already exists
    existing = frappe.db.exists("Attendance", {
        "employee": employee_id,
        "attendance_date": attendance_date,
        "docstatus": ["!=", 2]  # Not cancelled
    })
    
    if existing:
        frappe.throw(_("Attendance for employee {0} on {1} already exists").format(
            employee_id, attendance_date))
    
    # Create new attendance
    attendance = frappe.new_doc("Attendance")
    attendance.employee = employee_id
    attendance.attendance_date = attendance_date
    attendance.status = status
    
    if check_in:
        attendance.check_in = check_in
    if check_out:
        attendance.check_out = check_out
    
    # Calculate working hours if both check_in and check_out provided
    if check_in and check_out:
        try:
            check_in_time = datetime.strptime(check_in, "%Y-%m-%d %H:%M:%S")
            check_out_time = datetime.strptime(check_out, "%Y-%m-%d %H:%M:%S")
            working_hours = (check_out_time - check_in_time).total_seconds() / 3600
            attendance.working_hours = round(working_hours, 2)
        except Exception:
            frappe.log_error("Error calculating working hours")
    
    attendance.insert()
    attendance.submit()
    
    return {
        "name": attendance.name,
        "status": attendance.status,
        "employee": attendance.employee,
        "attendance_date": attendance.attendance_date,
        "working_hours": attendance.working_hours
    }

@frappe.whitelist()
def get_monthly_attendance(employee_id, month, year):
    """
    Get monthly attendance for an employee
    
    Args:
        employee_id (str): Employee ID
        month (int): Month (1-12)
        year (int): Year
        
    Returns:
        dict: Monthly attendance data
    """
    if not frappe.has_permission("Attendance", "read"):
        frappe.throw(_("Not permitted to access attendance"), frappe.PermissionError)
    
    # Convert to integers
    month = cint(month)
    year = cint(year)
    
    if month < 1 or month > 12:
        frappe.throw(_("Invalid month"))
    
    # Calculate start and end dates for the month
    import calendar
    num_days = calendar.monthrange(year, month)[1]
    start_date = datetime(year, month, 1).date()
    end_date = datetime(year, month, num_days).date()
    
    # Get attendance records for the month
    attendance_records = frappe.get_all("Attendance",
        filters={
            "employee": employee_id,
            "attendance_date": ["between", [start_date, end_date]],
            "docstatus": 1  # Submitted documents only
        },
        fields=["name", "employee", "attendance_date", "status", "check_in", "check_out", "working_hours"]
    )
    
    # Organize by date
    daily_attendance = {}
    for record in attendance_records:
        date_str = record.attendance_date.strftime("%Y-%m-%d")
        daily_attendance[date_str] = record
    
    # Calculate summary
    present_count = len([r for r in attendance_records if r.status == "Present"])
    absent_count = len([r for r in attendance_records if r.status == "Absent"])
    half_day_count = len([r for r in attendance_records if r.status == "Half Day"])
    leave_count = len([r for r in attendance_records if r.status == "On Leave"])
    
    return {
        "employee": employee_id,
        "month": month,
        "year": year,
        "daily_attendance": daily_attendance,
        "summary": {
            "present": present_count,
            "absent": absent_count,
            "half_day": half_day_count,
            "on_leave": leave_count,
            "working_days": num_days,
            "attendance_percentage": round((present_count + (half_day_count / 2)) / num_days * 100, 2) if num_days > 0 else 0
        }
    }

# ------------------------------------------------------
# Leave APIs
# ------------------------------------------------------

@frappe.whitelist()
def apply_leave(employee_id, leave_type_id, from_date, to_date, reason=None):
    """
    Apply for leave
    
    Args:
        employee_id (str): Employee ID
        leave_type_id (str): Leave Type ID
        from_date (str): From date
        to_date (str): To date
        reason (str, optional): Reason for leave
        
    Returns:
        dict: Leave application details
    """
    from frappe.utils import date_diff
    
    if not frappe.has_permission("Leave Application", "write"):
        frappe.throw(_("Not permitted to apply for leave"), frappe.PermissionError)
    
    # Check if employee exists
    if not frappe.db.exists("Employee", employee_id):
        frappe.throw(_("Employee {0} does not exist").format(employee_id))
    
    # Check if leave type exists
    if not frappe.db.exists("Leave Type", leave_type_id):
        frappe.throw(_("Leave Type {0} does not exist").format(leave_type_id))
    
    # Convert date strings to date objects
    from_date = getdate(from_date)
    to_date = getdate(to_date)
    
    # Check if to_date is after from_date
    if from_date > to_date:
        frappe.throw(_("From Date cannot be after To Date"))
    
    # Calculate total leave days
    total_leave_days = date_diff(to_date, from_date) + 1
    
    # Create new leave application
    leave_application = frappe.new_doc("Leave Application")
    leave_application.employee = employee_id
    leave_application.leave_type = leave_type_id
    leave_application.from_date = from_date
    leave_application.to_date = to_date
    leave_application.total_leave_days = total_leave_days
    leave_application.status = "Open"
    
    if reason:
        leave_application.reason = reason
    
    leave_application.insert()
    
    return {
        "name": leave_application.name,
        "employee": leave_application.employee,
        "leave_type": leave_application.leave_type,
        "from_date": leave_application.from_date,
        "to_date": leave_application.to_date,
        "total_leave_days": leave_application.total_leave_days,
        "status": leave_application.status
    }

@frappe.whitelist()
def get_leave_balance(employee_id, leave_type=None):
    """
    Get leave balance for an employee
    
    Args:
        employee_id (str): Employee ID
        leave_type (str, optional): Leave Type ID
        
    Returns:
        dict: Leave balance details
    """
    if not frappe.has_permission("Leave Application", "read"):
        frappe.throw(_("Not permitted to access leave balance"), frappe.PermissionError)
    
    # Get all leave types
    filters = {}
    if leave_type:
        filters["name"] = leave_type
    
    leave_types = frappe.get_all("Leave Type", 
        filters=filters,
        fields=["name", "max_days_allowed", "is_paid_leave"]
    )
    
    # Get leave allocations for this employee
    from frappe.utils import getdate
    
    # Calculate for the current year
    current_year = getdate(today()).year
    start_date = getdate(f"{current_year}-01-01")
    end_date = getdate(f"{current_year}-12-31")
    
    result = {}
    for lt in leave_types:
        leave_type_id = lt.get("name")
        
        # Get approved leave applications
        taken_leaves = frappe.db.sql("""
            SELECT SUM(total_leave_days) FROM `tabLeave Application`
            WHERE employee = %s AND leave_type = %s 
            AND status = 'Approved' AND docstatus = 1
            AND (from_date BETWEEN %s AND %s OR to_date BETWEEN %s AND %s)
        """, (employee_id, leave_type_id, start_date, end_date, start_date, end_date))
        
        taken_leaves = flt(taken_leaves[0][0]) if taken_leaves and taken_leaves[0][0] else 0
        
        # Calculate balance
        max_allowed = lt.get("max_days_allowed") or 0
        balance = max_allowed - taken_leaves
        
        result[leave_type_id] = {
            "leave_type": leave_type_id,
            "max_allowed": max_allowed,
            "taken": taken_leaves,
            "balance": balance,
            "is_paid_leave": lt.get("is_paid_leave")
        }
    
    return {
        "employee": employee_id,
        "year": current_year,
        "leave_balances": result
    }

# ------------------------------------------------------
# Payroll APIs
# ------------------------------------------------------

@frappe.whitelist()
def get_salary_slip_list(employee_id=None, status=None, from_date=None, to_date=None):
    """
    Get list of salary slips
    
    Args:
        employee_id (str, optional): Employee ID
        status (str, optional): Status (Draft, Submitted, Cancelled)
        from_date (str, optional): From date
        to_date (str, optional): To date
        
    Returns:
        list: List of salary slips
    """
    if not frappe.has_permission("Salary Slip", "read"):
        frappe.throw(_("Not permitted to access salary slips"), frappe.PermissionError)
    
    filters = {}
    
    if employee_id:
        filters["employee"] = employee_id
    
    if status:
        filters["status"] = status
    
    # Add date filters if provided
    if from_date:
        from_date = getdate(from_date)
        filters.update({"start_date": [">=", from_date]})
    
    if to_date:
        to_date = getdate(to_date)
        filters.update({"end_date": ["<=", to_date]})
    
    # Get salary slips
    salary_slips = frappe.get_all("Salary Slip",
        filters=filters,
        fields=["name", "employee", "employee_name", "start_date", "end_date", 
                "posting_date", "gross_pay", "total_deduction", "net_pay", "status"],
        order_by="posting_date desc"
    )
    
    return salary_slips

@frappe.whitelist()
def generate_salary_slip(employee_id, start_date, end_date, salary_structure=None):
    """
    Generate salary slip for an employee
    
    Args:
        employee_id (str): Employee ID
        start_date (str): Start date
        end_date (str): End date
        salary_structure (str, optional): Salary Structure ID
        
    Returns:
        dict: Salary slip details
    """
    from hrms.payroll.doctype.salary_structure.salary_structure import make_salary_slip
    
    if not frappe.has_permission("Salary Slip", "write"):
        frappe.throw(_("Not permitted to generate salary slip"), frappe.PermissionError)
    
    # Check if employee exists
    if not frappe.db.exists("Employee", employee_id):
        frappe.throw(_("Employee {0} does not exist").format(employee_id))
    
    # Convert date strings to date objects
    start_date = getdate(start_date)
    end_date = getdate(end_date)
    
    # Check if to_date is after from_date
    if start_date > end_date:
        frappe.throw(_("Start Date cannot be after End Date"))
    
    # Get salary structure if not provided
    if not salary_structure:
        salary_structure = frappe.db.get_value("Salary Structure Assignment", 
            {"employee": employee_id, "docstatus": 1}, "salary_structure")
        
        if not salary_structure:
            from hrms.payroll.doctype.salary_structure.salary_structure import get_salary_structure
            salary_structure = get_salary_structure(employee_id)
            
        if not salary_structure:
            frappe.throw(_("No active Salary Structure found for employee {0}").format(employee_id))
    
    # Create new salary slip
    salary_slip = make_salary_slip(salary_structure, employee_id)
    
    # Set dates
    salary_slip.start_date = start_date
    salary_slip.end_date = end_date
    salary_slip.posting_date = today()
    
    # Calculate payment days and other fields
    from hrms.payroll.doctype.salary_slip.salary_slip import get_payment_days
    payment_days_data = get_payment_days(start_date, end_date, employee_id)
    
    salary_slip.total_working_days = payment_days_data.get("total_working_days")
    salary_slip.leave_without_pay = payment_days_data.get("leave_without_pay")
    salary_slip.absent_days = payment_days_data.get("absent_days")
    salary_slip.payment_days = payment_days_data.get("payment_days")
    
    # Calculate net pay
    salary_slip.calculate_net_pay()
    
    salary_slip.insert()
    
    return {
        "name": salary_slip.name,
        "employee": salary_slip.employee,
        "employee_name": salary_slip.employee_name,
        "start_date": salary_slip.start_date,
        "end_date": salary_slip.end_date,
        "gross_pay": salary_slip.gross_pay,
        "total_deduction": salary_slip.total_deduction,
        "net_pay": salary_slip.net_pay,
        "status": salary_slip.status
    }

# ------------------------------------------------------
# Recruitment APIs
# ------------------------------------------------------

@frappe.whitelist()
def get_job_openings(status=None, department=None):
    """
    Get list of job openings
    
    Args:
        status (str, optional): Status (Open, Closed)
        department (str, optional): Department
        
    Returns:
        list: List of job openings
    """
    if not frappe.has_permission("Job Opening", "read"):
        frappe.throw(_("Not permitted to access job openings"), frappe.PermissionError)
    
    filters = {}
    
    if status:
        filters["status"] = status
    
    if department:
        filters["department"] = department
    
    # Get job openings
    job_openings = frappe.get_all("Job Opening",
        filters=filters,
        fields=["name", "job_title", "status", "department", "designation", "publish",
                "description", "application_deadline"],
        order_by="application_deadline desc"
    )
    
    return job_openings

@frappe.whitelist(allow_guest=True)
def get_published_job_openings():
    """
    Get list of published job openings for public viewing
    
    Returns:
        list: List of published job openings
    """
    current_date = getdate(today())
    
    # Get published and open job openings with valid application deadlines
    job_openings = frappe.get_all("Job Opening",
        filters={
            "status": "Open",
            "publish": 1,
            "application_deadline": [">=", current_date]
        },
        fields=["name", "job_title", "department", "designation", "description", 
                "application_deadline", "experience", "qualification"],
        order_by="application_deadline asc"
    )
    
    # Limit what data is exposed to the public
    public_fields = ["job_title", "department", "designation", "description", 
                    "application_deadline", "experience", "qualification"]
    
    result = []
    for job in job_openings:
        public_job = {field: job.get(field) for field in public_fields}
        public_job["id"] = job.get("name")  # Include job ID for reference
        result.append(public_job)
    
    return result