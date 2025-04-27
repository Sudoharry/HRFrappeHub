"""
Example Usage of Frappe Compatibility Layer with Flask

This file demonstrates how to use the Frappe compatibility layer
with our existing Flask application.
"""

from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

import os
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("FLASK_SECRET_KEY") or "a secret key"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Initialize login manager
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Initialize Frappe compatibility layer
from frappe_init import init_frappe_compat
init_frappe_compat(app, db)

# Import Frappe-like functions
from frappe_compat import get_doc, new_doc, get_all, db_get_value, whitelist, has_permission

# ---------- Example Route Using Frappe Compatibility Layer ----------

@app.route('/frappe/employees')
@login_required
def frappe_employees_list():
    """Example route using Frappe compatibility layer to list employees"""
    if not has_permission("Employee", "read"):
        flash('You do not have permission to access this page.')
        return redirect(url_for('employee_portal'))
    
    # Using get_all to fetch employees (Frappe-style)
    employees = get_all("Employee", 
                       fields=["id", "employee_id", "first_name", "last_name", "email", 
                               "department", "designation", "status", "date_of_joining"],
                       filters={"status": "Active"},
                       order_by="date_of_joining desc")
    
    # Format employee data
    employee_list = []
    for emp in employees:
        employee_list.append({
            'id': emp.get('id'),
            'employee_id': emp.get('employee_id'),
            'name': f"{emp.get('first_name')} {emp.get('last_name') or ''}".strip(),
            'email': emp.get('email'),
            'department': emp.get('department'),
            'designation': emp.get('designation'),
            'status': emp.get('status'),
            'joining_date': emp.get('date_of_joining')
        })
    
    return render_template('modern/employees.html', 
                          employees=employee_list,
                          active_page='employees',
                          title='Employees (Frappe API)')

@app.route('/frappe/employee/<int:employee_id>')
@login_required
def frappe_employee_detail(employee_id):
    """Example route using Frappe compatibility layer to show employee details"""
    if not has_permission("Employee", "read"):
        flash('You do not have permission to access this page.')
        return redirect(url_for('employee_portal'))
    
    # Using get_doc to fetch a single employee (Frappe-style)
    try:
        employee = get_doc("Employee", employee_id)
    except ValueError:
        flash('Employee not found.')
        return redirect(url_for('frappe_employees_list'))
    
    return render_template('modern/employee_detail.html',
                          employee=employee,
                          active_page='employees',
                          title=f'Employee: {employee.first_name} {employee.last_name or ""}')

@app.route('/frappe/employee/new', methods=['GET', 'POST'])
@login_required
def frappe_new_employee():
    """Example route using Frappe compatibility layer to create a new employee"""
    if not has_permission("Employee", "create"):
        flash('You do not have permission to create employees.')
        return redirect(url_for('frappe_employees_list'))
    
    if request.method == 'POST':
        # Create a new employee document (Frappe-style)
        try:
            employee = new_doc("Employee")
            employee.employee_id = request.form.get('employee_id')
            employee.first_name = request.form.get('first_name')
            employee.last_name = request.form.get('last_name')
            employee.email = request.form.get('email')
            employee.department = request.form.get('department')
            employee.designation = request.form.get('designation')
            employee.date_of_joining = datetime.datetime.strptime(
                request.form.get('date_of_joining'), '%Y-%m-%d').date()
            employee.gender = request.form.get('gender')
            
            # Insert the document
            employee.insert()
            
            flash('Employee created successfully.')
            return redirect(url_for('frappe_employee_detail', employee_id=employee.id))
        except Exception as e:
            flash(f'Error creating employee: {str(e)}')
    
    return render_template('modern/employee_form.html',
                          active_page='employees',
                          title='New Employee')

# ---------- API Example Using Frappe Compatibility Layer ----------

@app.route('/api/v1/employees')
@whitelist()
def api_employees_list():
    """API endpoint using Frappe compatibility layer to list employees"""
    filters = {}
    
    # Parse filters from request
    status = request.args.get('status')
    if status:
        filters['status'] = status
    
    department = request.args.get('department')
    if department:
        filters['department'] = department
    
    # Get employees using Frappe-style function
    employees = get_all("Employee", 
                       fields=["id", "employee_id", "first_name", "last_name", "email", 
                              "department", "designation", "status", "date_of_joining"],
                       filters=filters,
                       order_by="date_of_joining desc")
    
    # Return as JSON
    return jsonify(employees)

@app.route('/api/v1/employees/<int:employee_id>')
@whitelist()
def api_employee_detail(employee_id):
    """API endpoint using Frappe compatibility layer to get employee details"""
    try:
        employee = get_doc("Employee", employee_id)
        
        # Convert employee to dict
        employee_data = {
            'id': employee.id,
            'employee_id': employee.employee_id,
            'first_name': employee.first_name,
            'last_name': employee.last_name,
            'email': employee.email,
            'department': employee.department,
            'designation': employee.designation,
            'status': employee.status,
            'date_of_joining': employee.date_of_joining,
            'gender': employee.gender
        }
        
        return jsonify(employee_data)
    except ValueError:
        return jsonify({'error': 'Employee not found'}), 404

@app.route('/api/v1/employees', methods=['POST'])
@whitelist()
def api_create_employee():
    """API endpoint using Frappe compatibility layer to create an employee"""
    try:
        # Get data from request
        data = request.get_json()
        
        # Create new employee
        employee = new_doc("Employee")
        employee.employee_id = data.get('employee_id')
        employee.first_name = data.get('first_name')
        employee.last_name = data.get('last_name')
        employee.email = data.get('email')
        employee.department = data.get('department')
        employee.designation = data.get('designation')
        employee.status = data.get('status', 'Active')
        
        # Parse date if provided
        date_of_joining = data.get('date_of_joining')
        if date_of_joining:
            employee.date_of_joining = datetime.datetime.strptime(date_of_joining, '%Y-%m-%d').date()
        
        employee.gender = data.get('gender')
        
        # Insert the document
        employee.insert()
        
        return jsonify({
            'success': True,
            'message': 'Employee created successfully',
            'employee_id': employee.id
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error creating employee: {str(e)}'
        }), 400