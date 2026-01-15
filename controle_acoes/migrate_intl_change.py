import sqlite3
import os

db_path = os.path.join('instance', 'investments.db')

def migrate():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Adding daily_change to international table...")
        cursor.execute("ALTER TABLE international ADD COLUMN daily_change REAL DEFAULT 0.0")
        print("Column daily_change added successfully.")
    except Exception as e:
        print(f"Error adding column (might already exist): {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    if os.path.exists(db_path):
        migrate()
    else:
        print(f"Database not found at {db_path}")
