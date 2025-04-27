# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate, add_days, add_months

class Appraisal(Document):
    def validate(self):
        self.validate_dates()
        self.validate_existing_appraisal()
        self.calculate_total_score()
    
    def validate_dates(self):
        if self.start_date and self.end_date and getdate(self.end_date) < getdate(self.start_date):
            frappe.throw(_("End Date cannot be before Start Date"))
            
        if self.start_date and getdate(self.start_date) > getdate(nowdate()):
            frappe.throw(_("Start Date cannot be in the future"))
    
    def validate_existing_appraisal(self):
        # Check for overlapping appraisals
        if not self.is_new():
            return
            
        existing = frappe.db.sql("""
            SELECT name FROM `tabAppraisal`
            WHERE employee = %s 
            AND docstatus < 2
            AND name != %s
            AND ((start_date BETWEEN %s AND %s) 
                OR (end_date BETWEEN %s AND %s)
                OR (start_date <= %s AND end_date >= %s))
        """, (self.employee, self.name, self.start_date, self.end_date, 
              self.start_date, self.end_date, self.start_date, self.end_date))
        
        if existing:
            frappe.throw(_("Employee {0} already has an appraisal {1} in this period")
                .format(self.employee_name, existing[0][0]))
    
    def on_submit(self):
        self.update_status()
        self.notify_employee()
    
    def on_cancel(self):
        self.update_status()
    
    def calculate_total_score(self):
        """Calculate total score and weighted score"""
        self.total_score = 0
        self.score = 0
        total_weights = 0
        
        for goal in self.goals:
            if goal.score:
                self.total_score += flt(goal.score)
                
                if goal.weight:
                    self.score += flt(goal.score) * flt(goal.weight) / 100
                    total_weights += flt(goal.weight)
        
        if self.goals:
            self.total_score = self.total_score / len(self.goals)
            
            if total_weights != 100:
                frappe.msgprint(_("Total weight for all goals should be 100%"), indicator="orange")
    
    def update_status(self):
        """Update status based on workflow"""
        status = "Completed" if self.docstatus == 1 else "Draft" if self.docstatus == 0 else "Cancelled"
        
        frappe.db.set_value("Appraisal", self.name, "status", status)
    
    def notify_employee(self):
        """Notify employee about appraisal completion"""
        if self.status == "Completed":
            employee = frappe.get_doc("Employee", self.employee)
            if employee.user_id:
                user = frappe.get_doc("User", employee.user_id)
                subject = _("Appraisal Completed")
                message = _("Your appraisal for the period {0} to {1} has been completed. Overall score: {2}")
                
                frappe.sendmail(
                    recipients=[user.email],
                    subject=subject,
                    message=message.format(
                        frappe.format(self.start_date, {"fieldtype": "Date"}),
                        frappe.format(self.end_date, {"fieldtype": "Date"}),
                        self.score
                    ),
                    reference_doctype=self.doctype,
                    reference_name=self.name
                )
    
    def get_appraisal_template(self):
        """Get goals from appraisal template"""
        if not self.appraisal_template:
            return
            
        template = frappe.get_doc("Appraisal Template", self.appraisal_template)
        
        # Clear goals table
        self.goals = []
        
        # Add goals from template
        for goal in template.goals:
            self.append("goals", {
                "goal": goal.goal,
                "description": goal.description,
                "weight": goal.weight,
                "score": 0
            })
    
    def create_follow_up_appraisal(self):
        """Create follow-up appraisal for next period"""
        if self.status != "Completed":
            frappe.throw(_("Cannot create follow-up for incomplete appraisal"))
            
        # Calculate new period (next quarter)
        new_start_date = add_days(self.end_date, 1)
        new_end_date = add_months(new_start_date, 3)
        
        appraisal = frappe.new_doc("Appraisal")
        appraisal.employee = self.employee
        appraisal.employee_name = self.employee_name
        appraisal.department = self.department
        appraisal.designation = self.designation
        appraisal.appraisal_template = self.appraisal_template
        appraisal.start_date = new_start_date
        appraisal.end_date = new_end_date
        
        # Copy previous goals as a starting point
        for goal in self.goals:
            appraisal.append("goals", {
                "goal": goal.goal,
                "description": goal.description,
                "weight": goal.weight,
                "score": 0,
                "previous_target": goal.target,
                "previous_score": goal.score
            })
        
        return appraisal
    
    def get_employee_previous_appraisals(employee):
        """Get previous appraisals for an employee"""
        appraisals = frappe.get_all(
            "Appraisal",
            filters={"employee": employee, "docstatus": 1},
            fields=["name", "start_date", "end_date", "score", "total_score", "status"],
            order_by="end_date desc"
        )
        
        return appraisals
