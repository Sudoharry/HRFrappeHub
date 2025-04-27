"""
Employee DocType Controller

This module contains the controller for the Employee DocType
which handles business logic and validations.
"""

import frappe
from frappe import _
from frappe.model.document import Document

class Employee(Document):
    def validate(self):
        """Validate employee data"""
        self.validate_status()
        self.validate_dates()
        self.update_employee_name()
    
    def validate_status(self):
        """Validate status"""
        if not self.status:
            self.status = "Active"
        
        # Check if status transition is valid
        if not self.is_new() and self.status != self.db_get("status"):
            # Implement status transition rules
            pass
    
    def validate_dates(self):
        """Validate date fields"""
        # Date of birth should be in the past
        if self.date_of_birth and self.date_of_birth > frappe.utils.today():
            frappe.throw(_("Date of Birth cannot be in the future."))
        
        # Date of joining should not be in the future
        if self.date_of_joining and self.date_of_joining > frappe.utils.today():
            frappe.throw(_("Date of Joining cannot be in the future."))
    
    def update_employee_name(self):
        """Update full name based on first and last name"""
        self.employee_name = " ".join(filter(None, [self.first_name, self.last_name]))
    
    def on_update(self):
        """Updates after save"""
        # Update linked user if any
        if self.user_id:
            self.update_user()
        
        # If employee status changes to inactive or terminated
        if not self.is_new() and self.status in ["Inactive", "Terminated"]:
            self.handle_inactive_employee()
    
    def update_user(self):
        """Update User document with employee info"""
        # This would update the linked user document
        pass
    
    def handle_inactive_employee(self):
        """Handle when employee becomes inactive"""
        # This would handle deactivation of the employee
        pass
    
    def after_insert(self):
        """Run after insertion"""
        # Any post-creation activities
        pass
    
    @frappe.whitelist()
    def generate_employee_id(self):
        """Generate a unique employee ID"""
        # Logic to generate employee ID
        prefix = "EMP"
        last_employee = frappe.get_all(
            "Employee",
            fields=["employee_id"],
            filters={"employee_id": ("like", f"{prefix}%")},
            order_by="creation desc",
            limit=1
        )
        
        if last_employee:
            # Extract number and increment
            last_id = last_employee[0].employee_id
            try:
                num = int(last_id.replace(prefix, ""))
                return f"{prefix}{(num + 1):04d}"
            except ValueError:
                pass
        
        # Default if no existing ID or error
        return f"{prefix}0001"

def get_timeline_data(doctype, name):
    """Get timeline data for this employee"""
    # Return timeline data for employee
    return {}

def has_permission(doc, user=None, ptype="read"):
    """Check permissions for Employee"""
    # Implement permission logic
    if not user:
        user = frappe.session.user
    
    # Administrator can do anything
    if "Administrator" in frappe.get_roles(user):
        return True
    
    # HR Manager can do anything with employees
    if "HR Manager" in frappe.get_roles(user):
        return True
    
    # Users can read their own employee records
    if ptype == "read" and doc.user_id == user:
        return True
    
    return False

def get_permission_query_conditions(user):
    """Return permission query conditions for this doctype"""
    # Implement condition builder for permission queries
    if not user:
        user = frappe.session.user
    
    # Administrator sees all
    if "Administrator" in frappe.get_roles(user):
        return ""
    
    # HR Manager sees all
    if "HR Manager" in frappe.get_roles(user):
        return ""
    
    # Employee sees only their own
    if "Employee" in frappe.get_roles(user):
        employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
        if employee:
            return f"(`tabEmployee`.name = '{employee}')"
    
    # Default: see nothing
    return "1=0"

@frappe.whitelist()
def create_employee_from_user(user_id):
    """Create an employee from a user"""
    # Implement creation of employee from user
    pass