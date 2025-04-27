# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from frappe import _

def get_data():
    return [
        {
            "module_name": "HRMS",
            "color": "#3498db",
            "icon": "octicon octicon-organization",
            "type": "module",
            "label": _("HRMS")
        },
        {
            "module_name": "HR",
            "color": "#2ecc71",
            "icon": "octicon octicon-organization",
            "type": "module",
            "label": _("Human Resources")
        },
        {
            "module_name": "Payroll",
            "color": "#e74c3c",
            "icon": "octicon octicon-credit-card",
            "type": "module",
            "label": _("Payroll")
        },
        {
            "module_name": "Recruitment",
            "color": "#9b59b6",
            "icon": "octicon octicon-briefcase",
            "type": "module",
            "label": _("Recruitment")
        },
        {
            "module_name": "Performance",
            "color": "#f39c12",
            "icon": "octicon octicon-graph",
            "type": "module",
            "label": _("Performance")
        }
    ]
