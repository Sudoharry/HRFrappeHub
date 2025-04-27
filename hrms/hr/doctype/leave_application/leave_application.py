"""
Leave Application DocType Controller

This module contains the controller for the Leave Application DocType
which handles business logic and validations.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, add_days, getdate, cint, flt, get_weekday

class LeaveApplication(Document):
    def validate(self):
        """Validate leave application"""
        self.validate_dates()
        self.validate_balance_leaves()
        self.validate_overlaps()
        self.calculate_total_leave_days()
        self.validate_approver()
    
    def validate_dates(self):
        """Validate leave application dates"""
        # Check that from_date is not after to_date
        if self.from_date and self.to_date and getdate(self.to_date) < getdate(self.from_date):
            frappe.throw(_("To Date cannot be before From Date"))
        
        # Check that dates are not in the past unless user has permissions
        if not frappe.has_permission("Leave Application", ptype="write", raise_exception=False):
            if getdate(self.from_date) < getdate(frappe.utils.nowdate()):
                frappe.throw(_("Leave application cannot be created for past dates"))
    
    def validate_balance_leaves(self):
        """Validate leave balance is available"""
        if self.status == "Open" and not frappe.db.get_value("Leave Type", self.leave_type, "is_lwp"):
            self.leave_balance = self.get_leave_balance()
            
            if self.leave_balance < self.total_leave_days:
                if frappe.db.get_value("Leave Type", self.leave_type, "allow_negative"):
                    frappe.msgprint(_("Note: Sufficient leave balance is not available for the leave type {0}")
                        .format(self.leave_type))
                else:
                    frappe.throw(_("Insufficient leave balance for leave type {0}")
                        .format(self.leave_type))
    
    def validate_overlaps(self):
        """Validate overlapping leave applications"""
        # Check for overlapping leave applications
        overlapping = frappe.db.sql("""
            SELECT name, leave_type, from_date, to_date
            FROM `tabLeave Application`
            WHERE employee = %s AND docstatus < 2 AND status in ('Open', 'Approved')
            AND name != %s
            AND (from_date BETWEEN %s AND %s OR to_date BETWEEN %s AND %s)
        """, (self.employee, self.name, self.from_date, self.to_date, self.from_date, self.to_date))
        
        if overlapping:
            overlapping_details = []
            for name, leave_type, from_date, to_date in overlapping:
                overlapping_details.append(_("{0}: {1} ({2} to {3})").format(name, leave_type, from_date, to_date))
            
            frappe.throw(_("Leave application overlaps with existing applications:\n{0}")
                .format("\n".join(overlapping_details)))
    
    def calculate_total_leave_days(self):
        """Calculate total number of leave days"""
        if self.from_date and self.to_date:
            # Calculate total days
            total_days = date_diff(self.to_date, self.from_date) + 1
            
            # Adjust for half day if applicable
            if self.half_day:
                total_days = total_days - 0.5
            
            # Consider holidays if needed
            if not frappe.db.get_value("Leave Type", self.leave_type, "include_holiday"):
                total_days = self.exclude_holidays(total_days)
            
            self.total_leave_days = total_days
    
    def exclude_holidays(self, total_days):
        """Exclude holidays from leave days"""
        # This would check a Holiday List and exclude holidays
        # Simplified implementation for now
        holiday_dates = self.get_holidays()
        leave_days = total_days
        
        for holiday_date in holiday_dates:
            if getdate(self.from_date) <= holiday_date <= getdate(self.to_date):
                leave_days -= 1
        
        return max(0, leave_days)
    
    def get_holidays(self):
        """Get list of holidays between from_date and to_date"""
        # This would get the list of holidays from a Holiday List
        # Simplified implementation for now
        return []
    
    def get_leave_balance(self):
        """Get leave balance for the leave type"""
        # This would calculate the leave balance based on allocations and previous leaves
        # Simplified implementation for now
        return frappe.db.get_value("Leave Type", self.leave_type, "max_days_allowed") or 0
    
    def validate_approver(self):
        """Validate leave approver"""
        if self.leave_approver and "HR Manager" not in frappe.get_roles(self.leave_approver):
            frappe.throw(_("{0} is not authorized to approve this leave").format(
                frappe.get_fullname(self.leave_approver)))
    
    def on_submit(self):
        """Actions when leave is submitted"""
        # Update employee status if approved
        if self.status == "Approved":
            self.update_employee_status()
    
    def on_cancel(self):
        """Actions when leave is cancelled"""
        # Reset employee status
        self.update_employee_status(cancel=True)
    
    def update_employee_status(self, cancel=False):
        """Update employee status based on leave"""
        # Only update status for longer leaves (e.g., > 5 days)
        if self.total_leave_days > 5 and not cancel:
            frappe.db.set_value("Employee", self.employee, "status", "On Leave")
        elif cancel:
            # Check if this was the reason the employee is on leave
            frappe.db.set_value("Employee", self.employee, "status", "Active")

def update_leave_status():
    """
    Update leave status based on dates
    
    This is typically run as a scheduled job daily
    """
    today = frappe.utils.today()
    
    # Find leaves that are approved but status not updated
    leave_applications = frappe.get_all(
        "Leave Application",
        filters={
            "status": "Approved",
            "docstatus": 1,
            "from_date": ("<=", today),
            "to_date": (">=", today)
        },
        fields=["name", "employee"]
    )
    
    # Update employee status to "On Leave"
    for leave in leave_applications:
        frappe.db.set_value("Employee", leave.employee, "status", "On Leave")
    
    # Find leaves that have ended
    ended_leaves = frappe.get_all(
        "Leave Application",
        filters={
            "status": "Approved",
            "docstatus": 1,
            "to_date": ("<", today)
        },
        fields=["name", "employee"]
    )
    
    # Update employee status back to "Active"
    for leave in ended_leaves:
        # Check if there are other current leaves
        current_leave = frappe.db.exists(
            "Leave Application",
            {
                "employee": leave.employee,
                "status": "Approved",
                "docstatus": 1,
                "from_date": ("<=", today),
                "to_date": (">=", today)
            }
        )
        
        if not current_leave:
            frappe.db.set_value("Employee", leave.employee, "status", "Active")

def get_permission_query_conditions(user):
    """Get permission query conditions for leave application"""
    if not user:
        user = frappe.session.user
    
    if "HR Manager" in frappe.get_roles(user):
        return ""
    
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if employee:
        return f'(`tabLeave Application`.employee = "{employee}")'
    
    return "1=0"

def has_permission(doc, user=None, ptype="read"):
    """Check permission for Leave Application"""
    if not user:
        user = frappe.session.user
    
    if "HR Manager" in frappe.get_roles(user) or "HR User" in frappe.get_roles(user):
        return True
    
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if employee and doc.employee == employee:
        return True
    
    return False

@frappe.whitelist()
def get_leave_approver(employee):
    """Get the leave approver for an employee"""
    # Check if reporting manager is set
    reports_to = frappe.db.get_value("Employee", employee, "reports_to")
    if reports_to:
        # Get user ID of reporting manager
        user_id = frappe.db.get_value("Employee", reports_to, "user_id")
        if user_id and "HR User" in frappe.get_roles(user_id):
            return user_id
    
    # Fall back to HR Users
    hr_users = frappe.get_all(
        "Has Role",
        filters={"role": "HR User", "parenttype": "User"},
        fields=["parent"]
    )
    
    if hr_users:
        return hr_users[0].parent
    
    return None