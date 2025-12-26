import sqlite3

conn = sqlite3.connect('instance/financas.db')
cursor = conn.cursor()

# Listar TODAS as tabelas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tabelas = cursor.fetchall()

print("Tabelas no banco Flask:")
for t in tabelas:
    print(f"  - {t[0]}")
    cursor.execute(f"SELECT COUNT(*) FROM {t[0]}")
    print(f"    Registros: {cursor.fetchone()[0]}")

conn.close()
