"""
Salary Structure DocType Controller

This module contains the controller for the Salary Structure DocType
which handles business logic and validations.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, flt

class SalaryStructure(Document):
    def validate(self):
        """Validate salary structure"""
        self.validate_date()
        self.validate_amount()
        self.validate_applicable_for()
    
    def validate_date(self):
        """Validate from_date"""
        if self.from_date and getdate(self.from_date) > getdate(frappe.utils.today()):
            frappe.throw(_("From Date cannot be in the future"))
    
    def validate_amount(self):
        """Validate amount"""
        # Base amount should be greater than 0
        if flt(self.base_amount) <= 0:
            frappe.throw(_("Base Amount should be greater than 0"))
        
        # Check earnings and deductions
        if hasattr(self, 'earnings') and self.earnings:
            for earning in self.earnings:
                if flt(earning.amount) < 0:
                    frappe.throw(_("Amount cannot be negative for earning {0}").format(earning.salary_component))
        
        if hasattr(self, 'deductions') and self.deductions:
            for deduction in self.deductions:
                if flt(deduction.amount) < 0:
                    frappe.throw(_("Amount cannot be negative for deduction {0}").format(deduction.salary_component))
    
    def validate_applicable_for(self):
        """Validate applicable_for fields"""
        if self.applicable_for:
            if self.applicable_for == "Department" and not self.department:
                frappe.throw(_("Please select Department"))
            elif self.applicable_for == "Designation" and not self.designation:
                frappe.throw(_("Please select Designation"))
            elif self.applicable_for == "Employee Grade" and not self.employee_grade:
                frappe.throw(_("Please select Employee Grade"))
            elif self.applicable_for == "Employee" and not self.employee:
                frappe.throw(_("Please select Employee"))
    
    def on_update(self):
        """On update actions"""
        # If is_active is checked, ensure all other structures for the same criteria are inactive
        if self.is_active:
            self.check_other_active_structures()
    
    def check_other_active_structures(self):
        """Deactivate other salary structures with the same criteria"""
        filters = {
            "name": ("!=", self.name),
            "is_active": 1
        }
        
        # Add applicable_for condition
        if self.applicable_for and self.applicable_for != "All Employees":
            filters["applicable_for"] = self.applicable_for
            
            if self.applicable_for == "Department" and self.department:
                filters["department"] = self.department
            elif self.applicable_for == "Designation" and self.designation:
                filters["designation"] = self.designation
            elif self.applicable_for == "Employee Grade" and self.employee_grade:
                filters["employee_grade"] = self.employee_grade
            elif self.applicable_for == "Employee" and self.employee:
                filters["employee"] = self.employee
        
        # Find other active structures
        other_structures = frappe.get_all("Salary Structure", filters=filters)
        
        # Deactivate them
        for structure in other_structures:
            frappe.db.set_value("Salary Structure", structure.name, "is_active", 0)
            frappe.msgprint(_("Salary Structure {0} has been set as inactive").format(structure.name))

def get_salary_structure(employee, date=None):
    """Get applicable salary structure for an employee on a given date"""
    if not date:
        date = frappe.utils.today()
    
    # Get employee details
    employee_details = frappe.db.get_value("Employee", employee, 
        ["department", "designation", "grade"], as_dict=True)
    
    # Find active salary structure for the employee
    # First try for the specific employee
    salary_structure = frappe.db.get_value("Salary Structure", {
        "employee": employee,
        "is_active": 1,
        "applicable_for": "Employee",
        "from_date": ("<=", date)
    }, "name")
    
    if not salary_structure and employee_details.grade:
        # Try for employee grade
        salary_structure = frappe.db.get_value("Salary Structure", {
            "employee_grade": employee_details.grade,
            "is_active": 1,
            "applicable_for": "Employee Grade",
            "from_date": ("<=", date)
        }, "name")
    
    if not salary_structure and employee_details.designation:
        # Try for designation
        salary_structure = frappe.db.get_value("Salary Structure", {
            "designation": employee_details.designation,
            "is_active": 1,
            "applicable_for": "Designation",
            "from_date": ("<=", date)
        }, "name")
    
    if not salary_structure and employee_details.department:
        # Try for department
        salary_structure = frappe.db.get_value("Salary Structure", {
            "department": employee_details.department,
            "is_active": 1,
            "applicable_for": "Department",
            "from_date": ("<=", date)
        }, "name")
    
    if not salary_structure:
        # Finally try for all employees
        salary_structure = frappe.db.get_value("Salary Structure", {
            "applicable_for": "All Employees",
            "is_active": 1,
            "from_date": ("<=", date)
        }, "name")
    
    return salary_structure

@frappe.whitelist()
def make_salary_slip(salary_structure, employee):
    """Create a salary slip from a salary structure"""
    # Get the salary structure
    struct = frappe.get_doc("Salary Structure", salary_structure)
    
    # Create a new salary slip
    salary_slip = frappe.new_doc("Salary Slip")
    salary_slip.employee = employee
    salary_slip.employee_name = frappe.db.get_value("Employee", employee, "employee_name")
    salary_slip.salary_structure = struct.name
    
    # Set dates (assuming monthly payroll)
    import calendar
    from datetime import datetime
    
    today = datetime.now()
    last_day = calendar.monthrange(today.year, today.month)[1]
    salary_slip.start_date = today.replace(day=1).strftime('%Y-%m-%d')
    salary_slip.end_date = today.replace(day=last_day).strftime('%Y-%m-%d')
    salary_slip.posting_date = frappe.utils.today()
    
    # Set company
    salary_slip.company = struct.company
    
    # Set gross pay from base amount
    salary_slip.gross_pay = struct.base_amount
    
    # TODO: Handle earnings and deductions
    
    return salary_slip