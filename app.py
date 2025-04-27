import os
import sys
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize Flask app
app = Flask(__name__, 
            template_folder='hrms/www',  # Use existing template folder
            static_folder='hrms/public')  # Use existing static folder
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'hr-management-system-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hrms.db'
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
    password_hash = db.Column(db.String(128))
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
    return render_template('login.html')

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
    
    return render_template('login.html')

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
    
    return render_template('hr_dashboard.html', **context)

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
    
    return render_template('employee_portal.html', **context)

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

# Create a login page template
@app.route('/create-login-template')
def create_login_template():
    login_html = """
{% extends "templates/web.html" %}

{% block title %}{{ _("Login") }}{% endblock %}

{% block page_content %}
<div class="login-page">
    <div class="container">
        <div class="row">
            <div class="col-md-6 col-md-offset-3">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h3 class="panel-title">{{ _("Login") }}</h3>
                    </div>
                    <div class="panel-body">
                        {% with messages = get_flashed_messages() %}
                        {% if messages %}
                        <div class="alert alert-danger">
                            {% for message in messages %}
                            {{ message }}
                            {% endfor %}
                        </div>
                        {% endif %}
                        {% endwith %}
                        
                        <form method="POST" action="{{ url_for('login') }}">
                            <div class="form-group">
                                <label for="username">{{ _("Username") }}</label>
                                <input type="text" class="form-control" id="username" name="username" required>
                            </div>
                            <div class="form-group">
                                <label for="password">{{ _("Password") }}</label>
                                <input type="password" class="form-control" id="password" name="password" required>
                            </div>
                            <button type="submit" class="btn btn-primary btn-block">{{ _("Login") }}</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<style>
.login-page {
    padding: 40px 0;
}
</style>
{% endblock %}
"""
    # Create templates directory if it doesn't exist
    os.makedirs('hrms/www/templates', exist_ok=True)
    
    with open('hrms/www/login.html', 'w') as f:
        f.write(login_html)
    
    return "Login template created successfully"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        add_test_data()
    app.run(host='0.0.0.0', port=5000, debug=True)