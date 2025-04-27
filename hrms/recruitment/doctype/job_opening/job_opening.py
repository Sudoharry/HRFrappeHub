# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, getdate, nowdate
from frappe.website.website_generator import WebsiteGenerator

class JobOpening(WebsiteGenerator):
    website = frappe._dict(
        template = "templates/generators/job_opening.html",
        condition_field = "publish",
        page_title_field = "job_title",
    )
    
    def validate(self):
        if not self.route:
            self.route = "jobs/" + self.scrub(self.job_title)
            
        self.validate_dates()
        self.update_status()
    
    def validate_dates(self):
        if self.application_end_date and getdate(self.application_end_date) < getdate(nowdate()):
            frappe.throw(_("Application End Date cannot be in the past"))
            
        if self.application_end_date and self.starting_date and getdate(self.application_end_date) > getdate(self.starting_date):
            frappe.throw(_("Application End Date cannot be after Starting Date"))
    
    def update_status(self):
        if self.application_end_date and getdate(self.application_end_date) < getdate(nowdate()):
            self.status = "Closed"
        elif self.status == "Closed" and (not self.application_end_date or getdate(self.application_end_date) >= getdate(nowdate())):
            self.status = "Open"
    
    def on_update(self):
        self.update_website_meta()
    
    def update_website_meta(self):
        # Update website metadata for SEO
        self.meta_title = self.job_title
        self.meta_description = self.description[:160] if self.description else ""
        self.meta_keywords = ", ".join([self.job_title, self.designation, self.department, self.company])
    
    def get_context(self, context):
        context.parents = [{"name": _("Jobs"), "route": "jobs"}]
        
        # Add job details to context
        context.job = self
        return context
    
    def get_applicants(self):
        """Get applicants for this job opening"""
        return frappe.get_all("Job Applicant", 
            filters={
                "job_title": self.job_title,
                "status": ["not in", ["Rejected", "Withdrawn"]]
            },
            fields=["name", "applicant_name", "status", "creation"]
        )
    
    def create_website_page(self):
        """Create website page for this job opening"""
        if not self.publish:
            return
            
        # In a real implementation, this might create webpage, route, etc.
        # For Frappe framework, route handling is done by the website_generator
        frappe.msgprint(_("Job opening published on website"))
    
    def close_job_opening(self):
        """Close this job opening"""
        self.status = "Closed"
        self.save()
    
    def reopen_job_opening(self):
        """Reopen this job opening"""
        self.status = "Open"
        self.save()
    
    def notify_department_head(self):
        """Notify department head about new job opening"""
        if not self.department:
            return
            
        department_head = frappe.db.get_value("Department", self.department, "department_head")
        if department_head:
            # Get user ID for department head
            employee = frappe.db.get_value("Employee", {"name": department_head}, "user_id")
            if employee:
                frappe.sendmail(
                    recipients=[employee],
                    subject=_("New Job Opening: {0}").format(self.job_title),
                    message=_("A new job opening has been created under your department: {0}").format(self.job_title),
                    reference_doctype=self.doctype,
                    reference_name=self.name
                )
