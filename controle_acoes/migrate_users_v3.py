import sqlite3
import os

DB_PATH = os.path.join('instance', 'investments.db')

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Update USER table
        print("Migrating User table...")
        columns = [row[1] for row in cursor.execute("PRAGMA table_info(user)")]
        if 'role' not in columns:
            cursor.execute("ALTER TABLE user ADD COLUMN role TEXT DEFAULT 'user'")
            print("Added 'role' to user")
        if 'expiry_date' not in columns:
            cursor.execute("ALTER TABLE user ADD COLUMN expiry_date DATE")
            print("Added 'expiry_date' to user")
        
        # Set Admin Role for User ID 1 (Assuming 1 is the main user)
        cursor.execute("UPDATE user SET role = 'admin' WHERE id = 1")
        
        # 2. Update ASSETS and other tables
        tables = ['asset', 'trade_history', 'option', 'settings', 'fixed_income', 
                  'investment_fund', 'crypto', 'pension', 'international']
        
        for table in tables:
            print(f"Migrating {table} table...")
            # Check if table exists first (some might be UpperCase or different depending on SQLAlchemy, usually lowercase)
            # Actually SQLAlchemy defaults to snakecase class name usually.
            
            # Verify table existence
            try:
                cursor.execute(f"SELECT 1 FROM {table} LIMIT 1")
            except sqlite3.OperationalError:
                print(f"Table {table} not found, skipping...")
                continue
                
            t_columns = [row[1] for row in cursor.execute(f"PRAGMA table_info({table})")]
            if 'user_id' not in t_columns:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER DEFAULT 1")
                print(f"Added 'user_id' to {table}")
                # Add Foreign Key constraint is hard in SQLite ALTER, but column is enough for app logic.
        
        conn.commit()
        print("Migration V3 Complete!")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
