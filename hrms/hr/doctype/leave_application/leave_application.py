# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import date_diff, add_days, getdate, cint, format_date
from frappe.model.document import Document

class LeaveApplication(Document):
    def validate(self):
        self.validate_leave_type()
        self.validate_dates()
        self.validate_balance_leaves()
        self.validate_leave_overlap()
        self.validate_holidays()
        self.validate_attendance()
        self.validate_half_day()
        
        if frappe.db.get_value("Leave Type", self.leave_type, "is_lwp"):
            self.calculate_lwp_days()
    
    def on_submit(self):
        self.update_attendance()
        self.update_leave_allocation()
        self.notify_employee()
    
    def on_cancel(self):
        self.update_attendance(cancel=True)
        self.update_leave_allocation(cancel=True)
        self.notify_employee(cancelled=True)
    
    def validate_leave_type(self):
        if not frappe.db.exists("Leave Type", self.leave_type):
            frappe.throw(_("Leave Type {0} does not exist").format(self.leave_type))
            
        # Check if leave type is active
        if not frappe.db.get_value("Leave Type", self.leave_type, "is_active"):
            frappe.throw(_("Leave Type {0} is not active").format(self.leave_type))
    
    def validate_dates(self):
        if self.from_date and self.to_date:
            if getdate(self.to_date) < getdate(self.from_date):
                frappe.throw(_("To date cannot be before from date"))
                
            if getdate(self.from_date) < getdate():
                if not frappe.db.get_value("Leave Type", self.leave_type, "allow_backdated_application"):
                    frappe.throw(_("Leave application can only be for future dates"))
                
            # Check against joining date
            joining_date, relieving_date = frappe.db.get_value("Employee", self.employee, 
                ["date_of_joining", "relieving_date"])
                
            if getdate(self.from_date) < getdate(joining_date):
                frappe.throw(_("From date cannot be before employee's joining date"))
                
            if relieving_date and getdate(self.to_date) > getdate(relieving_date):
                frappe.throw(_("To date cannot be after employee's relieving date"))
    
    def validate_balance_leaves(self):
        if self.from_date and self.to_date:
            self.total_leave_days = self.get_leave_days()
            
            allocation = self.get_leave_allocation()
            if allocation:
                # Get leave balance
                self.leave_balance = allocation.total_leaves_allocated - allocation.total_leaves_taken
                
                if self.total_leave_days > self.leave_balance:
                    if frappe.db.get_value("Leave Type", self.leave_type, "allow_negative"):
                        frappe.msgprint(_("Note: The leave balance of {0} days for {1} is less than the requested {2} days")
                            .format(self.leave_balance, self.leave_type, self.total_leave_days))
                    else:
                        frappe.throw(_("The leave balance of {0} days for {1} is less than the requested {2} days")
                            .format(self.leave_balance, self.leave_type, self.total_leave_days))
            else:
                frappe.throw(_("No leave allocation found for employee {0} for leave type {1}")
                    .format(self.employee_name, self.leave_type))
    
    def validate_leave_overlap(self):
        if self.from_date and self.to_date:
            existing_leave = frappe.db.sql("""
                SELECT name, leave_type, posting_date, from_date, to_date, total_leave_days, half_day_date
                FROM `tabLeave Application`
                WHERE employee = %s AND docstatus < 2 AND name != %s
                AND status != "Rejected"
                AND (from_date BETWEEN %s AND %s OR to_date BETWEEN %s AND %s)
            """, (self.employee, self.name, self.from_date, self.to_date, self.from_date, self.to_date), as_dict=True)
            
            if existing_leave:
                for leave in existing_leave:
                    if (getdate(self.half_day_date) == getdate(leave.half_day_date) and 
                        getdate(self.from_date) == getdate(leave.from_date) and 
                        getdate(self.to_date) == getdate(leave.to_date) and 
                        self.half_day == 1 and leave.half_day == 1):
                        frappe.throw(_("Employee {0} already has a half-day leave application {1} with date {2}")
                            .format(self.employee_name, leave.name, format_date(leave.half_day_date)))
                    else:
                        frappe.throw(_("Employee {0} already has a leave application {1} with overlapping dates")
                            .format(self.employee_name, leave.name))
    
    def validate_holidays(self):
        if self.from_date and self.to_date:
            holiday_list = get_holiday_list_for_employee(self.employee)
            if holiday_list:
                holidays = frappe.get_all("Holiday", fields=["holiday_date", "description"],
                    filters={"parent": holiday_list, "holiday_date": ["between", [self.from_date, self.to_date]]})
                    
                if holidays:
                    holiday_dates = [holiday.holiday_date for holiday in holidays]
                    if not frappe.db.get_value("Leave Type", self.leave_type, "include_holiday"):
                        total_holidays = len(holiday_dates)
                        if self.total_leave_days == total_holidays:
                            frappe.throw(_("The leave period falls entirely on holidays"))
                        
                        self.total_leave_days -= total_holidays
                        if self.total_leave_days < 0:
                            self.total_leave_days = 0
                        
                        # Notify about holidays
                        holiday_descriptions = ["{0}: {1}".format(format_date(holiday.holiday_date), holiday.description) 
                            for holiday in holidays]
                        frappe.msgprint(_("The following holidays are within the selected leave period:<br>{0}")
                            .format("<br>".join(holiday_descriptions)))
    
    def validate_attendance(self):
        if self.from_date and self.to_date:
            attendance = frappe.db.sql("""
                SELECT name, attendance_date, status
                FROM `tabAttendance`
                WHERE employee = %s AND attendance_date BETWEEN %s AND %s
                AND docstatus = 1
            """, (self.employee, self.from_date, self.to_date), as_dict=True)
            
            if attendance:
                for record in attendance:
                    if record.status in ["Present", "Half Day"]:
                        frappe.throw(_("Employee {0} already has an attendance record {1} with status {2} on {3}")
                            .format(self.employee_name, record.name, record.status, format_date(record.attendance_date)))
    
    def validate_half_day(self):
        if self.half_day:
            if not self.half_day_date:
                frappe.throw(_("Half Day Date is mandatory"))
            
            if not (getdate(self.from_date) <= getdate(self.half_day_date) <= getdate(self.to_date)):
                frappe.throw(_("Half Day Date {0} should be between From Date {1} and To Date {2}")
                    .format(format_date(self.half_day_date), format_date(self.from_date), format_date(self.to_date)))
    
    def calculate_lwp_days(self):
        # LWP (Leave Without Pay) days calculation
        self.lwp_days = self.total_leave_days
    
    def get_leave_days(self):
        if not (self.from_date and self.to_date):
            return 0
            
        total_days = date_diff(self.to_date, self.from_date) + 1
        
        if self.half_day:
            total_days -= 0.5
        
        return total_days
    
    def get_leave_allocation(self):
        allocation = frappe.db.sql("""
            SELECT name, total_leaves_allocated, total_leaves_taken
            FROM `tabLeave Allocation`
            WHERE employee = %s AND leave_type = %s
            AND %s BETWEEN from_date AND to_date
            AND docstatus = 1
        """, (self.employee, self.leave_type, self.from_date), as_dict=True)
        
        return allocation[0] if allocation else None
    
    def update_attendance(self, cancel=False):
        # Mark attendance as On Leave or delete attendance if leave is cancelled
        for dt in frappe.date_range(self.from_date, self.to_date):
            date = dt.strftime("%Y-%m-%d")
            attendance = frappe.db.exists("Attendance", {
                "employee": self.employee,
                "attendance_date": date,
                "docstatus": 1
            })
            
            if cancel:
                if attendance:
                    # Delete attendance on cancel
                    attend_doc = frappe.get_doc("Attendance", attendance)
                    attend_doc.cancel()
                    attend_doc.delete()
            else:
                if not attendance:
                    # Create attendance with On Leave status
                    attend = frappe.new_doc("Attendance")
                    attend.employee = self.employee
                    attend.employee_name = self.employee_name
                    attend.attendance_date = date
                    attend.status = "On Leave"
                    attend.leave_type = self.leave_type
                    attend.leave_application = self.name
                    attend.company = frappe.db.get_value("Employee", self.employee, "company")
                    attend.flags.ignore_validate = True
                    attend.insert(ignore_permissions=True)
                    attend.submit()
    
    def update_leave_allocation(self, cancel=False):
        allocation = self.get_leave_allocation()
        if allocation:
            # Update leave allocation
            if cancel:
                # Add back leaves if leave is cancelled
                new_total_leaves_taken = allocation.total_leaves_taken - self.total_leave_days
            else:
                # Deduct leaves when leave is approved
                new_total_leaves_taken = allocation.total_leaves_taken + self.total_leave_days
                
            frappe.db.set_value("Leave Allocation", allocation.name, "total_leaves_taken", 
                new_total_leaves_taken if new_total_leaves_taken > 0 else 0)
    
    def notify_employee(self, cancelled=False):
        if self.status == "Approved" or cancelled:
            # Notify employee about leave approval or cancellation
            message = _("Your leave application for {0} from {1} to {2} has been {3}").format(
                self.leave_type, format_date(self.from_date), format_date(self.to_date),
                _("cancelled") if cancelled else _("approved")
            )
            
            # Get employee email
            employee_user_id = frappe.db.get_value("Employee", self.employee, "user_id")
            if employee_user_id:
                email = frappe.db.get_value("User", employee_user_id, "email")
                if email:
                    frappe.sendmail(
                        recipients=[email],
                        subject=_("Leave Application - {0}").format(_("Cancelled") if cancelled else _("Approved")),
                        message=message,
                        reference_doctype=self.doctype,
                        reference_name=self.name
                    )
    
    def update_leave_status(date=None):
        """Update the status of leave applications based on the current date"""
        if not date:
            date = getdate()
            
        # Update leave applications that have expired (all days are in the past)
        frappe.db.sql("""
            UPDATE `tabLeave Application` 
            SET status = 'Completed' 
            WHERE status = 'Approved' AND to_date < %s AND docstatus = 1
        """, (date))
        
        # Update leave applications that are currently active (current date is within the leave period)
        frappe.db.sql("""
            UPDATE `tabLeave Application` 
            SET status = 'Active' 
            WHERE status = 'Approved' AND from_date <= %s AND to_date >= %s AND docstatus = 1
        """, (date, date))

def get_holiday_list_for_employee(employee):
    holiday_list = frappe.db.get_value("Employee", employee, "holiday_list")
    if not holiday_list:
        # Get default holiday list from company
        company = frappe.db.get_value("Employee", employee, "company")
        holiday_list = frappe.db.get_value("Company", company, "default_holiday_list")
    
    return holiday_list

def get_permission_query_conditions(user):
    if not user: user = frappe.session.user
    
    # HR Manager can see all leave applications
    if "HR Manager" in frappe.get_roles(user):
        return ""
    
    # HR User can see all leave applications
    if "HR User" in frappe.get_roles(user):
        return ""
    
    # Employee can only see their own leave applications
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if employee:
        return '(`tabLeave Application`.employee = {0})'.format(frappe.db.escape(employee))
    
    # Leave approver can see leave applications that they need to approve
    leave_applications = frappe.get_all(
        "Leave Application",
        filters={"leave_approver": user},
        fields=["name"]
    )
    
    if leave_applications:
        names = ['" "'] + ['"' + la.name + '"' for la in leave_applications]
        return '(`tabLeave Application`.name IN ({0}) OR `tabLeave Application`.leave_approver = {1})'.format(
            ", ".join(names), frappe.db.escape(user))
    
    return '1=0'

def has_permission(doc, user):
    # HR Manager can see all leave applications
    if "HR Manager" in frappe.get_roles(user):
        return True
    
    # HR User can see all leave applications
    if "HR User" in frappe.get_roles(user):
        return True
    
    # Employee can only see their own leave applications
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if employee and employee == doc.employee:
        return True
    
    # Leave approver can see leave applications that they need to approve
    if user == doc.leave_approver:
        return True
    
    return False
