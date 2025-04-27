-- MariaDB initialization script for Frappe HRMS

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS hrms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user and grant privileges
CREATE USER IF NOT EXISTS 'frappe'@'%' IDENTIFIED BY 'frappe_password';
GRANT ALL PRIVILEGES ON hrms.* TO 'frappe'@'%';
FLUSH PRIVILEGES;

-- Set MariaDB parameters for Frappe compatibility
SET GLOBAL character_set_server = 'utf8mb4';
SET GLOBAL collation_server = 'utf8mb4_unicode_ci';

-- This should be set in the my.cnf file for production, but we set it here for dev
SET GLOBAL innodb_file_format = 'Barracuda';
SET GLOBAL innodb_file_per_table = 1;
SET GLOBAL innodb_large_prefix = 1;

-- Create Frappe system tables if they don't exist
USE hrms;

-- Common fields for all DocTypes
CREATE TABLE IF NOT EXISTS `tabDocType` (
  `name` varchar(140) NOT NULL,
  `owner` varchar(140) NOT NULL,
  `creation` datetime NOT NULL,
  `modified` datetime NOT NULL,
  `modified_by` varchar(140) NOT NULL,
  `docstatus` int(1) NOT NULL DEFAULT 0,
  `module` varchar(140) NOT NULL,
  `custom` int(1) NOT NULL DEFAULT 0,
  `is_virtual` int(1) NOT NULL DEFAULT 0,
  `is_submittable` int(1) NOT NULL DEFAULT 0,
  `title_field` varchar(140) DEFAULT NULL,
  PRIMARY KEY (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert basic Frappe DocTypes needed for the system
INSERT IGNORE INTO `tabDocType` (`name`, `owner`, `creation`, `modified`, `modified_by`, `docstatus`, `module`, `custom`, `is_virtual`, `is_submittable`, `title_field`) 
VALUES 
('User', 'Administrator', NOW(), NOW(), 'Administrator', 0, 'Core', 0, 0, 0, 'full_name'),
('Role', 'Administrator', NOW(), NOW(), 'Administrator', 0, 'Core', 0, 0, 0, 'role_name'),
('Employee', 'Administrator', NOW(), NOW(), 'Administrator', 0, 'HR', 0, 0, 0, 'employee_name'),
('Department', 'Administrator', NOW(), NOW(), 'Administrator', 0, 'HR', 0, 0, 0, 'department_name'),
('Attendance', 'Administrator', NOW(), NOW(), 'Administrator', 0, 'HR', 0, 0, 1, NULL),
('Leave Type', 'Administrator', NOW(), NOW(), 'Administrator', 0, 'HR', 0, 0, 0, 'leave_type_name'),
('Leave Application', 'Administrator', NOW(), NOW(), 'Administrator', 0, 'HR', 0, 0, 1, NULL),
('Salary Structure', 'Administrator', NOW(), NOW(), 'Administrator', 0, 'Payroll', 0, 0, 1, 'salary_structure_name'),
('Salary Slip', 'Administrator', NOW(), NOW(), 'Administrator', 0, 'Payroll', 0, 0, 1, NULL),
('Job Opening', 'Administrator', NOW(), NOW(), 'Administrator', 0, 'Recruitment', 0, 0, 0, 'job_title'),
('Job Applicant', 'Administrator', NOW(), NOW(), 'Administrator', 0, 'Recruitment', 0, 0, 0, 'applicant_name');

-- Create Role table for access control
CREATE TABLE IF NOT EXISTS `tabRole` (
  `name` varchar(140) NOT NULL,
  `owner` varchar(140) NOT NULL,
  `creation` datetime NOT NULL,
  `modified` datetime NOT NULL,
  `modified_by` varchar(140) NOT NULL,
  `docstatus` int(1) NOT NULL DEFAULT 0,
  `role_name` varchar(140) NOT NULL,
  `desk_access` int(1) NOT NULL DEFAULT 1,
  `is_custom` int(1) NOT NULL DEFAULT 0,
  `disabled` int(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`name`),
  UNIQUE KEY `role_name` (`role_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert default roles
INSERT IGNORE INTO `tabRole` (`name`, `owner`, `creation`, `modified`, `modified_by`, `docstatus`, `role_name`, `desk_access`, `is_custom`, `disabled`)
VALUES
('Administrator', 'Administrator', NOW(), NOW(), 'Administrator', 0, 'Administrator', 1, 0, 0),
('System Manager', 'Administrator', NOW(), NOW(), 'Administrator', 0, 'System Manager', 1, 0, 0),
('HR Manager', 'Administrator', NOW(), NOW(), 'Administrator', 0, 'HR Manager', 1, 0, 0),
('HR User', 'Administrator', NOW(), NOW(), 'Administrator', 0, 'HR User', 1, 0, 0),
('Employee', 'Administrator', NOW(), NOW(), 'Administrator', 0, 'Employee', 1, 0, 0),
('Guest', 'Administrator', NOW(), NOW(), 'Administrator', 0, 'Guest', 0, 0, 0);

-- Create User table
CREATE TABLE IF NOT EXISTS `tabUser` (
  `name` varchar(140) NOT NULL,
  `owner` varchar(140) NOT NULL,
  `creation` datetime NOT NULL,
  `modified` datetime NOT NULL,
  `modified_by` varchar(140) NOT NULL,
  `docstatus` int(1) NOT NULL DEFAULT 0,
  `username` varchar(140) DEFAULT NULL,
  `email` varchar(140) NOT NULL,
  `password` varchar(512) DEFAULT NULL,
  `first_name` varchar(140) DEFAULT NULL,
  `last_name` varchar(140) DEFAULT NULL,
  `full_name` varchar(140) GENERATED ALWAYS AS (CONCAT_WS(' ', NULLIF(`first_name`,''), NULLIF(`last_name`,''))) STORED,
  `enabled` int(1) NOT NULL DEFAULT 1,
  `user_type` varchar(20) DEFAULT 'System User',
  `role` varchar(140) DEFAULT NULL,
  PRIMARY KEY (`name`),
  UNIQUE KEY `email` (`email`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert Administrator user
INSERT IGNORE INTO `tabUser` (`name`, `owner`, `creation`, `modified`, `modified_by`, `docstatus`, `username`, `email`, `password`, `first_name`, `last_name`, `enabled`, `user_type`, `role`)
VALUES
('Administrator', 'Administrator', NOW(), NOW(), 'Administrator', 0, 'Administrator', 'admin@example.com', '$2b$12$SVOzG5fiUIhkgXFrmJNgX.e5A0MKrtz5N1aWtqewq468XLc4tW8Mq', 'System', 'Administrator', 1, 'System User', 'Administrator');