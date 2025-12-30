
import sqlite3
import os

db_path = os.path.join('instance', 'investments.db')
print(f"Checking DB: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(option)")
    columns = cursor.fetchall()
    
    print("--- Option Table Columns ---")
    found_cols = []
    for col in columns:
        print(col)
        found_cols.append(col[1])
        
    required = ['current_option_price', 'sale_price', 'last_update']
    missing = [c for c in required if c not in found_cols]
    
    if missing:
        print(f"MISSING COLUMNS: {missing}")
    else:
        print("Schema looks OK (checked current_option_price, sale_price, last_update)")
        
    conn.close()
    
except Exception as e:
    print(f"Error checking DB: {e}")
