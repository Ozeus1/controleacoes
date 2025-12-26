
import sqlite3
import os

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance', 'investments.db')

def migrate_history():
    print(f"Migrating database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Add entry_date to asset
    try:
        cursor.execute("ALTER TABLE asset ADD COLUMN entry_date DATE")
        print("Added column entry_date to asset.")
    except sqlite3.OperationalError as e:
        if 'duplicate column name' in str(e):
            print("Column entry_date already exists.")
        else:
            print(f"Error adding entry_date: {e}")
            
    # 2. Create TradeHistory table
    try:
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker VARCHAR(10) NOT NULL,
            strategy VARCHAR(50),
            entry_date DATE,
            exit_date DATE,
            buy_price FLOAT,
            sell_price FLOAT,
            quantity INTEGER,
            profit_value FLOAT,
            profit_pct FLOAT,
            days_held INTEGER,
            reason VARCHAR(20)
        )
        ''')
        print("Created TradeHistory table.")
    except Exception as e:
        print(f"Error creating TradeHistory table: {e}")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate_history()
