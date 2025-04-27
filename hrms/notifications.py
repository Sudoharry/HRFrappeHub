# Copyright (c) 2023, Your Company and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.desk.notifications import get_filters_for
import json

def get_notification_config():
    """Get notification configuration for HRMS"""
    return {
        "for_doctype": {
            "Employee": {"status": ("!=", "Left")},
            "Leave Application": {"status": "Open", "docstatus": 0},
            "Attendance": {"docstatus": 0},
            "Salary Slip": {"docstatus": 0},
            "Appraisal": {"status": "Draft"},
            "Job Applicant": {"status": "Open"},
            "Job Opening": {"status": "Open"}
        },
        "for_module_doctypes": {
            "HR": [
                "Employee", "Department", "Designation",
                "Branch", "Employment Type"
            ],
            "Payroll": [
                "Salary Structure", "Salary Slip",
                "Salary Structure Assignment", "Payroll Entry"
            ],
            "Recruitment": [
                "Job Opening", "Job Applicant",
                "Job Offer", "Interview"
            ],
            "Performance": [
                "Appraisal", "Appraisal Template"
            ]
        }
    }

def notify_leave_approval(doc, method=None):
    """Notify employee about their leave application status change"""
    if doc.docstatus != 1:
        return
    
    # Skip if status is not changed
    if not doc.get("__islocal") and not doc.has_value_changed("status"):
        return
    
    # Get employee's user
    employee_user = frappe.db.get_value("Employee", doc.employee, "user_id")
    if not employee_user:
        return
    
    # Check if employee has email
    employee_email = frappe.db.get_value("User", employee_user, "email")
    if not employee_email:
        return
    
    # Create notification
    notification = create_notification(
        doc=doc,
        for_user=employee_user,
        title=_("Leave Application {0}").format(doc.status),
        message=_("Your leave application from {0} to {1} has been {2}").format(
            frappe.format(doc.from_date, {"fieldtype": "Date"}),
            frappe.format(doc.to_date, {"fieldtype": "Date"}),
            doc.status.lower()
        ),
        type="Alert" if doc.status == "Rejected" else "Success"
    )
    
    # Send email
    if notification:
        try:
            send_email_notification(
                recipients=[employee_email],
                subject=_("Leave Application {0}").format(doc.status),
                message=notification.get("message"),
                reference_doctype=doc.doctype,
                reference_name=doc.name
            )
        except Exception as e:
            frappe.log_error(title=_("Failed to send leave approval notification"),
                message=frappe.get_traceback())

def notify_leave_cancellation(doc, method=None):
    """Notify employee about leave application cancellation"""
    if doc.docstatus != 2:
        return
    
    # Get employee's user
    employee_user = frappe.db.get_value("Employee", doc.employee, "user_id")
    if not employee_user:
        return
    
    # Check if employee has email
    employee_email = frappe.db.get_value("User", employee_user, "email")
    if not employee_email:
        return
    
    # Create notification
    notification = create_notification(
        doc=doc,
        for_user=employee_user,
        title=_("Leave Application Cancelled"),
        message=_("Your leave application from {0} to {1} has been cancelled").format(
            frappe.format(doc.from_date, {"fieldtype": "Date"}),
            frappe.format(doc.to_date, {"fieldtype": "Date"})
        ),
        type="Alert"
    )
    
    # Send email
    if notification:
        try:
            send_email_notification(
                recipients=[employee_email],
                subject=_("Leave Application Cancelled"),
                message=notification.get("message"),
                reference_doctype=doc.doctype,
                reference_name=doc.name
            )
        except Exception as e:
            frappe.log_error(title=_("Failed to send leave cancellation notification"),
                message=frappe.get_traceback())

def notify_salary_slip_creation(doc, method=None):
    """Notify employee about salary slip creation"""
    if doc.docstatus != 1:
        return
    
    # Get employee's user
    employee_user = frappe.db.get_value("Employee", doc.employee, "user_id")
    if not employee_user:
        return
    
    # Check if employee has email
    employee_email = frappe.db.get_value("User", employee_user, "email")
    if not employee_email:
        return
    
    # Create notification
    notification = create_notification(
        doc=doc,
        for_user=employee_user,
        title=_("Salary Slip Generated"),
        message=_("Your salary slip for the period {0} to {1} has been generated. Net pay: {2}").format(
            frappe.format(doc.start_date, {"fieldtype": "Date"}),
            frappe.format(doc.end_date, {"fieldtype": "Date"}),
            frappe.format(doc.net_pay, {"fieldtype": "Currency"})
        ),
        type="Success"
    )
    
    # Send email
    if notification:
        try:
            send_email_notification(
                recipients=[employee_email],
                subject=_("Salary Slip Generated"),
                message=notification.get("message"),
                reference_doctype=doc.doctype,
                reference_name=doc.name
            )
        except Exception as e:
            frappe.log_error(title=_("Failed to send salary slip notification"),
                message=frappe.get_traceback())

def create_notification(doc, for_user, title, message, type=None):
    """Create notification for user"""
    try:
        return frappe.get_doc({
            "doctype": "Notification Log",
            "for_user": for_user,
            "document_type": doc.doctype,
            "document_name": doc.name,
            "subject": title,
            "email_content": message,
            "type": type or "Alert"
        }).insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(title=_("Failed to create notification"),
            message=frappe.get_traceback())
        return None

def send_email_notification(recipients, subject, message, reference_doctype=None, reference_name=None):
    """Send email notification to recipients"""
    try:
        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            message=message,
            reference_doctype=reference_doctype,
            reference_name=reference_name
        )
        return True
    except Exception as e:
        frappe.log_error(title=_("Failed to send email notification"),
            message=frappe.get_traceback())
        return False

def send_birthday_reminders():
    """Send birthday reminders to HR team"""
    # Get today's birthdays
    from frappe.utils import today, getdate
    
    today_date = getdate(today())
    
    birthdays = frappe.db.sql("""
        SELECT name, employee_name, department, date_of_birth
        FROM `tabEmployee`
        WHERE status = 'Active'
        AND DAY(date_of_birth) = %s
        AND MONTH(date_of_birth) = %s
    """, (today_date.day, today_date.month), as_dict=True)
    
    if not birthdays:
        return
    
    # Get HR users to notify
    hr_users = get_hr_users()
    if not hr_users:
        return
    
    # Create birthday message
    message = "<h3>Employee Birthdays Today</h3><ul>"
    for employee in birthdays:
        message += f"<li><strong>{employee.employee_name}</strong> - {employee.department}</li>"
    message += "</ul>"
    
    # Send email to HR team
    try:
        frappe.sendmail(
            recipients=hr_users,
            subject=_("Employee Birthdays Today - {0}").format(today()),
            message=message
        )
    except Exception:
        frappe.log_error(title=_("Failed to send birthday reminders"),
            message=frappe.get_traceback())

def send_work_anniversary_reminders():
    """Send work anniversary reminders to HR team"""
    # Get today's work anniversaries
    from frappe.utils import today, getdate, get_datetime
    from dateutil.relativedelta import relativedelta
    
    today_date = getdate(today())
    
    anniversaries = frappe.db.sql("""
        SELECT name, employee_name, department, date_of_joining
        FROM `tabEmployee`
        WHERE status = 'Active'
        AND DAY(date_of_joining) = %s
        AND MONTH(date_of_joining) = %s
        AND date_of_joining < %s
    """, (today_date.day, today_date.month, today_date), as_dict=True)
    
    if not anniversaries:
        return
    
    # Calculate years of service
    for employee in anniversaries:
        doj = getdate(employee.date_of_joining)
        years = today_date.year - doj.year
        employee.years_of_service = years
    
    # Get HR users to notify
    hr_users = get_hr_users()
    if not hr_users:
        return
    
    # Create anniversary message
    message = "<h3>Work Anniversaries Today</h3><ul>"
    for employee in anniversaries:
        message += f"<li><strong>{employee.employee_name}</strong> - {employee.department} - " + \
                  _("{0} Year(s) of Service").format(employee.years_of_service) + "</li>"
    message += "</ul>"
    
    # Send email to HR team
    try:
        frappe.sendmail(
            recipients=hr_users,
            subject=_("Work Anniversaries Today - {0}").format(today()),
            message=message
        )
    except Exception:
        frappe.log_error(title=_("Failed to send work anniversary reminders"),
            message=frappe.get_traceback())

def get_hr_users():
    """Get HR users email addresses"""
    hr_users = []
    
    # Get users with HR Manager or HR User role
    users = frappe.get_all(
        "Has Role", 
        filters=[
            ["role", "in", ["HR Manager", "HR User"]],
            ["parenttype", "=", "User"]
        ],
        fields=["parent"]
    )
    
    # Get their email addresses
    for user in users:
        user_email = frappe.db.get_value("User", user.parent, "email")
        if user_email:
            hr_users.append(user_email)
    
    return list(set(hr_users))  # Remove duplicates

def send_probation_ending_reminder():
    """Send reminder for employees whose probation period is ending soon"""
    from frappe.utils import add_days, getdate, today
    
    # Get employees whose probation ends in the next 7 days
    today_date = getdate(today())
    seven_days_later = add_days(today_date, 7)
    
    employees = frappe.db.sql("""
        SELECT name, employee_name, department, designation, date_of_joining, probation_end_date
        FROM `tabEmployee`
        WHERE status = 'Active'
        AND probation_end_date BETWEEN %s AND %s
    """, (today_date, seven_days_later), as_dict=True)
    
    if not employees:
        return
    
    # Get HR users and reporting managers
    hr_users = get_hr_users()
    
    for employee in employees:
        # Notify HR team
        if hr_users:
            message = f"""
            <p>Hello,</p>
            <p>This is a reminder that the probation period for <strong>{employee.employee_name}</strong> 
            ({employee.designation} - {employee.department}) is ending on 
            {frappe.format(employee.probation_end_date, {"fieldtype": "Date"})}.</p>
            <p>Please take appropriate action regarding their employment status.</p>
            """
            
            try:
                frappe.sendmail(
                    recipients=hr_users,
                    subject=_("Probation Period Ending: {0}").format(employee.employee_name),
                    message=message,
                    reference_doctype="Employee",
                    reference_name=employee.name
                )
            except Exception:
                frappe.log_error(title=_("Failed to send probation reminder"),
                    message=frappe.get_traceback())
        
        # Notify reporting manager if exists
        reports_to = frappe.db.get_value("Employee", employee.name, "reports_to")
        if reports_to:
            manager = frappe.get_doc("Employee", reports_to)
            if manager.user_id:
                manager_email = frappe.db.get_value("User", manager.user_id, "email")
                
                if manager_email:
                    message = f"""
                    <p>Hello {manager.employee_name},</p>
                    <p>This is a reminder that the probation period for your team member <strong>{employee.employee_name}</strong> 
                    ({employee.designation}) is ending on 
                    {frappe.format(employee.probation_end_date, {"fieldtype": "Date"})}.</p>
                    <p>Please provide your feedback and recommendation to the HR department.</p>
                    """
                    
                    try:
                        frappe.sendmail(
                            recipients=[manager_email],
                            subject=_("Probation Period Ending: {0}").format(employee.employee_name),
                            message=message,
                            reference_doctype="Employee",
                            reference_name=employee.name
                        )
                    except Exception:
                        frappe.log_error(title=_("Failed to send probation reminder to manager"),
                            message=frappe.get_traceback())
