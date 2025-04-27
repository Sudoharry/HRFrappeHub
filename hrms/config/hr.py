# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from frappe import _

def get_data():
    return [
        {
            "label": _("Employee"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Employee",
                    "description": _("Employee records."),
                    "onboard": 1,
                },
                {
                    "type": "doctype",
                    "name": "Employment Type",
                    "description": _("Types of employment (permanent, contract, intern etc.).")
                },
                {
                    "type": "doctype",
                    "name": "Branch",
                    "description": _("Company branches.")
                },
                {
                    "type": "doctype",
                    "name": "Department",
                    "description": _("Company departments.")
                },
                {
                    "type": "doctype",
                    "name": "Designation",
                    "description": _("Employee designations.")
                }
            ]
        },
        {
            "label": _("Attendance"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Attendance",
                    "description": _("Attendance record."),
                    "onboard": 1,
                },
                {
                    "type": "doctype",
                    "name": "Attendance Request",
                    "description": _("Request for attendance record.")
                },
                {
                    "type": "doctype",
                    "name": "Upload Attendance",
                    "description": _("Upload attendance from a CSV file.")
                }
            ]
        },
        {
            "label": _("Leaves"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Leave Application",
                    "description": _("Leave applications."),
                    "onboard": 1,
                },
                {
                    "type": "doctype",
                    "name": "Leave Type",
                    "description": _("Types of leaves (casual, sick, privilege etc.).")
                },
                {
                    "type": "doctype",
                    "name": "Leave Period",
                    "description": _("Leave accounting period.")
                },
                {
                    "type": "doctype",
                    "name": "Leave Policy",
                    "description": _("Leave policy for different leave types.")
                },
                {
                    "type": "doctype",
                    "name": "Leave Allocation",
                    "description": _("Allocate leaves to employees.")
                }
            ]
        },
        {
            "label": _("Payroll"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Salary Structure",
                    "description": _("Salary structure template."),
                    "onboard": 1,
                },
                {
                    "type": "doctype",
                    "name": "Salary Slip",
                    "description": _("Monthly salary statement.")
                },
                {
                    "type": "doctype",
                    "name": "Payroll Entry",
                    "description": _("Process payroll for multiple employees.")
                },
                {
                    "type": "doctype",
                    "name": "Salary Component",
                    "description": _("Salary components like basic, allowances, deductions etc.")
                }
            ]
        },
        {
            "label": _("Recruitment"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Job Opening",
                    "description": _("Available job positions."),
                    "onboard": 1,
                },
                {
                    "type": "doctype",
                    "name": "Job Applicant",
                    "description": _("Applicants for jobs.")
                },
                {
                    "type": "doctype",
                    "name": "Interview",
                    "description": _("Interview details.")
                },
                {
                    "type": "doctype",
                    "name": "Job Offer",
                    "description": _("Offer letters to job applicants.")
                }
            ]
        },
        {
            "label": _("Performance"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Appraisal",
                    "description": _("Employee performance appraisal."),
                    "onboard": 1,
                },
                {
                    "type": "doctype",
                    "name": "Appraisal Template",
                    "description": _("Templates for performance appraisals.")
                }
            ]
        },
        {
            "label": _("Reports"),
            "icon": "fa fa-list",
            "items": [
                {
                    "type": "report",
                    "name": "Employee Leave Balance",
                    "doctype": "Leave Application",
                    "is_query_report": True
                },
                {
                    "type": "report",
                    "name": "Employee Birthday",
                    "doctype": "Employee",
                    "is_query_report": True
                },
                {
                    "type": "report",
                    "name": "Monthly Attendance Sheet",
                    "doctype": "Attendance",
                    "is_query_report": True
                },
                {
                    "type": "report",
                    "name": "Employee Information",
                    "doctype": "Employee",
                    "is_query_report": True
                }
            ]
        }
    ]
