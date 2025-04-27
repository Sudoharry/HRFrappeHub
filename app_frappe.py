"""
HR Management System with Frappe Compatibility

This is the main entry point for the HR Management System
that integrates with the Frappe compatibility layer.
"""

# Import the fixed app with Frappe compatibility
from fixed_app import app

# Run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)