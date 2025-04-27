# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class LeaveType(Document):
    def validate(self):
        # Validate max continuous days
        if self.max_continuous_days and self.max_continuous_days <= 0:
            frappe.throw(_("Maximum Continuous Days should be greater than 0"))
        
        # Validate carry forward settings
        if self.is_carry_forward and self.max_carry_forwarded_leaves and self.max_carry_forwarded_leaves <= 0:
            frappe.throw(_("Maximum Carry Forwarded Leaves should be greater than 0"))
        
        # Ensure encashment settings are consistent
        if self.allow_encashment and not self.is_encash:
            frappe.throw(_("To allow encashment, Leave Type must be encashable"))
        
        # Validate encashment threshold
        if self.is_encash and self.encashment_threshold_days and self.encashment_threshold_days <= 0:
            frappe.throw(_("Encashment Threshold Days should be greater than 0"))
        
        # Validate fraction day
        if self.allow_fraction_day and (not self.minimum_fraction_day or self.minimum_fraction_day <= 0):
            frappe.throw(_("Minimum Fraction Day should be greater than 0"))
        
        # Validate paid leave
        if self.is_lwp and self.is_ppl:
            frappe.throw(_("Leave Type cannot be both LWP (Leave Without Pay) and PPL (Partially Paid Leave)"))
