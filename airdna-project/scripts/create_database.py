#!/usr/bin/env python3
"""
Create SQLite database from schema.sql
Run this first before loading data.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'airbnb.db')
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), '..', 'schema.sql')

def create_database():
    """Create the SQLite database and execute schema."""
    # Ensure db directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    # Read schema
    with open(SCHEMA_PATH, 'r') as f:
        schema = f.read()

    # Create database and execute schema
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(schema)
    conn.close()

    print(f"Database created at: {os.path.abspath(DB_PATH)}")
    print("Schema executed successfully!")

if __name__ == '__main__':
    create_database()
