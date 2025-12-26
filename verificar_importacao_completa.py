import sqlite3

print("=" * 70)
print("VERIFICAÇÃO COMPLETA DA IMPORTAÇÃO")
print("=" * 70)

# Banco antigo
conn_old = sqlite3.connect('financas.db')
old_despesas = conn_old.execute('SELECT COUNT(*) FROM despesas').fetchone()[0]
print(f"\n📊 BANCO ANTIGO (financas.db):")
print(f"   Despesas: {old_despesas}")
conn_old.close()

# Banco antigo - receitas
try:
    conn_old_rec = sqlite3.connect('financas_receitas.db')
    old_receitas = conn_old_rec.execute('SELECT COUNT(*) FROM receitas').fetchone()[0]
    print(f"\n📊 BANCO ANTIGO (financas_receitas.db):")
    print(f"   Receitas: {old_receitas}")
    conn_old_rec.close()
except Exception as e:
    print(f"\n⚠️  Receitas antigas: {e}")
    old_receitas = 0

# Banco antigo - fluxo
try:
    conn_old_flx = sqlite3.connect('fluxo_caixa.db')
    old_balancos = conn_old_flx.execute('SELECT COUNT(*) FROM balanco_mensal').fetchone()[0]
    old_eventos = conn_old_flx.execute('SELECT COUNT(*) FROM eventos_caixa_avulsos').fetchone()[0]
    print(f"\n📊 BANCO ANTIGO (fluxo_caixa.db):")
    print(f"   Balanços: {old_balancos}")
    print(f"   Eventos:  {old_eventos}")
    conn_old_flx.close()
except Exception as e:
    print(f"\n⚠️  Fluxo de caixa antigo: {e}")
    old_balancos = 0
    old_eventos = 0

# Banco novo
print(f"\n" + "=" * 70)
print("📦 BANCO NOVO (instance/financeiro.db):")
print("=" * 70)

conn_new = sqlite3.connect('instance/financeiro.db')

# Despesas
new_despesas = conn_new.execute('SELECT COUNT(*) FROM despesa').fetchone()[0]
print(f"\n✓ Despesas: {new_despesas}")

# Receitas
new_receitas = conn_new.execute('SELECT COUNT(*) FROM receita').fetchone()[0]
print(f"✓ Receitas: {new_receitas}")

# Categorias
cat_despesa = conn_new.execute('SELECT COUNT(*) FROM categoria_despesa').fetchone()[0]
cat_receita = conn_new.execute('SELECT COUNT(*) FROM categoria_receita').fetchone()[0]
print(f"\n✓ Categorias de Despesa: {cat_despesa}")
print(f"✓ Categorias de Receita: {cat_receita}")

# Meios
meio_pag = conn_new.execute('SELECT COUNT(*) FROM meio_pagamento').fetchone()[0]
meio_rec = conn_new.execute('SELECT COUNT(*) FROM meio_recebimento').fetchone()[0]
print(f"\n✓ Meios de Pagamento: {meio_pag}")
print(f"✓ Meios de Recebimento: {meio_rec}")

# Fluxo de caixa
balancos = conn_new.execute('SELECT COUNT(*) FROM balanco_mensal').fetchone()[0]
eventos = conn_new.execute('SELECT COUNT(*) FROM evento_caixa_avulso').fetchone()[0]
print(f"\n✓ Balanços Mensais: {balancos}")
print(f"✓ Eventos de Caixa Avulsos: {eventos}")

conn_new.close()

# Análise
print(f"\n" + "=" * 70)
print("📈 ANÁLISE DE DUPLICAÇÃO:")
print("=" * 70)

if old_despesas > 0:
    ratio_desp = new_despesas / old_despesas
    print(f"\n  Despesas:")
    print(f"    Antigo: {old_despesas}")
    print(f"    Novo:   {new_despesas}")
    print(f"    Razão:  {ratio_desp:.2f}x")
    
    if ratio_desp >= 2.9:
        print(f"    Status: ⚠️⚠️⚠️ TRIPLICADO!")
    elif ratio_desp >= 1.9:
        print(f"    Status: ⚠️ DUPLICADO!")
    elif 0.95 <= ratio_desp <= 1.05:
        print(f"    Status: ✅ PERFEITO!")
    else:
        print(f"    Status: ⚠️  Verificar (razão {ratio_desp:.2f}x)")

if old_receitas > 0:
    ratio_rec = new_receitas / old_receitas
    print(f"\n  Receitas:")
    print(f"    Antigo: {old_receitas}")
    print(f"    Novo:   {new_receitas}")
    print(f"    Razão:  {ratio_rec:.2f}x")
    
    if 0.95 <= ratio_rec <= 1.05:
        print(f"    Status: ✅ PERFEITO!")
    else:
        print(f"    Status: ⚠️  Verificar")

if old_balancos > 0:
    ratio_bal = balancos / old_balancos
    print(f"\n  Balanços Mensais:")
    print(f"    Antigo: {old_balancos}")
    print(f"    Novo:   {balancos}")
    print(f"    Razão:  {ratio_bal:.2f}x")
    
    if 0.95 <= ratio_bal <= 1.05:
        print(f"    Status: ✅ PERFEITO!")
    else:
        print(f"    Status: ⚠️  Verificar")

print(f"\n" + "=" * 70)
