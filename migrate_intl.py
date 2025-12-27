import sqlite3
import os

# Path to database
db_path = os.path.join(os.getcwd(), 'controle_acoes', 'instance', 'investments.db')

print(f"Connecting to database at: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Add columns if they don't exist
    columns = [
        ('category', 'TEXT DEFAULT "RV"'),
        ('description', 'TEXT'),
        ('invested_value', 'REAL')
    ]

    for col_name, col_type in columns:
        try:
            print(f"Attempting to add column {col_name}...")
            cursor.execute(f"ALTER TABLE international ADD COLUMN {col_name} {col_type}")
            print(f"Column {col_name} added successfully.")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e):
                print(f"Column {col_name} already exists.")
            else:
                print(f"Error adding {col_name}: {e}")

    conn.commit()
    conn.close()
    print("Migration completed.")

except Exception as e:
    print(f"Migration failed: {e}")
