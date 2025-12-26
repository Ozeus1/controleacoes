"""
Script para executar RESET E REIMPORTAÇÃO sem conflito com servidor rodando
Usa conexão direta ao SQLite para evitar conflitos
"""

import sqlite3
import os
from datetime import datetime

def resetar_e_reimportar():
    """Executa reset e reimportação diretamente no banco"""
    
    db_path = os.path.join('instance', 'financeiro.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Banco de dados não encontrado: {db_path}")
        return
    
    try:
        print("="*70)
        print("RESET E REIMPORTAÇÃO - Conexão Direta SQLite")
        print("="*70)
        
        # Conectar ao banco
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Passo 1: Contar registros antes
        cursor.execute("SELECT COUNT(*) FROM despesa")
        total_despesas = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM receita")
        total_receitas = cursor.fetchone()[0]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='balanco_mensal'")
        tem_balanco = cursor.fetchone() is not None
        total_balancos = 0
        if tem_balanco:
            cursor.execute("SELECT COUNT(*) FROM balanco_mensal")
            total_balancos = cursor.fetchone()[0]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='evento_caixa_avulso'")
        tem_eventos = cursor.fetchone() is not None
        total_eventos = 0
        if tem_eventos:
            cursor.execute("SELECT COUNT(*) FROM evento_caixa_avulso")
            total_eventos = cursor.fetchone()[0]
        
        print(f"\n📊 Registros ANTES do reset:")
        print(f"  Despesas:         {total_despesas}")
        print(f"  Receitas:         {total_receitas}")
        print(f"  Balanços Mensais: {total_balancos}")
        print(f"  Eventos de Caixa: {total_eventos}")
        print(f"  TOTAL:            {total_despesas + total_receitas + total_balancos + total_eventos}")
        
        # Passo 2: Apagar dados
        print(f"\n🗑️  Removendo registros...")
        cursor.execute("DELETE FROM despesa")
        print(f"  ✓ {cursor.rowcount} despesas removidas")
        
        cursor.execute("DELETE FROM receita")
        print(f"  ✓ {cursor.rowcount} receitas removidas")
        
        if tem_balanco:
            cursor.execute("DELETE FROM balanco_mensal")
            print(f"  ✓ {cursor.rowcount} balanços removidos")
        
        if tem_eventos:
            cursor.execute("DELETE FROM evento_caixa_avulso")
            print(f"  ✓ {cursor.rowcount} eventos removidos")
        
        conn.commit()
        print("  ✓ Todos os registros removidos")
        
        conn.close()
        
        print("\n" + "="*70)
        print("✅ RESET CONCLUÍDO!")
        print("="*70)
        print("\n⚠️  IMPORTANTE: Agora você precisa executar a IMPORTAÇÃO")
        print("\nOpções:")
        print("1. Através da interface web: http://localhost:5000/config/importar-dados-antigos")
        print("2. Executando o comando:")
        print("   python -c \"from utils.importador import *; from flask import Flask; app=Flask(__name__); app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///instance/financeiro.db'; importar_dados_antigos(app); importar_fluxo_caixa(app)\"")
        
        print("\n" + "="*70)
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    resetar_e_reimportar()
