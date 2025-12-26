#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlite3

try:
    print("Conectando em financas.db...")
    conn = sqlite3.connect('financas.db')
    cursor = conn.cursor()
    
    # Tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tabelas = cursor.fetchall()
    print(f"Tabelas: {tabelas}")
    
    # Contagem de despesas
    cursor.execute("SELECT COUNT(*) FROM despesas")
    count = cursor.fetchone()[0]
    print(f"Total de despesas: {count}")
    
    # Estrutura da tabela despesas
    cursor.execute("PRAGMA table_info(despesas)")
    cols = cursor.fetchall()
    print(f"Colunas da tabela despesas: {[c[1] for c in cols]}")
    
    # Um exemplo
    if count > 0:
        cursor.execute("SELECT * FROM despesas LIMIT 1")
        exemplo = cursor.fetchone()
        print(f"Exemplo: {exemplo}")
    
    conn.close()
    print("OK!")
    
except Exception as e:
    print(f"ERRO: {e}")
