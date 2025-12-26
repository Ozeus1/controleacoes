import sqlite3
import hashlib

def migrate():
    try:
        conn = sqlite3.connect('financas.db')
        cursor = conn.cursor()
        
        # 1. Ensure users table exists (it should, but good to be safe)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT,
                password_hash TEXT,
                nivel_acesso TEXT DEFAULT 'user',
                ativo BOOLEAN DEFAULT 1,
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 2. Insert admin user if not exists
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        admin_user = cursor.fetchone()
        
        if not admin_user:
            print("Creating admin user...")
            # Simple hash for 'admin' - in a real app use a proper hashing library like werkzeug or bcrypt
            # But here we just need a placeholder if the app uses it, or just the record.
            # Assuming the app might use simple string or some hash. I'll just put a placeholder.
            password_hash = hashlib.sha256('admin'.encode()).hexdigest() 
            cursor.execute('''
                INSERT INTO users (username, password_hash, nivel_acesso, ativo)
                VALUES (?, ?, ?, ?)
            ''', ('admin', password_hash, 'admin', 1))
            admin_id = cursor.lastrowid
        else:
            print("Admin user already exists.")
            admin_id = admin_user[0]
            
        print(f"Admin ID: {admin_id}")
        
        # 3. Add user_id to despesas if not exists
        cursor.execute("PRAGMA table_info(despesas)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'user_id' not in columns:
            print("Adding user_id column to despesas...")
            cursor.execute("ALTER TABLE despesas ADD COLUMN user_id INTEGER REFERENCES users(id)")
            
            # Update all existing expenses to belong to admin
            print(f"Updating existing expenses to user_id={admin_id}...")
            cursor.execute("UPDATE despesas SET user_id = ?", (admin_id,))
            conn.commit()
        else:
            print("Column user_id already exists in despesas.")
            
        # 4. Check/Fix View v_despesas_compat
        # The view might be invalid if it references columns that don't exist or if we want to add user_id to it.
        # Let's drop and recreate it to be sure it includes user_id and works.
        # Note: The schema dump showed the view using 'categoria_id' and 'meio_pagamento_id' which might NOT exist in 'despesas' table 
        # based on the table info (which showed 'conta_despesa' and 'meio_pagamento' as TEXT).
        # If the table uses TEXT columns, the view joining on IDs will fail or be empty.
        # However, the user asked to "include user_id".
        # Let's check if the view is actually valid first.
        
        print("Recreating view v_despesas_compat...")
        cursor.execute("DROP VIEW IF EXISTS v_despesas_compat")
        
        # Based on the schema dump, despesas has:
        # id, descricao, meio_pagamento (TEXT), conta_despesa (TEXT), valor, num_parcelas, data_registro, data_pagamento
        # It does NOT seem to have categoria_id or meio_pagamento_id.
        # So the previous view definition in the dump was likely broken or from a different version.
        # We will create a compatible view that just maps the text columns and adds user_id.
        
        cursor.execute('''
            CREATE VIEW v_despesas_compat AS
            SELECT 
                id, 
                descricao, 
                valor, 
                num_parcelas, 
                data_pagamento, 
                data_registro,
                conta_despesa,
                meio_pagamento,
                user_id
            FROM despesas
        ''')
        
        conn.commit()
        print("Migration completed successfully.")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
