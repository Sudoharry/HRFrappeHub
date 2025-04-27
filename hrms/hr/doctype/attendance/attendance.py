"""
Attendance DocType Controller

This module contains the controller for the Attendance DocType
which handles business logic and validations.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import time_diff_in_hours, getdate, get_datetime

class Attendance(Document):
    def validate(self):
        """Validate attendance data"""
        self.validate_duplicate_record()
        self.validate_attendance_date()
        self.validate_check_in_out()
        self.calculate_working_hours()
    
    def validate_duplicate_record(self):
        """Check for duplicate attendance record"""
        attendance = frappe.db.exists(
            "Attendance",
            {
                "employee": self.employee,
                "attendance_date": self.attendance_date,
                "name": ("!=", self.name),
                "docstatus": ("!=", 2)
            }
        )
        
        if attendance:
            frappe.throw(_("Attendance for employee {0} is already marked for this date").format(
                frappe.bold(self.employee_name or self.employee)))
    
    def validate_attendance_date(self):
        """Validate attendance date is not a future date"""
        if getdate(self.attendance_date) > getdate(frappe.utils.today()):
            frappe.throw(_("Attendance cannot be marked for future dates"))
    
    def validate_check_in_out(self):
        """Validate check-in and check-out times"""
        if self.check_in and self.check_out:
            if get_datetime(self.check_out) < get_datetime(self.check_in):
                frappe.throw(_("Check Out time cannot be before Check In time"))
    
    def calculate_working_hours(self):
        """Calculate working hours based on check-in and check-out times"""
        if self.check_in and self.check_out:
            self.working_hours = time_diff_in_hours(self.check_out, self.check_in)
    
    def on_submit(self):
        """On submit operations"""
        # Update the status of any associated leave application
        if self.status == "On Leave" and self.leave_application:
            self.update_leave_application()
    
    def update_leave_application(self):
        """Update related leave application if exists"""
        if frappe.db.exists("Leave Application", self.leave_application):
            leave_app = frappe.get_doc("Leave Application", self.leave_application)
            if leave_app.status == "Open":
                leave_app.status = "Approved"
                leave_app.save()
    
    def on_cancel(self):
        """On cancel operations"""
        # Reset changes to leave application if needed
        if self.status == "On Leave" and self.leave_application:
            self.reset_leave_application()
    
    def reset_leave_application(self):
        """Reset leave application status if needed"""
        if frappe.db.exists("Leave Application", self.leave_application):
            leave_app = frappe.get_doc("Leave Application", self.leave_application)
            leave_app.status = "Open"
            leave_app.save()

def mark_absent_for_unmarked_employees(company=None):
    """
    Mark absent for employees who haven't marked attendance
    
    This is typically run as a scheduled job at the end of the day
    """
    from datetime import datetime, timedelta
    
    today = frappe.utils.today()
    yesterday = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Get all active employees
    employee_filter = {"status": "Active"}
    if company:
        employee_filter["company"] = company
    
    employees = frappe.get_all("Employee", filters=employee_filter, fields=["name", "employee_name"])
    
    # Get list of employees who already have attendance for yesterday
    marked_attendance = frappe.get_all(
        "Attendance",
        filters={"attendance_date": yesterday, "docstatus": ("!=", 2)},
        fields=["employee"]
    )
    
    marked_employees = [att.employee for att in marked_attendance]
    
    # Create absent attendance for employees without attendance records
    for employee in employees:
        if employee.name not in marked_employees:
            # Check if employee was on approved leave
            leave_application = frappe.db.exists(
                "Leave Application",
                {
                    "employee": employee.name,
                    "from_date": ("<=", yesterday),
                    "to_date": (">=", yesterday),
                    "status": "Approved",
                    "docstatus": 1
                }
            )
            
            if leave_application:
                # Skip creating absent record if on approved leave
                continue
            
            # Create an absent attendance record
            attendance = frappe.new_doc("Attendance")
            attendance.employee = employee.name
            attendance.employee_name = employee.employee_name
            attendance.attendance_date = yesterday
            attendance.status = "Absent"
            attendance.company = company
            attendance.insert(ignore_permissions=True)
            attendance.submit()

def get_permission_query_conditions(user):
    """Get permission query conditions for attendance"""
    if not user:
        user = frappe.session.user
    
    if "HR Manager" in frappe.get_roles(user):
        return ""
    
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if employee:
        return f'(`tabAttendance`.employee = "{employee}")'
    
    return "1=0"

def has_permission(doc, user=None, ptype="read"):
    """Check permission for Attendance"""
    if not user:
        user = frappe.session.user
    
    if "HR Manager" in frappe.get_roles(user) or "HR User" in frappe.get_roles(user):
        return True
    
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if employee and doc.employee == employee:
        return True
    
    return False