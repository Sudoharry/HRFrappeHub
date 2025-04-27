# Copyright (c) 2023, Your Company and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, nowdate, add_days, date_diff, flt, cint
from frappe.model.mapper import get_mapped_doc
import datetime

def create_employee_for_user(doc, method=None):
    """Create employee record for new user if they don't have one"""
    if doc.doctype != "User":
        return
    
    # Don't create employee for system users or disabled users
    if cint(doc.enabled) != 1 or doc.user_type == "System User" or doc.name == "Administrator":
        return
    
    # Check if employee already exists for this user
    existing_employee = frappe.db.exists("Employee", {"user_id": doc.name})
    if existing_employee:
        return
    
    # Check if user has an Employee role
    has_employee_role = frappe.db.exists("Has Role", {"parent": doc.name, "role": "Employee"})
    if not has_employee_role:
        return
    
    # Create new employee record
    try:
        employee = frappe.new_doc("Employee")
        employee.first_name = doc.first_name
        employee.last_name = doc.last_name
        employee.user_id = doc.name
        employee.gender = doc.gender if hasattr(doc, "gender") else None
        employee.personal_email = doc.email
        employee.company_email = doc.email
        employee.status = "Active"
        employee.date_of_joining = nowdate()
        
        # Get default company
        default_company = frappe.defaults.get_user_default("Company")
        if default_company:
            employee.company = default_company
        
        # Save the employee record
        employee.flags.ignore_mandatory = True  # For required fields to be filled later
        employee.save(ignore_permissions=True)
        frappe.db.commit()
        
        frappe.msgprint(_("Employee record created for {0}").format(doc.name))
    except Exception as e:
        frappe.log_error(title=_("Error creating employee for user"),
            message=f"Could not create employee for user {doc.name}: {str(e)}\n\n{frappe.get_traceback()}")

def update_employee_details(doc, method=None):
    """Update user details when employee record is updated"""
    if not doc.user_id:
        return
    
    try:
        # Update user record
        user = frappe.get_doc("User", doc.user_id)
        
        update_fields = {
            "first_name": doc.first_name,
            "last_name": doc.last_name or "",
            "full_name": doc.employee_name
        }
        
        # Update email if company email is set
        if doc.company_email and doc.company_email != user.email:
            update_fields["email"] = doc.company_email
        
        # Update user
        for field, value in update_fields.items():
            if hasattr(user, field) and value:
                user.set(field, value)
        
        user.save(ignore_permissions=True)
        
        # Update employee's user permissions
        if doc.create_user_permission:
            create_user_permission(doc)
    except Exception as e:
        frappe.log_error(title=_("Error updating user details from employee"),
            message=f"Could not update user {doc.user_id} from employee {doc.name}: {str(e)}\n\n{frappe.get_traceback()}")

def create_user_permission(employee):
    """Create user permission for the employee"""
    if not employee.user_id:
        return
        
    # Check if permission already exists
    existing_permission = frappe.db.exists("User Permission", {
        "user": employee.user_id,
        "allow": "Employee",
        "for_value": employee.name
    })
    
    if existing_permission:
        return
        
    try:
        # Create new user permission
        user_permission = frappe.new_doc("User Permission")
        user_permission.user = employee.user_id
        user_permission.allow = "Employee"
        user_permission.for_value = employee.name
        user_permission.apply_to_all_doctypes = 1
        user_permission.save(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(title=_("Error creating user permission"),
            message=f"Could not create user permission for {employee.user_id}: {str(e)}\n\n{frappe.get_traceback()}")

def check_holiday(employee, date):
    """Check if the given date is a holiday for the employee"""
    holiday_list = get_holiday_list_for_employee(employee)
    if not holiday_list:
        return False
        
    return frappe.db.exists("Holiday", {
        "parent": holiday_list,
        "holiday_date": date
    })

def get_holiday_list_for_employee(employee):
    """Get the holiday list for an employee"""
    if isinstance(employee, str):
        # If employee ID is provided, get the holiday list from employee record
        holiday_list = frappe.db.get_value("Employee", employee, "holiday_list")
        if not holiday_list:
            # If not found, get from employee's company
            company = frappe.db.get_value("Employee", employee, "company")
            holiday_list = frappe.db.get_value("Company", company, "default_holiday_list")
    else:
        # If employee document is provided
        holiday_list = employee.holiday_list
        if not holiday_list:
            holiday_list = frappe.db.get_value("Company", employee.company, "default_holiday_list")
            
    return holiday_list

def validate_active_employee(employee):
    """Validate that the employee is active"""
    if isinstance(employee, str):
        employee_status = frappe.db.get_value("Employee", employee, "status")
    else:
        employee_status = employee.status
        
    if employee_status != "Active":
        frappe.throw(_("Employee {0} is not active").format(employee))
        
    return True

def validate_duplicate_record(doctype, employee, date_field, date_value, name=None):
    """Check for duplicate records for the same employee on the same date"""
    filters = {
        "employee": employee,
        date_field: date_value,
        "docstatus": ["!=", 2]  # Not cancelled
    }
    
    if name:
        filters["name"] = ["!=", name]
        
    existing = frappe.db.exists(doctype, filters)
    
    if existing:
        frappe.throw(_("There is already a {0} record for employee {1} on {2}").format(
            doctype, employee, date_value))
            
    return False

def calculate_work_experience(employee):
    """Calculate total work experience for an employee"""
    # Get employee's joining date
    joining_date = frappe.db.get_value("Employee", employee, "date_of_joining")
    if not joining_date:
        return 0
        
    # Get external work experience
    external_work_experience = frappe.db.sql("""
        SELECT SUM(
            TIMESTAMPDIFF(MONTH, from_date, IF(to_date, to_date, CURDATE()))
        ) as months
        FROM `tabEmployee External Work History`
        WHERE parent = %s
    """, (employee,))
    
    external_months = external_work_experience[0][0] or 0
    
    # Calculate internal experience
    today = getdate()
    internal_months = (today.year - joining_date.year) * 12 + today.month - joining_date.month
    
    # Total experience in months
    total_months = external_months + internal_months
    
    # Convert to years and months
    years = total_months // 12
    remaining_months = total_months % 12
    
    return {
        "years": years,
        "months": remaining_months,
        "total_months": total_months
    }

def get_leave_allocation_for_period(employee, leave_type, from_date, to_date):
    """Get leave allocation for an employee for a specific period"""
    leave_allocation = frappe.db.sql("""
        SELECT name, total_leaves_allocated, total_leaves_taken
        FROM `tabLeave Allocation`
        WHERE employee = %s AND leave_type = %s
        AND docstatus = 1
        AND from_date <= %s AND to_date >= %s
    """, (employee, leave_type, to_date, from_date), as_dict=True)
    
    if leave_allocation:
        return leave_allocation[0]
    return None

def calculate_leave_balance(employee, leave_type, date=None):
    """Calculate leave balance for an employee"""
    if not date:
        date = getdate()
        
    # Get leave allocation
    allocation = get_leave_allocation_for_period(employee, leave_type, date, date)
    if not allocation:
        return 0
        
    balance = flt(allocation.total_leaves_allocated) - flt(allocation.total_leaves_taken)
    return balance

def get_pending_salary_slip_count(employee=None):
    """Get count of pending salary slips"""
    filters = {"docstatus": 0}
    if employee:
        filters["employee"] = employee
        
    return frappe.db.count("Salary Slip", filters)

def get_approved_leaves_for_period(employee, from_date, to_date):
    """Get approved leaves for an employee in a specific period"""
    leaves = frappe.db.sql("""
        SELECT leave_type, from_date, to_date, total_leave_days
        FROM `tabLeave Application`
        WHERE employee = %s
        AND status = 'Approved' AND docstatus = 1
        AND (from_date BETWEEN %s AND %s
            OR to_date BETWEEN %s AND %s
            OR (from_date < %s AND to_date > %s))
    """, (employee, from_date, to_date, from_date, to_date, from_date, to_date), as_dict=True)
    
    return leaves

def get_retirement_date(employee):
    """Calculate retirement date for an employee"""
    # Get date of birth and retirement age
    dob = frappe.db.get_value("Employee", employee, "date_of_birth")
    if not dob:
        return None
        
    retirement_age = frappe.db.get_single_value("HR Settings", "retirement_age") or 60
    
    # Calculate retirement date
    retirement_date = add_days(
        add_days(dob, retirement_age * 365),
        -1  # Last day before next birthday
    )
    
    return retirement_date

def get_employees_with_birthdays_this_month():
    """Get employees with birthdays in the current month"""
    today = getdate()
    
    employees = frappe.db.sql("""
        SELECT name, employee_name, date_of_birth, department, designation
        FROM `tabEmployee`
        WHERE status = 'Active'
        AND MONTH(date_of_birth) = %s
    """, (today.month,), as_dict=True)
    
    for employee in employees:
        dob = getdate(employee.date_of_birth)
        birthday_this_year = datetime.date(today.year, dob.month, dob.day)
        employee.birthday_on = birthday_this_year
        employee.days_until_birthday = date_diff(birthday_this_year, today)
        
    return employees

def get_department_head(department):
    """Get department head for a department"""
    return frappe.db.get_value("Department", department, "department_head")

def make_bank_entry(salary_slip):
    """Create bank entry for salary payment"""
    # This is a placeholder for a function that would create a bank entry
    # In a real implementation, this would create a payment entry or bank voucher
    pass
