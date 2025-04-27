#!/usr/bin/env python3
"""
Database Migration Utility for HR Management System

This script provides functionality to migrate data from PostgreSQL to MariaDB
for the HR Management System's transition to the Frappe/ERPNext framework.

Usage:
    python migrate_db.py --source postgresql --target mariadb [--upgrade]
    python migrate_db.py --upgrade (only run schema upgrades)
"""

import argparse
import os
import sys
import json
import logging
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('db_migration.log')
    ]
)
logger = logging.getLogger("db_migration")

try:
    import sqlalchemy
    from sqlalchemy import create_engine, MetaData, Table, Column, inspect
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.ext.declarative import declarative_base
except ImportError:
    logger.error("SQLAlchemy is required for this script. Install it with 'pip install sqlalchemy'.")
    sys.exit(1)

try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    logger.warning("PyMySQL not found. If migrating to MariaDB, install with 'pip install pymysql'.")

try:
    import psycopg2
except ImportError:
    logger.warning("psycopg2 not found. If migrating from PostgreSQL, install with 'pip install psycopg2-binary'.")

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Define base tables and models based on the application
Base = declarative_base()

# SQL transformations for different databases
TRANSFORMATIONS = {
    "postgresql_to_mariadb": {
        "TEXT": "LONGTEXT",
        "BYTEA": "BLOB",
        "BOOLEAN": "TINYINT(1)",
        "SERIAL": "INT AUTO_INCREMENT",
        "BIGSERIAL": "BIGINT AUTO_INCREMENT",
        "now()": "NOW()",
        "current_timestamp": "CURRENT_TIMESTAMP",
        "::text": "",  # PostgreSQL-specific cast to text
    }
}

# Import model declarations
try:
    from app import User, Employee, Department, Attendance, LeaveType, LeaveApplication, \
                   SalaryStructure, SalarySlip, JobOpening, JobApplicant, Appraisal
    MODELS = [User, Employee, Department, Attendance, LeaveType, LeaveApplication, 
              SalaryStructure, SalarySlip, JobOpening, JobApplicant, Appraisal]
except ImportError:
    logger.warning("Unable to import models from app.py. Will use metadata inspection instead.")
    MODELS = []

# Frappe schema mappings
FRAPPE_SCHEMA_MAPPINGS = {
    "User": {
        "table_name": "tabUser",
        "field_mappings": {
            "id": "name",
            "username": "username",
            "email": "email",
            "password_hash": "password",
            "first_name": "first_name",
            "last_name": "last_name",
            "role": "role"
        },
        "additional_fields": {
            "owner": "Administrator",
            "creation": "NOW()",
            "modified": "NOW()",
            "modified_by": "Administrator",
            "docstatus": 0
        }
    },
    "Employee": {
        "table_name": "tabEmployee",
        "field_mappings": {
            "id": "name",
            "employee_id": "employee_id",
            "user_id": "user_id",
            "first_name": "first_name",
            "last_name": "last_name",
            "email": "email",
            "status": "status",
            "gender": "gender",
            "date_of_birth": "date_of_birth",
            "date_of_joining": "date_of_joining",
            "department": "department",
            "designation": "designation",
            "reports_to": "reports_to",
            "company": "company"
        },
        "additional_fields": {
            "owner": "Administrator",
            "creation": "NOW()",
            "modified": "NOW()",
            "modified_by": "Administrator",
            "docstatus": 0
        }
    }
    # Add mappings for other tables as needed
}

def get_connection_uri(db_type: str) -> str:
    """Get database connection URI based on the database type."""
    if db_type == "postgresql":
        return os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/hrdb")
    elif db_type == "mariadb":
        db_user = os.environ.get("DB_USER", "frappe")
        db_password = os.environ.get("DB_PASSWORD", "frappe_password")
        db_host = os.environ.get("DB_HOST", "localhost")
        db_port = os.environ.get("DB_PORT", "3306")
        db_name = os.environ.get("DB_NAME", "hrms")
        return f"mysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

def create_engine_with_retry(uri: str, max_retries: int = 5) -> sqlalchemy.engine.Engine:
    """Create a SQLAlchemy engine with retry logic."""
    for attempt in range(max_retries):
        try:
            engine = create_engine(uri)
            # Test connection
            with engine.connect() as conn:
                conn.execute(sqlalchemy.text("SELECT 1"))
            return engine
        except Exception as e:
            logger.warning(f"Connection attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                raise
            import time
            time.sleep(5)  # Wait before retrying

def get_schema_from_db(engine, schema_name="public") -> dict:
    """Extract database schema from the given engine."""
    inspector = inspect(engine)
    schema = {}
    
    for table_name in inspector.get_table_names(schema=schema_name):
        columns = []
        primary_keys = inspector.get_pk_constraint(table_name, schema=schema_name).get('constrained_columns', [])
        foreign_keys = inspector.get_foreign_keys(table_name, schema=schema_name)
        indices = inspector.get_indexes(table_name, schema=schema_name)
        
        for column in inspector.get_columns(table_name, schema=schema_name):
            column_info = {
                "name": column["name"],
                "type": str(column["type"]),
                "nullable": column.get("nullable", True),
                "default": column.get("default"),
                "primary_key": column["name"] in primary_keys
            }
            columns.append(column_info)
        
        schema[table_name] = {
            "columns": columns,
            "primary_keys": primary_keys,
            "foreign_keys": foreign_keys,
            "indices": indices
        }
    
    return schema

def transform_schema_for_mariadb(schema: dict) -> dict:
    """Transform PostgreSQL schema to be compatible with MariaDB."""
    mariadb_schema = {}
    
    for table_name, table_info in schema.items():
        new_table_info = table_info.copy()
        new_columns = []
        
        for column in table_info["columns"]:
            new_column = column.copy()
            
            # Transform column type
            pg_type = new_column["type"]
            for pg_pattern, mariadb_pattern in TRANSFORMATIONS["postgresql_to_mariadb"].items():
                if pg_pattern in pg_type:
                    new_column["type"] = pg_type.replace(pg_pattern, mariadb_pattern)
            
            # Adjust defaults
            if new_column.get("default"):
                default_value = new_column["default"]
                for pg_default, mariadb_default in TRANSFORMATIONS["postgresql_to_mariadb"].items():
                    if pg_default in default_value:
                        new_column["default"] = default_value.replace(pg_default, mariadb_default)
            
            new_columns.append(new_column)
        
        new_table_info["columns"] = new_columns
        mariadb_schema[table_name] = new_table_info
    
    return mariadb_schema

def generate_mariadb_schema_sql(schema: dict, frappe_mappings: dict = None) -> str:
    """Generate SQL statements to create the MariaDB schema."""
    sql_statements = []
    
    for table_name, table_info in schema.items():
        # Check if we have a Frappe mapping for this table
        frappe_table_name = table_name
        if frappe_mappings and table_name in frappe_mappings:
            frappe_table_name = frappe_mappings[table_name]["table_name"]
        
        columns_sql = []
        primary_keys = []
        
        for column in table_info["columns"]:
            column_name = column["name"]
            
            # Map column name if we have a mapping
            if (frappe_mappings and table_name in frappe_mappings and 
                "field_mappings" in frappe_mappings[table_name] and
                column_name in frappe_mappings[table_name]["field_mappings"]):
                column_name = frappe_mappings[table_name]["field_mappings"][column_name]
            
            column_type = column["type"]
            nullable = "NULL" if column.get("nullable", True) else "NOT NULL"
            default = f"DEFAULT {column['default']}" if column.get("default") else ""
            
            if column.get("primary_key"):
                primary_keys.append(column_name)
            
            columns_sql.append(f"    `{column_name}` {column_type} {nullable} {default}")
        
        # Add Frappe standard fields if we're using Frappe mappings
        if frappe_mappings and table_name in frappe_mappings and "additional_fields" in frappe_mappings[table_name]:
            for field_name, field_default in frappe_mappings[table_name]["additional_fields"].items():
                # Skip if the field already exists
                if any(c["name"] == field_name for c in table_info["columns"]):
                    continue
                
                if field_name in ("creation", "modified"):
                    columns_sql.append(f"    `{field_name}` DATETIME NOT NULL DEFAULT {field_default}")
                elif field_name in ("owner", "modified_by"):
                    columns_sql.append(f"    `{field_name}` VARCHAR(140) NOT NULL DEFAULT '{field_default}'")
                elif field_name == "docstatus":
                    columns_sql.append(f"    `{field_name}` INT NOT NULL DEFAULT {field_default}")
                else:
                    columns_sql.append(f"    `{field_name}` VARCHAR(140) DEFAULT '{field_default}'")
        
        # Add primary key constraint
        if primary_keys:
            primary_key_str = ", ".join(f"`{pk}`" for pk in primary_keys)
            columns_sql.append(f"    PRIMARY KEY ({primary_key_str})")
        
        # Add foreign key constraints
        for fk in table_info.get("foreign_keys", []):
            constrained_columns = ", ".join(f"`{col}`" for col in fk["constrained_columns"])
            referred_columns = ", ".join(f"`{col}`" for col in fk["referred_columns"])
            referred_table = fk["referred_table"]
            
            # Map referred table if we have a mapping
            if frappe_mappings and referred_table in frappe_mappings:
                referred_table = frappe_mappings[referred_table]["table_name"]
            
            fk_name = fk.get("name", f"fk_{table_name}_{referred_table}")
            fk_sql = f"    CONSTRAINT `{fk_name}` FOREIGN KEY ({constrained_columns}) REFERENCES `{referred_table}` ({referred_columns})"
            
            # Add ON DELETE/UPDATE clauses if present
            if "options" in fk and "ondelete" in fk["options"]:
                fk_sql += f" ON DELETE {fk['options']['ondelete']}"
            if "options" in fk and "onupdate" in fk["options"]:
                fk_sql += f" ON UPDATE {fk['options']['onupdate']}"
            
            columns_sql.append(fk_sql)
        
        create_table_sql = f"CREATE TABLE IF NOT EXISTS `{frappe_table_name}` (\n"
        create_table_sql += ",\n".join(columns_sql)
        create_table_sql += "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"
        
        sql_statements.append(create_table_sql)
        
        # Add indices
        for index in table_info.get("indices", []):
            index_name = index.get("name", f"idx_{table_name}_{index['column_names'][0]}")
            index_columns = ", ".join(f"`{col}`" for col in index["column_names"])
            index_type = "UNIQUE" if index.get("unique", False) else ""
            
            index_sql = f"CREATE {index_type} INDEX `{index_name}` ON `{frappe_table_name}` ({index_columns});"
            sql_statements.append(index_sql)
    
    return "\n\n".join(sql_statements)

def extract_data_from_source(source_engine, tables: List[str] = None) -> Dict[str, List[Dict]]:
    """Extract data from the source database."""
    metadata = MetaData()
    metadata.reflect(bind=source_engine)
    
    if not tables:
        tables = metadata.tables.keys()
    
    data = {}
    for table_name in tables:
        if table_name in metadata.tables:
            table = metadata.tables[table_name]
            
            with source_engine.connect() as conn:
                result = conn.execute(table.select())
                rows = [dict(row) for row in result]
                data[table_name] = rows
                logger.info(f"Extracted {len(rows)} rows from {table_name}")
        else:
            logger.warning(f"Table {table_name} not found in source database")
    
    return data

def transform_data_for_frappe(data: Dict[str, List[Dict]], frappe_mappings: dict) -> Dict[str, List[Dict]]:
    """Transform data to match Frappe schema."""
    transformed_data = {}
    
    for table_name, rows in data.items():
        if table_name not in frappe_mappings:
            logger.warning(f"No Frappe mapping found for table {table_name}, skipping transformation")
            transformed_data[table_name] = rows
            continue
        
        mapping = frappe_mappings[table_name]
        frappe_table_name = mapping["table_name"]
        field_mappings = mapping.get("field_mappings", {})
        additional_fields = mapping.get("additional_fields", {})
        
        transformed_rows = []
        for row in rows:
            transformed_row = {}
            
            # Map existing fields
            for old_field, new_field in field_mappings.items():
                if old_field in row:
                    transformed_row[new_field] = row[old_field]
            
            # Add additional fields with defaults
            for field, default in additional_fields.items():
                if field not in transformed_row:
                    if default == "NOW()":
                        transformed_row[field] = datetime.datetime.now()
                    else:
                        transformed_row[field] = default
            
            transformed_rows.append(transformed_row)
        
        transformed_data[frappe_table_name] = transformed_rows
        logger.info(f"Transformed {len(transformed_rows)} rows for {frappe_table_name}")
    
    return transformed_data

def load_data_to_target(target_engine, data: Dict[str, List[Dict]]) -> None:
    """Load transformed data into the target database."""
    metadata = MetaData()
    metadata.reflect(bind=target_engine)
    
    with target_engine.begin() as conn:
        for table_name, rows in data.items():
            if not rows:
                logger.info(f"No data to insert for table {table_name}")
                continue
            
            if table_name in metadata.tables:
                table = metadata.tables[table_name]
                
                # Insert in batches to avoid memory issues
                batch_size = 1000
                for i in range(0, len(rows), batch_size):
                    batch = rows[i:i+batch_size]
                    result = conn.execute(table.insert(), batch)
                    logger.info(f"Inserted batch of {len(batch)} rows into {table_name}")
            else:
                logger.warning(f"Table {table_name} not found in target database, skipping data load")

def apply_frappe_migrations(engine) -> None:
    """Apply Frappe-specific migrations if needed."""
    try:
        from frappe_init import apply_migrations
        apply_migrations(engine)
        logger.info("Applied Frappe migrations successfully")
    except ImportError:
        logger.warning("frappe_init.py not found, skipping Frappe migrations")

def main() -> None:
    """Main function to handle the migration process."""
    parser = argparse.ArgumentParser(description="Database migration utility for HR Management System")
    parser.add_argument("--source", choices=["postgresql"], help="Source database type")
    parser.add_argument("--target", choices=["mariadb"], help="Target database type")
    parser.add_argument("--upgrade", action="store_true", help="Run schema upgrades only (no data migration)")
    
    args = parser.parse_args()
    
    # If only running upgrades, apply Frappe migrations
    if args.upgrade and not (args.source and args.target):
        logger.info("Running schema upgrades only")
        target_uri = get_connection_uri("mariadb")
        target_engine = create_engine_with_retry(target_uri)
        
        apply_frappe_migrations(target_engine)
        logger.info("Schema upgrades completed successfully")
        return
    
    # Full migration requires both source and target
    if not args.source or not args.target:
        parser.error("Both --source and --target are required for migration")
    
    logger.info(f"Starting migration from {args.source} to {args.target}")
    
    # Connect to source and target databases
    source_uri = get_connection_uri(args.source)
    target_uri = get_connection_uri(args.target)
    
    logger.info(f"Connecting to source database: {source_uri.split('@')[-1]}")
    source_engine = create_engine_with_retry(source_uri)
    
    logger.info(f"Connecting to target database: {target_uri.split('@')[-1]}")
    target_engine = create_engine_with_retry(target_uri)
    
    # Extract schema from source
    logger.info("Extracting schema from source database")
    source_schema = get_schema_from_db(source_engine)
    
    # Transform schema for target
    logger.info(f"Transforming schema for {args.target}")
    if args.target == "mariadb":
        target_schema = transform_schema_for_mariadb(source_schema)
    else:
        target_schema = source_schema
    
    # Generate and execute schema creation SQL
    logger.info(f"Generating schema creation SQL for {args.target}")
    schema_sql = generate_mariadb_schema_sql(target_schema, FRAPPE_SCHEMA_MAPPINGS)
    
    # Write schema SQL to file for reference
    schema_file = Path(f"schema_{args.target}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.sql")
    schema_file.write_text(schema_sql)
    logger.info(f"Schema SQL written to {schema_file}")
    
    # Execute schema creation
    logger.info("Creating schema in target database")
    with target_engine.begin() as conn:
        for statement in schema_sql.split(";"):
            if statement.strip():
                conn.execute(sqlalchemy.text(statement + ";"))
    
    # Extract, transform, and load data
    if not args.upgrade:
        logger.info("Extracting data from source database")
        source_data = extract_data_from_source(source_engine)
        
        if args.target == "mariadb" and FRAPPE_SCHEMA_MAPPINGS:
            logger.info("Transforming data for Frappe schema")
            target_data = transform_data_for_frappe(source_data, FRAPPE_SCHEMA_MAPPINGS)
        else:
            target_data = source_data
        
        logger.info("Loading data into target database")
        load_data_to_target(target_engine, target_data)
    
    # Apply Frappe-specific migrations if needed
    if args.target == "mariadb":
        apply_frappe_migrations(target_engine)
    
    logger.info("Migration completed successfully")

if __name__ == "__main__":
    main()