# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, format_date

class Attendance(Document):
    def validate(self):
        self.validate_attendance_date()
        self.validate_duplicate_record()
        self.validate_employee_status()
        self.check_leave_record()
    
    def validate_attendance_date(self):
        date = getdate(self.attendance_date)
        
        if date > getdate(nowdate()):
            frappe.throw(_("Attendance cannot be marked for future dates"))
            
        # Check if attendance date is less than joining date
        joining_date = frappe.db.get_value("Employee", self.employee, "date_of_joining")
        if date < getdate(joining_date):
            frappe.throw(_("Attendance date {0} cannot be less than employee {1}'s joining date {2}")
                .format(format_date(self.attendance_date), self.employee_name, format_date(joining_date)))
    
    def validate_duplicate_record(self):
        duplicate = frappe.db.exists("Attendance", {
            "employee": self.employee,
            "attendance_date": self.attendance_date,
            "docstatus": ("!=", 2),
            "name": ("!=", self.name)
        })
        
        if duplicate:
            frappe.throw(_("Attendance for employee {0} is already marked for this date")
                .format(self.employee_name))
    
    def validate_employee_status(self):
        if frappe.db.get_value("Employee", self.employee, "status") == "Inactive":
            frappe.throw(_("Cannot mark attendance for an inactive employee {0}")
                .format(self.employee_name))
                
        if frappe.db.get_value("Employee", self.employee, "status") == "Left":
            relieving_date = frappe.db.get_value("Employee", self.employee, "relieving_date")
            if relieving_date and getdate(self.attendance_date) > getdate(relieving_date):
                frappe.throw(_("Cannot mark attendance for an employee who has left on {0}")
                    .format(format_date(relieving_date)))
    
    def check_leave_record(self):
        leave_record = frappe.db.sql("""
            SELECT leave_type, half_day, half_day_date
            FROM `tabLeave Application`
            WHERE employee = %s AND %s BETWEEN from_date AND to_date
            AND docstatus = 1
        """, (self.employee, self.attendance_date), as_dict=True)
        
        if leave_record:
            for d in leave_record:
                if d.half_day and getdate(d.half_day_date) == getdate(self.attendance_date):
                    if self.status == "Absent":
                        frappe.throw(_("Employee {0} is on Half Day Leave on {1}")
                            .format(self.employee_name, format_date(self.attendance_date)))
                else:
                    if self.status == "Present" or self.status == "Half Day":
                        frappe.throw(_("Employee {0} is on Leave on {1}")
                            .format(self.employee_name, format_date(self.attendance_date)))
    
    def on_submit(self):
        self.update_leave_application()
    
    def on_cancel(self):
        self.update_leave_application()
    
    def update_leave_application(self):
        # Update leave application status based on attendance
        leave = frappe.db.sql("""
            SELECT name 
            FROM `tabLeave Application`
            WHERE employee = %s AND %s BETWEEN from_date AND to_date
            AND docstatus = 1
        """, (self.employee, self.attendance_date), as_dict=True)
        
        if leave:
            for l in leave:
                leave_app = frappe.get_doc("Leave Application", l.name)
                leave_app.db_set("status", "Approved" if self.status == "Absent" else "Rejected")
    
    def mark_absent_for_unmarked_employees(date=None):
        """Marks employees as Absent if they haven't marked attendance for a day"""
        if not date:
            date = getdate(nowdate())
        else:
            date = getdate(date)
        
        employees = frappe.db.get_all("Employee", 
            filters={
                "status": "Active",
                "date_of_joining": ("<=", date)
            },
            fields=["name", "employee_name"]
        )
        
        for employee in employees:
            attendance = frappe.db.exists("Attendance", {
                "employee": employee.name,
                "attendance_date": date,
                "docstatus": ("!=", 2)
            })
            
            if not attendance:
                doc = frappe.new_doc("Attendance")
                doc.employee = employee.name
                doc.employee_name = employee.employee_name
                doc.attendance_date = date
                doc.status = "Absent"
                doc.company = frappe.db.get_value("Employee", employee.name, "company")
                doc.flags.ignore_validate = True
                doc.insert(ignore_permissions=True)
                doc.submit()
                
    def process_auto_attendance():
        """Process auto attendance based on check-in/check-out logs"""
        # This would integrate with an attendance device/system
        # For the scope of this task, we'll just provide a placeholder function
        # In a real implementation, this would query an attendance device API, biometric system, etc.
        pass

def get_permission_query_conditions(user):
    if not user: user = frappe.session.user
    
    # HR Manager can see all attendance records
    if "HR Manager" in frappe.get_roles(user):
        return ""
    
    # HR User can see all attendance records
    if "HR User" in frappe.get_roles(user):
        return ""
    
    # Employee can only see their own attendance records
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if employee:
        return '(`tabAttendance`.employee = {0})'.format(frappe.db.escape(employee))
    
    return '1=0'

def has_permission(doc, user):
    # HR Manager can see all attendance records
    if "HR Manager" in frappe.get_roles(user):
        return True
    
    # HR User can see all attendance records
    if "HR User" in frappe.get_roles(user):
        return True
    
    # Employee can only see their own attendance records
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if employee and employee == doc.employee:
        return True
    
    return False
