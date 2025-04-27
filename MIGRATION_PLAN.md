# Migration Plan: Flask HR System to Frappe/ERPNext

## Current State Analysis

Our project currently has:

1. A Flask application (`app.py`) with SQLAlchemy models for HR entities
2. A partially set up Frappe/ERPNext structure in the `hrms` directory with:
   - Proper DocType JSON definitions
   - Python controllers for DocTypes
   - API modules
   - Hooks configuration

However, the Frappe framework itself is not fully installed or operational.

## Migration Strategy

Since setting up a full Frappe environment is challenging in this environment, we will implement a hybrid approach that allows us to gradually transition:

### Phase 1: Document Structure Alignment

1. Ensure our Flask SQLAlchemy models match the structure of Frappe DocTypes
2. Create utility functions to convert between SQLAlchemy objects and Frappe-style documents
3. Implement Frappe-like document API in our Flask app

### Phase 2: Migration of Business Logic

1. Move business logic from Flask routes to DocType controller methods
2. Implement Frappe hooks-like functionality within our Flask app
3. Set up Frappe-style permission system

### Phase 3: Web Interface Adaptation

1. Update templates to use Frappe UI patterns and concepts
2. Implement desk-like functionality for HR Manager interfaces
3. Create employee portal with Frappe-style web forms

### Phase 4: API Transition

1. Implement Frappe-style REST API endpoints
2. Add support for Frappe's whitelisted methods pattern
3. Create compatibility layer for both systems during transition

## Implementation Steps

### 1. Create Models Compatibility Layer

Create a layer that allows us to use Frappe-style syntax with our SQLAlchemy models:

```python
# frappe_compat.py

class Document:
    """Base class for document-like functionality with SQLAlchemy models"""
    
    @classmethod
    def get_doc(cls, doctype, name=None, filters=None):
        """Frappe-like get_doc implementation using SQLAlchemy"""
        # Implementation that maps to SQLAlchemy queries
        pass
    
    @classmethod
    def new_doc(cls, doctype):
        """Create a new document of the specified doctype"""
        # Implementation that creates SQLAlchemy model instances
        pass
    
    def insert(self, ignore_permissions=False):
        """Insert document into database"""
        # Add to session and commit
        pass
    
    def save(self, ignore_permissions=False):
        """Save document to database"""
        # Commit changes
        pass
    
    def delete(self):
        """Delete document from database"""
        # Delete and commit
        pass
    
    # More Frappe compatibility methods
```

### 2. Implement DocType Controllers in Flask

Adapt the existing Frappe DocType controllers to work with our Flask app:

```python
# employee_controller.py

from frappe_compat import Document
from models import Employee

class EmployeeController:
    def validate(self):
        # Validation logic from Frappe controller
        pass
    
    def on_update(self):
        # Update hooks from Frappe controller
        pass
    
    def has_permission(self, user):
        # Permission checks from Frappe controller
        pass
```

### 3. Update API Layer

Create a wrapper around our Flask routes to make them behave like Frappe API endpoints:

```python
# api.py

def whitelist(fn=None, allow_guest=False):
    """Decorator for API methods similar to Frappe's"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            # Check permissions
            # Handle response formatting
            return f(*args, **kwargs)
        return wrapper
    
    if fn:
        return decorator(fn)
    return decorator

@whitelist()
def get_employee_dashboard_data(employee=None):
    # Existing API logic
    pass
```

### 4. Implement Frappe-like Hooks

Create a hooks system to mimic Frappe's event system:

```python
# hooks.py

doc_events = {
    "User": {
        "after_insert": "hrms.hrms_controller.create_employee_for_user"
    },
    "Employee": {
        "on_update": "hrms.hrms_controller.update_employee_details"
    },
    # etc.
}

def trigger_hook(doctype, event, doc):
    """Trigger hooks for document events"""
    if doctype in doc_events and event in doc_events[doctype]:
        method = doc_events[doctype][event]
        module_path, method_name = method.rsplit('.', 1)
        module = importlib.import_module(module_path)
        method = getattr(module, method_name)
        return method(doc)
```

### 5. Update Template Rendering

Modify our templates to include Frappe-style components and layouts.

### 6. Implement Permission System

Create a permission system that mimics Frappe's role-based permissions.

## Long-term Strategy

While we implement this hybrid approach for immediate functionality, we should continue working toward:

1. Setting up a proper Frappe bench environment in a development environment
2. Fully migrating to the Frappe/ERPNext architecture
3. Creating a proper ERPNext app that can be installed through bench

This migration plan allows us to start using Frappe concepts and patterns immediately while working toward a full migration to the Frappe/ERPNext ecosystem.