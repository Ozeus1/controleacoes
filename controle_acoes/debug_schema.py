import sqlite3
import os

DB_PATH = os.path.join('instance', 'investments.db')

def check_structure():
    if not os.path.exists(DB_PATH):
        print("DB not found")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check User
    print("--- User Columns ---")
    for row in cursor.execute("PRAGMA table_info(user)"):
        print(row)
        
    # Check Asset
    print("\n--- Asset Columns ---")
    for row in cursor.execute("PRAGMA table_info(asset)"):
        print(row)
        
    conn.close()

if __name__ == "__main__":
    check_structure()
