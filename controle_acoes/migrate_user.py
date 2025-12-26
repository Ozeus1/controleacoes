
import sqlite3
import os

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance', 'investments.db')

def migrate_user():
    print(f"Migrating database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create User table
    try:
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(80) NOT NULL UNIQUE,
            password_hash VARCHAR(128)
        )
        ''')
        print("Created User table.")
    except Exception as e:
        print(f"Error creating User table: {e}")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate_user()
