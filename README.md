# HR Management System

A comprehensive HR Management System built on the Frappe/ERPNext framework, designed to provide a seamless and interactive employee experience with a robust DocType-based structure.

![HR Management System](generated-icon.png)

## Table of Contents

- [Features](#features)
- [Technology Stack](#technology-stack)
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Local Development](#local-development)
  - [Using Docker](#using-docker)
  - [Using Docker Compose](#using-docker-compose)
- [Environment Variables](#environment-variables)
- [Database Setup](#database-setup)
  - [MariaDB Configuration](#mariadb-configuration)
  - [Migration from PostgreSQL](#migration-from-postgresql)
- [Project Structure](#project-structure)
- [Core Functionalities](#core-functionalities)
- [API Documentation](#api-documentation)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Employee Management**: Complete employee lifecycle management from onboarding to offboarding
- **Attendance Tracking**: Daily attendance, monthly reports, and bulk upload features
- **Leave Management**: Leave applications, approvals, and balance tracking
- **Payroll Management**: Salary structures, salary slips, and payroll processing
- **Recruitment**: Job openings, applicant tracking, and interview management
- **Performance Management**: Appraisals, goals, and feedback
- **Reporting**: Comprehensive reports on employees, attendance, leaves, and payroll
- **User Management**: Role-based access control (Employee, HR Manager, Administrator)
- **Modern UI**: Responsive design with interactive charts and data visualization

## Technology Stack

- **Backend Framework**: Frappe with Flask compatibility layer
- **Frontend**: HTML5, CSS3, JavaScript with Bootstrap 5 and Frappe UI components
- **Database**: MariaDB (PostgreSQL support during migration)
- **ORM**: Frappe ORM with SQLAlchemy bridge
- **Authentication**: Frappe User System with Flask-Login compatibility
- **Web Server**: Gunicorn (Production)
- **Additional Libraries**:
  - Frappe Framework for document management and business logic
  - Flask-SQLAlchemy for database operations during migration
  - WebSocket support for real-time updates
  - Python-dotenv for environment variables

## Installation

### Prerequisites

- Python 3.11 or higher
- MariaDB (or PostgreSQL during migration)
- Node.js 16+ (for Frappe frontend assets)
- pip (Python package manager)

### Local Development

1. Clone the repository
```bash
git clone https://github.com/yourusername/hr-management-system.git
cd hr-management-system
```

2. Create and activate a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
```bash
cp .env.example .env
# Edit .env file with your database credentials and other configuration
```

5. Initialize the database
```bash
# If using MariaDB (recommended)
python setup.py --init-db
# If still using PostgreSQL during migration
python -c "from app import db; db.create_all()"
```

6. Run the development server
```bash
flask run --host=0.0.0.0 --port=5000
```

### Using Docker

1. Build the Docker image
```bash
docker build -t hr-management-system .
```

2. Run the container
```bash
docker run -p 5000:5000 --env-file .env hr-management-system
```

### Using Docker Compose

For a complete development or production environment with MariaDB:

1. Make sure Docker and Docker Compose are installed

2. Launch the application stack
```bash
docker-compose up -d
```

3. Access the application at http://localhost:5000

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```
# Application configuration
FLASK_APP=app_frappe.py
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=your_secret_key

# Database configuration (PostgreSQL for migration)
DATABASE_URL=postgresql://username:password@localhost:5432/hrdb

# Database configuration (MariaDB for Frappe)
DB_HOST=mariadb
DB_NAME=hrms
DB_USER=frappe
DB_PASSWORD=frappe_password
DB_ROOT_PASSWORD=mariadb_root_password
DB_PORT=3306

# Frappe configuration
FRAPPE_SITE_NAME=hrms.localhost
ADMIN_PASSWORD=admin_password
```

## Database Setup

### MariaDB Configuration

The system is migrating to MariaDB for Frappe compatibility. Set up MariaDB using the following commands:

```sql
CREATE DATABASE hrms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'frappe'@'%' IDENTIFIED BY 'frappe_password';
GRANT ALL PRIVILEGES ON hrms.* TO 'frappe'@'%';
FLUSH PRIVILEGES;
```

### Migration from PostgreSQL

If you're migrating from the previous PostgreSQL database, use the provided migration script:

```bash
python migrate_db.py --source postgresql --target mariadb
```

This script will:
1. Export data from PostgreSQL
2. Transform it to match the Frappe data model
3. Import it into MariaDB with proper validation

## Project Structure

```
hr-management-system/
├── app.py                  # Flask application file (during migration)
├── app_frappe.py           # Main Frappe application entry point
├── fixed_app.py            # Enhanced Flask app with Frappe hooks
├── frappe_compat.py        # Compatibility layer for Frappe/Flask
├── frappe_init.py          # Frappe initialization utilities
├── hooks.py                # Frappe hooks definition
├── templates/              # Frappe templates
│   ├── includes/          # Partial templates for inclusion
│   │   └── job_opening_row.html # Job opening card template
│   ├── pages/             # Page templates
│   │   ├── jobs.html      # Job listings page
│   │   └── job_application.html # Job application form
│   └── web.html           # Base web template
├── hrms/                   # Application module (Frappe style)
│   ├── api.py             # API endpoints
│   ├── hr/                # HR module
│   │   └── doctype/       # HR DocTypes
│   │       ├── employee/  # Employee doctype
│   │       │   ├── employee.py  # Employee controller
│   │       │   └── employee.json # Employee schema
│   │       ├── attendance/ # Attendance doctype
│   │       ├── leave_application/ # Leave application doctype
│   │       └── leave_type/ # Leave type doctype
│   ├── payroll/           # Payroll module
│   │   └── doctype/       # Payroll DocTypes
│   │       ├── salary_structure/ # Salary structure doctype
│   │       └── salary_slip/ # Salary slip doctype
│   └── recruitment/       # Recruitment module
│       └── doctype/       # Recruitment DocTypes
│           ├── job_opening/ # Job opening doctype
│           └── job_applicant/ # Job applicant doctype
├── frappe-bench/          # Frappe bench directory (for bench tooling)
├── static/                # Static assets
│   ├── css/               # CSS stylesheets
│   ├── js/                # JavaScript files
│   └── img/               # Images
├── migrate_db.py          # Database migration utility
├── docker-compose.yml     # Docker Compose configuration
├── Dockerfile             # Production-ready Docker configuration
├── MIGRATION_PLAN.md      # Migration strategy documentation
├── pyproject.toml         # Project dependencies
├── requirements.txt       # Explicit dependencies list
└── README.md              # Project documentation
```

## Core Functionalities

### User Management
- Role-based access control (Employee, HR Manager, Administrator)
- Secure authentication using password hashing

### Employee Management
- Complete employee profile management
- Department and designation tracking
- Reporting structure

### Attendance Management
- Daily attendance tracking
- Monthly attendance reports
- Bulk attendance upload

### Leave Management
- Leave application and approval workflow
- Different leave types with custom rules
- Leave balance tracking

### Payroll Management
- Salary structure configuration
- Salary slip generation
- Payroll processing

### Recruitment
- Job opening creation and management
- Applicant tracking system
- Interview scheduling and feedback

### Performance Management
- Performance appraisals
- Goal setting and tracking
- 360-degree feedback system

### Reporting
- Employee reports
- Attendance reports
- Leave reports
- Payroll reports

## API Documentation

The system provides RESTful and WebSocket API endpoints following Frappe standards:

### Core Data Endpoints

#### Employee Dashboard Data
```
GET /api/method/hrms.api.get_employee_dashboard_data
```
Returns data for the employee dashboard including attendance summary, leave balance, recent activities, etc.

#### HR Dashboard Data
```
GET /api/method/hrms.api.get_hr_dashboard_data
```
Returns data for the HR dashboard including employee count, attendance data, pending leave applications, open job positions, etc.

### DocType API Endpoints

All Frappe DocTypes expose standard REST endpoints:

```
GET /api/resource/{doctype}                # List all documents of a DocType
POST /api/resource/{doctype}               # Create a new document
GET /api/resource/{doctype}/{name}         # Get a specific document
PUT /api/resource/{doctype}/{name}         # Update a document
DELETE /api/resource/{doctype}/{name}      # Delete a document
```

### WebSocket Notifications

Real-time updates are delivered through WebSocket connections:

```
WebSocket: /ws
```

Clients can subscribe to document changes with:
```javascript
socket.send(JSON.stringify({
  cmd: "subscribe",
  doctype: "DocType",
  name: "document_name"
}));
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.