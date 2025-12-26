import sqlite3
import os

print("=" * 70)
print("STATUS DOS BANCOS DE DADOS")
print("=" * 70)

# Banco antigo
antigo_path = 'financas.db'
if os.path.exists(antigo_path):
    conn_antigo = sqlite3.connect(antigo_path)
    total_antigo = conn_antigo.execute('SELECT COUNT(*) FROM despesas').fetchone()[0]
    print(f"\n✓ Banco antigo (financas.db): {total_antigo} despesas")
    conn_antigo.close()
else:
    print(f"\n✗ Banco antigo não encontrado: {antigo_path}")
    total_antigo = 0

# Banco novo
novo_path = os.path.join('instance', 'financeiro.db')
if os.path.exists(novo_path):
    conn_novo = sqlite3.connect(novo_path)
    cursor = conn_novo.cursor()
    
    # Listar tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tabelas = [t[0] for t in cursor.fetchall()]
    print(f"\n✓ Banco novo (instance/financeiro.db)")
    print(f"  Tabelas ({len(tabelas)}): {', '.join(tabelas)}")
    
    # Procurar tabela de despesas
    tabela_despesas = None
    for nome in ['despesa', 'despesas', 'Despesa', 'Despesas']:
        if nome in tabelas:
            tabela_despesas = nome
            break
    
    if tabela_despesas:
        total_novo = conn_novo.execute(f'SELECT COUNT(*) FROM {tabela_despesas}').fetchone()[0]
        print(f"  Despesas na tabela '{tabela_despesas}': {total_novo}")
        
        # Calcular proporção
        if total_antigo > 0:
            proporcao = total_novo / total_antigo
            print(f"\n" + "=" * 70)
            print("ANÁLISE DE DUPLICAÇÃO")
            print("=" * 70)
            print(f"  Banco antigo: {total_antigo} despesas")
            print(f"  Banco novo:   {total_novo} despesas")
            print(f"  Proporção:    {proporcao:.2f}x")
            
            if 2.9 <= proporcao <= 3.1:
                print(f"\n⚠️⚠️⚠️  ALERTA: Dados TRIPLICADOS!")
            elif 1.9 <= proporcao <= 2.1:
                print(f"\n⚠️  ALERTA: Dados DUPLICADOS!")
            elif proporcao > 1.1:
                print(f"\n⚠️  AVISO: Mais dados no banco novo ({proporcao:.2f}x)")
            else:
                print(f"\n✓ Proporção adequada")
    else:
        print(f"  ✗ Tabela de despesas não encontrada")
    
    conn_novo.close()
else:
    print(f"\n✗ Banco novo não encontrado: {novo_path}")

print("\n" + "=" * 70)
