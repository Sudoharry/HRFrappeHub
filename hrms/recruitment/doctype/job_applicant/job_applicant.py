# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url, now_datetime
import re

class JobApplicant(Document):
    def validate(self):
        self.validate_email()
        self.validate_name()
        self.validate_phone()
        self.validate_job_opening()
    
    def validate_email(self):
        if self.email:
            # Use email validation pattern
            valid_email = re.match(r"[^@]+@[^@]+\.[^@]+", self.email)
            if not valid_email:
                frappe.throw(_("Please enter a valid email address"))
                
            # Check for duplicate email
            if not self.is_new():
                return
                
            duplicate = frappe.db.exists("Job Applicant", {
                "email": self.email,
                "name": ["!=", self.name]
            })
            
            if duplicate:
                frappe.throw(_("Email {0} already exists in another application").format(self.email))
    
    def validate_name(self):
        if not self.applicant_name:
            frappe.throw(_("Applicant name is required"))
    
    def validate_phone(self):
        if self.phone and not self.phone.isdigit():
            frappe.throw(_("Phone number should contain only digits"))
    
    def validate_job_opening(self):
        if self.job_title:
            # Check if job opening exists and is open
            job = frappe.db.get_value("Job Opening", {"job_title": self.job_title}, 
                ["status", "application_end_date"], as_dict=True)
                
            if not job:
                frappe.throw(_("Job Opening {0} does not exist").format(self.job_title))
                
            if job.status == "Closed":
                frappe.throw(_("Applications are closed for {0}").format(self.job_title))
                
            if job.application_end_date and now_datetime().date() > job.application_end_date:
                frappe.throw(_("Application deadline has passed for {0}").format(self.job_title))
    
    def on_update(self):
        # Send notifications based on status changes
        self.notify_status_change()
    
    def notify_status_change(self):
        """Send notifications based on status changes"""
        if self.get("__islocal") or not self.has_value_changed("status"):
            return
            
        if self.email:
            if self.status == "Accepted":
                self.send_applicant_email("Application Accepted", 
                    _("Congratulations! Your application has been accepted."))
            elif self.status == "Rejected":
                self.send_applicant_email("Application Status", 
                    _("Thank you for your interest. We have decided to proceed with other candidates."))
            elif self.status == "Open":
                self.send_applicant_email("Application Received", 
                    _("Thank you for your application. We have received it and will review it shortly."))
            elif self.status == "Replied":
                # No email - recruiter has already communicated with the applicant
                pass
            elif self.status == "Hold":
                self.send_applicant_email("Application Status", 
                    _("Your application is currently on hold. We will get back to you soon."))
    
    def send_applicant_email(self, subject, message):
        """Send email to applicant"""
        frappe.sendmail(
            recipients=[self.email],
            subject=subject,
            message=message,
            reference_doctype=self.doctype,
            reference_name=self.name
        )
    
    def get_interview_details(self):
        """Get interview details for this applicant"""
        return frappe.get_all("Interview", 
            filters={"job_applicant": self.name},
            fields=["name", "scheduled_on", "status", "interviewer", "notes"]
        )
    
    def create_employee(self):
        """Create an employee from this applicant"""
        if self.status != "Accepted":
            frappe.throw(_("Cannot create employee for non-accepted applicant"))
            
        existing_employee = frappe.db.exists("Employee", {"job_applicant": self.name})
        if existing_employee:
            frappe.throw(_("Employee already created for this applicant"))
            
        employee = frappe.new_doc("Employee")
        employee.first_name = self.applicant_name.split(" ")[0] if " " in self.applicant_name else self.applicant_name
        employee.last_name = " ".join(self.applicant_name.split(" ")[1:]) if " " in self.applicant_name else ""
        employee.personal_email = self.email
        employee.company = frappe.db.get_value("Job Opening", {"job_title": self.job_title}, "company")
        employee.job_applicant = self.name
        
        if self.designation:
            employee.designation = self.designation
        else:
            # Get designation from job opening
            employee.designation = frappe.db.get_value("Job Opening", {"job_title": self.job_title}, "designation")
        
        if self.department:
            employee.department = self.department
        else:
            # Get department from job opening
            employee.department = frappe.db.get_value("Job Opening", {"job_title": self.job_title}, "department")
        
        return employee
    
    def schedule_interview(self):
        """Schedule an interview for this applicant"""
        if self.status == "Rejected":
            frappe.throw(_("Cannot schedule interview for rejected applicant"))
            
        return {
            "job_applicant": self.name,
            "applicant_name": self.applicant_name,
            "job_title": self.job_title,
            "designation": self.designation,
            "department": self.department
        }
