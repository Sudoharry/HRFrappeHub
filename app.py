import os
import sys
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize Flask app
app = Flask(__name__, 
            template_folder='templates')  # Explicitly set template folder
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'hr-management-system-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Define models based on the existing doctypes
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(512))  # Increased length for password hash
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    role = db.Column(db.String(80))
    
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80))
    email = db.Column(db.String(120))
    status = db.Column(db.String(20), default='Active')
    gender = db.Column(db.String(10))
    date_of_birth = db.Column(db.Date)
    date_of_joining = db.Column(db.Date)
    department = db.Column(db.String(80))
    designation = db.Column(db.String(80))
    reports_to = db.Column(db.Integer, db.ForeignKey('employee.id'))
    company = db.Column(db.String(80))
    
    @property
    def employee_name(self):
        return f"{self.first_name} {self.last_name}" if self.last_name else self.first_name

class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    department_head = db.Column(db.Integer, db.ForeignKey('employee.id'))

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # Present, Absent, Half Day, On Leave
    check_in = db.Column(db.DateTime)
    check_out = db.Column(db.DateTime)
    working_hours = db.Column(db.Float)
    
    employee = db.relationship('Employee', backref='attendance')

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
    status = db.Column(db.String(20))
    
    employee = db.relationship('Employee', backref='salary_slips')
    salary_structure = db.relationship('SalaryStructure')

class JobOpening(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_title = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), default='Open')
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    publish = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text)
    
    department = db.relationship('Department')

class JobApplicant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_opening_id = db.Column(db.Integer, db.ForeignKey('job_opening.id'))
    applicant_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    status = db.Column(db.String(20), default='Open')
    resume = db.Column(db.String(255))
    cover_letter = db.Column(db.Text)
    
    job_opening = db.relationship('JobOpening', backref='applicants')

class Appraisal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='Draft')
    score = db.Column(db.Float)
    feedback = db.Column(db.Text)
    
    employee = db.relationship('Employee', backref='appraisals')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Add test data
def add_test_data():
    # Check if data already exists
    if User.query.filter_by(username='admin').first():
        return
    
    # Create admin user
    admin = User(
        username='admin',
        email='admin@example.com',
        password='admin123',
        first_name='Admin',
        role='Administrator'
    )
    
    hr_user = User(
        username='hr',
        email='hr@example.com',
        password='hr123',
        first_name='HR',
        last_name='Manager',
        role='HR Manager'
    )
    
    emp_user = User(
        username='john',
        email='john@example.com',
        password='john123',
        first_name='John',
        last_name='Doe',
        role='Employee'
    )
    
    db.session.add_all([admin, hr_user, emp_user])
    db.session.commit()
    
    # Create departments
    hr_dept = Department(name='Human Resources')
    it_dept = Department(name='Information Technology')
    finance_dept = Department(name='Finance')
    
    db.session.add_all([hr_dept, it_dept, finance_dept])
    db.session.commit()
    
    # Create employees
    hr_emp = Employee(
        employee_id='EMP-001',
        user_id=hr_user.id,
        first_name='HR',
        last_name='Manager',
        email='hr@example.com',
        gender='Female',
        date_of_birth=datetime(1985, 5, 15),
        date_of_joining=datetime(2010, 1, 10),
        department='Human Resources',
        designation='HR Manager',
        company='ABC Company'
    )
    
    john = Employee(
        employee_id='EMP-002',
        user_id=emp_user.id,
        first_name='John',
        last_name='Doe',
        email='john@example.com',
        gender='Male',
        date_of_birth=datetime(1990, 8, 21),
        date_of_joining=datetime(2018, 4, 5),
        department='Information Technology',
        designation='Software Developer',
        reports_to=1,
        company='ABC Company'
    )
    
    db.session.add_all([hr_emp, john])
    db.session.commit()
    
    # Set department head
    hr_dept.department_head = hr_emp.id
    it_dept.department_head = hr_emp.id
    db.session.commit()
    
    # Create leave types
    casual_leave = LeaveType(name='Casual Leave', max_days_allowed=10, is_paid_leave=True)
    sick_leave = LeaveType(name='Sick Leave', max_days_allowed=8, is_paid_leave=True)
    unpaid_leave = LeaveType(name='Unpaid Leave', max_days_allowed=30, is_paid_leave=False)
    
    db.session.add_all([casual_leave, sick_leave, unpaid_leave])
    db.session.commit()
    
    # Create job openings
    job1 = JobOpening(
        job_title='Senior Developer',
        department_id=it_dept.id,
        description='We are looking for an experienced senior developer...'
    )
    
    job2 = JobOpening(
        job_title='HR Associate',
        department_id=hr_dept.id,
        description='Position for HR Associate with 2+ years experience...'
    )
    
    db.session.add_all([job1, job2])
    db.session.commit()
    
    # Create salary structure
    salary_structure = SalaryStructure(
        name='Standard Salary Structure',
        is_active=True,
        from_date=datetime(2023, 1, 1),
        base_amount=5000.00
    )
    
    db.session.add(salary_structure)
    db.session.commit()

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'HR Manager':
            return redirect(url_for('hr_dashboard'))
        else:
            return redirect(url_for('employee_portal'))
    return render_template('modern/login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.verify_password(password):
            login_user(user)
            if user.role == 'HR Manager':
                return redirect(url_for('hr_dashboard'))
            else:
                return redirect(url_for('employee_portal'))
        else:
            flash('Invalid username or password')
    
    return render_template('modern/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/hr-dashboard')
@login_required
def hr_dashboard():
    if current_user.role != 'HR Manager' and current_user.role != 'Administrator':
        flash('You do not have permission to access this page.')
        return redirect(url_for('employee_portal'))
    
    context = {}
    context['departments'] = Department.query.all()
    context['is_hr_manager'] = True
    context['is_hr_user'] = True
    context['title'] = 'HR Dashboard'
    context['parents'] = [{"name": "Home", "route": "/"}]
    
    return render_template('modern/hr_dashboard.html', **context)

@app.route('/employee-portal')
@login_required
def employee_portal():
    # Get employee for current user
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    if not employee:
        flash('You do not have an associated Employee record.')
        return redirect(url_for('login'))
    
    # Build context
    context = {}
    context['employee'] = employee
    context['employee_id'] = employee.employee_id
    context['employee_name'] = employee.employee_name
    
    # Get reports_to information
    if employee.reports_to:
        reports_to = Employee.query.get(employee.reports_to)
        context['reports_to_name'] = reports_to.employee_name if reports_to else None
    else:
        context['reports_to_name'] = None
    
    # Leave balances (simplified)
    context['leave_balances'] = [
        {'leave_type': 'Casual Leave', 'balance_leaves': 8},
        {'leave_type': 'Sick Leave', 'balance_leaves': 7}
    ]
    
    # Recent leave applications
    context['leave_applications'] = []
    for leave in LeaveApplication.query.filter_by(employee_id=employee.id).order_by(LeaveApplication.id.desc()).limit(5).all():
        leave_type = LeaveType.query.get(leave.leave_type_id)
        if leave.status == "Approved":
            indicator = "green"
        elif leave.status == "Rejected":
            indicator = "red"
        else:
            indicator = "orange"
            
        context['leave_applications'].append({
            'name': f"LEAVE-{leave.id}",
            'leave_type': leave_type.name,
            'from_date': leave.from_date,
            'to_date': leave.to_date,
            'total_leave_days': leave.total_leave_days,
            'status': leave.status,
            'indicator': indicator
        })
    
    # Attendance summary
    today = datetime.now().date()
    first_day = datetime(today.year, today.month, 1).date()
    
    context['month_year'] = f"{today.strftime('%B')} {today.year}"
    context['attendance_summary'] = {
        'present': Attendance.query.filter_by(employee_id=employee.id, status='Present').count(),
        'absent': Attendance.query.filter_by(employee_id=employee.id, status='Absent').count(),
        'half_day': Attendance.query.filter_by(employee_id=employee.id, status='Half Day').count(),
        'on_leave': Attendance.query.filter_by(employee_id=employee.id, status='On Leave').count()
    }
    
    # Upcoming holidays (simplified)
    today = datetime.now().date()
    upcoming_days = [today + timedelta(days=i) for i in range(5)]
    context['holidays'] = [
        {
            'description': 'International Workers Day',
            'holiday_date': upcoming_days[0],
            'days_away': 0,
            'is_today': True
        },
        {
            'description': 'Independence Day',
            'holiday_date': upcoming_days[3],
            'days_away': 3,
            'is_today': False
        }
    ]
    
    # Recent salary slips
    context['salary_slips'] = []
    for slip in SalarySlip.query.filter_by(employee_id=employee.id).order_by(SalarySlip.id.desc()).limit(3).all():
        context['salary_slips'].append({
            'name': f"SLIP-{slip.id}",
            'month': slip.start_date.strftime('%B'),
            'year': slip.start_date.year,
            'net_pay': slip.net_pay,
            'status': 'Submitted' if slip.status else 'Draft',
            'indicator': 'green' if slip.status else 'orange'
        })
    
    # Performance appraisals
    context['appraisals'] = []
    for appraisal in Appraisal.query.filter_by(employee_id=employee.id).order_by(Appraisal.id.desc()).limit(3).all():
        context['appraisals'].append({
            'name': f"APP-{appraisal.id}",
            'start_date': appraisal.start_date,
            'end_date': appraisal.end_date,
            'score': appraisal.score,
            'status': appraisal.status,
            'indicator': 'green' if appraisal.status == 'Completed' else 'blue'
        })
    
    context['title'] = 'Employee Portal'
    context['parents'] = [{"name": "Home", "route": "/"}]
    
    return render_template('modern/employee_portal.html', **context)

# Employee feature routes
@app.route('/apply-leave', methods=['GET', 'POST'])
@login_required
def apply_leave():
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    if not employee:
        flash('You do not have an associated Employee record.')
        return redirect(url_for('login'))
    
    leave_types = LeaveType.query.all()
    
    if request.method == 'POST':
        leave_type_id = request.form.get('leave_type_id')
        from_date = datetime.strptime(request.form.get('from_date'), '%Y-%m-%d').date()
        to_date = datetime.strptime(request.form.get('to_date'), '%Y-%m-%d').date()
        reason = request.form.get('reason')
        
        # Calculate total leave days (simplified)
        delta = to_date - from_date
        total_days = delta.days + 1
        
        new_leave = LeaveApplication(
            employee_id=employee.id,
            leave_type_id=leave_type_id,
            from_date=from_date,
            to_date=to_date,
            total_leave_days=total_days,
            reason=reason,
            status='Open'
        )
        
        db.session.add(new_leave)
        db.session.commit()
        
        flash('Leave application submitted successfully.')
        return redirect(url_for('view_leaves'))
    
    return render_template('apply_leave.html', employee=employee, leave_types=leave_types)

@app.route('/view-leaves')
@login_required
def view_leaves():
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    if not employee:
        flash('You do not have an associated Employee record.')
        return redirect(url_for('login'))
    
    leaves = LeaveApplication.query.filter_by(employee_id=employee.id).order_by(LeaveApplication.id.desc()).all()
    
    # Process leaves for display
    leave_list = []
    for leave in leaves:
        leave_type = LeaveType.query.get(leave.leave_type_id)
        leave_list.append({
            'id': leave.id,
            'leave_type': leave_type.name if leave_type else 'Unknown',
            'from_date': leave.from_date,
            'to_date': leave.to_date,
            'total_leave_days': leave.total_leave_days,
            'status': leave.status,
            'reason': leave.reason,
            'indicator': 'green' if leave.status == 'Approved' else 'red' if leave.status == 'Rejected' else 'blue'
        })
    
    return render_template('view_leaves.html', leaves=leave_list, employee=employee)

@app.route('/mark-attendance', methods=['GET', 'POST'])
@login_required
def mark_attendance():
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    if not employee:
        flash('You do not have an associated Employee record.')
        return redirect(url_for('login'))
    
    today = datetime.now().date()
    existing_attendance = Attendance.query.filter_by(
        employee_id=employee.id, 
        attendance_date=today
    ).first()
    
    if request.method == 'POST':
        status = request.form.get('status')
        
        if existing_attendance:
            # Update existing attendance
            existing_attendance.status = status
            existing_attendance.check_in = datetime.now() if status == 'Present' else None
            db.session.commit()
            flash('Attendance updated successfully.')
        else:
            # Create new attendance record
            new_attendance = Attendance(
                employee_id=employee.id,
                attendance_date=today,
                status=status,
                check_in=datetime.now() if status == 'Present' else None
            )
            db.session.add(new_attendance)
            db.session.commit()
            flash('Attendance marked successfully.')
        
        return redirect(url_for('view_attendance'))
    
    return render_template('mark_attendance.html', 
                          employee=employee, 
                          today=today.strftime('%Y-%m-%d'),
                          existing_attendance=existing_attendance)

@app.route('/view-attendance')
@login_required
def view_attendance():
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    if not employee:
        flash('You do not have an associated Employee record.')
        return redirect(url_for('login'))
    
    # Get attendance records for the current month
    now = datetime.now()
    month_start = datetime(now.year, now.month, 1).date()
    month_end = (datetime(now.year, now.month+1, 1) - timedelta(days=1)).date() if now.month < 12 else datetime(now.year, 12, 31).date()
    
    attendance_records = Attendance.query.filter(
        Attendance.employee_id == employee.id,
        Attendance.attendance_date >= month_start,
        Attendance.attendance_date <= month_end
    ).order_by(Attendance.attendance_date.desc()).all()
    
    # Process attendance for display
    attendance_list = []
    for record in attendance_records:
        attendance_list.append({
            'id': record.id,
            'date': record.attendance_date,
            'status': record.status,
            'check_in': record.check_in,
            'check_out': record.check_out,
            'working_hours': record.working_hours,
            'indicator': 'green' if record.status == 'Present' else 'red' if record.status == 'Absent' else 'blue'
        })
    
    return render_template('view_attendance.html', 
                          attendance=attendance_list, 
                          employee=employee, 
                          month=now.strftime('%B %Y'))

@app.route('/view-salary-slips')
@login_required
def view_salary_slips():
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    if not employee:
        flash('You do not have an associated Employee record.')
        return redirect(url_for('login'))
    
    salary_slips = SalarySlip.query.filter_by(employee_id=employee.id).order_by(SalarySlip.id.desc()).all()
    
    # Process salary slips for display
    slip_list = []
    for slip in salary_slips:
        slip_list.append({
            'id': slip.id,
            'month': slip.start_date.strftime('%B'),
            'year': slip.start_date.year,
            'start_date': slip.start_date,
            'end_date': slip.end_date,
            'posting_date': slip.posting_date,
            'gross_pay': slip.gross_pay,
            'total_deduction': slip.total_deduction,
            'net_pay': slip.net_pay,
            'status': slip.status,
            'indicator': 'green' if slip.status == 'Paid' else 'blue'
        })
    
    return render_template('view_salary_slips.html', salary_slips=slip_list, employee=employee)

@app.route('/view-salary-slip/<int:slip_id>')
@login_required
def view_salary_slip_detail(slip_id):
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    if not employee:
        flash('You do not have an associated Employee record.')
        return redirect(url_for('login'))
    
    salary_slip = SalarySlip.query.get_or_404(slip_id)
    
    # Make sure employee can only view their own salary slip
    if salary_slip.employee_id != employee.id:
        flash('You are not authorized to view this salary slip.')
        return redirect(url_for('view_salary_slips'))
    
    return render_template('salary_slip_detail.html', 
                          slip=salary_slip, 
                          employee=employee)

@app.route('/my-profile')
@login_required
def my_profile():
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    if not employee:
        flash('You do not have an associated Employee record.')
        return redirect(url_for('login'))
    
    user = User.query.get(current_user.id)
    
    # Get reporting manager if any
    reports_to_name = None
    if employee.reports_to:
        reports_to = Employee.query.get(employee.reports_to)
        reports_to_name = reports_to.employee_name if reports_to else None
    
    return render_template('my_profile.html', 
                          employee=employee, 
                          user=user,
                          reports_to_name=reports_to_name)

# HR Manager Routes
@app.route('/employees')
@login_required
def employees_list():
    if current_user.role != 'HR Manager' and current_user.role != 'Administrator':
        flash('You do not have permission to access this page.')
        return redirect(url_for('employee_portal'))
    
    employees = Employee.query.all()
    
    # Process employees for display
    employee_list = []
    for emp in employees:
        employee_list.append({
            'id': emp.id,
            'employee_id': emp.employee_id,
            'name': emp.employee_name,
            'email': emp.email,
            'department': emp.department,
            'designation': emp.designation,
            'status': emp.status,
            'date_of_joining': emp.date_of_joining
        })
    
    return render_template('modern/employees.html', 
                          employees=employee_list,
                          active_page='employees',
                          title='Employees')

@app.route('/attendance/daily-status')
@login_required
def attendance_daily_view():
    if current_user.role != 'HR Manager' and current_user.role != 'Administrator':
        flash('You do not have permission to access this page.')
        return redirect(url_for('employee_portal'))
    
    today = datetime.now().date()
    attendance_records = Attendance.query.filter_by(attendance_date=today).all()
    
    # Get all employees
    employees = Employee.query.filter_by(status='Active').all()
    
    # Process attendance for display
    attendance_status = []
    for emp in employees:
        att_record = next((att for att in attendance_records if att.employee_id == emp.id), None)
        
        attendance_status.append({
            'employee_id': emp.id,
            'employee_name': emp.employee_name,
            'department': emp.department,
            'status': att_record.status if att_record else 'Not Marked',
            'check_in': att_record.check_in if att_record else None,
            'check_out': att_record.check_out if att_record else None,
            'working_hours': att_record.working_hours if att_record else None
        })
    
    # Use hr_dashboard.html as the template to make sure we use the existing template
    # Backwords compatibility
    return render_template('modern/hr_dashboard.html', 
                          attendance=attendance_status,
                          today=today.strftime('%Y-%m-%d'),
                          active_page='attendance_daily_status',
                          section='Attendance Management',
                          subsection='Daily Status',
                          title='Daily Attendance Status')

@app.route('/leave/pending-approvals')
@login_required
def leave_pending_approvals():
    if current_user.role != 'HR Manager' and current_user.role != 'Administrator':
        flash('You do not have permission to access this page.')
        return redirect(url_for('employee_portal'))
    
    pending_leaves = LeaveApplication.query.filter_by(status='Open').all()
    
    # Process leaves for display
    leave_list = []
    for leave in pending_leaves:
        employee = Employee.query.get(leave.employee_id)
        leave_type = LeaveType.query.get(leave.leave_type_id)
        
        leave_list.append({
            'id': leave.id,
            'employee_name': employee.employee_name if employee else 'Unknown',
            'department': employee.department if employee else 'Unknown',
            'leave_type': leave_type.name if leave_type else 'Unknown',
            'from_date': leave.from_date,
            'to_date': leave.to_date,
            'total_leave_days': leave.total_leave_days,
            'reason': leave.reason,
            'status': leave.status
        })
    
    return render_template('modern/leave_pending.html', 
                          leaves=leave_list,
                          active_page='leave_management',
                          title='Pending Leave Approvals')

@app.route('/recruitment/job-openings')
@login_required
def job_openings():
    if current_user.role != 'HR Manager' and current_user.role != 'Administrator':
        flash('You do not have permission to access this page.')
        return redirect(url_for('employee_portal'))
    
    job_openings = JobOpening.query.all()
    
    # Process job openings for display
    jobs_list = []
    for job in job_openings:
        department = Department.query.get(job.department_id)
        applicant_count = JobApplicant.query.filter_by(job_opening_id=job.id).count()
        
        jobs_list.append({
            'id': job.id,
            'job_title': job.job_title,
            'department': department.name if department else 'Not Specified',
            'status': job.status,
            'applicant_count': applicant_count,
            'description': job.description,
            'publish': job.publish
        })
    
    return render_template('modern/job_openings.html', 
                          jobs=jobs_list,
                          active_page='recruitment',
                          title='Job Openings')

@app.route('/payroll/salary-slips')
@login_required
def payroll_salary_slips():
    if current_user.role != 'HR Manager' and current_user.role != 'Administrator':
        flash('You do not have permission to access this page.')
        return redirect(url_for('employee_portal'))
    
    salary_slips = SalarySlip.query.all()
    
    # Process salary slips for display
    slip_list = []
    for slip in salary_slips:
        employee = Employee.query.get(slip.employee_id)
        
        slip_list.append({
            'id': slip.id,
            'employee_name': employee.employee_name if employee else 'Unknown',
            'department': employee.department if employee else 'Unknown',
            'month': slip.start_date.strftime('%B'),
            'year': slip.start_date.year,
            'start_date': slip.start_date,
            'end_date': slip.end_date,
            'posting_date': slip.posting_date,
            'gross_pay': slip.gross_pay,
            'total_deduction': slip.total_deduction,
            'net_pay': slip.net_pay,
            'status': slip.status
        })
    
    return render_template('modern/payroll_slips.html', 
                          salary_slips=slip_list,
                          active_page='payroll',
                          title='Salary Slips')

@app.route('/performance/appraisals')
@login_required
def performance_appraisals():
    if current_user.role != 'HR Manager' and current_user.role != 'Administrator':
        flash('You do not have permission to access this page.')
        return redirect(url_for('employee_portal'))
    
    appraisals = Appraisal.query.all()
    
    # Process appraisals for display
    appraisal_list = []
    for appraisal in appraisals:
        employee = Employee.query.get(appraisal.employee_id)
        
        appraisal_list.append({
            'id': appraisal.id,
            'employee_name': employee.employee_name if employee else 'Unknown',
            'department': employee.department if employee else 'Unknown',
            'start_date': appraisal.start_date,
            'end_date': appraisal.end_date,
            'status': appraisal.status,
            'score': appraisal.score,
            'feedback': appraisal.feedback
        })
    
    return render_template('modern/performance_appraisals.html', 
                          appraisals=appraisal_list,
                          active_page='performance',
                          title='Performance Appraisals')

# Notification Routes
@app.route('/notifications')
@login_required
def notifications_list():
    # In a real application, this would fetch notifications from a database
    notifications = [
        {
            'id': 1,
            'title': 'Attendance status updated!',
            'message': 'Your attendance has been marked as Present for today.',
            'date': datetime.now() - timedelta(days=2),
            'is_read': False,
            'type': 'attendance'
        },
        {
            'id': 2, 
            'title': 'Leave application approved',
            'message': 'Your leave application for casual leave has been approved.',
            'date': datetime.now() - timedelta(days=3),
            'is_read': True,
            'type': 'leave'
        },
        {
            'id': 3,
            'title': 'Payroll processing on 28th April',
            'message': 'Your salary slip will be processed on 28th April. Please make sure all your attendance records are correct.',
            'date': datetime.now() - timedelta(days=5),
            'is_read': False,
            'type': 'payroll'
        }
    ]
    
    return render_template('modern/notifications.html', 
                           notifications=notifications,
                           now=datetime.now(),
                           title='Notifications')

@app.route('/notifications/view/<int:notification_id>')
@login_required
def view_notification(notification_id):
    # In a real application, this would fetch a specific notification
    notifications = {
        1: {
            'id': 1,
            'title': 'Attendance status updated!',
            'message': 'Your attendance has been marked as Present for today.',
            'date': datetime.now() - timedelta(days=2),
            'is_read': True,  # Mark as read when viewed
            'type': 'attendance',
            'details': 'You have clocked in at 9:00 AM and clocked out at 5:30 PM. Total working hours: 8.5 hours.'
        },
        2: {
            'id': 2, 
            'title': 'Leave application approved',
            'message': 'Your leave application for casual leave has been approved.',
            'date': datetime.now() - timedelta(days=3),
            'is_read': True,
            'type': 'leave',
            'details': 'Your leave application for 2 days of casual leave from 25/04/2025 to 26/04/2025 has been approved by HR Manager.'
        },
        3: {
            'id': 3,
            'title': 'Payroll processing on 28th April',
            'message': 'Your salary slip will be processed on 28th April. Please make sure all your attendance records are correct.',
            'date': datetime.now() - timedelta(days=5),
            'is_read': True,
            'type': 'payroll',
            'details': 'The payroll for April 2025 will be processed on 28th April. Please review your attendance and leave records before 27th April to ensure accuracy.'
        }
    }
    
    notification = notifications.get(notification_id)
    if not notification:
        flash('Notification not found.')
        return redirect(url_for('notifications_list'))
    
    return render_template('modern/notification_detail.html', 
                           notification=notification,
                           now=datetime.now(),
                           title='Notification Detail')

# Messages Routes
@app.route('/messages')
@login_required
def messages_list():
    # In a real application, this would fetch messages from a database
    messages = [
        {
            'id': 1,
            'sender': 'HR Manager',
            'sender_id': 1,
            'subject': 'Your monthly performance review is available now',
            'message': 'Please check your performance review for the month of March 2025.',
            'date': datetime.now() - timedelta(hours=1),
            'is_read': False
        },
        {
            'id': 2,
            'sender': 'Team Lead',
            'sender_id': 3,
            'subject': 'Team meeting scheduled for Monday, 10AM',
            'message': 'We will discuss the upcoming project timeline and deliverables.',
            'date': datetime.now() - timedelta(days=2),
            'is_read': True
        },
        {
            'id': 3,
            'sender': 'System Administrator',
            'sender_id': 2,
            'subject': 'System maintenance scheduled',
            'message': 'There will be a system maintenance on Sunday, 03:00 AM. The system will be unavailable for approximately 2 hours.',
            'date': datetime.now() - timedelta(days=4),
            'is_read': True
        }
    ]
    
    return render_template('modern/messages.html', 
                           messages=messages,
                           now=datetime.now(),
                           title='Messages')

@app.route('/messages/view/<int:message_id>')
@login_required
def view_message(message_id):
    # In a real application, this would fetch a specific message
    messages = {
        1: {
            'id': 1,
            'sender': 'HR Manager',
            'sender_id': 1,
            'subject': 'Your monthly performance review is available now',
            'message': 'Please check your performance review for the month of March 2025. Your overall score is 4.2/5.0, which is excellent. There are a few areas where you can improve further. Let\'s discuss in our next one-on-one meeting.',
            'date': datetime.now() - timedelta(hours=1),
            'is_read': True
        },
        2: {
            'id': 2,
            'sender': 'Team Lead',
            'sender_id': 3,
            'subject': 'Team meeting scheduled for Monday, 10AM',
            'message': 'We will discuss the upcoming project timeline and deliverables. Please prepare your current project status and any blockers you might be facing. The meeting will be held in the conference room.',
            'date': datetime.now() - timedelta(days=2),
            'is_read': True
        }
    }
    
    message = messages.get(message_id)
    if not message:
        flash('Message not found.')
        return redirect(url_for('messages_list'))
    
    return render_template('modern/message_detail.html', 
                           message=message,
                           now=datetime.now(),
                           title='Message Detail')

# Attendance Module Additional Routes
@app.route('/attendance/daily-summary')
@login_required
def attendance_daily_summary():
    # In a real application, this would fetch detailed attendance for today
    attendance_data = {
        'date': datetime.now().date(),
        'total_employees': 54,
        'present': 48,
        'absent': 3,
        'on_leave': 2,
        'half_day': 1,
        'attendance_by_department': [
            {'department': 'Engineering', 'present': 15, 'absent': 1, 'on_leave': 0, 'half_day': 0},
            {'department': 'HR', 'present': 5, 'absent': 0, 'on_leave': 0, 'half_day': 0},
            {'department': 'Finance', 'present': 8, 'absent': 0, 'on_leave': 1, 'half_day': 0},
            {'department': 'Marketing', 'present': 12, 'absent': 1, 'on_leave': 0, 'half_day': 1},
            {'department': 'Operations', 'present': 8, 'absent': 1, 'on_leave': 1, 'half_day': 0}
        ]
    }
    
    return render_template('modern/hr_dashboard.html', 
                          active_page='attendance_daily_summary',
                          title='Daily Attendance Summary',
                          section='Attendance Management',
                          subsection='Daily Summary',
                          data=attendance_data)

@app.route('/attendance/monthly-report')
@login_required
def attendance_monthly_report():
    # In a real application, this would fetch monthly attendance report
    month = datetime.now().month
    year = datetime.now().year
    month_name = datetime.now().strftime('%B')
    
    attendance_data = {
        'month': month_name,
        'year': year,
        'total_working_days': 21,
        'attendance_summary': [
            {'department': 'Engineering', 'headcount': 16, 'avg_presence': 92},
            {'department': 'HR', 'headcount': 5, 'avg_presence': 95},
            {'department': 'Finance', 'headcount': 9, 'avg_presence': 98},
            {'department': 'Marketing', 'headcount': 14, 'avg_presence': 90},
            {'department': 'Operations', 'headcount': 10, 'avg_presence': 94}
        ]
    }
    
    return render_template('modern/hr_dashboard.html', 
                          active_page='attendance_monthly_report',
                          title='Monthly Attendance Report',
                          section='Attendance Management',
                          subsection='Monthly Report',
                          data=attendance_data)

@app.route('/attendance/upload-bulk')
@login_required
def attendance_upload_bulk():
    # This would be a form to upload bulk attendance
    return render_template('modern/hr_dashboard.html', 
                          active_page='attendance_upload_bulk',
                          title='Upload Bulk Attendance',
                          section='Attendance Management',
                          subsection='Bulk Upload')

# Leave Module Additional Routes
@app.route('/leave/leave-report')
@login_required
def leave_report():
    # In a real application, this would fetch leave report
    leave_data = {
        'year': datetime.now().year,
        'leave_by_type': [
            {'leave_type': 'Casual Leave', 'total_taken': 142, 'total_employees': 54},
            {'leave_type': 'Sick Leave', 'total_taken': 87, 'total_employees': 54},
            {'leave_type': 'Paid Time Off', 'total_taken': 214, 'total_employees': 54},
            {'leave_type': 'Unpaid Leave', 'total_taken': 12, 'total_employees': 54},
        ],
        'leave_by_department': [
            {'department': 'Engineering', 'headcount': 16, 'casual': 45, 'sick': 28, 'paid': 67, 'unpaid': 3},
            {'department': 'HR', 'headcount': 5, 'casual': 12, 'sick': 8, 'paid': 21, 'unpaid': 0},
            {'department': 'Finance', 'headcount': 9, 'casual': 21, 'sick': 15, 'paid': 34, 'unpaid': 2},
            {'department': 'Marketing', 'headcount': 14, 'casual': 37, 'sick': 22, 'paid': 56, 'unpaid': 5},
            {'department': 'Operations', 'headcount': 10, 'casual': 27, 'sick': 14, 'paid': 36, 'unpaid': 2}
        ]
    }
    
    return render_template('modern/hr_dashboard.html', 
                          active_page='leave_report',
                          title='Leave Report',
                          section='Leave Management',
                          subsection='Leave Report',
                          data=leave_data)

# Payroll Module Additional Routes
@app.route('/payroll/process-payroll')
@login_required
def process_payroll():
    # This would be a page to process payroll
    if current_user.role != 'HR Manager' and current_user.role != 'Administrator':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))
    
    payroll_data = {
        'month': datetime.now().strftime('%B'),
        'year': datetime.now().year,
        'total_employees': 54,
        'processed': 0,
        'pending': 54,
        'total_amount': 0,
        'departments': [
            {'name': 'Engineering', 'headcount': 16, 'total_salary': 0, 'status': 'Pending'},
            {'name': 'HR', 'headcount': 5, 'total_salary': 0, 'status': 'Pending'},
            {'name': 'Finance', 'headcount': 9, 'total_salary': 0, 'status': 'Pending'},
            {'name': 'Marketing', 'headcount': 14, 'total_salary': 0, 'status': 'Pending'},
            {'name': 'Operations', 'headcount': 10, 'total_salary': 0, 'status': 'Pending'}
        ]
    }
    
    return render_template('modern/hr_dashboard.html', 
                          active_page='process_payroll',
                          title='Process Payroll',
                          section='Payroll Management',
                          subsection='Process Payroll',
                          data=payroll_data)

# Recruitment Module Additional Routes
@app.route('/recruitment/job-openings')
@login_required
def recruitment_job_openings():
    # In a real application, this would fetch job openings
    job_openings = []
    for job in JobOpening.query.filter_by(status='Open').all():
        department = Department.query.get(job.department_id)
        job_openings.append({
            'id': job.id,
            'job_title': job.job_title,
            'department': department.name if department else 'Unknown',
            'status': job.status,
            'applicants_count': JobApplicant.query.filter_by(job_opening_id=job.id).count(),
            'description': job.description
        })
    
    return render_template('modern/hr_dashboard.html', 
                          active_page='recruitment_job_openings',
                          title='Job Openings',
                          section='Recruitment',
                          subsection='Job Openings',
                          jobs=job_openings)

@app.route('/recruitment/job-applicants')
@login_required
def recruitment_job_applicants():
    # In a real application, this would fetch job applicants
    if current_user.role != 'HR Manager' and current_user.role != 'Administrator':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))
    
    applicants = []
    for applicant in JobApplicant.query.all():
        job = JobOpening.query.get(applicant.job_opening_id)
        applicants.append({
            'id': applicant.id,
            'name': applicant.applicant_name,
            'email': applicant.email,
            'job_title': job.job_title if job else 'Unknown',
            'status': applicant.status,
            'resume': applicant.resume,
            'cover_letter': applicant.cover_letter
        })
    
    return render_template('modern/hr_dashboard.html', 
                          active_page='recruitment_job_applicants',
                          title='Job Applicants',
                          section='Recruitment',
                          subsection='Job Applicants',
                          applicants=applicants)

# Additional Performance Module Routes
@app.route('/performance/appraisals')
@login_required
def performance_appraisals_list():
    if current_user.role != 'HR Manager' and current_user.role != 'Administrator':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))
    
    # Get appraisal data
    appraisals = []
    for appraisal in Appraisal.query.all():
        employee = Employee.query.get(appraisal.employee_id)
        appraisals.append({
            'id': appraisal.id,
            'employee_name': employee.employee_name if employee else 'Unknown',
            'department': employee.department if employee else 'Unknown',
            'start_date': appraisal.start_date,
            'end_date': appraisal.end_date,
            'status': appraisal.status,
            'score': appraisal.score
        })
    
    return render_template('modern/hr_dashboard.html',
                          active_page='performance_appraisals',
                          title='Performance Appraisals',
                          section='Performance Management',
                          subsection='Appraisals',
                          appraisals=appraisals)

@app.route('/performance/goals')
@login_required
def performance_goals():
    # For demonstration, we'll use static data
    goals_data = {
        'company_goals': [
            {'title': 'Increase Revenue by 20%', 'status': 'In Progress', 'completion': 65},
            {'title': 'Reduce Employee Turnover', 'status': 'In Progress', 'completion': 40},
            {'title': 'Launch New Product Line', 'status': 'Completed', 'completion': 100},
        ],
        'department_goals': [
            {'department': 'Engineering', 'title': 'Complete Platform Migration', 'status': 'In Progress', 'completion': 75},
            {'department': 'HR', 'title': 'Implement New Training Program', 'status': 'In Progress', 'completion': 60},
            {'department': 'Marketing', 'title': 'Increase Social Media Engagement', 'status': 'In Progress', 'completion': 80},
        ],
    }
    
    return render_template('modern/hr_dashboard.html',
                          active_page='performance_goals',
                          title='Performance Goals',
                          section='Performance Management',
                          subsection='Goals',
                          data=goals_data)

@app.route('/performance/feedback')
@login_required
def performance_feedback():
    # For demonstration, we'll use static data
    feedback_data = {
        'recent_feedback': [
            {'employee': 'John Smith', 'reviewer': 'Alice Johnson', 'type': '360 Review', 'date': datetime.now() - timedelta(days=5)},
            {'employee': 'Mary Wilson', 'reviewer': 'Tom Davis', 'type': 'Manager Feedback', 'date': datetime.now() - timedelta(days=7)},
            {'employee': 'Robert Brown', 'reviewer': 'Sarah Miller', 'type': 'Peer Review', 'date': datetime.now() - timedelta(days=10)},
        ]
    }
    
    return render_template('modern/hr_dashboard.html',
                          active_page='performance_feedback',
                          title='Performance Feedback',
                          section='Performance Management',
                          subsection='Feedback',
                          data=feedback_data)

# Reports Module Routes
@app.route('/reports/employee')
@login_required
def reports_employee():
    if current_user.role != 'HR Manager' and current_user.role != 'Administrator':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))
    
    # For demonstration, we'll use static data
    report_data = {
        'total_employees': Employee.query.filter_by(status='Active').count(),
        'departments': Department.query.count(),
        'new_hires_this_month': 3,
        'turnover_rate': 5.2,
        'department_distribution': [
            {'department': 'Engineering', 'count': 16, 'percentage': 29.6},
            {'department': 'HR', 'count': 5, 'percentage': 9.3},
            {'department': 'Finance', 'count': 9, 'percentage': 16.7},
            {'department': 'Marketing', 'count': 14, 'percentage': 25.9},
            {'department': 'Operations', 'count': 10, 'percentage': 18.5}
        ]
    }
    
    return render_template('modern/hr_dashboard.html',
                          active_page='reports_employee',
                          title='Employee Reports',
                          section='Reports',
                          subsection='Employee Reports',
                          data=report_data)

@app.route('/reports/attendance')
@login_required
def reports_attendance():
    if current_user.role != 'HR Manager' and current_user.role != 'Administrator':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))
    
    # For demonstration, we'll use static data
    report_data = {
        'attendance_trend': [
            {'month': 'Jan', 'present_percentage': 92},
            {'month': 'Feb', 'present_percentage': 94},
            {'month': 'Mar', 'present_percentage': 91},
            {'month': 'Apr', 'present_percentage': 93},
        ],
        'department_attendance': [
            {'department': 'Engineering', 'present_percentage': 94, 'absent_percentage': 6},
            {'department': 'HR', 'present_percentage': 95, 'absent_percentage': 5},
            {'department': 'Finance', 'present_percentage': 98, 'absent_percentage': 2},
            {'department': 'Marketing', 'present_percentage': 90, 'absent_percentage': 10},
            {'department': 'Operations', 'present_percentage': 93, 'absent_percentage': 7}
        ]
    }
    
    return render_template('modern/hr_dashboard.html',
                          active_page='reports_attendance',
                          title='Attendance Reports',
                          section='Reports',
                          subsection='Attendance Reports',
                          data=report_data)

@app.route('/reports/leave')
@login_required
def reports_leave():
    if current_user.role != 'HR Manager' and current_user.role != 'Administrator':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))
    
    # For demonstration, we'll use static data
    report_data = {
        'leave_utilization': [
            {'month': 'Jan', 'days_taken': 45},
            {'month': 'Feb', 'days_taken': 38},
            {'month': 'Mar', 'days_taken': 52},
            {'month': 'Apr', 'days_taken': 42},
        ],
        'leave_by_type': [
            {'type': 'Casual Leave', 'days_taken': 142, 'percentage': 31.3},
            {'type': 'Sick Leave', 'days_taken': 87, 'percentage': 19.2},
            {'type': 'Paid Time Off', 'days_taken': 214, 'percentage': 47.2},
            {'type': 'Unpaid Leave', 'days_taken': 12, 'percentage': 2.3}
        ]
    }
    
    return render_template('modern/hr_dashboard.html',
                          active_page='reports_leave',
                          title='Leave Reports',
                          section='Reports',
                          subsection='Leave Reports',
                          data=report_data)

@app.route('/reports/payroll')
@login_required
def reports_payroll():
    if current_user.role != 'HR Manager' and current_user.role != 'Administrator':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))
    
    # For demonstration, we'll use static data
    report_data = {
        'payroll_trend': [
            {'month': 'Jan', 'amount': 158000},
            {'month': 'Feb', 'amount': 159500},
            {'month': 'Mar', 'amount': 160000},
            {'month': 'Apr', 'amount': 162000},
        ],
        'department_payroll': [
            {'department': 'Engineering', 'amount': 65000, 'percentage': 40.1},
            {'department': 'HR', 'amount': 15000, 'percentage': 9.3},
            {'department': 'Finance', 'amount': 28000, 'percentage': 17.3},
            {'department': 'Marketing', 'amount': 32000, 'percentage': 19.8},
            {'department': 'Operations', 'amount': 22000, 'percentage': 13.5}
        ]
    }
    
    return render_template('modern/hr_dashboard.html',
                          active_page='reports_payroll',
                          title='Payroll Reports',
                          section='Reports',
                          subsection='Payroll Reports',
                          data=report_data)

# Additional Routes for Payroll Module
@app.route('/payroll/salary-slips')
@login_required
def payroll_salary_slips_list():
    if current_user.role != 'HR Manager' and current_user.role != 'Administrator':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))
    
    # Get salary slip data
    salary_slips = []
    for slip in SalarySlip.query.all():
        employee = Employee.query.get(slip.employee_id)
        salary_slips.append({
            'id': slip.id,
            'employee_name': employee.employee_name if employee else 'Unknown',
            'department': employee.department if employee else 'Unknown',
            'posting_date': slip.posting_date,
            'start_date': slip.start_date,
            'end_date': slip.end_date,
            'gross_pay': slip.gross_pay,
            'net_pay': slip.net_pay,
            'status': slip.status
        })
    
    return render_template('modern/hr_dashboard.html',
                          active_page='payroll_salary_slips',
                          title='Salary Slips',
                          section='Payroll Management',
                          subsection='Salary Slips',
                          slips=salary_slips)

@app.route('/payroll/salary-structures')
@login_required
def payroll_salary_structures():
    if current_user.role != 'HR Manager' and current_user.role != 'Administrator':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))
    
    # Get salary structure data
    structures = []
    for structure in SalaryStructure.query.all():
        structures.append({
            'id': structure.id,
            'name': structure.name,
            'is_active': structure.is_active,
            'from_date': structure.from_date,
            'base_amount': structure.base_amount
        })
    
    return render_template('modern/hr_dashboard.html',
                          active_page='payroll_salary_structures',
                          title='Salary Structures',
                          section='Payroll Management',
                          subsection='Salary Structures',
                          structures=structures)

# Additional Routes for Leave Management
@app.route('/leave/types')
@login_required
def leave_types():
    if current_user.role != 'HR Manager' and current_user.role != 'Administrator':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))
    
    # Get leave type data
    leave_types = []
    for leave_type in LeaveType.query.all():
        leave_types.append({
            'id': leave_type.id,
            'name': leave_type.name,
            'max_days_allowed': leave_type.max_days_allowed,
            'is_paid_leave': leave_type.is_paid_leave
        })
    
    return render_template('modern/hr_dashboard.html',
                          active_page='leave_types',
                          title='Leave Types',
                          section='Leave Management',
                          subsection='Leave Types',
                          leave_types=leave_types)

# Additional Routes for Recruitment
@app.route('/recruitment/interviews')
@login_required
def recruitment_interviews():
    if current_user.role != 'HR Manager' and current_user.role != 'Administrator':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))
    
    # For demonstration, we'll use static data
    interviews = [
        {'id': 1, 'applicant_name': 'John Doe', 'job_title': 'Senior Developer', 'schedule_date': datetime.now() + timedelta(days=2), 'interviewer': 'Alice Johnson', 'status': 'Scheduled'},
        {'id': 2, 'applicant_name': 'Mary Smith', 'job_title': 'HR Specialist', 'schedule_date': datetime.now() + timedelta(days=1), 'interviewer': 'Tom Davis', 'status': 'Scheduled'},
        {'id': 3, 'applicant_name': 'Robert Brown', 'job_title': 'Marketing Manager', 'schedule_date': datetime.now() - timedelta(days=1), 'interviewer': 'Sarah Miller', 'status': 'Completed'}
    ]
    
    return render_template('modern/hr_dashboard.html',
                          active_page='recruitment_interviews',
                          title='Interviews',
                          section='Recruitment',
                          subsection='Interviews',
                          interviews=interviews)

# Settings Routes
@app.route('/settings')
@login_required
def settings():
    return render_template('modern/settings.html',
                          active_page='settings',
                          title='Settings')

# API Routes
@app.route('/api/employee-dashboard-data')
@login_required
def get_employee_dashboard_data():
    # Get employee for current user
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    if not employee:
        return jsonify({"error": "No employee record found"})
    
    # Get leave balance
    leave_balance = {
        "total": 15,
        "leave_types": [
            {"leave_type": "Casual Leave", "balance": 8},
            {"leave_type": "Sick Leave", "balance": 7}
        ]
    }
    
    # Get attendance summary
    attendance_summary = {
        "present": 18,
        "absent": 2,
        "half_day": 0,
        "on_leave": 1,
        "total": 21
    }
    
    # Recent activities
    activities = [
        {
            "date": datetime.now() - timedelta(days=2),
            "description": "Leave Application: Casual Leave (Approved)",
            "reference_type": "Leave Application",
            "reference_name": "LEAVE-001",
            "indicator": "green"
        },
        {
            "date": datetime.now() - timedelta(days=5),
            "description": "Attendance: Present on Apr 22, 2025",
            "reference_type": "Attendance",
            "reference_name": "ATT-001",
            "indicator": "green"
        }
    ]
    
    # Return consolidated data
    return jsonify({
        "employee": {
            "name": employee.employee_id,
            "employee_name": employee.employee_name,
            "designation": employee.designation,
            "department": employee.department,
            "email": employee.email,
            "date_of_joining": employee.date_of_joining.strftime('%Y-%m-%d') if employee.date_of_joining else None
        },
        "leave_balance": leave_balance,
        "attendance_summary": attendance_summary,
        "activities": activities
    })

@app.route('/api/hr-dashboard-data')
@login_required
def get_hr_dashboard_data():
    if current_user.role != 'HR Manager' and current_user.role != 'Administrator':
        return jsonify({"error": "Access denied"})
    
    # Basic counts
    employee_count = Employee.query.filter_by(status='Active').count()
    attendance_today = Attendance.query.filter_by(status='Present').filter(Attendance.attendance_date == datetime.now().date()).count()
    leave_pending = LeaveApplication.query.filter_by(status='Open').count()
    job_openings = JobOpening.query.filter_by(status='Open').count()
    
    # Department data
    department_data = []
    for dept in Department.query.all():
        dept_count = Employee.query.filter_by(department=dept.name, status='Active').count()
        department_data.append({
            "department": dept.name,
            "count": dept_count
        })
    
    # Attendance data
    attendance_data = {
        "present": Attendance.query.filter_by(status='Present').filter(Attendance.attendance_date == datetime.now().date()).count(),
        "absent": Attendance.query.filter_by(status='Absent').filter(Attendance.attendance_date == datetime.now().date()).count(),
        "on_leave": Attendance.query.filter_by(status='On Leave').filter(Attendance.attendance_date == datetime.now().date()).count(),
        "half_day": Attendance.query.filter_by(status='Half Day').filter(Attendance.attendance_date == datetime.now().date()).count()
    }
    
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