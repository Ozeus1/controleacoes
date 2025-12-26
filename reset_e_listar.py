"""
Script para listar tabelas e resetar banco de dados
"""

import sqlite3
import os

db_path = os.path.join('instance', 'financeiro.db')

if not os.path.exists(db_path):
    print(f"❌ Banco não encontrado: {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Listar tabelas
    print("="*70)
    print("TABELAS NO BANCO DE DADOS")
    print("="*70)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tabelas = [t[0] for t in cursor.fetchall()]
    
    for i, tabela in enumerate(tabelas, 1):
        # Contar registros
        cursor.execute(f"SELECT COUNT(*) FROM `{tabela}`")
        count = cursor.fetchone()[0]
        print(f"{i}. {tabela}: {count} registros")
    
    print("\n" + "="*70)
    print("RESETANDO DADOS (mantendo estrutura)")
    print("="*70)
    
    # Resetar tabelas de dados (não configurações)
    tabelas_dados = []
    for tabela in tabelas:
        nome_lower = tabela.lower()
        # Apenas tabelas de dados, não de configuração
        if any(x in nome_lower for x in ['despesa', 'receita', 'balanco', 'evento']):
            tabelas_dados.append(tabela)
    
    print(f"\nTabelas que serão resetadas: {', '.join(tabelas_dados)}")
    
    for tabela in tabelas_dados:
        cursor.execute(f"DELETE FROM `{tabela}`")
        print(f"  ✓ {tabela}: {cursor.rowcount} registros removidos")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Reset concluído!")
    print("\nPor favor, execute a importação através da interface web:")
    print("http://localhost:5000/config/importar-dados-antigos")
