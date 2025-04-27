# Copyright (c) 2023, Your Company and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def get_context(context):
    """Add data to context object for rendering the HR dashboard page"""
    if not frappe.session.user or frappe.session.user == "Guest":
        frappe.throw(_("You need to be logged in to access this page"), frappe.PermissionError)
    
    # Check if user has HR permissions
    if not frappe.has_permission("Employee", "read"):
        frappe.throw(_("You don't have permission to access this page"), frappe.PermissionError)
    
    # Add departments to context for filter dropdown
    context.departments = frappe.get_all("Department", fields=["name"])
    
    # Add user role info to context
    context.is_hr_manager = "HR Manager" in frappe.get_roles(frappe.session.user)
    context.is_hr_user = "HR User" in frappe.get_roles(frappe.session.user)
    
    # Set page title and breadcrumbs
    context.title = _("HR Dashboard")
    context.parents = [{"name": _("Home"), "route": "/"}]
    
    return context
