
import sqlite3
import os

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance', 'investments.db')

def migrate_fii_type():
    print(f"Migrating database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE asset ADD COLUMN fii_type VARCHAR(50)")
        print("Added column fii_type to asset.")
    except sqlite3.OperationalError as e:
        if 'duplicate column name' in str(e):
            print("Column fii_type already exists.")
        else:
            print(f"Error adding fii_type: {e}")
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate_fii_type()
