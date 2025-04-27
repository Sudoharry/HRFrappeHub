"""
Job Applicant DocType Controller

This module contains the controller for the Job Applicant DocType
which handles business logic and validations.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, validate_email_address

class JobApplicant(Document):
    def validate(self):
        """Validate job applicant"""
        self.validate_email()
        self.validate_employee_creation()
    
    def validate_email(self):
        """Validate email address"""
        if self.email:
            validate_email_address(self.email, throw=True)
    
    def validate_employee_creation(self):
        """An employee can't be created against a rejected or hold applicant"""
        if self.status in ['Rejected', 'Hold'] and self.employee:
            frappe.throw(_("Employee cannot be created for a Rejected or On-Hold applicant"))
    
    def onload(self):
        """Load additional data when the document is loaded"""
        if self.job_opening:
            self.set_onload('job_opening_details', frappe.get_doc("Job Opening", self.job_opening))
    
    def has_permission(self, ptype='read', user=None):
        """Check if user has permission on this document"""
        return super().has_permission(ptype, user)
    
    def after_insert(self):
        """Actions after inserting applicant"""
        # Notify managers
        self.notify_managers_of_new_applicant()
    
    def on_update(self):
        """Track status changes and send notifications"""
        if self.has_value_changed("status"):
            self.handle_status_change()
    
    def handle_status_change(self):
        """Handle actions based on status change"""
        if self.status == "Accepted":
            # Create employee if status is accepted
            self.create_employee()
        elif self.status == "Rejected":
            # Notify applicant of rejection if applicable
            if frappe.db.get_single_value("HR Settings", "send_rejection_notification"):
                self.notify_applicant_of_rejection()
    
    def notify_managers_of_new_applicant(self):
        """Notify managers about new applicant"""
        subject = _("New Job Applicant: {0}").format(self.applicant_name)
        
        if self.job_opening:
            job_title = frappe.db.get_value("Job Opening", self.job_opening, "job_title")
            job_link = frappe.utils.get_link_to_form("Job Opening", self.job_opening)
            subject = _("New Applicant for {0}: {1}").format(job_title, self.applicant_name)
        
        message = _("""
            <p>A new job application has been submitted:</p>
            <ul>
                <li><strong>Applicant:</strong> {0}</li>
                <li><strong>Email:</strong> {1}</li>
                <li><strong>Status:</strong> {2}</li>
        """).format(self.applicant_name, self.email, self.status)
        
        if self.job_opening:
            message += _("<li><strong>Job Opening:</strong> {0}</li>").format(job_link)
        
        message += "</ul>"
        
        # Send notification to HR managers
        hr_managers = frappe.get_all("User", 
            filters={"role": "HR Manager"},
            fields=["email"]
        )
        
        for user in hr_managers:
            if user.email:
                frappe.sendmail(
                    recipients=user.email,
                    subject=subject,
                    message=message,
                    reference_doctype=self.doctype,
                    reference_name=self.name
                )
    
    def notify_applicant_of_rejection(self):
        """Notify applicant about rejection"""
        if not self.email:
            return
            
        subject = _("Update on your application")
        rejection_message = frappe.db.get_single_value("HR Settings", "rejection_message") or _("""
            <p>Thank you for your interest in working with us.</p>
            <p>After careful consideration, we have decided to pursue other candidates for this position.</p>
            <p>We appreciate your time and interest in our company and wish you the best in your job search.</p>
        """)
        
        message = _("""
            <p>Dear {0},</p>
            {1}
            <p>Regards,<br>HR Team</p>
        """).format(self.applicant_name, rejection_message)
        
        frappe.sendmail(
            recipients=self.email,
            subject=subject,
            message=message,
            reference_doctype=self.doctype,
            reference_name=self.name
        )
        
        # Log the email sent
        frappe.db.set_value(self.doctype, self.name, "feedback", 
            (_("Rejection email sent on {0}")).format(frappe.utils.now_datetime().strftime("%Y-%m-%d %H:%M:%S"))
        )
    
    def create_employee(self):
        """Create an employee from job applicant"""
        if self.employee:
            frappe.throw(_("Employee already created"))
            
        # Check if employee with same email already exists
        if self.email and frappe.db.get_value("Employee", {"email": self.email}):
            frappe.throw(_("Employee with email {0} already exists").format(self.email))
        
        # Create a new employee
        employee = frappe.new_doc("Employee")
        employee.first_name = self.applicant_name.split(" ")[0] if " " in self.applicant_name else self.applicant_name
        if " " in self.applicant_name:
            employee.last_name = self.applicant_name.split(" ")[1] if len(self.applicant_name.split(" ")) > 1 else ""
        
        employee.email = self.email
        employee.status = "Active"
        
        if self.job_opening:
            job_opening = frappe.get_doc("Job Opening", self.job_opening)
            if job_opening.department:
                employee.department = job_opening.department
            if job_opening.designation:
                employee.designation = job_opening.designation
                
        employee.date_of_joining = frappe.utils.today()
        
        try:
            employee.insert()
            # Link the employee to the applicant
            self.db_set("employee", employee.name)
            frappe.msgprint(_("Employee {0} created").format(employee.name))
            return employee
        except Exception as e:
            frappe.log_error(str(e), "Employee Creation from Job Applicant Failed")
            frappe.throw(_("Could not create Employee: {0}").format(str(e)))

@frappe.whitelist()
def schedule_interview(job_applicant, interviewer, interview_date, interview_time, interview_round=None):
    """Schedule an interview for a job applicant"""
    if not frappe.has_permission("Job Applicant", "write", job_applicant):
        frappe.throw(_("Not permitted to schedule interview"))
        
    # Get the applicant details
    applicant = frappe.get_doc("Job Applicant", job_applicant)
    
    # Create a new interview
    interview = frappe.new_doc("Interview")
    interview.job_applicant = job_applicant
    interview.applicant_name = applicant.applicant_name
    interview.interviewer = interviewer
    interview.interview_date = interview_date
    interview.interview_time = interview_time
    
    if interview_round:
        interview.interview_round = interview_round
        
    if applicant.job_opening:
        interview.job_opening = applicant.job_opening
        
    interview.status = "Scheduled"
    
    interview.insert()
    
    # Update applicant's interview round
    if interview_round:
        applicant.db_set("interview_round", interview_round)
        
    applicant.db_set("hiring_status", "In Process")
    
    return interview.name

@frappe.whitelist()
def get_applicant_summary(job_applicant):
    """Get summary of applicant for dashboard"""
    if not frappe.has_permission("Job Applicant", "read", job_applicant):
        frappe.throw(_("Not permitted to view applicant details"))
    
    applicant = frappe.get_doc("Job Applicant", job_applicant)
    
    # Get interviews
    interviews = frappe.get_all("Interview", 
        filters={"job_applicant": job_applicant},
        fields=["name", "interview_round", "interview_date", "status", "interviewer"],
        order_by="interview_date desc"
    )
    
    job_opening_details = None
    if applicant.job_opening:
        job_opening_details = frappe.get_doc("Job Opening", applicant.job_opening, 
            fields=["job_title", "department", "designation", "status"]
        )
    
    return {
        "applicant": {
            "name": applicant.name,
            "applicant_name": applicant.applicant_name,
            "email": applicant.email,
            "status": applicant.status,
            "hiring_status": applicant.hiring_status or "Not Evaluated",
            "rating": applicant.rating or 0
        },
        "job_opening": job_opening_details,
        "interviews": interviews,
        "employee": frappe.get_doc("Employee", applicant.employee, fields=["name", "employee_name", "status"]) if applicant.employee else None
    }