import sqlite3
import os

def init_database():
    """Initialize the network dashboard database"""
    db_path = 'data/network.db'

    # Create data directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Read database schema
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r') as f:
        schema = f.read()

    # Create database and tables
    conn = sqlite3.connect(db_path)
    conn.executescript(schema)
    conn.close()

    print(f"Database initialized successfully at: {db_path}")

if __name__ == '__main__':
    init_database()
