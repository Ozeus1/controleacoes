#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Relatório detalhado da importação
"""
import sqlite3
import os

# Conectar ao banco novo
db_novo = 'instance/financeiro.db'
if not os.path.exists(db_novo):
    print(f"Banco {db_novo} não encontrado!")
    exit(1)

conn = sqlite3.connect(db_novo)
cursor = conn.cursor()

print()
print("=" * 80)
print(" RELATÓRIO COMPLETO DA IMPORTAÇÃO DOS DADOS ANTIGOS")
print("=" * 80)
print()

# Tabelas e suas contagens
tabelas_config = [
    ("categoria_despesa", "Categorias de Despesa"),
    ("categoria_receita", "Categorias de Receita"),
    ("meio_pagamento", "Meios de Pagamento"),
    ("meio_recebimento", "Meios de Recebimento"),
]

tabelas_transacoes = [
    ("despesa", "Despesas"),
    ("receita", "Receitas"),
]

tabelas_fluxo = [
    ("balanco_mensal", "Balanços Mensais"),
    ("evento_caixa_avulso", "Eventos de Caixa Avulsos"),
]

print("📋 CONFIGURAÇÕES IMPORTADAS:")
print("-" * 80)
for table_name, label in tabelas_config:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
        count = cursor.fetchone()[0]
        status = "✓" if count > 0 else "○"
        print(f"  {status} {label:35s} {count:5d}")
    except Exception as e:
        print(f"  ✗ {label:35s} ERRO: {e}")

print()
print("💰 TRANSAÇÕES IMPORT ADAS:")
print("-" * 80)
for table_name, label in tabelas_transacoes:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
        count = cursor.fetchone()[0]
        status = "✓" if count > 0 else "○"
        print(f"  {status} {label:35s} {count:5d}")
        
        if count > 0:
            # Mostrar primeira e última transação
            cursor.execute(f"""
                SELECT MIN(data_pagamento), MAX(data_pagamento) 
                FROM `{table_name}`
            """ if table_name == "despesa" else """
                SELECT MIN(data_recebimento), MAX(data_recebimento)
                FROM `{table_name}`
            """)
            min_date, max_date = cursor.fetchone()
            if min_date and max_date:
                print(f"      Período: {min_date} a {max_date}")
            
            # Total de valores
            cursor.execute(f"SELECT SUM(valor) FROM `{table_name}`")
            total = cursor.fetchone()[0] or 0
            print(f"      Total: R$ {total:,.2f}")
            
    except Exception as e:
        print(f"  ✗ {label:35s} ERRO: {e}")

print()
print("📊 FLUXO DE CAIXA IMPORTADO:")
print("" * 80)
for table_name, label in tabelas_fluxo:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
        count = cursor.fetchone()[0]
        status = "✓" if count > 0 else "○"
        print(f"  {status} {label:35s} {count:5d}")
    except Exception as e:
        print(f"  ✗ {label:35s} ERRO: {e}")

print()
print("=" * 80)
print("IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
print("=" * 80)
print()
print("Próximos passos:")
print("  1. Acesse o sistema em: http://localhost:5000")
print("  2. Faça login com as credenciais configuradas")
print("  3. Verifique os dados importados no dashboard")
print()

conn.close()
