
import sqlite3
import os

db_path = 'investments.db'

def inspect_db():
    print(f"Checking database at: {os.path.abspath(db_path)}")
    if not os.path.exists(db_path):
        print("Database file NOT FOUND at this path.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tables found: {tables}")
    
    for table in tables:
        table_name = table[0]
        print(f"\nProbing table: {table_name}")
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
            
    conn.close()

if __name__ == "__main__":
    inspect_db()
