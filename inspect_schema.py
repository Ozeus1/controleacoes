import sqlite3

def inspect_db():
    try:
        conn = sqlite3.connect('financas.db')
        cursor = conn.cursor()
        
        with open('schema_dump.txt', 'w', encoding='utf-8') as f:
            f.write("--- Tables ---\n")
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            for table in tables:
                f.write(f"{table[0]}\n")
                cursor.execute(f"PRAGMA table_info({table[0]})")
                columns = cursor.fetchall()
                for col in columns:
                    f.write(f"  - {col[1]} ({col[2]})\n")
            
            f.write("\n--- Views ---\n")
            cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='view'")
            views = cursor.fetchall()
            for view in views:
                f.write(f"{view[0]}:\n")
                f.write(f"{view[1]}\n")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_db()
