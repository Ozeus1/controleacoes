"""
Teste rápido para verificar se o gerenciador de sync consegue acessar os dados
"""
import sqlite3
import os

# Mesmo caminho que o gerenciador usa
flask_db = os.path.join(os.path.dirname(__file__), 'instance', 'financas.db')

print("="*70)
print(" TESTE DE ACESSO AO BANCO FLASK")
print("="*70)

print(f"\n📁 Caminho do banco: {flask_db}")
print(f"   Existe? {os.path.exists(flask_db)}")

if os.path.exists(flask_db):
    try:
        conn = sqlite3.connect(flask_db)
        cursor = conn.cursor()
        
        # Verificar tabela despesas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='despesas'")
        tem_despesas = cursor.fetchone()
        
        if tem_despesas:
            print(f"\n✓ Tabela 'despesas' encontrada!")
            
            # Contar despesas do admin (user_id = 1)
            admin_id = 1
            cursor.execute("SELECT COUNT(*) FROM despesas WHERE user_id = ?", (admin_id,))
            count = cursor.fetchone()[0]
            
            print(f"✓ Despesas do admin (user_id={admin_id}): {count}")
            
            if count > 0:
                # Mostrar primeiras 5 despesas
                cursor.execute("""
                    SELECT descricao, valor, conta_despesa, data_pagamento 
                    FROM despesas 
                    WHERE user_id = ? 
                    ORDER BY data_pagamento DESC 
                    LIMIT 5
                """, (admin_id,))
                
                despesas = cursor.fetchall()
                print(f"\n📋 Primeiras 5 despesas:")
                for desc, valor, categoria, data in despesas:
                    print(f"   - {data}: {desc} ({categoria}) - R$ {valor:.2f}")
                
                # Total
                cursor.execute("SELECT SUM(valor) FROM despesas WHERE user_id = ?", (admin_id,))
                total = cursor.fetchone()[0]
                print(f"\n💰 Valor total: R$ {total:.2f}")
                
                print(f"\n✅ SUCESSO! O gerenciador de sync poderá importar {count} despesas!")
            else:
                print(f"\n⚠️ AVISO: Tabela existe mas não tem despesas do admin!")
                print(f"   Execute: python popular_flask_db.py")
        else:
            print(f"\n❌ ERRO: Tabela 'despesas' NÃO encontrada!")
            
            # Listar o que tem
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tabelas = cursor.fetchall()
            print(f"\n📊 Tabelas existentes:")
            for t in tabelas:
                print(f"   - {t[0]}")
            
            print(f"\n💡 Execute: python init_flask_db.py")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ ERRO ao acessar o banco: {e}")
else:
    print(f"\n❌ Banco NÃO encontrado!")
    print(f"\n💡 Execute o app Flask primeiro: python app.py")

print("="*70)
