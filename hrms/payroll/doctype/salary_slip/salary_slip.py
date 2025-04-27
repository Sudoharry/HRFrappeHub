# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, date_diff, add_days, getdate, cint, get_last_day, get_first_day

class SalarySlip(Document):
    def validate(self):
        self.validate_dates()
        self.validate_employee_details()
        self.calculate_net_pay()
    
    def validate_dates(self):
        if getdate(self.end_date) < getdate(self.start_date):
            frappe.throw(_("End date cannot be before start date"))
            
        if getdate(self.start_date) > getdate():
            frappe.throw(_("Future dates not allowed in salary slip"))
    
    def validate_employee_details(self):
        # Get employee details
        emp = frappe.db.get_value("Employee", self.employee, 
            ["status", "date_of_joining", "relieving_date"], as_dict=True)
            
        if not emp:
            frappe.throw(_("Employee {0} does not exist").format(self.employee))
            
        if emp.status == "Left" or emp.status == "Inactive":
            frappe.throw(_("Cannot create salary slip for inactive employee {0}").format(self.employee_name))
            
        if getdate(emp.date_of_joining) > getdate(self.start_date):
            frappe.throw(_("Employee joined after this payroll period"))
            
        if emp.relieving_date and getdate(emp.relieving_date) < getdate(self.end_date):
            frappe.throw(_("Employee has left before the end of this payroll period"))
    
    def on_submit(self):
        self.update_status(self.name)
        
        # Create salary payment entry if auto-payment is enabled
        if self.get_auto_payment_setting():
            self.create_payment_entry()
    
    def on_cancel(self):
        self.update_status()
    
    def calculate_net_pay(self):
        # Calculate totals for earnings and deductions
        self.total_earning = 0
        self.total_deduction = 0
        
        # Add up earnings
        for earning in self.earnings:
            self.total_earning += flt(earning.amount)
        
        # Add up deductions
        for deduction in self.deductions:
            self.total_deduction += flt(deduction.amount)
        
        # Calculate net pay
        self.net_pay = self.total_earning - self.total_deduction
        
        # Round to nearest integer if configured
        if frappe.db.get_single_value("Payroll Settings", "round_off_to_nearest_integer"):
            self.net_pay = round(self.net_pay)
    
    def make_salary_slip_from_salary_structure(self):
        """Get salary structure and create salary slip"""
        if not self.salary_structure:
            frappe.throw(_("Please select a salary structure for employee {0}").format(self.employee_name))
            
        # Get salary structure
        salary_structure = frappe.get_doc("Salary Structure", self.salary_structure)
        
        # Get employee assignment details
        assignment = self.get_salary_structure_assignment()
        if not assignment:
            frappe.throw(_("No active Salary Structure Assignment for employee {0} in this period")
                .format(self.employee_name))
        
        # Get start and end dates
        if not self.start_date:
            self.start_date = get_first_day(self.posting_date)
        if not self.end_date:
            self.end_date = get_last_day(self.posting_date)
        
        # Clear existing tables
        self.earnings = []
        self.deductions = []
        
        # Fill earnings and deductions from structure
        for component in salary_structure.earnings:
            self.add_component(component, "earnings", assignment)
            
        for component in salary_structure.deductions:
            self.add_component(component, "deductions", assignment)
            
        # Calculate totals
        self.calculate_net_pay()
    
    def add_component(self, component, component_type, assignment):
        """Add salary component to earnings or deductions table"""
        amount = self.calculate_component_amount(component, assignment)
        
        if amount != 0:
            row = self.append(component_type)
            row.salary_component = component.salary_component
            row.amount = amount
    
    def calculate_component_amount(self, component, assignment):
        """Calculate amount for a salary component based on formula or fixed amount"""
        # For simplicity - in a real implementation, this would evaluate component formula
        # with variables for base, variable pay, gross pay, etc.
        if component.formula:
            # Base formula calculation - in real implementation, this would be more complex
            # and handle variables like base pay, attendance, etc.
            amount = assignment.base * (flt(component.amount) / 100)
        else:
            amount = flt(component.amount)
            
        return amount
    
    def get_salary_structure_assignment(self):
        """Get active salary structure assignment for the employee and date"""
        assignments = frappe.db.sql("""
            SELECT * FROM `tabSalary Structure Assignment`
            WHERE employee=%s AND salary_structure=%s
            AND docstatus=1
            AND (from_date <= %s OR from_date <= '0000-00-00')
            AND (to_date >= %s OR to_date IS NULL OR to_date = '0000-00-00')
        """, (self.employee, self.salary_structure, self.start_date, self.end_date), as_dict=True)
        
        return assignments[0] if assignments else None
    
    def get_auto_payment_setting(self):
        """Check if auto payment is enabled in payroll settings"""
        return frappe.db.get_single_value("Payroll Settings", "auto_create_payment_entry")
    
    def create_payment_entry(self):
        """Create payment entry for salary payment"""
        # This would be a complex method creating actual payment entries
        # in a real implementation. For simplicity, we're just showing a placeholder.
        frappe.msgprint(_("Payment entry for salary would be created here"))
    
    def update_status(self, slip_name=None):
        """Update status of salary slip"""
        paid = "Paid" if self.docstatus == 1 else None
        status = "Submitted" if self.docstatus == 1 else "Draft" if self.docstatus == 0 else "Cancelled"
        
        slip_name = slip_name or self.name
        
        frappe.db.set_value("Salary Slip", slip_name, {
            "paid": paid,
            "status": status
        })
    
    def process_scheduled_salary_slips():
        """Scheduled task to create salary slips"""
        # This is a method that would be called by scheduler
        # to auto-generate salary slips based on salary structures
        # We'll just define the basic structure
        
        # Get current month's start and end dates
        today = getdate()
        first_day = get_first_day(today)
        last_day = get_last_day(today)
        
        # Find all active salary structure assignments
        assignments = frappe.db.sql("""
            SELECT 
                ssa.employee, ssa.employee_name, ssa.salary_structure
            FROM 
                `tabSalary Structure Assignment` ssa
            JOIN 
                `tabEmployee` emp ON ssa.employee = emp.name
            WHERE 
                ssa.docstatus = 1 
                AND emp.status = 'Active'
                AND (ssa.from_date <= %s OR ssa.from_date <= '0000-00-00')
                AND (ssa.to_date >= %s OR ssa.to_date IS NULL OR ssa.to_date = '0000-00-00')
                AND NOT EXISTS (
                    SELECT name FROM `tabSalary Slip` 
                    WHERE employee = ssa.employee 
                    AND start_date = %s 
                    AND end_date = %s 
                    AND docstatus != 2
                )
        """, (last_day, first_day, first_day, last_day), as_dict=True)
        
        # Create salary slips for each employee
        for assignment in assignments:
            try:
                salary_slip = frappe.new_doc("Salary Slip")
                salary_slip.employee = assignment.employee
                salary_slip.employee_name = assignment.employee_name
                salary_slip.salary_structure = assignment.salary_structure
                salary_slip.start_date = first_day
                salary_slip.end_date = last_day
                salary_slip.posting_date = today
                
                # Make salary slip from structure
                salary_slip.make_salary_slip_from_salary_structure()
                
                salary_slip.insert()
                
                # Auto-submit if configured
                if frappe.db.get_single_value("Payroll Settings", "auto_submit_salary_slip"):
                    salary_slip.submit()
                    
            except Exception as e:
                frappe.log_error(f"Error creating salary slip for {assignment.employee}: {str(e)}")
