#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('instance/financeiro.db')
cursor = conn.cursor()

# Listar todas as tabelas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tabelas = cursor.fetchall()

print("=" * 70)
print("RESULTADO DA IMPORTAÇÃO DOS BANCOS ANTIGOS")
print("=" * 70)
print()

total_registros = 0
for tabela in tabelas:
    nome = tabela[0]
    try:
        cursor.execute(f"SELECT COUNT(*) FROM `{nome}`")
        count = cursor.fetchone()[0]
        total_registros += count
        status = "✓" if count > 0 else "○"
        print(f"{status} {nome:30s} {count:6d} registros")
    except:
        print(f"✗ {nome:30s} (erro ao contar)")

print()
print(f"Total de registros no banco: {total_registros}")
print("=" * 70)

conn.close()
