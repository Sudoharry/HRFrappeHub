"""
Job Opening DocType Controller

This module contains the controller for the Job Opening DocType
which handles business logic and validations.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.website.website_generator import WebsiteGenerator
from frappe.utils import getdate, now_datetime

class JobOpening(Document):
    def validate(self):
        """Validate job opening"""
        self.validate_application_deadline()
        self.validate_min_max_salary()
        
        # If the job opening is closed, you can't publish it on the website
        if self.status == "Closed" and self.publish:
            self.publish = 0
            frappe.msgprint(_("Automatically unpublished the Job Opening as it is now closed"))
    
    def validate_application_deadline(self):
        """Validate application deadline"""
        if self.application_deadline:
            # Application deadline cannot be in the past
            if getdate(self.application_deadline) < getdate(now_datetime()):
                frappe.throw(_("Application Deadline cannot be in the past"))
    
    def validate_min_max_salary(self):
        """Validate min and max salary"""
        if self.min_salary and self.max_salary:
            if self.min_salary > self.max_salary:
                frappe.throw(_("Minimum Salary cannot be greater than Maximum Salary"))
    
    def on_update(self):
        """On update actions"""
        # Update related documents or perform any other actions when the job opening is updated
        pass
    
    def has_permission(self, ptype='read', user=None):
        """Check if user has permission on this document"""
        # Everyone can read published job openings
        if ptype == 'read' and self.publish:
            return True
        
        # For other actions, use standard permission system
        return super().has_permission(ptype, user)

def get_list_context(context=None):
    """Get context for list view on website"""
    context.update({
        "title": _("Job Openings"),
        "introduction": _("Current job openings"),
        "get_list": get_published_job_openings,
        "row_template": "hrms/templates/includes/job_opening_row.html",
        "show_sidebar": True,
        "show_search": True,
        "no_breadcrumbs": True
    })
    return context

def get_published_job_openings(doctype, txt=None, filters=None, limit_start=0, limit_page_length=20, order_by=None):
    """Get list of published job openings for website"""
    return frappe.get_all("Job Opening",
        filters={
            "status": "Open",
            "publish": 1,
            "application_deadline": [">=", getdate(now_datetime())]
        },
        fields=["name", "job_title", "department", "designation", "application_deadline", "description"],
        limit_start=limit_start,
        limit_page_length=limit_page_length,
        order_by="application_deadline asc" if not order_by else order_by
    )

@frappe.whitelist(allow_guest=True)
def apply_for_job(job_opening, applicant_name, email, cover_letter=None, resume=None):
    """API for applying to a job opening from website"""
    # Validate required fields
    if not job_opening or not applicant_name or not email:
        return {"status": "error", "message": _("Missing required fields")}
    
    # Check if job opening exists and is open
    job = frappe.get_doc("Job Opening", job_opening)
    if job.status != "Open" or not job.publish:
        return {"status": "error", "message": _("This job opening is not accepting applications")}
    
    # Check if application deadline has passed
    if job.application_deadline and getdate(job.application_deadline) < getdate(now_datetime()):
        return {"status": "error", "message": _("Application deadline has passed")}
    
    # Create a new job applicant
    try:
        applicant = frappe.new_doc("Job Applicant")
        applicant.applicant_name = applicant_name
        applicant.email = email
        applicant.job_opening = job_opening
        applicant.status = "Open"
        
        if cover_letter:
            applicant.cover_letter = cover_letter
        
        if resume:
            # Handle resume upload if provided
            # This would need to use Frappe's file attachment APIs
            pass
        
        applicant.insert(ignore_permissions=True)
        
        # Send notification to HR
        notify_hr_about_new_applicant(applicant)
        
        return {
            "status": "success", 
            "message": _("Your application has been submitted successfully"),
            "applicant_id": applicant.name
        }
    except Exception as e:
        frappe.log_error(str(e), "Job Application Error")
        return {"status": "error", "message": _("An error occurred while submitting your application")}

def notify_hr_about_new_applicant(applicant):
    """Send notification to HR team about new applicant"""
    subject = _("New Job Application for {0}").format(applicant.job_opening)
    message = _("""
        <p>A new job application has been submitted:</p>
        <ul>
            <li><strong>Job Opening:</strong> {0}</li>
            <li><strong>Applicant:</strong> {1}</li>
            <li><strong>Email:</strong> {2}</li>
        </ul>
        <p>Please review the application at your earliest convenience.</p>
    """).format(applicant.job_opening, applicant.applicant_name, applicant.email)
    
    # Send notification to HR users
    hr_users = frappe.get_all("User", 
        filters={"role": "HR User"},
        fields=["email"]
    )
    
    for user in hr_users:
        if user.email:
            frappe.sendmail(
                recipients=user.email,
                subject=subject,
                message=message,
                reference_doctype="Job Applicant",
                reference_name=applicant.name
            )