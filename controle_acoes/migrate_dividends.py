import sqlite3
import os

DB_PATH = 'instance/investments.db'

# Fallback checking
if not os.path.exists(DB_PATH) and os.path.exists('instance/financas.db'):
    DB_PATH = 'instance/financas.db'

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Checking database for 'dividend' table...")

    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='dividend'")
        if cursor.fetchone():
            print("Table 'dividend' already exists.")
        else:
            print("Creating 'dividend' table...")
            cursor.execute('''
                CREATE TABLE dividend (
                    id INTEGER PRIMARY KEY,
                    asset_id INTEGER NOT NULL,
                    ticker VARCHAR(10) NOT NULL,
                    type VARCHAR(20) NOT NULL,
                    payment_date DATE,
                    ex_date DATE,
                    amount FLOAT NOT NULL,
                    FOREIGN KEY(asset_id) REFERENCES asset(id)
                )
            ''')
            print("Table 'dividend' created.")

        conn.commit()
        print("Migration completed successfully.")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
