# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, validate_email_address, get_url, get_formatted_email
from frappe.model.naming import set_name_by_naming_series
import datetime

class Employee(Document):
    def validate(self):
        self.validate_date_of_birth()
        self.validate_date_of_joining()
        self.validate_employee_email()
        self.validate_status()
        
        if self.user_id:
            self.validate_user_details()
            
        if self.create_user_permission:
            self.create_user_permission_for_employee()
    
    def validate_date_of_birth(self):
        if self.date_of_birth:
            if getdate(self.date_of_birth) > getdate():
                frappe.throw(_("Date of Birth cannot be in the future."))
            
            # Check if employee is at least 18 years old
            age = datetime.date.today().year - getdate(self.date_of_birth).year
            if age < 18:
                frappe.throw(_("Employee must be at least 18 years old."))
    
    def validate_date_of_joining(self):
        if self.date_of_joining:
            if getdate(self.date_of_joining) > getdate():
                frappe.throw(_("Date of Joining cannot be in the future."))
    
    def validate_employee_email(self):
        if self.company_email:
            validate_email_address(self.company_email)
        if self.personal_email:
            validate_email_address(self.personal_email)
    
    def validate_status(self):
        if self.status == 'Left' and not self.relieving_date:
            frappe.throw(_("Please set Relieving Date for employee with status 'Left'"))
        if self.status == 'Active' and self.relieving_date:
            frappe.throw(_("Relieving Date should be blank for active employees"))
    
    def validate_user_details(self):
        user = frappe.get_doc("User", self.user_id)
        if user.enabled:
            if self.status == 'Left':
                user.enabled = 0
                user.save()
        else:
            if self.status == 'Active':
                user.enabled = 1
                user.save()
    
    def autoname(self):
        naming_method = frappe.db.get_value("HR Settings", None, "emp_created_by")
        if not naming_method:
            naming_method = "naming_series"
            
        if naming_method == "naming_series":
            set_name_by_naming_series(self)
        elif naming_method == "employee_number":
            self.name = self.employee_number
        else:
            self.name = self.employee_number
    
    def create_user_permission_for_employee(self):
        if not self.user_id:
            return
            
        # Check if permission already exists
        has_permission = frappe.db.exists("User Permission", {
            "user": self.user_id,
            "allow": "Employee",
            "for_value": self.name
        })
        
        if not has_permission:
            frappe.get_doc({
                "doctype": "User Permission",
                "user": self.user_id,
                "allow": "Employee",
                "for_value": self.name,
                "apply_to_all_doctypes": 1
            }).insert(ignore_permissions=True)
    
    def on_update(self):
        # Update User information if exists
        if self.user_id:
            user = frappe.get_doc("User", self.user_id)
            user.first_name = self.first_name
            user.last_name = self.last_name
            user.save()
    
    def after_insert(self):
        self.create_default_leave_allocations()
        self.send_welcome_email()
    
    def create_default_leave_allocations(self):
        """Create default leave allocations for the employee based on leave policy"""
        # This can be expanded to actually create leave allocations based on the company's policy
        pass
    
    def send_welcome_email(self):
        if self.status != "Active":
            return
            
        if not self.company_email and not self.personal_email:
            return
            
        employee_name = self.employee_name or self.employee
        
        try:
            email_template = frappe.get_doc("Email Template", "New Employee Welcome")
            message = frappe.render_template(email_template.response, {
                "employee_name": employee_name,
                "company": self.company,
                "employee_id": self.name
            })
            
            email = self.company_email or self.personal_email
            frappe.sendmail(
                recipients=[email],
                subject=_("Welcome to {0}").format(self.company),
                message=message,
                header=[_("Welcome"), "green"]
            )
        except Exception:
            frappe.log_error(title=_("Failed to send welcome email to {0}").format(employee_name))
    
    def has_website_permission(self, ptype, user, verbose=False):
        employee = frappe.db.get_value("Employee", {"user_id": user}, ["name"])
        if employee and employee == self.name:
            return True
        return False

def get_timeline_data(doctype, name):
    """Return timeline for employee"""
    timeline_data = {}
    
    # Get Leave Applications
    leave_applications = frappe.get_all("Leave Application",
        fields=["name", "creation", "status"],
        filters={"employee": name}
    )
    
    for application in leave_applications:
        timeline_data[application.creation] = {
            'title': _('Leave Application {0} {1}').format(application.name, application.status),
            'content': _('Leave Application {0} {1}').format(application.name, application.status),
            'doctype': 'Leave Application',
            'docname': application.name
        }
    
    # Get Attendance
    attendance_records = frappe.get_all("Attendance",
        fields=["name", "creation", "status"],
        filters={"employee": name}
    )
    
    for attendance in attendance_records:
        timeline_data[attendance.creation] = {
            'title': _('Attendance {0} {1}').format(attendance.name, attendance.status),
            'content': _('Attendance {0} {1}').format(attendance.name, attendance.status),
            'doctype': 'Attendance',
            'docname': attendance.name
        }
    
    # Get Salary Slips
    salary_slips = frappe.get_all("Salary Slip",
        fields=["name", "creation", "status"],
        filters={"employee": name}
    )
    
    for slip in salary_slips:
        timeline_data[slip.creation] = {
            'title': _('Salary Slip {0} {1}').format(slip.name, slip.status),
            'content': _('Salary Slip {0} {1}').format(slip.name, slip.status),
            'doctype': 'Salary Slip',
            'docname': slip.name
        }
    
    return timeline_data

def get_permission_query_conditions(user):
    if not user: user = frappe.session.user
    
    # HR Manager can see all employees
    if "HR Manager" in frappe.get_roles(user):
        return ""
    
    # HR User can see all employees
    if "HR User" in frappe.get_roles(user):
        return ""
    
    # Employee can only see their own record
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if employee:
        return '(`tabEmployee`.name = {0})'.format(frappe.db.escape(employee))
    
    return '1=0'

def has_permission(doc, user):
    # HR Manager can see all employees
    if "HR Manager" in frappe.get_roles(user):
        return True
    
    # HR User can see all employees
    if "HR User" in frappe.get_roles(user):
        return True
    
    # Employee can only see their own record
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if employee and employee == doc.name:
        return True
    
    return False
