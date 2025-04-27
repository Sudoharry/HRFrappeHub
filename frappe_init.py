"""
Frappe Framework Initializer for Flask App

This module updates the Flask app to use the Frappe compatibility layer.
"""

import logging
from frappe_compat import init_app, Document, whitelist, has_permission, msgprint, get_messages

def init_frappe_compat(app, db):
    """Initialize Frappe compatibility layer with Flask app"""
    logging.info("Initializing Frappe compatibility layer")
    
    # Initialize frappe_compat with db
    init_app(db)
    
    # Add Frappe-like functions to the global namespace
    app.jinja_env.globals.update(
        has_permission=has_permission,
        msgprint=msgprint,
        get_messages=get_messages
    )
    
    # Register template helper functions
    @app.context_processor
    def inject_frappe_helpers():
        return {
            'get_messages': get_messages,
            'has_permission': has_permission
        }
    
    logging.info("Frappe compatibility layer initialized")
    
    return app

def convert_models_to_doctypes():
    """Convert existing SQLAlchemy models to Frappe DocTypes"""
    # This would be a more extensive process in a real migration
    # For now, we'll just ensure our compatibility layer can work with them
    pass

# Adapters for specific modules
def init_hr_module(app):
    """Initialize HR module with Frappe-like functionality"""
    # Setup HR module hooks and customizations
    pass

def init_payroll_module(app):
    """Initialize Payroll module with Frappe-like functionality"""
    # Setup Payroll module hooks and customizations
    pass

def init_recruitment_module(app):
    """Initialize Recruitment module with Frappe-like functionality"""
    # Setup Recruitment module hooks and customizations
    pass

def init_performance_module(app):
    """Initialize Performance module with Frappe-like functionality"""
    # Setup Performance module hooks and customizations
    pass