# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, cint

class SalaryStructure(Document):
    def validate(self):
        self.validate_dates()
        self.validate_salary_components()
        self.validate_employees()
    
    def validate_dates(self):
        if self.from_date and self.to_date and getdate(self.to_date) < getdate(self.from_date):
            frappe.throw(_("To Date cannot be before From Date"))
    
    def validate_salary_components(self):
        # Ensure there are earnings and deductions
        if not self.earnings:
            frappe.throw(_("Earnings table cannot be empty"))
        
        # Validate that component formulas are valid
        for component in self.earnings + self.deductions:
            if component.formula:
                try:
                    # Just a simple test to see if formula syntax is valid
                    # In a real implementation, this would evaluate with some test data
                    salary_component = frappe.get_doc("Salary Component", component.salary_component)
                    if not salary_component.formula_help:
                        frappe.msgprint(_("Hint: Check if formula for {0} is correct").format(component.salary_component))
                except:
                    frappe.throw(_("Formula syntax error for component {0}").format(component.salary_component))
    
    def validate_employees(self):
        if self.docstatus != 1:
            return
            
        # Check if already assigned to employees
        if not self.employees:
            frappe.msgprint(_("This Salary Structure is not assigned to any employee"))
    
    def on_update(self):
        self.assign_salary_structure()
    
    def on_submit(self):
        self.assign_salary_structure()
    
    def on_cancel(self):
        self.unassign_salary_structure()
    
    def assign_salary_structure(self):
        if self.docstatus != 1 or not self.employees:
            return
            
        for employee in self.employees:
            # Check if employee exists and is active
            emp = frappe.db.get_value("Employee", employee.employee, ["status", "company"], as_dict=True)
            if emp and emp.status == "Active" and emp.company == self.company:
                # Update employee with this salary structure
                frappe.db.set_value("Employee", employee.employee, "salary_structure", self.name)
                
                # Create or update Salary Structure Assignment
                existing = frappe.db.exists("Salary Structure Assignment", {
                    "employee": employee.employee,
                    "salary_structure": self.name,
                    "from_date": self.from_date
                })
                
                if existing:
                    # Update existing assignment
                    assignment = frappe.get_doc("Salary Structure Assignment", existing)
                    assignment.base = employee.base
                    assignment.variable = employee.variable
                    assignment.from_date = self.from_date
                    assignment.to_date = self.to_date
                    assignment.save()
                else:
                    # Create new assignment
                    assignment = frappe.new_doc("Salary Structure Assignment")
                    assignment.employee = employee.employee
                    assignment.salary_structure = self.name
                    assignment.company = self.company
                    assignment.base = employee.base
                    assignment.variable = employee.variable
                    assignment.from_date = self.from_date
                    assignment.to_date = self.to_date
                    assignment.save()
    
    def unassign_salary_structure(self):
        if not self.employees:
            return
            
        for employee in self.employees:
            # Check if employee still has this salary structure
            if frappe.db.get_value("Employee", employee.employee, "salary_structure") == self.name:
                frappe.db.set_value("Employee", employee.employee, "salary_structure", "")
            
            # Delete or cancel salary structure assignments
            assignments = frappe.get_all("Salary Structure Assignment", 
                filters={
                    "salary_structure": self.name,
                    "employee": employee.employee
                }
            )
            
            for assignment in assignments:
                frappe.delete_doc("Salary Structure Assignment", assignment.name)
    
    def get_employees(self):
        """Get employees based on department, designation, branch, company"""
        conditions = []
        
        if self.company:
            conditions.append("company = '{0}'".format(self.company))
        
        if self.department:
            conditions.append("department = '{0}'".format(self.department))
            
        if self.designation:
            conditions.append("designation = '{0}'".format(self.designation))
            
        if self.branch:
            conditions.append("branch = '{0}'".format(self.branch))
            
        # Always get active employees
        conditions.append("status = 'Active'")
        
        condition_str = " AND ".join(conditions)
        
        employees = frappe.db.sql("""
            SELECT name, employee_name
            FROM `tabEmployee`
            WHERE {0}
        """.format(condition_str), as_dict=True)
        
        return employees
    
    def get_employee_base_salary(self, employee):
        """Get employee's base salary"""
        # In a real implementation, this would fetch the base salary from current salary
        # For simplicity, returning a default value
        return 0
