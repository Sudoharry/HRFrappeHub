from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta, date
import random
import calendar
import json

# Create the app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("FLASK_SECRET_KEY") or "your-secret-key"  # Replace with a secure key in production

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize database
db = SQLAlchemy(app)

# Login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize Frappe compatibility layer
from frappe_init import init_frappe_compat
app = init_frappe_compat(app, db)

# Import Frappe-like functions
from frappe_compat import (
    get_doc, new_doc, get_all, db_get_value, db_count,
    whitelist, has_permission, msgprint, get_messages,
    create_response, FrappeJSONEncoder
)

# Set JSON encoder to handle dates and other special types
app.json_encoder = FrappeJSONEncoder

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(512))  # Increased length for password hash
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    role = db.Column(db.String(80))  # 'Employee', 'HR Manager', 'Administrator'
    
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Frappe hooks
    def after_insert(self):
        """Hook that runs after inserting a new user"""
        from hooks import trigger_hook
        trigger_hook('User', 'after_insert', self)
    
    def on_update(self):
        """Hook that runs after updating a user"""
        from hooks import trigger_hook
        trigger_hook('User', 'on_update', self)
    
    def before_delete(self):
        """Hook that runs before deleting a user"""
        from hooks import trigger_hook
        trigger_hook('User', 'before_delete', self)
    
    def has_permission(self, user, ptype='read'):
        """Check if user has permission on this document"""
        from hooks import check_role_permissions
        
        # Admin can do anything
        if user.role == 'Administrator':
            return True
        
        # Check role permissions
        return check_role_permissions(user, 'User', ptype)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80))
    email = db.Column(db.String(120))
    status = db.Column(db.String(20), default='Active')  # Active, Inactive, On Leave, Terminated
    gender = db.Column(db.String(10))
    date_of_birth = db.Column(db.Date)
    date_of_joining = db.Column(db.Date)
    department = db.Column(db.String(80))
    designation = db.Column(db.String(80))
    reports_to = db.Column(db.Integer, db.ForeignKey('employee.id'))
    company = db.Column(db.String(80))
    
    @property
    def employee_name(self):
        return f"{self.first_name} {self.last_name if self.last_name else ''}"
    
    # Frappe hooks
    def validate(self):
        """Validate employee data"""
        # Example validation: ensure employee_id is not empty
        if not self.employee_id:
            raise ValueError("Employee ID is required")
    
    def after_insert(self):
        """Hook that runs after inserting a new employee"""
        from hooks import trigger_hook
        trigger_hook('Employee', 'after_insert', self)
    
    def on_update(self):
        """Hook that runs after updating an employee"""
        from hooks import trigger_hook
        trigger_hook('Employee', 'on_update', self)
    
    def before_delete(self):
        """Hook that runs before deleting an employee"""
        from hooks import trigger_hook
        trigger_hook('Employee', 'before_delete', self)
    
    def has_permission(self, user, ptype='read'):
        """Check if user has permission on this document"""
        from hooks import check_role_permissions
        
        # Admin can do anything
        if user.role == 'Administrator':
            return True
        
        # HR Manager can do anything with employees
        if user.role == 'HR Manager':
            return True
        
        # Users can read their own employee records
        if ptype == 'read' and self.user_id == user.id:
            return True
        
        # Check role permissions
        return check_role_permissions(user, 'Employee', ptype)

class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    department_head = db.Column(db.Integer, db.ForeignKey('employee.id'))

    # Frappe hooks
    def validate(self):
        """Validate department data"""
        pass
    
    def on_update(self):
        """Hook that runs after updating a department"""
        from hooks import trigger_hook
        trigger_hook('Department', 'on_update', self)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # Present, Absent, Half Day, On Leave
    check_in = db.Column(db.DateTime)
    check_out = db.Column(db.DateTime)
    working_hours = db.Column(db.Float)
    
    employee = db.relationship('Employee', backref='attendance')
    
    # Frappe hooks
    def validate(self):
        """Validate attendance data"""
        # Example validation: ensure dates are valid
        if self.check_in and self.check_out and self.check_in > self.check_out:
            raise ValueError("Check-out time cannot be earlier than check-in time")
    
    def on_submit(self):
        """Hook that runs when attendance is submitted"""
        from hooks import trigger_hook
        trigger_hook('Attendance', 'on_submit', self)
    
    def has_permission(self, user, ptype='read'):
        """Check if user has permission on this document"""
        from hooks import check_role_permissions
        
        # Admin can do anything
        if user.role == 'Administrator':
            return True
        
        # HR Manager can do anything with attendance
        if user.role == 'HR Manager':
            return True
        
        # Users can read their own attendance
        if ptype == 'read':
            employee = Employee.query.filter_by(user_id=user.id).first()
            if employee and self.employee_id == employee.id:
                return True
        
        # Check role permissions
        return check_role_permissions(user, 'Attendance', ptype)

class LeaveType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    max_days_allowed = db.Column(db.Integer)
    is_paid_leave = db.Column(db.Boolean, default=True)

class LeaveApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    leave_type_id = db.Column(db.Integer, db.ForeignKey('leave_type.id'), nullable=False)
    from_date = db.Column(db.Date, nullable=False)
    to_date = db.Column(db.Date, nullable=False)
    total_leave_days = db.Column(db.Float)
    status = db.Column(db.String(20), default='Open')  # Open, Approved, Rejected
    reason = db.Column(db.Text)
    
    employee = db.relationship('Employee', backref='leave_applications')
    leave_type = db.relationship('LeaveType')
    
    # Frappe hooks
    def validate(self):
        """Validate leave application"""
        # Example validation: ensure dates are valid
        if self.from_date > self.to_date:
            raise ValueError("To Date cannot be before From Date")
        
        # Calculate total leave days if not set
        if not self.total_leave_days:
            delta = self.to_date - self.from_date
            self.total_leave_days = delta.days + 1
    
    def on_submit(self):
        """Hook that runs when leave application is submitted"""
        from hooks import trigger_hook
        trigger_hook('Leave Application', 'on_submit', self)
    
    def on_cancel(self):
        """Hook that runs when leave application is cancelled"""
        from hooks import trigger_hook
        trigger_hook('Leave Application', 'on_cancel', self)
    
    def has_permission(self, user, ptype='read'):
        """Check if user has permission on this document"""
        from hooks import check_role_permissions
        
        # Admin can do anything
        if user.role == 'Administrator':
            return True
        
        # HR Manager can do anything with leave applications
        if user.role == 'HR Manager':
            return True
        
        # Users can read/write their own leave applications
        if ptype in ['read', 'write', 'create']:
            employee = Employee.query.filter_by(user_id=user.id).first()
            if employee and self.employee_id == employee.id:
                return True
        
        # Check role permissions
        return check_role_permissions(user, 'Leave Application', ptype)

class SalaryStructure(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    from_date = db.Column(db.Date)
    base_amount = db.Column(db.Float)

class SalarySlip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    salary_structure_id = db.Column(db.Integer, db.ForeignKey('salary_structure.id'))
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    posting_date = db.Column(db.Date)
    total_working_days = db.Column(db.Integer)
    gross_pay = db.Column(db.Float)
    total_deduction = db.Column(db.Float)
    net_pay = db.Column(db.Float)
    status = db.Column(db.String(20))  # Draft, Submitted, Cancelled
    
    employee = db.relationship('Employee', backref='salary_slips')
    salary_structure = db.relationship('SalaryStructure')
    
    # Frappe hooks
    def validate(self):
        """Validate salary slip data"""
        # Example validation: ensure dates are valid
        if self.start_date > self.end_date:
            raise ValueError("End Date cannot be before Start Date")
    
    def on_submit(self):
        """Hook that runs when salary slip is submitted"""
        from hooks import trigger_hook
        trigger_hook('Salary Slip', 'on_submit', self)
    
    def has_permission(self, user, ptype='read'):
        """Check if user has permission on this document"""
        from hooks import check_role_permissions
        
        # Admin can do anything
        if user.role == 'Administrator':
            return True
        
        # HR Manager can do anything with salary slips
        if user.role == 'HR Manager':
            return True
        
        # Users can read their own salary slips
        if ptype == 'read':
            employee = Employee.query.filter_by(user_id=user.id).first()
            if employee and self.employee_id == employee.id:
                return True
        
        # Check role permissions
        return check_role_permissions(user, 'Salary Slip', ptype)

class JobOpening(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_title = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), default='Open')  # Open, Closed
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    publish = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text)
    
    department = db.relationship('Department')

class JobApplicant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_opening_id = db.Column(db.Integer, db.ForeignKey('job_opening.id'))
    applicant_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    status = db.Column(db.String(20), default='Open')  # Open, Replied, Rejected, Hold
    resume = db.Column(db.String(255))
    cover_letter = db.Column(db.Text)
    
    job_opening = db.relationship('JobOpening', backref='applicants')

class Appraisal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='Draft')  # Draft, Submitted, Completed, Cancelled
    score = db.Column(db.Float)
    feedback = db.Column(db.Text)
    
    employee = db.relationship('Employee', backref='appraisals')
    
    # Frappe hooks
    def validate(self):
        """Validate appraisal data"""
        # Example validation: ensure dates are valid
        if self.start_date > self.end_date:
            raise ValueError("End Date cannot be before Start Date")
    
    def on_submit(self):
        """Hook that runs when appraisal is submitted"""
        from hooks import trigger_hook
        trigger_hook('Appraisal', 'on_submit', self)
    
    def has_permission(self, user, ptype='read'):
        """Check if user has permission on this document"""
        from hooks import check_role_permissions
        
        # Admin can do anything
        if user.role == 'Administrator':
            return True
        
        # HR Manager can do anything with appraisals
        if user.role == 'HR Manager':
            return True
        
        # Users can read their own appraisals
        if ptype == 'read':
            employee = Employee.query.filter_by(user_id=user.id).first()
            if employee and self.employee_id == employee.id:
                return True
        
        # Check role permissions
        return check_role_permissions(user, 'Appraisal', ptype)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def add_test_data():
    # Add some initial data for testing if the database is empty
    if User.query.count() == 0:
        # Add admin user
        admin = User(username='admin', email='admin@example.com', first_name='Admin', last_name='User', role='Administrator')
        admin.password = 'admin123'
        db.session.add(admin)
        
        # Add HR Manager
        hr_manager = User(username='hrmanager', email='hr@example.com', first_name='HR', last_name='Manager', role='HR Manager')
        hr_manager.password = 'hr123'
        db.session.add(hr_manager)
        
        # Add employee user
        employee_user = User(username='employee', email='employee@example.com', first_name='John', last_name='Doe', role='Employee')
        employee_user.password = 'emp123'
        db.session.add(employee_user)
        
        db.session.commit()
        
        # Add departments
        dept1 = Department(name='HR')
        dept2 = Department(name='IT')
        dept3 = Department(name='Finance')
        db.session.add_all([dept1, dept2, dept3])
        db.session.commit()
        
        # Add employees
        emp1 = Employee(
            employee_id='EMP-0001',
            user_id=employee_user.id,
            first_name='John',
            last_name='Doe',
            email='employee@example.com',
            status='Active',
            gender='Male',
            date_of_birth=date(1985, 5, 15),
            date_of_joining=date(2020, 1, 10),
            department='IT',
            designation='Software Developer',
            company='Our Company'
        )
        
        emp2 = Employee(
            employee_id='EMP-0002',
            first_name='Jane',
            last_name='Smith',
            email='jane@example.com',
            status='Active',
            gender='Female',
            date_of_birth=date(1990, 8, 22),
            date_of_joining=date(2021, 3, 5),
            department='HR',
            designation='HR Assistant',
            company='Our Company'
        )
        
        db.session.add_all([emp1, emp2])
        db.session.commit()
        
        # Add leave types
        leave_type1 = LeaveType(name='Casual Leave', max_days_allowed=10, is_paid_leave=True)
        leave_type2 = LeaveType(name='Sick Leave', max_days_allowed=7, is_paid_leave=True)
        leave_type3 = LeaveType(name='Unpaid Leave', max_days_allowed=30, is_paid_leave=False)
        
        db.session.add_all([leave_type1, leave_type2, leave_type3])
        db.session.commit()
        
        # Add salary structures
        salary_structure = SalaryStructure(
            name='Standard Employee',
            is_active=True,
            from_date=date(2022, 1, 1),
            base_amount=50000.0
        )
        
        db.session.add(salary_structure)
        db.session.commit()
        
        # Add job openings
        job1 = JobOpening(
            job_title='Senior Developer',
            status='Open',
            department_id=dept2.id,
            publish=True,
            description='We are looking for an experienced senior developer to join our team.'
        )
        
        job2 = JobOpening(
            job_title='HR Executive',
            status='Open',
            department_id=dept1.id,
            publish=True,
            description='We are looking for an HR executive to manage recruitment and employee relations.'
        )
        
        db.session.add_all([job1, job2])
        db.session.commit()
        
        print("Test data added successfully!")

# Routes

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'HR Manager' or current_user.role == 'Administrator':
            return redirect(url_for('hr_dashboard'))
        else:
            return redirect(url_for('employee_portal'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user is not None and user.verify_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            
            if user.role == 'HR Manager' or user.role == 'Administrator':
                return redirect(url_for('hr_dashboard'))
            else:
                return redirect(url_for('employee_portal'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/hr-dashboard')
@login_required
def hr_dashboard():
    if current_user.role != 'HR Manager' and current_user.role != 'Administrator':
        flash('Access denied. You do not have permission to view this page.', 'danger')
        return redirect(url_for('employee_portal'))
    
    # Example of using Frappe-style API
    employee_count = db_count("Employee", {"status": "Active"})
    
    # For other stats, we can continue using the existing SQLAlchemy queries
    # or gradually convert them to use Frappe-style API
    
    return render_template('hr_dashboard.html', 
                           active_page='dashboard',
                           title='HR Dashboard')

@app.route('/employee-portal')
@login_required
def employee_portal():
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    
    if not employee:
        flash('Employee record not found. Please contact HR.', 'warning')
        # Still show the portal but with limited data
    
    return render_template('employee_portal.html', 
                           employee=employee,
                           active_page='dashboard',
                           title='Employee Portal')

@app.route('/apply-leave', methods=['GET', 'POST'])
@login_required
def apply_leave():
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    
    if not employee:
        flash('Employee record not found. You cannot apply for leave.', 'danger')
        return redirect(url_for('employee_portal'))
    
    leave_types = LeaveType.query.all()
    
    if request.method == 'POST':
        # Example of using Frappe-style API
        try:
            leave_application = new_doc("Leave Application")
            leave_application.employee_id = employee.id
            leave_application.leave_type_id = int(request.form.get('leave_type_id'))
            leave_application.from_date = datetime.strptime(request.form.get('from_date'), '%Y-%m-%d').date()
            leave_application.to_date = datetime.strptime(request.form.get('to_date'), '%Y-%m-%d').date()
            leave_application.reason = request.form.get('reason')
            
            # Validate and insert
            leave_application.validate()
            leave_application.insert()
            
            flash('Leave application submitted successfully.', 'success')
            return redirect(url_for('view_leaves'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('apply_leave.html', 
                           employee=employee,
                           leave_types=leave_types,
                           active_page='leaves',
                           title='Apply for Leave')

@app.route('/view-leaves')
@login_required
def view_leaves():
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    
    if not employee:
        flash('Employee record not found.', 'danger')
        return redirect(url_for('employee_portal'))
    
    # Example of using Frappe-style API
    leave_applications = get_all("Leave Application", 
                               filters={"employee_id": employee.id},
                               order_by="from_date desc")
    
    return render_template('leave_applications.html', 
                           leaves=leave_applications,
                           active_page='leaves',
                           title='My Leave Applications')

# Continue with other routes, but gradually convert to use Frappe-style API...

@app.route('/mark-attendance', methods=['GET', 'POST'])
@login_required
def mark_attendance():
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    
    if not employee:
        flash('Employee record not found. You cannot mark attendance.', 'danger')
        return redirect(url_for('employee_portal'))
    
    today = date.today()
    existing_attendance = Attendance.query.filter_by(
        employee_id=employee.id, 
        attendance_date=today
    ).first()
    
    if request.method == 'POST':
        if existing_attendance:
            # Update checkout time
            if request.form.get('action') == 'checkout':
                checkout_time = datetime.now()
                existing_attendance.check_out = checkout_time
                
                # Calculate working hours
                if existing_attendance.check_in:
                    time_diff = checkout_time - existing_attendance.check_in
                    existing_attendance.working_hours = time_diff.total_seconds() / 3600  # Convert to hours
                
                db.session.commit()
                flash('Check-out recorded successfully.', 'success')
        else:
            # Create new attendance record
            new_attendance = Attendance(
                employee_id=employee.id,
                attendance_date=today,
                status='Present',
                check_in=datetime.now()
            )
            db.session.add(new_attendance)
            db.session.commit()
            flash('Check-in recorded successfully.', 'success')
    
    return render_template('mark_attendance.html', 
                           employee=employee,
                           existing_attendance=existing_attendance,
                           today=today,
                           active_page='attendance',
                           title='Mark Attendance')

@app.route('/view-attendance')
@login_required
def view_attendance():
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    
    if not employee:
        flash('Employee record not found.', 'danger')
        return redirect(url_for('employee_portal'))
    
    month = request.args.get('month', datetime.now().month)
    year = request.args.get('year', datetime.now().year)
    
    try:
        month = int(month)
        year = int(year)
    except ValueError:
        month = datetime.now().month
        year = datetime.now().year
    
    # Get attendance records for this month
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    
    attendance_records = Attendance.query.filter_by(employee_id=employee.id).filter(
        Attendance.attendance_date >= first_day,
        Attendance.attendance_date <= last_day
    ).order_by(Attendance.attendance_date).all()
    
    # Create calendar with attendance data
    cal = calendar.monthcalendar(year, month)
    attendance_calendar = []
    
    for week in cal:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append(None)
            else:
                day_date = date(year, month, day)
                attendance = next((a for a in attendance_records if a.attendance_date == day_date), None)
                week_data.append({
                    'day': day,
                    'attendance': attendance,
                    'date': day_date
                })
        attendance_calendar.append(week_data)
    
    return render_template('view_attendance.html', 
                           employee=employee,
                           attendance_calendar=attendance_calendar,
                           month=month,
                           year=year,
                           month_name=calendar.month_name[month],
                           active_page='attendance',
                           title='My Attendance')

@app.route('/view-salary-slips')
@login_required
def view_salary_slips():
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    
    if not employee:
        flash('Employee record not found.', 'danger')
        return redirect(url_for('employee_portal'))
    
    # Example of using Frappe-style API
    salary_slips = get_all("Salary Slip", 
                         filters={"employee_id": employee.id},
                         order_by="start_date desc")
    
    return render_template('salary_slips.html', 
                           salary_slips=salary_slips,
                           active_page='payroll',
                           title='My Salary Slips')

@app.route('/view-salary-slip/<int:slip_id>')
@login_required
def view_salary_slip_detail(slip_id):
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    
    if not employee:
        flash('Employee record not found.', 'danger')
        return redirect(url_for('employee_portal'))
    
    # Example of using Frappe-style API
    try:
        salary_slip = get_doc("Salary Slip", slip_id)
        
        # Check permission
        if not has_permission("Salary Slip", "read", salary_slip):
            flash('You do not have permission to view this salary slip.', 'danger')
            return redirect(url_for('view_salary_slips'))
        
        return render_template('salary_slip_detail.html', 
                              salary_slip=salary_slip,
                              employee=employee,
                              active_page='payroll',
                              title='Salary Slip Details')
    except ValueError:
        flash('Salary slip not found.', 'danger')
        return redirect(url_for('view_salary_slips'))

@app.route('/my-profile')
@login_required
def my_profile():
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    
    return render_template('employee_profile.html', 
                           employee=employee,
                           user=current_user,
                           active_page='profile',
                           title='My Profile')

# HR Manager Routes

@app.route('/employees')
@login_required
def employees_list():
    if current_user.role != 'HR Manager' and current_user.role != 'Administrator':
        flash('Access denied. You do not have permission to view this page.', 'danger')
        return redirect(url_for('employee_portal'))
    
    # Example of using Frappe-style API
    employees = get_all("Employee", 
                       fields=["id", "employee_id", "first_name", "last_name", "email", 
                               "department", "designation", "status", "date_of_joining"],
                       order_by="date_of_joining desc")
    
    return render_template('employees.html', 
                           employees=employees,
                           active_page='employees',
                           title='Employees')

@app.route('/attendance/daily-status')
@login_required
def attendance_daily_view():
    if current_user.role != 'HR Manager' and current_user.role != 'Administrator':
        flash('Access denied. You do not have permission to view this page.', 'danger')
        return redirect(url_for('employee_portal'))
    
    selected_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    try:
        attendance_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except ValueError:
        attendance_date = date.today()
    
    # Get all attendance records for the selected date
    attendance_records = Attendance.query.filter_by(attendance_date=attendance_date).all()
    
    # Get all employees
    employees = Employee.query.filter_by(status='Active').all()
    
    # Map attendance records to employees
    attendance_data = []
    for employee in employees:
        attendance = next((a for a in attendance_records if a.employee_id == employee.id), None)
        attendance_data.append({
            'employee': employee,
            'attendance': attendance
        })
    
    return render_template('attendance_daily.html', 
                           attendance_data=attendance_data,
                           attendance_date=attendance_date,
                           active_page='attendance',
                           title='Daily Attendance Status')

@app.route('/leave-approvals')
@login_required
def leave_pending_approvals():
    if current_user.role != 'HR Manager' and current_user.role != 'Administrator':
        flash('Access denied. You do not have permission to view this page.', 'danger')
        return redirect(url_for('employee_portal'))
    
    # Example of using Frappe-style API
    pending_leaves = get_all("Leave Application", 
                           filters={"status": "Open"},
                           order_by="from_date")
    
    return render_template('leave_approvals.html', 
                           leaves=pending_leaves,
                           active_page='leaves',
                           title='Leave Approvals')

# API Endpoints - Frappe-style whitelist

@app.route('/api/employee/dashboard')
@whitelist()
def get_employee_dashboard_data():
    """API endpoint for employee dashboard data"""
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    
    if not employee:
        return create_response(error="Employee record not found")
    
    # Get pending leave applications
    pending_leaves = LeaveApplication.query.filter_by(
        employee_id=employee.id,
        status='Open'
    ).count()
    
    # Get attendance stats
    today = date.today()
    first_day_of_month = date(today.year, today.month, 1)
    last_day_of_month = (date(today.year, today.month + 1, 1) if today.month < 12 
                         else date(today.year + 1, 1, 1)) - timedelta(days=1)
    
    # Count days present in current month
    days_present = Attendance.query.filter_by(
        employee_id=employee.id,
        status='Present'
    ).filter(
        Attendance.attendance_date >= first_day_of_month,
        Attendance.attendance_date <= last_day_of_month
    ).count()
    
    # Check today's attendance
    today_attendance = Attendance.query.filter_by(
        employee_id=employee.id,
        attendance_date=today
    ).first()
    
    # Get upcoming appraisal if any
    upcoming_appraisal = Appraisal.query.filter_by(
        employee_id=employee.id,
        status='Draft'
    ).order_by(Appraisal.end_date).first()
    
    # Get recent salary slip
    recent_salary = SalarySlip.query.filter_by(
        employee_id=employee.id
    ).order_by(SalarySlip.end_date.desc()).first()
    
    data = {
        "employee": {
            "id": employee.id,
            "employee_id": employee.employee_id,
            "name": f"{employee.first_name} {employee.last_name or ''}".strip(),
            "department": employee.department,
            "designation": employee.designation
        },
        "attendance": {
            "today": {
                "status": today_attendance.status if today_attendance else "Not Marked",
                "check_in": today_attendance.check_in.strftime("%H:%M") if today_attendance and today_attendance.check_in else None,
                "check_out": today_attendance.check_out.strftime("%H:%M") if today_attendance and today_attendance.check_out else None
            },
            "month": {
                "present": days_present,
                "total_days": (today - first_day_of_month).days + 1,
                "percentage": round((days_present / ((today - first_day_of_month).days + 1)) * 100) if (today - first_day_of_month).days > 0 else 0
            }
        },
        "leaves": {
            "pending": pending_leaves
        },
        "appraisal": {
            "upcoming": {
                "id": upcoming_appraisal.id if upcoming_appraisal else None,
                "end_date": upcoming_appraisal.end_date.strftime("%Y-%m-%d") if upcoming_appraisal else None
            }
        },
        "salary": {
            "recent": {
                "id": recent_salary.id if recent_salary else None,
                "month": recent_salary.end_date.strftime("%B %Y") if recent_salary else None,
                "amount": recent_salary.net_pay if recent_salary else None
            }
        }
    }
    
    return create_response(data)

@app.route('/api/hr/dashboard')
@whitelist()
def get_hr_dashboard_data():
    """API endpoint for HR dashboard data"""
    if current_user.role != 'HR Manager' and current_user.role != 'Administrator':
        return create_response(error="Access denied", status_code=403)
    
    # Employee count
    employee_count = Employee.query.filter_by(status='Active').count()
    
    # Attendance today
    today = date.today()
    attendance_today = Attendance.query.filter_by(attendance_date=today).count()
    
    # Pending leaves
    leave_pending = LeaveApplication.query.filter_by(status='Open').count()
    
    # Job openings
    job_openings = JobOpening.query.filter_by(status='Open').count()
    
    # Department-wise employee count
    departments = db.session.query(
        Employee.department, 
        db.func.count(Employee.id)
    ).filter_by(
        status='Active'
    ).group_by(
        Employee.department
    ).all()
    
    department_data = [
        {"department": dept, "count": count} 
        for dept, count in departments
    ]
    
    # Attendance status for today
    attendance_stats = db.session.query(
        Attendance.status, 
        db.func.count(Attendance.id)
    ).filter_by(
        attendance_date=today
    ).group_by(
        Attendance.status
    ).all()
    
    attendance_data = [
        {"status": status, "count": count} 
        for status, count in attendance_stats
    ]
    
    # Return data
    return jsonify({
        "employee_count": employee_count,
        "attendance_today": attendance_today,
        "leave_pending": leave_pending,
        "job_openings": job_openings,
        "department_data": department_data,
        "attendance_data": attendance_data
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        add_test_data()
    app.run(host='0.0.0.0', port=5000, debug=True)