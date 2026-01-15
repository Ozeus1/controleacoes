import sqlite3
import os

db_path = os.path.join('instance', 'investments.db')

def migrate():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Adding entry_date to option table...")
        cursor.execute("ALTER TABLE option ADD COLUMN entry_date DATE")
        print("Column entry_date added successfully.")
    except Exception as e:
        print(f"Error adding column (might already exist): {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    if os.path.exists(db_path):
        migrate()
    else:
        print(f"Database not found at {db_path}")
