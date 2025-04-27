"""
Hooks System for Flask-based HR Management System

This module provides a hooks system similar to Frappe's hooks,
allowing for event-driven programming and customization.
"""

import importlib
import logging
from flask import current_app

# Document Events
# Hook on document methods and events
doc_events = {
    "User": {
        "after_insert": "hrms.hrms_controller.create_employee_for_user"
    },
    "Employee": {
        "on_update": "hrms.hrms_controller.update_employee_details"
    },
    "Leave Application": {
        "on_submit": "hrms.notifications.notify_leave_approval",
        "on_cancel": "hrms.notifications.notify_leave_cancellation"
    },
    "Attendance": {
        "on_submit": "hrms.hr.doctype.attendance.attendance.process_auto_attendance"
    },
    "Salary Slip": {
        "on_submit": "hrms.notifications.notify_salary_slip_creation"
    }
}

# Permission Handlers
permission_query_conditions = {
    "Employee": "hrms.hr.doctype.employee.employee.get_permission_query_conditions",
    "Attendance": "hrms.hr.doctype.attendance.attendance.get_permission_query_conditions",
    "Leave Application": "hrms.hr.doctype.leave_application.leave_application.get_permission_query_conditions",
}

has_permission = {
    "Employee": "hrms.hr.doctype.employee.employee.has_permission",
    "Attendance": "hrms.hr.doctype.attendance.attendance.has_permission",
    "Leave Application": "hrms.hr.doctype.leave_application.leave_application.has_permission",
}

# Role-based Permissions
role_permissions = {
    "HR Manager": [
        ["Employee", "read", "write", "create", "delete", "submit", "cancel", "amend"],
        ["Attendance", "read", "write", "create", "delete", "submit", "cancel", "amend"],
        ["Leave Application", "read", "write", "create", "delete", "submit", "cancel", "amend"],
        ["Salary Slip", "read", "write", "create", "delete", "submit", "cancel", "amend"],
        ["Job Opening", "read", "write", "create", "delete", "submit", "cancel", "amend"],
        ["Job Applicant", "read", "write", "create", "delete", "submit", "cancel", "amend"],
        ["Appraisal", "read", "write", "create", "delete", "submit", "cancel", "amend"]
    ],
    "HR User": [
        ["Employee", "read", "write", "create"],
        ["Attendance", "read", "write", "create", "submit"],
        ["Leave Application", "read", "write", "create", "submit"],
        ["Salary Slip", "read"],
        ["Job Opening", "read", "write", "create"],
        ["Job Applicant", "read", "write", "create"],
        ["Appraisal", "read", "write", "create"]
    ],
    "Employee": [
        ["Employee", "read", {"user": "owner"}],
        ["Attendance", "read", "write", "create", {"user": "owner"}],
        ["Leave Application", "read", "write", "create", {"user": "owner"}],
        ["Salary Slip", "read", {"user": "owner"}],
        ["Appraisal", "read", {"user": "owner"}]
    ]
}

# Scheduled Tasks
scheduler_events = {
    "daily": [
        "hrms.hr.doctype.attendance.attendance.mark_absent_for_unmarked_employees",
        "hrms.hr.doctype.leave_application.leave_application.update_leave_status"
    ],
    "monthly": [
        "hrms.payroll.doctype.salary_slip.salary_slip.process_scheduled_salary_slips"
    ]
}

# API Endpoints
api_endpoints = {
    "Employee": "hrms/api/employee",
    "Leave Application": "hrms/api/leave",
    "Attendance": "hrms/api/attendance",
    "Job Opening": "hrms/api/job_opening",
    "Job Applicant": "hrms/api/job_applicant"
}

# Hook Functions

def trigger_hook(doctype, event, doc):
    """Trigger hooks for document events"""
    if doctype in doc_events and event in doc_events[doctype]:
        method_path = doc_events[doctype][event]
        return _call_hook_method(method_path, doc)
    return None

def trigger_permission_query(doctype, user=None):
    """Get permission query for doctype"""
    if doctype in permission_query_conditions:
        method_path = permission_query_conditions[doctype]
        return _call_hook_method(method_path, user)
    return None

def trigger_has_permission(doctype, doc, user=None):
    """Check permission for document"""
    if doctype in has_permission:
        method_path = has_permission[doctype]
        return _call_hook_method(method_path, doc, user)
    return None

def _call_hook_method(method_path, *args, **kwargs):
    """Helper to call a hook method from its string path"""
    try:
        module_path, method_name = method_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        method = getattr(module, method_name)
        return method(*args, **kwargs)
    except (ImportError, AttributeError) as e:
        logging.error(f"Error calling hook method {method_path}: {e}")
        return None

def check_role_permissions(user, doctype, ptype):
    """Check if user has permission based on roles"""
    if not hasattr(user, 'role'):
        return False
    
    user_role = user.role
    if user_role in role_permissions:
        for permission in role_permissions[user_role]:
            if permission[0] == doctype and ptype in permission[1:]:
                # Check for user-specific conditions
                for item in permission[1:]:
                    if isinstance(item, dict) and 'user' in item:
                        if item['user'] == 'owner':
                            # This requires the document to have a user_id or owner field
                            # This is a placeholder and would need to be customized
                            return True
                return True
    
    return False

def init_scheduler(scheduler):
    """Initialize scheduler with tasks from hooks"""
    # This would register tasks with a scheduler like APScheduler
    # For now, this is a placeholder
    pass