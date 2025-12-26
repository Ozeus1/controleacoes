import sqlite3
import sys

# Redirect output to file
output_file = open('resultado_importacao.txt', 'w', encoding='utf-8')
sys.stdout = output_file

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
except Exception as e:
    old_receitas = 0

# Banco antigo - fluxo
try:
    conn_old_flx = sqlite3.connect('fluxo_caixa.db')
    old_balancos = conn_old_flx.execute('SELECT COUNT(*) FROM balanco_mensal').fetchone()[0]
    old_eventos = conn_old_flx.execute('SELECT COUNT(*) FROM eventos_caixa_avulsos').fetchone()[0]
    conn_old_flx.close()
except Exception as e:
    old_balancos = 0
    old_eventos = 0

# Banco novo
conn_new = sqlite3.connect('instance/financeiro.db')
cursor = conn_new.cursor()

# Obter contagens
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
print(f"\nDADOS IMPORTADOS:")
print(f"  Categorias de Despesa:  {cat_despesa}")
print(f"  Categorias de Receita:  {cat_receita}")
print(f"  Meios de Pagamento:     {meio_pag}")
print(f"  Meios de Recebimento:   {meio_rec}")
print(f"  Despesas:               {new_despesas}")
print(f"  Receitas:               {new_receitas}")
print(f"  Balanços Mensais:       {balancos}")
print(f"  Eventos Avulsos:        {eventos}")

# Análise de duplicação
print(f"\n{'='*70}")
print("ANÁLISE DE DUPLICAÇÃO:")
print(f"{'='*70}")

status_geral = True

if old_despesas > 0:
    ratio_desp = new_despesas / old_despesas
    print(f"\nDESPESAS:")
    print(f"  Banco antigo: {old_despesas}")
    print(f"  Banco novo:   {new_despesas}")
    print(f"  Proporção:    {ratio_desp:.2f}x")
    
    if ratio_desp >= 2.9:
        print(f"  Status: TRIPLICADO! ⚠️⚠️⚠️")
        status_geral = False
    elif ratio_desp >= 1.9:
        print(f"  Status: DUPLICADO! ⚠️")
        status_geral = False
    elif 0.95 <= ratio_desp <= 1.05:
        print(f"  Status: PERFEITO! ✅")
    else:
        print(f"  Status: ATENÇÃO - Verificar proporção ⚠️")
        status_geral = False

if old_receitas > 0:
    ratio_rec = new_receitas / old_receitas
    print(f"\nRECEITAS:")
    print(f"  Banco antigo: {old_receitas}")
    print(f"  Banco novo:   {new_receitas}")
    print(f"  Proporção:    {ratio_rec:.2f}x")
    
    if 0.95 <= ratio_rec <= 1.05:
        print(f"  Status: PERFEITO! ✅")
    else:
        print(f"  Status: ATENÇÃO - Verificar proporção ⚠️")
        status_geral = False

if old_balancos > 0:
    ratio_bal = balancos / old_balancos
    print(f"\nBALANÇOS MENSAIS:")
    print(f"  Banco antigo: {old_balancos}")
    print(f"  Banco novo:   {balancos}")
    print(f"  Proporção:    {ratio_bal:.2f}x")
    
    if 0.95 <= ratio_bal <= 1.05:
        print(f"  Status: PERFEITO! ✅")
    else:
        print(f"  Status: ATENÇÃO - Verificar proporção ⚠️")
        status_geral = False

if old_eventos > 0:
    ratio_evt = eventos / old_eventos
    print(f"\nEVENTOS DE CAIXA:")
    print(f"  Banco antigo: {old_eventos}")
    print(f"  Banco novo:   {eventos}")
    print(f"  Proporção:    {ratio_evt:.2f}x")
    
    if 0.95 <= ratio_evt <= 1.05:
        print(f"  Status: PERFEITO! ✅")
    else:
        print(f"  Status: ATENÇÃO - Verificar proporção ⚠️")
        status_geral = False

# Conclusão
print(f"\n{'='*70}")
if status_geral:
    print("✅ IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
    print("   Todos os dados foram importados sem duplicação.")
else:
    print("⚠️  ATENÇÃO: Algumas proporções estão fora do esperado.")
    print("   Verifique os resultados acima.")
print(f"{'='*70}\n")

output_file.close()

# Print to console também
with open('resultado_importacao.txt', 'r', encoding='utf-8') as f:
    print(f.read(), file=sys.__stdout__)
