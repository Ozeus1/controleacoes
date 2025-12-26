
import sqlite3
import os

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance', 'investments.db')

def migrate_quotes():
    print(f"Migrating database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    columns = [
        ('current_price', 'FLOAT DEFAULT 0.0'),
        ('daily_change', 'FLOAT DEFAULT 0.0'),
        ('last_update', 'TIMESTAMP')
    ]
    
    for col_name, col_type in columns:
        try:
            cursor.execute(f"ALTER TABLE asset ADD COLUMN {col_name} {col_type}")
            print(f"Added column {col_name}")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e):
                print(f"Column {col_name} already exists.")
            else:
                print(f"Error adding {col_name}: {e}")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate_quotes()
