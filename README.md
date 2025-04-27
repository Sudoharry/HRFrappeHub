# HR Management System

A comprehensive HR Management System built with Flask and PostgreSQL, designed to provide a seamless and interactive employee experience.

![HR Management System](generated-icon.png)

## Table of Contents

- [Features](#features)
- [Technology Stack](#technology-stack)
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Local Development](#local-development)
  - [Using Docker](#using-docker)
- [Environment Variables](#environment-variables)
- [Database Setup](#database-setup)
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

- **Backend**: Python 3.11 with Flask framework
- **Frontend**: HTML5, CSS3, JavaScript with Bootstrap 5
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Authentication**: Flask-Login
- **Web Server**: Gunicorn (Production)
- **Additional Libraries**:
  - Flask-SocketIO for real-time updates
  - Flask-WTF for form handling
  - Python-dotenv for environment variables

## Installation

### Prerequisites

- Python 3.11 or higher
- PostgreSQL
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
pip install .
```

4. Set up environment variables
```bash
cp .env.example .env
# Edit .env file with your database credentials and other configuration
```

5. Initialize the database
```bash
python -c "from app import db; db.create_all()"
```

6. Run the development server
```bash
flask run
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

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=1
DATABASE_URL=postgresql://username:password@localhost:5432/hrdb
SECRET_KEY=your_secret_key
```

## Database Setup

The system uses PostgreSQL as the database. You need to create a PostgreSQL database and set the `DATABASE_URL` environment variable.

```sql
CREATE DATABASE hrdb;
CREATE USER hruser WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE hrdb TO hruser;
```

## Project Structure

```
hr-management-system/
├── app.py                  # Main application file
├── models.py               # Database models (included in app.py)
├── templates/              # HTML templates
│   ├── modern/            # Modern UI templates
│   │   ├── base.html      # Base template with navigation
│   │   ├── hr_dashboard.html  # HR dashboard template
│   │   ├── employee_portal.html  # Employee portal
│   │   ├── login.html     # Login page
│   │   └── ... (other templates)
├── static/                # Static files (CSS, JS, images)
│   ├── css/               # CSS stylesheets
│   ├── js/                # JavaScript files
│   └── img/               # Images
├── instance/              # Instance-specific files
│   └── hrms.db            # SQLite database (development only)
├── hrms/                  # Module directory
│   ├── api.py             # API functions
│   ├── hooks.py           # Event hooks
│   ├── hrms_controller.py # Controller functions
│   └── ... (other module files)
├── Dockerfile             # Docker configuration
├── pyproject.toml         # Project dependencies
├── uv.lock                # Package lock file
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

The system provides two main API endpoints:

### Employee Dashboard Data
```
GET /api/employee-dashboard-data
```
Returns data for the employee dashboard including attendance summary, leave balance, recent activities, etc.

### HR Dashboard Data
```
GET /api/hr-dashboard-data
```
Returns data for the HR dashboard including employee count, attendance data, pending leave applications, open job positions, etc.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.