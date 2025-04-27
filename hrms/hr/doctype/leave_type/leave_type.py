"""
Leave Type DocType Controller

This module contains the controller for the Leave Type DocType
which handles business logic and validations.
"""

import frappe
from frappe import _
from frappe.model.document import Document

class LeaveType(Document):
    def validate(self):
        """Validate leave type"""
        self.validate_lwp_settings()
        self.validate_earned_leave_settings()
        self.validate_carry_forward_settings()
    
    def validate_lwp_settings(self):
        """Validate Leave Without Pay settings"""
        if self.is_lwp and self.is_paid_leave:
            frappe.throw(_("Leave Type cannot be both Paid and Leave Without Pay"))
        
        if self.is_lwp and self.allow_encashment:
            frappe.throw(_("Leave Without Pay cannot be encashed"))
    
    def validate_earned_leave_settings(self):
        """Validate Earned Leave settings"""
        if self.is_earned_leave:
            if not self.earned_leave_frequency:
                frappe.throw(_("Earned Leave Frequency is mandatory for Earned Leave"))
            
            if not self.earned_leave_per_year:
                frappe.throw(_("Earned Leave per Year is mandatory for Earned Leave"))
    
    def validate_carry_forward_settings(self):
        """Validate Carry Forward settings"""
        if self.is_carry_forward:
            if not self.carry_forward_percentage:
                self.carry_forward_percentage = 100
            
            if self.carry_forward_percentage < 0 or self.carry_forward_percentage > 100:
                frappe.throw(_("Carry Forward Percentage cannot be less than 0 or greater than 100"))
    
    def on_update(self):
        """On update actions"""
        # Update any leave allocations if needed
        pass

def get_leave_type_details(leave_type):
    """Get leave type details"""
    leave_type_doc = frappe.get_doc("Leave Type", leave_type)
    return {
        "name": leave_type_doc.name,
        "max_days_allowed": leave_type_doc.max_days_allowed,
        "is_paid_leave": leave_type_doc.is_paid_leave,
        "is_lwp": leave_type_doc.is_lwp,
        "is_carry_forward": leave_type_doc.is_carry_forward,
        "is_earned_leave": leave_type_doc.is_earned_leave,
        "allow_negative": leave_type_doc.allow_negative,
        "include_holiday": leave_type_doc.include_holiday
    }