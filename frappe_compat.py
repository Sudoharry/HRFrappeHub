"""
Frappe Compatibility Layer for Flask + SQLAlchemy

This module provides a compatibility layer that mimics Frappe API
while using Flask and SQLAlchemy under the hood.
"""

import importlib
import json
import inspect
import datetime
from functools import wraps
from flask import request, jsonify, g, current_app, session
from flask_login import current_user
from sqlalchemy import or_, and_, inspect as sa_inspect

# This will be initialized with the SQLAlchemy db instance
db = None

def init_app(flask_db):
    """Initialize with SQLAlchemy db instance"""
    global db
    db = flask_db

class FrappeJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles dates and other special types."""
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        return super().default(obj)

def create_response(data=None, status_code=200, error=None):
    """Create standardized API response in Frappe format"""
    response = {}
    
    if error:
        response["status_code"] = 500 if status_code == 200 else status_code
        response["error"] = error
    else:
        response["status_code"] = status_code
        response["data"] = data
        
    return jsonify(response), response["status_code"]

def whitelist(fn=None, allow_guest=False):
    """Decorator for whitelisted methods in Frappe style"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # If allow_guest is False, check if the user is logged in
            if not allow_guest and not current_user.is_authenticated:
                return create_response(error="Not authenticated", status_code=403)
            
            try:
                # Convert request data to args/kwargs if appropriate
                if request.method == 'POST':
                    if request.is_json:
                        # Handle JSON requests
                        req_data = request.get_json()
                        
                        # Update kwargs with JSON data
                        if isinstance(req_data, dict):
                            kwargs.update(req_data)
                    else:
                        # Handle form data
                        for key, value in request.form.items():
                            kwargs[key] = value
                
                # Call the original function
                result = f(*args, **kwargs)
                
                # If the result is a tuple, assume it's (data, status_code)
                if isinstance(result, tuple) and len(result) == 2:
                    return create_response(result[0], result[1])
                
                # Otherwise, wrap the result as data
                return create_response(result)
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                return create_response(error=str(e), status_code=500)
                
        # Mark the function as whitelisted
        wrapper.whitelisted = True
        wrapper.allow_guest = allow_guest
        return wrapper
    
    if fn:
        return decorator(fn)
    return decorator

class Document:
    """Base class for document-like functionality with SQLAlchemy models"""
    
    @classmethod
    def get_model_class(cls, doctype):
        """Get the SQLAlchemy model class from doctype name"""
        from app import User, Employee, Department, Attendance, LeaveType
        from app import LeaveApplication, SalaryStructure, SalarySlip
        from app import JobOpening, JobApplicant, Appraisal
        
        # Map doctype names to SQLAlchemy model classes
        doctype_map = {
            'User': User,
            'Employee': Employee,
            'Department': Department,
            'Attendance': Attendance,
            'Leave Type': LeaveType,
            'Leave Application': LeaveApplication,
            'Salary Structure': SalaryStructure,
            'Salary Slip': SalarySlip,
            'Job Opening': JobOpening,
            'Job Applicant': JobApplicant,
            'Appraisal': Appraisal
        }
        
        return doctype_map.get(doctype)
    
    @classmethod
    def get_doc(cls, doctype, name=None, filters=None):
        """Frappe-like get_doc implementation using SQLAlchemy"""
        model_class = cls.get_model_class(doctype)
        if not model_class:
            raise ValueError(f"DocType {doctype} not found")
        
        # Query by name (primary key)
        if name is not None:
            try:
                name = int(name)  # Convert to int if possible (for numeric IDs)
            except (ValueError, TypeError):
                pass
                
            obj = model_class.query.get(name)
            if not obj:
                raise ValueError(f"{doctype} {name} not found")
            
            return cls._wrap_model(obj)
        
        # Query by filters
        elif filters:
            query = model_class.query
            
            # Process filters
            if isinstance(filters, dict):
                for field, value in filters.items():
                    if isinstance(value, (list, tuple)) and len(value) == 2:
                        operator, operand = value
                        if operator == '=':
                            query = query.filter(getattr(model_class, field) == operand)
                        elif operator == '!=':
                            query = query.filter(getattr(model_class, field) != operand)
                        elif operator == '>':
                            query = query.filter(getattr(model_class, field) > operand)
                        elif operator == '<':
                            query = query.filter(getattr(model_class, field) < operand)
                        # Add more operators as needed
                    else:
                        query = query.filter(getattr(model_class, field) == value)
            
            # Get the first result
            obj = query.first()
            if not obj:
                raise ValueError(f"No {doctype} found for given filters")
            
            return cls._wrap_model(obj)
        
        else:
            raise ValueError("Either name or filters is required")
    
    @classmethod
    def get_all(cls, doctype, filters=None, fields=None, order_by=None, limit=None, as_list=False):
        """Get multiple documents based on filters"""
        model_class = cls.get_model_class(doctype)
        if not model_class:
            raise ValueError(f"DocType {doctype} not found")
        
        # Start with a base query
        query = model_class.query
        
        # Apply filters if provided
        if filters:
            if isinstance(filters, dict):
                for field, value in filters.items():
                    if isinstance(value, (list, tuple)) and len(value) >= 2:
                        operator, operand = value[0], value[1]
                        if operator == '=':
                            query = query.filter(getattr(model_class, field) == operand)
                        elif operator == '!=':
                            query = query.filter(getattr(model_class, field) != operand)
                        elif operator == '>':
                            query = query.filter(getattr(model_class, field) > operand)
                        elif operator == '<':
                            query = query.filter(getattr(model_class, field) < operand)
                        elif operator == 'in':
                            query = query.filter(getattr(model_class, field).in_(operand))
                        elif operator == 'not in':
                            query = query.filter(~getattr(model_class, field).in_(operand))
                        elif operator == 'like':
                            query = query.filter(getattr(model_class, field).like(f"%{operand}%"))
                    else:
                        query = query.filter(getattr(model_class, field) == value)
        
        # Apply sorting
        if order_by:
            if isinstance(order_by, str):
                # Handle 'field ASC' or 'field DESC'
                parts = order_by.split()
                if len(parts) > 1 and parts[1].upper() == 'DESC':
                    query = query.order_by(getattr(model_class, parts[0]).desc())
                else:
                    query = query.order_by(getattr(model_class, parts[0]))
            elif isinstance(order_by, (list, tuple)):
                # Handle multiple sort criteria
                sort_criteria = []
                for criterion in order_by:
                    if isinstance(criterion, str):
                        parts = criterion.split()
                        if len(parts) > 1 and parts[1].upper() == 'DESC':
                            sort_criteria.append(getattr(model_class, parts[0]).desc())
                        else:
                            sort_criteria.append(getattr(model_class, parts[0]))
                query = query.order_by(*sort_criteria)
        
        # Apply limit
        if limit:
            query = query.limit(limit)
        
        # Execute query
        objects = query.all()
        
        # Return as list or dicts
        if as_list:
            # Return as list of lists with only the requested fields
            if fields:
                result = []
                for obj in objects:
                    row = []
                    for field in fields:
                        row.append(getattr(obj, field, None))
                    result.append(row)
                return result
            else:
                # Return all fields if no specific fields requested
                result = []
                for obj in objects:
                    inspector = sa_inspect(obj)
                    row = [getattr(obj, column.key) for column in inspector.mapper.column_attrs]
                    result.append(row)
                return result
        else:
            # Return as list of wrapped objects or dicts with specific fields
            if fields:
                result = []
                for obj in objects:
                    doc = {}
                    for field in fields:
                        doc[field] = getattr(obj, field, None)
                    result.append(doc)
                return result
            else:
                # Return all fields as documents
                return [cls._wrap_model(obj) for obj in objects]
    
    @classmethod
    def _wrap_model(cls, model_obj):
        """Wrap a SQLAlchemy model instance in a Document-like object"""
        doc = DocumentWrapper(model_obj)
        return doc
    
    @classmethod
    def new_doc(cls, doctype):
        """Create a new document of the specified doctype"""
        model_class = cls.get_model_class(doctype)
        if not model_class:
            raise ValueError(f"DocType {doctype} not found")
        
        # Create a new instance
        obj = model_class()
        
        # Wrap and return
        return cls._wrap_model(obj)
    
    @classmethod
    def db_get_value(cls, doctype, filters, fieldname, as_dict=False):
        """Get a single value from the database"""
        model_class = cls.get_model_class(doctype)
        if not model_class:
            raise ValueError(f"DocType {doctype} not found")
        
        # Build query based on filters
        query = model_class.query
        
        if isinstance(filters, dict):
            for field, value in filters.items():
                query = query.filter(getattr(model_class, field) == value)
        elif isinstance(filters, (list, tuple)):
            # Handle list of conditions
            conditions = []
            for condition in filters:
                if len(condition) >= 3:
                    field, operator, value = condition
                    if operator == '=':
                        conditions.append(getattr(model_class, field) == value)
                    elif operator == '!=':
                        conditions.append(getattr(model_class, field) != value)
                    # Add more operators as needed
            if conditions:
                query = query.filter(and_(*conditions))
        else:
            # Assume it's a primary key
            query = query.filter(model_class.id == filters)
        
        # Execute query
        obj = query.first()
        
        if not obj:
            return None
        
        # Handle the result
        if as_dict:
            if isinstance(fieldname, (list, tuple)):
                result = {}
                for field in fieldname:
                    result[field] = getattr(obj, field, None)
                return result
            else:
                return {fieldname: getattr(obj, fieldname, None)}
        else:
            if isinstance(fieldname, (list, tuple)):
                return [getattr(obj, field, None) for field in fieldname]
            else:
                return getattr(obj, fieldname, None)
    
    @classmethod
    def db_count(cls, doctype, filters=None):
        """Count documents with given filters"""
        model_class = cls.get_model_class(doctype)
        if not model_class:
            raise ValueError(f"DocType {doctype} not found")
        
        # Build query based on filters
        query = model_class.query
        
        if filters:
            if isinstance(filters, dict):
                for field, value in filters.items():
                    query = query.filter(getattr(model_class, field) == value)
        
        # Return count
        return query.count()

class DocumentWrapper:
    """Wrapper around SQLAlchemy model to provide Frappe-like document interface"""
    
    def __init__(self, model_obj):
        self._model = model_obj
        self._doctype = model_obj.__class__.__name__
        
        # Set up attributes
        self._setup_attributes()
    
    def _setup_attributes(self):
        """Set up attributes for easy access"""
        # Map SQLAlchemy model attributes to this wrapper
        for column in sa_inspect(self._model).mapper.column_attrs:
            setattr(self, column.key, getattr(self._model, column.key))
    
    def __getattr__(self, name):
        """Fallback for attributes not found"""
        if hasattr(self._model, name):
            return getattr(self._model, name)
        raise AttributeError(f"'{self._doctype}' object has no attribute '{name}'")
    
    def __setattr__(self, name, value):
        """Set attributes"""
        if name.startswith('_'):
            super().__setattr__(name, value)
        elif hasattr(self, '_model') and hasattr(self._model, name):
            setattr(self._model, name, value)
            super().__setattr__(name, value)  # Also update the wrapper
        else:
            super().__setattr__(name, value)
    
    def insert(self, ignore_permissions=False):
        """Insert document into database"""
        if not ignore_permissions:
            # Check permissions (could be expanded)
            if hasattr(self._model, 'has_permission'):
                if not self._model.has_permission(current_user, 'create'):
                    raise PermissionError(f"No permission to create {self._doctype}")
        
        # Add to session and commit
        db.session.add(self._model)
        db.session.commit()
        
        # Update attributes
        self._setup_attributes()
        
        # Trigger after_insert hook if exists
        self._trigger_hook('after_insert')
        
        return self
    
    def save(self, ignore_permissions=False):
        """Save document to database"""
        if not ignore_permissions:
            # Check permissions (could be expanded)
            if hasattr(self._model, 'has_permission'):
                if not self._model.has_permission(current_user, 'write'):
                    raise PermissionError(f"No permission to modify {self._doctype}")
        
        # Trigger validate hook if exists
        self._trigger_hook('validate')
        
        # Trigger before_save hook if exists
        self._trigger_hook('before_save')
        
        # Commit changes
        db.session.commit()
        
        # Update attributes
        self._setup_attributes()
        
        # Trigger after_save hook if exists
        self._trigger_hook('after_save')
        
        # Trigger on_update hook if exists
        self._trigger_hook('on_update')
        
        return self
    
    def delete(self, ignore_permissions=False):
        """Delete document from database"""
        if not ignore_permissions:
            # Check permissions (could be expanded)
            if hasattr(self._model, 'has_permission'):
                if not self._model.has_permission(current_user, 'delete'):
                    raise PermissionError(f"No permission to delete {self._doctype}")
        
        # Trigger before_delete hook if exists
        self._trigger_hook('before_delete')
        
        # Delete and commit
        db.session.delete(self._model)
        db.session.commit()
        
        # Trigger after_delete hook if exists
        self._trigger_hook('after_delete')
        
        return True
    
    def db_set(self, field, value, update_modified=True):
        """Set a database field value"""
        setattr(self._model, field, value)
        db.session.commit()
        setattr(self, field, value)  # Also update the wrapper
        return self
    
    def reload(self):
        """Reload document from database"""
        db.session.refresh(self._model)
        self._setup_attributes()
        return self
    
    def _trigger_hook(self, hook_name):
        """Trigger a document hook if it exists"""
        # Check if the model has this method
        if hasattr(self._model, hook_name):
            method = getattr(self._model, hook_name)
            if callable(method):
                method()
        
        # Also check global hooks
        # This would need to be expanded based on how hooks are registered
        from hooks import trigger_hook
        trigger_hook(self._doctype, hook_name, self)

# Hook system for document events
def trigger_hook(doctype, event, doc):
    """Trigger hooks for document events"""
    from hooks import doc_events
    
    if doctype in doc_events and event in doc_events[doctype]:
        method_path = doc_events[doctype][event]
        module_path, method_name = method_path.rsplit('.', 1)
        
        try:
            module = importlib.import_module(module_path)
            method = getattr(module, method_name)
            return method(doc)
        except (ImportError, AttributeError) as e:
            current_app.logger.error(f"Error triggering hook {doctype}.{event}: {e}")
            return None

# Add more Frappe-like functions as needed
def get_meta(doctype):
    """Get metadata for a doctype"""
    # This would be much more complex in actual Frappe
    # Here we'll return a simple structure based on SQLAlchemy model
    model_class = Document.get_model_class(doctype)
    if not model_class:
        raise ValueError(f"DocType {doctype} not found")
    
    fields = []
    for column in sa_inspect(model_class).mapper.column_attrs:
        field_type = "Data"  # Default
        column_obj = getattr(model_class, column.key).property.columns[0]
        
        if str(column_obj.type).startswith('INTEGER'):
            field_type = "Int"
        elif str(column_obj.type).startswith('NUMERIC') or str(column_obj.type).startswith('DECIMAL'):
            field_type = "Float"
        elif str(column_obj.type).startswith('BOOLEAN'):
            field_type = "Check"
        elif str(column_obj.type).startswith('DATE'):
            field_type = "Date"
        elif str(column_obj.type).startswith('DATETIME'):
            field_type = "Datetime"
        
        field = {
            "fieldname": column.key,
            "fieldtype": field_type,
            "label": column.key.replace('_', ' ').title()
        }
        fields.append(field)
    
    return {
        "name": doctype,
        "fields": fields,
        "is_submittable": False,  # This is simplified
        "actions": ["Save", "Delete"]  # Default actions
    }

def get_doc(*args, **kwargs):
    """Shorthand for Document.get_doc"""
    return Document.get_doc(*args, **kwargs)

def new_doc(*args, **kwargs):
    """Shorthand for Document.new_doc"""
    return Document.new_doc(*args, **kwargs)

def db_get_value(*args, **kwargs):
    """Shorthand for Document.db_get_value"""
    return Document.db_get_value(*args, **kwargs)

def get_all(*args, **kwargs):
    """Shorthand for Document.get_all"""
    return Document.get_all(*args, **kwargs)

def db_count(*args, **kwargs):
    """Shorthand for Document.db_count"""
    return Document.db_count(*args, **kwargs)

# Frappe-like utility functions
def has_permission(doctype, ptype="read", doc=None, user=None):
    """Check if user has permission on doctype"""
    if not user:
        user = current_user
    
    # Handle unauthenticated users
    if not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False
    
    # Check roles
    # Administrator always has permission
    if hasattr(user, 'role') and user.role == 'Administrator':
        return True
    
    # HR Manager has permission on most HR doctypes
    if hasattr(user, 'role') and user.role == 'HR Manager':
        hr_doctypes = ['Employee', 'Attendance', 'Leave Application', 'Salary Slip', 
                       'Job Opening', 'Job Applicant', 'Appraisal']
        if doctype in hr_doctypes:
            return True
    
    # Check document-specific permissions
    if doc:
        model_class = Document.get_model_class(doctype)
        if hasattr(model_class, 'has_permission'):
            return model_class.has_permission(doc, user)
    
    # Default to no permission
    return False

def msgprint(message, title=None, indicator=None):
    """Store a message to be displayed (session-based)"""
    if 'messages' not in session:
        session['messages'] = []
    
    msg = {
        'message': message,
        'title': title or 'Message',
        'indicator': indicator or 'blue'
    }
    
    session['messages'].append(msg)

def get_messages():
    """Get and clear stored messages"""
    messages = session.get('messages', [])
    session['messages'] = []
    return messages