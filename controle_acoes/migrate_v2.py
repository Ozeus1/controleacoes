
import sqlite3

def migrate():
    conn = sqlite3.connect('instance/investments.db')
    cursor = conn.cursor()
    
    # List of new columns and their types
    new_columns = [
        ('strategy', "TEXT NOT NULL DEFAULT 'HOLDER'"),
        ('stop_loss', "REAL"),
        ('gain1', "REAL"),
        ('gain2', "REAL"),
        ('recommendation', "TEXT")
    ]
    
    for col_name, col_type in new_columns:
        try:
            cursor.execute(f"ALTER TABLE Asset ADD COLUMN {col_name} {col_type}")
            print(f"Added column {col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"Column {col_name} already exists.")
            else:
                print(f"Error adding {col_name}: {e}")
                
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
