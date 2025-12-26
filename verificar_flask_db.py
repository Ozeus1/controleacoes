import sqlite3
import os

# Verificar banco Flask
flask_db = 'instance/financas.db'

print("="*60)
print("VERIFICAÇÃO DO BANCO FLASK")
print("="*60)

if os.path.exists(flask_db):
    print(f"✓ Banco encontrado: {flask_db}")
    print(f"  Tamanho: {os.path.getsize(flask_db)} bytes")
    
    conn = sqlite3.connect(flask_db)
    cursor = conn.cursor()
    
    # Listar todas as tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tabelas = cursor.fetchall()
    
    print(f"\n📋 Tabelas encontradas ({len(tabelas)}):")
    for tabela in tabelas:
        print(f"  - {tabela[0]}")
        
        # Contar registros em cada tabela
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {tabela[0]}")
            count = cursor.fetchone()[0]
            print(f"    ({count} registros)")
        except:
            print(f"    (erro ao contar)")
    
    # Verificar se existe tabela despesas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='despesas'")
    tem_despesas = cursor.fetchone()
    
    if tem_despesas:
        print(f"\n✓ Tabela 'despesas' EXISTE!")
        
        # Verificar estrutura
        cursor.execute("PRAGMA table_info(despesas)")
        colunas = cursor.fetchall()
        print(f"\n📊 Estrutura da tabela 'despesas':")
        for col in colunas:
            print(f"  - {col[1]} ({col[2]})")
        
        # Verificar se tem user_id
        cursor.execute("SELECT COUNT(*) FROM despesas")
        total = cursor.fetchone()[0]
        print(f"\n📈 Total de despesas: {total}")
        
        if total > 0:
            # Verificar se tem coluna user_id
            cursor.execute("PRAGMA table_info(despesas)")
            cols = [c[1] for c in cursor.fetchall()]
            
            if 'user_id' in cols:
                cursor.execute("SELECT user_id, COUNT(*) FROM despesas GROUP BY user_id")
                por_usuario = cursor.fetchall()
                print(f"\n👥 Despesas por usuário:")
                for user_id, count in por_usuario:
                    print(f"  - user_id {user_id}: {count} despesas")
            else:
                print(f"\n⚠️ Coluna 'user_id' NÃO EXISTE na tabela despesas!")
    else:
        print(f"\n✗ Tabela 'despesas' NÃO EXISTE!")
        print(f"\n💡 Sugestão: Execute o app Flask primeiro para criar as tabelas.")
    
    conn.close()
else:
    print(f"✗ Banco NÃO encontrado: {flask_db}")
    print(f"\n💡 Sugestão:")
    print(f"  1. Verifique se o app Flask já foi executado")
    print(f"  2. O caminho correto é: instance/financas.db")
    print(f"  3. Execute: python app.py")

print("="*60)
