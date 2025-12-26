import sqlite3

print("=" * 70)
print("RELATÓRIO COMPLETO DE IMPORTAÇÃO")
print("=" * 70)

# Banco antigo - despesas
conn_old = sqlite3.connect('financas.db')
old_despesas = conn_old.execute('SELECT COUNT(*) FROM despesas').fetchone()[0]
conn_old.close()

# Banco antigo - receitas
try:
    conn_old_rec = sqlite3.connect('financas_receitas.db')
    old_receitas = conn_old_rec.execute('SELECT COUNT(*) FROM receitas').fetchone()[0]
    conn_old_rec.close()
except:
    old_receitas = 0

# Banco antigo - fluxo
try:
    conn_old_flx = sqlite3.connect('fluxo_caixa.db')
    old_balancos = conn_old_flx.execute('SELECT COUNT(*) FROM balanco_mensal').fetchone()[0]
    old_eventos = conn_old_flx.execute('SELECT COUNT(*) FROM eventos_caixa_avulsos').fetchone()[0]
    conn_old_flx.close()
except:
    old_balancos = 0
    old_eventos = 0

# Banco novo
conn_new = sqlite3.connect('instance/financeiro.db')
cursor = conn_new.cursor()

# Obter contagens (usando os nomes corretos das tabelas do models.py)
new_despesas = cursor.execute('SELECT COUNT(*) FROM despesas').fetchone()[0]
new_receitas = cursor.execute('SELECT COUNT(*) FROM receitas').fetchone()[0]
cat_despesa = cursor.execute('SELECT COUNT(*) FROM categorias_despesa').fetchone()[0]
cat_receita = cursor.execute('SELECT COUNT(*) FROM categorias_receita').fetchone()[0]
meio_pag = cursor.execute('SELECT COUNT(*) FROM meios_pagamento').fetchone()[0]
meio_rec = cursor.execute('SELECT COUNT(*) FROM meios_recebimento').fetchone()[0]
balancos = cursor.execute('SELECT COUNT(*) FROM balanco_mensal').fetchone()[0]
eventos = cursor.execute('SELECT COUNT(*) FROM eventos_caixa_avulsos').fetchone()[0]

conn_new.close()

# Exibir resultados
print(f"\n┌─ DADOS IMPORTADOS ─────────────────────────────────────────┐")
print(f"│                                                            │")
print(f"│  📊 CATEGORIAS E MEIOS                                     │")
print(f"│     • Categorias de Despesa:  {cat_despesa:<3}                          │")
print(f"│     • Categorias de Receita:  {cat_receita:<3}                          │")
print(f"│     • Meios de Pagamento:     {meio_pag:<3}                          │")
print(f"│     • Meios de Recebimento:   {meio_rec:<3}                          │")
print(f"│                                                            │")
print(f"│  💰 TRANSAÇÕES FINANCEIRAS                                 │")
print(f"│     • Despesas:               {new_despesas:<4}                         │")
print(f"│     • Receitas:               {new_receitas:<4}                         │")
print(f"│                                                            │")
print(f"│  🏦 FLUXO DE CAIXA                                         │")
print(f"│     • Balanços Mensais:       {balancos:<4}                         │")
print(f"│     • Eventos Avulsos:        {eventos:<4}                         │")
print(f"│                                                            │")
print(f"└────────────────────────────────────────────────────────────┘")

# Análise de duplicação
print(f"\n┌─ ANÁLISE DE DUPLICAÇÃO ────────────────────────────────────┐")
print(f"│                                                            │")

status_geral = True

if old_despesas > 0:
    ratio_desp = new_despesas / old_despesas
    status_icon = "✅" if 0.95 <= ratio_desp <= 1.05 else "⚠️"
    if ratio_desp < 0.95 or ratio_desp > 1.05:
        status_geral = False
    
    print(f"│  {status_icon} DESPESAS                                              │")
    print(f"│     Banco antigo: {old_despesas:<4}  →  Banco novo: {new_despesas:<4}          │")
    print(f"│     Proporção: {ratio_desp:.2f}x                                   │")
    
    if ratio_desp >= 2.9:
        print(f"│     Status: TRIPLICADO! ⚠️⚠️⚠️                            │")
    elif ratio_desp >= 1.9:
        print(f"│     Status: DUPLICADO! ⚠️                                │")
    elif 0.95 <= ratio_desp <= 1.05:
        print(f"│     Status: PERFEITO! ✅                                 │")
    else:
        print(f"│     Status: ATENÇÃO - Verificar proporção               │")
    print(f"│                                                            │")

if old_receitas > 0:
    ratio_rec = new_receitas / old_receitas
    status_icon = "✅" if 0.95 <= ratio_rec <= 1.05 else "⚠️"
    if ratio_rec < 0.95 or ratio_rec > 1.05:
        status_geral = False
        
    print(f"│  {status_icon} RECEITAS                                              │")
    print(f"│     Banco antigo: {old_receitas:<4}  →  Banco novo: {new_receitas:<4}           │")
    print(f"│     Proporção: {ratio_rec:.2f}x                                   │")
    if 0.95 <= ratio_rec <= 1.05:
        print(f"│     Status: PERFEITO! ✅                                 │")
    else:
        print(f"│     Status: ATENÇÃO - Verificar proporção               │")
    print(f"│                                                            │")

if old_balancos > 0:
    ratio_bal = balancos / old_balancos
    status_icon = "✅" if 0.95 <= ratio_bal <= 1.05 else "⚠️"
    if ratio_bal < 0.95 or ratio_bal > 1.05:
        status_geral = False
        
    print(f"│  {status_icon} BALANÇOS MENSAIS                                      │")
    print(f"│     Banco antigo: {old_balancos:<4}  →  Banco novo: {balancos:<4}           │")
    print(f"│     Proporção: {ratio_bal:.2f}x                                   │")
    if 0.95 <= ratio_bal <= 1.05:
        print(f"│     Status: PERFEITO! ✅                                 │")
    else:
        print(f"│     Status: ATENÇÃO - Verificar proporção               │")
    print(f"│                                                            │")

print(f"└────────────────────────────────────────────────────────────┘")

# Conclusão
print(f"\n{'='*70}")
if status_geral:
    print("✅ IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
    print("   Todos os dados foram importados sem duplicação.")
else:
    print("⚠️  ATENÇÃO: Verifique os resultados acima.")
    print("   Algumas proporções estão fora do esperado.")
print(f"{'='*70}\n")
