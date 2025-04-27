"""
Salary Slip DocType Controller

This module contains the controller for the Salary Slip DocType
which handles business logic and validations.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, flt, date_diff, add_days, cint, money_in_words, formatdate

class SalarySlip(Document):
    def validate(self):
        """Validate salary slip"""
        self.validate_dates()
        self.calculate_net_pay()
        
        # Set total in words
        company_currency = frappe.db.get_value("Company", self.company, "default_currency")
        self.total_in_words = money_in_words(self.net_pay, company_currency)
    
    def validate_dates(self):
        """Validate salary slip dates"""
        # Start date should be before end date
        if self.start_date and self.end_date and getdate(self.start_date) > getdate(self.end_date):
            frappe.throw(_("Start Date cannot be after End Date"))
        
        # End date should not be in the future
        if self.end_date and getdate(self.end_date) > getdate(frappe.utils.today()):
            frappe.msgprint(_("End Date is in the future. It should be less than or equal to today's date."))
        
        # Calculate total working days if not set
        if not self.total_working_days:
            self.calculate_total_working_days()
        
        # Calculate payment days if not set
        if not self.payment_days:
            self.payment_days = self.total_working_days - self.leave_without_pay - self.absent_days
    
    def calculate_total_working_days(self):
        """Calculate total working days for the pay period"""
        days = date_diff(self.end_date, self.start_date) + 1
        self.total_working_days = days
    
    def calculate_net_pay(self):
        """Calculate total earnings, deductions, and net pay"""
        # Calculate total earnings
        if not self.gross_pay:
            gross_pay = 0
            if hasattr(self, 'earnings') and self.earnings:
                for earning in self.earnings:
                    gross_pay += flt(earning.amount)
            self.gross_pay = gross_pay
        
        # Calculate total deductions
        total_deduction = 0
        if hasattr(self, 'deductions') and self.deductions:
            for deduction in self.deductions:
                total_deduction += flt(deduction.amount)
        self.total_deduction = total_deduction
        
        # Calculate net pay
        self.net_pay = flt(self.gross_pay) - flt(self.total_deduction)
        
        # Set rounded total
        self.rounded_total = round(self.net_pay)
    
    def on_submit(self):
        """Actions when salary slip is submitted"""
        # Check minimum validations
        if not self.net_pay:
            frappe.throw(_("Net Pay cannot be zero"))
        
        # Update related records or perform any other post-submission tasks
        self.update_status("Submitted")
    
    def on_cancel(self):
        """Actions when salary slip is cancelled"""
        self.update_status("Cancelled")
    
    def update_status(self, status):
        """Update the status of the salary slip"""
        self.db_set("status", status)
        frappe.db.commit()

@frappe.whitelist()
def make_bank_entry(salary_slips):
    """Create bank entry from salary slips"""
    if isinstance(salary_slips, str):
        import json
        salary_slips = json.loads(salary_slips)
    
    if not salary_slips:
        frappe.throw(_("No salary slip selected"))
    
    # Fetch salary slips
    salary_slip_list = []
    for slip in salary_slips:
        if slip.get('name'):
            salary_slip = frappe.get_doc("Salary Slip", slip.get('name'))
            if salary_slip.docstatus != 1:
                frappe.throw(_("Salary Slip {0} must be submitted").format(salary_slip.name))
            salary_slip_list.append(salary_slip)
    
    if not salary_slip_list:
        frappe.throw(_("No salary slips found"))
    
    # Create a simple dictionary with payment details
    # In a real implementation, this would create an actual payment entry
    total_amount = sum(slip.net_pay for slip in salary_slip_list)
    
    payment_details = {
        "total_amount": total_amount,
        "payment_date": frappe.utils.today(),
        "salary_slips": [slip.name for slip in salary_slip_list],
        "employees": [slip.employee_name for slip in salary_slip_list]
    }
    
    return payment_details

@frappe.whitelist()
def get_payment_days(start_date, end_date, employee):
    """Calculate payment days based on attendance and leave records"""
    # Convert to date objects
    start_date = getdate(start_date)
    end_date = getdate(end_date)
    
    # Total calendar days
    total_days = date_diff(end_date, start_date) + 1
    
    # Get leave without pay
    lwp = frappe.db.sql("""
        SELECT SUM(total_leave_days) FROM `tabLeave Application`
        WHERE employee = %s AND status = 'Approved' AND docstatus = 1
        AND (from_date BETWEEN %s AND %s OR to_date BETWEEN %s AND %s)
        AND leave_type IN (SELECT name FROM `tabLeave Type` WHERE is_lwp = 1)
    """, (employee, start_date, end_date, start_date, end_date))
    
    lwp = flt(lwp[0][0]) if lwp and lwp[0][0] else 0
    
    # Get absent days
    absent = frappe.db.sql("""
        SELECT COUNT(*) FROM `tabAttendance`
        WHERE employee = %s AND status = 'Absent' AND docstatus = 1
        AND attendance_date BETWEEN %s AND %s
    """, (employee, start_date, end_date))
    
    absent = flt(absent[0][0]) if absent and absent[0][0] else 0
    
    # Payment days
    payment_days = total_days - lwp - absent
    
    return {
        "total_working_days": total_days,
        "leave_without_pay": lwp,
        "absent_days": absent,
        "payment_days": payment_days
    }