import sqlite3
import os

DB_PATH = 'instance/investments.db'

def update_database():
    if not os.path.exists(DB_PATH):
        print(f"Erro: Banco de dados não encontrado em {DB_PATH}")
        return

    print(f"Conectando ao banco de dados: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # List of new columns to add
    new_columns = [
        ('last_dividend', 'FLOAT'),
        ('last_dividend_date', 'DATE'),
        ('dividend_yield', 'FLOAT')
    ]

    table_name = 'asset'
    
    # Get existing columns
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = [row[1] for row in cursor.fetchall()]

    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            try:
                print(f"Adicionando coluna '{col_name}' ({col_type})...")
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")
                print(f"Coluna '{col_name}' adicionada com sucesso.")
            except Exception as e:
                print(f"Erro ao adicionar coluna '{col_name}': {e}")
        else:
            print(f"Coluna '{col_name}' já existe.")

    conn.commit()
    conn.close()
    print("Atualização do banco de dados concluída.")

if __name__ == "__main__":
    update_database()
