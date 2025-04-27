"""
API Module for HRMS

This module contains the API endpoints for the HRMS application.
"""

import frappe
from frappe import _
from frappe.utils import getdate, formatdate, today

@frappe.whitelist()
def get_employee_info(employee=None):
    """Get employee information"""
    if not employee:
        employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
        if not employee:
            return {"error": "No employee found for the current user"}
    
    employee_doc = frappe.get_doc("Employee", employee)
    return {
        "name": employee_doc.name,
        "employee_id": employee_doc.employee_id,
        "employee_name": employee_doc.employee_name,
        "department": employee_doc.department,
        "designation": employee_doc.designation,
        "status": employee_doc.status,
        "date_of_joining": formatdate(employee_doc.date_of_joining),
        "company": employee_doc.company
    }

@frappe.whitelist()
def get_leave_applications(employee=None, status=None):
    """Get leave applications for an employee"""
    if not employee:
        employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
        if not employee:
            return {"error": "No employee found for the current user"}
    
    filters = {"employee": employee}
    if status:
        filters["status"] = status
    
    leave_applications = frappe.get_all(
        "Leave Application",
        filters=filters,
        fields=["name", "leave_type", "from_date", "to_date", "total_leave_days", "status", "reason"],
        order_by="from_date desc"
    )
    
    for leave in leave_applications:
        leave.from_date = formatdate(leave.from_date)
        leave.to_date = formatdate(leave.to_date)
    
    return leave_applications

@frappe.whitelist()
def get_leave_balance(employee=None, leave_type=None):
    """Get leave balance for an employee"""
    if not employee:
        employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
        if not employee:
            return {"error": "No employee found for the current user"}
    
    if leave_type:
        # Get balance for a specific leave type
        balance = frappe.db.get_value("Leave Type", leave_type, "max_days_allowed") or 0
        
        # Deduct used leaves - this would actually be more complex
        # with allocations and calculations
        used_leaves = frappe.db.sql("""
            SELECT SUM(total_leave_days) 
            FROM `tabLeave Application` 
            WHERE employee=%s AND leave_type=%s AND status='Approved' AND docstatus=1
        """, (employee, leave_type))
        
        used = used_leaves[0][0] if used_leaves and used_leaves[0][0] else 0
        balance = balance - used
        
        return {
            "leave_type": leave_type,
            "balance": balance
        }
    else:
        # Get balance for all leave types
        leave_types = frappe.get_all(
            "Leave Type",
            fields=["name", "max_days_allowed"]
        )
        
        balances = []
        for lt in leave_types:
            # Deduct used leaves - this would actually be more complex
            # with allocations and calculations
            used_leaves = frappe.db.sql("""
                SELECT SUM(total_leave_days) 
                FROM `tabLeave Application` 
                WHERE employee=%s AND leave_type=%s AND status='Approved' AND docstatus=1
            """, (employee, lt.name))
            
            used = used_leaves[0][0] if used_leaves and used_leaves[0][0] else 0
            balance = lt.max_days_allowed - used if lt.max_days_allowed else 0
            
            balances.append({
                "leave_type": lt.name,
                "balance": balance
            })
        
        return balances

@frappe.whitelist()
def get_attendance_status(employee=None, date=None):
    """Get attendance status for an employee on a specific date"""
    if not employee:
        employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
        if not employee:
            return {"error": "No employee found for the current user"}
    
    if not date:
        date = today()
    
    attendance = frappe.db.get_value(
        "Attendance",
        {"employee": employee, "attendance_date": date, "docstatus": 1},
        ["status", "check_in", "check_out", "working_hours"],
        as_dict=1
    )
    
    if attendance:
        return {
            "date": formatdate(date),
            "status": attendance.status,
            "check_in": attendance.check_in.strftime("%H:%M:%S") if attendance.check_in else None,
            "check_out": attendance.check_out.strftime("%H:%M:%S") if attendance.check_out else None,
            "working_hours": attendance.working_hours
        }
    else:
        return {
            "date": formatdate(date),
            "status": "Not Marked"
        }

@frappe.whitelist()
def mark_attendance(employee=None, attendance_date=None, status="Present", check_in=None, check_out=None):
    """Mark attendance for an employee"""
    if not frappe.has_permission("Attendance", "write"):
        return {"error": "No permission to mark attendance"}
    
    if not employee:
        employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
        if not employee:
            return {"error": "No employee found for the current user"}
    
    if not attendance_date:
        attendance_date = today()
    
    # Check if attendance already exists
    existing_attendance = frappe.db.exists(
        "Attendance",
        {"employee": employee, "attendance_date": attendance_date, "docstatus": ("!=", 2)}
    )
    
    if existing_attendance:
        attendance = frappe.get_doc("Attendance", existing_attendance)
        
        # Update existing attendance
        if status:
            attendance.status = status
        
        if check_in:
            attendance.check_in = check_in
        
        if check_out:
            attendance.check_out = check_out
            
        # Calculate working hours if both check-in and check-out are set
        if attendance.check_in and attendance.check_out:
            from frappe.utils import time_diff_in_hours
            attendance.working_hours = time_diff_in_hours(attendance.check_out, attendance.check_in)
        
        attendance.save()
        if attendance.docstatus == 0:
            attendance.submit()
        
        return {
            "message": "Attendance updated successfully",
            "attendance": attendance.name
        }
    else:
        # Create new attendance
        attendance = frappe.new_doc("Attendance")
        attendance.employee = employee
        attendance.employee_name = frappe.db.get_value("Employee", employee, "employee_name")
        attendance.attendance_date = attendance_date
        attendance.status = status
        
        if check_in:
            attendance.check_in = check_in
        
        if check_out:
            attendance.check_out = check_out
            
        # Calculate working hours if both check-in and check-out are set
        if attendance.check_in and attendance.check_out:
            from frappe.utils import time_diff_in_hours
            attendance.working_hours = time_diff_in_hours(attendance.check_out, attendance.check_in)
        
        attendance.company = frappe.db.get_value("Employee", employee, "company")
        attendance.insert(ignore_permissions=True)
        attendance.submit()
        
        return {
            "message": "Attendance marked successfully",
            "attendance": attendance.name
        }

@frappe.whitelist()
def apply_leave(employee=None, leave_type=None, from_date=None, to_date=None, half_day=0, half_day_date=None, reason=None):
    """Apply for leave"""
    if not frappe.has_permission("Leave Application", "write"):
        return {"error": "No permission to apply for leave"}
    
    if not employee:
        employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
        if not employee:
            return {"error": "No employee found for the current user"}
    
    if not leave_type:
        return {"error": "Leave Type is mandatory"}
    
    if not from_date or not to_date:
        return {"error": "From Date and To Date are mandatory"}
    
    # Create leave application
    leave_application = frappe.new_doc("Leave Application")
    leave_application.employee = employee
    leave_application.leave_type = leave_type
    leave_application.from_date = from_date
    leave_application.to_date = to_date
    leave_application.half_day = half_day
    if half_day:
        leave_application.half_day_date = half_day_date
    leave_application.reason = reason
    leave_application.status = "Open"
    leave_application.posting_date = today()
    
    # Set company
    leave_application.company = frappe.db.get_value("Employee", employee, "company")
    
    # Validate and insert
    leave_application.insert(ignore_permissions=True)
    
    return {
        "message": "Leave application submitted successfully",
        "leave_application": leave_application.name
    }

@frappe.whitelist()
def get_hr_dashboard_data():
    """Get data for HR Dashboard"""
    if not frappe.has_permission("Employee", "read"):
        return {"error": "No permission to access HR Dashboard"}
    
    # Employee count
    employee_count = frappe.db.count("Employee", {"status": "Active"})
    
    # Attendance today
    today_str = today()
    attendance_count = frappe.db.count("Attendance", {"attendance_date": today_str})
    
    # Pending leave applications
    pending_leaves = frappe.db.count("Leave Application", {"status": "Open"})
    
    # Department-wise employee count
    departments = frappe.db.sql("""
        SELECT department, COUNT(*) as count
        FROM `tabEmployee`
        WHERE status = 'Active'
        GROUP BY department
    """, as_dict=1)
    
    # Attendance status for today
    attendance_stats = frappe.db.sql("""
        SELECT status, COUNT(*) as count
        FROM `tabAttendance`
        WHERE attendance_date = %s
        GROUP BY status
    """, (today_str,), as_dict=1)
    
    # Recent leaves
    recent_leaves = frappe.get_all(
        "Leave Application",
        filters={"status": ["in", ["Open", "Approved"]]},
        fields=["name", "employee", "employee_name", "leave_type", "from_date", "to_date", "total_leave_days", "status"],
        order_by="creation desc",
        limit=5
    )
    
    for leave in recent_leaves:
        leave.from_date = formatdate(leave.from_date)
        leave.to_date = formatdate(leave.to_date)
    
    # Return dashboard data
    return {
        "employee_count": employee_count,
        "attendance_today": attendance_count,
        "pending_leaves": pending_leaves,
        "departments": departments,
        "attendance_stats": attendance_stats,
        "recent_leaves": recent_leaves
    }