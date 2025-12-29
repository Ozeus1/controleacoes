import sqlite3
import os

DB_PATH = 'instance/investments.db'

# Fallback checking
if not os.path.exists(DB_PATH) and os.path.exists('instance/financas.db'):
    DB_PATH = 'instance/financas.db'

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}. Checking current directory...")
        if os.path.exists('investments.db'):
             # Handle case where run from inside instance path? Unlikely.
             pass
        print(f"CRITICAL: Database file not found. Expected at {os.path.abspath(DB_PATH)}")
        return

    print(f"Migrating database: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Checking database schema updates...")

    try:
        # 1. Update 'asset' table with 'sector'
        print("Checking 'asset' table...")
        cursor.execute("PRAGMA table_info(asset)")
        asset_cols = [row[1] for row in cursor.fetchall()]
        if 'sector' not in asset_cols:
            print("Adding column 'sector' to 'asset'...")
            cursor.execute("ALTER TABLE asset ADD COLUMN sector VARCHAR(50)")
        else:
            print("Column 'sector' already exists in 'asset'.")

        # 2. Update 'crypto' table with 'avg_price'
        print("Checking 'crypto' table...")
        cursor.execute("PRAGMA table_info(crypto)")
        crypto_cols = [row[1] for row in cursor.fetchall()]
        if 'avg_price' not in crypto_cols:
            print("Adding column 'avg_price' to 'crypto'...")
            cursor.execute("ALTER TABLE crypto ADD COLUMN avg_price FLOAT DEFAULT 0.0")
        else:
            print("Column 'avg_price' already exists in 'crypto'.")

        # 3. Update 'international' table with new fields
        print("Checking 'international' table...")
        cursor.execute("PRAGMA table_info(international)")
        intl_cols = [row[1] for row in cursor.fetchall()]
        
        intl_updates = [
            ("category", "VARCHAR(10) DEFAULT 'RV'"),
            ("purchase_price", "FLOAT"),
            ("invested_value", "FLOAT"),
            ("current_price", "FLOAT"),
            ("description", "VARCHAR(100)")
        ]
        
        for col_name, col_type in intl_updates:
            if col_name not in intl_cols:
                print(f"Adding column '{col_name}' to 'international'...")
                cursor.execute(f"ALTER TABLE international ADD COLUMN {col_name} {col_type}")
            else:
                print(f"Column '{col_name}' already exists in 'international'.")
        
        conn.commit()
        print("All migrations completed successfully.")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
