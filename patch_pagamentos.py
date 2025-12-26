"""
Script para aplicar automaticamente os filtros SQL que excluem a categoria 'Pagamentos'
dos relatórios de despesas no sistema_financeiro_v15.py
"""

import re

def apply_pagamentos_filter():
    """
    Lê o arquivo sistema_financeiro_v14.py e aplica todas as modificações necessárias
    para exc uir a categoria 'Pagamentos' dos relatórios de despesa.
    """
    
    # Ler o arquivo original
    with open('sistema_financeiro_v14.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Lista de modificações a aplicar
    modifications = [
        # 1. Atualizar_grafico - Total do mês
        {
            'pattern': r"(self\.cursor\.execute\(\"SELECT SUM\(valor\) FROM despesas WHERE strftime\('%Y-%m', data_pagamento\) = \?\",)",
            'replacement': r'self.cursor.execute("SELECT SUM(valor) FROM despesas WHERE strftime(\'%Y-%m\', data_pagamento) = ? AND conta_despesa != \'Pagamentos\' COLLATE NOCASE",'
        },
        # 2. Atualizar_grafico - Top 10 categorias
        {
            'pattern': r"(SELECT conta_despesa, SUM\(valor\) as total\s+FROM despesas\s+WHERE strftime\('%Y-%m', data_pagamento\) = \?\s+GROUP BY conta_despesa)",
            'replacement': r"SELECT conta_despesa, SUM(valor) as total\n            FROM despesas\n            WHERE strftime('%Y-%m', data_pagamento) = ?\n            AND conta_despesa != 'Pagamentos' COLLATE NOCASE\n            GROUP BY conta_despesa"
        },
        # 3. mostrar_relatorio_mensal - Consulta principal
        {
            'pattern': r"(SELECT \s+conta_despesa,\s+SUM\(valor\) as total_valor,\s+COUNT\(\*\) as total_registros\s+FROM despesas\s+WHERE data_pagamento BETWEEN \? AND \?\s+GROUP BY conta_despesa)",
            'replacement': r"SELECT \n                    conta_despesa, \n                    SUM(valor) as total_valor,\n                    COUNT(*) as total_registros\n                FROM despesas\n                WHERE data_pagamento BETWEEN ? AND ?\n                AND conta_despesa != 'Pagamentos' COLLATE NOCASE\n                GROUP BY conta_despesa"
        },
        # 4. mostrar_relatorio_entre_datas
        {
            'pattern': r"(SELECT \s+conta_despesa,\s+SUM\(valor\) as total_valor,\s+COUNT\(\*\) as total_registros\s+FROM despesas\s+WHERE data_pagamento BETWEEN \? AND \?\s+GROUP BY conta_despesa\s+ORDER BY total_valor DESC)",
            'replacement': r"SELECT \n                    conta_despesa, \n                    SUM(valor) as total_valor,\n                    COUNT(*) as total_registros\n                FROM despesas\n                WHERE data_pagamento BETWEEN ? AND ?\n                AND conta_despesa != 'Pagamentos' COLLATE NOCASE\n                GROUP BY conta_despesa\n                ORDER BY total_valor DESC"
        },
        # 5. mostrar_relatorio_mensal_periodo
        {
            'pattern': r"(SELECT \s+strftime\('%Y-%m', data_pagamento\) as ano_mes,\s+strftime\('%m/%Y', data_pagamento\) as mes_ano_formatado,\s+SUM\(valor\) as total_valor,\s+COUNT\(\*\) as total_registros\s+FROM despesas\s+WHERE data_pagamento BETWEEN \? AND \?\s+GROUP BY ano_mes)",
            'replacement': r"SELECT \n                    strftime('%Y-%m', data_pagamento) as ano_mes,\n                    strftime('%m/%Y', data_pagamento) as mes_ano_formatado,\n                    SUM(valor) as total_valor,\n                    COUNT(*) as total_registros\n                FROM despesas\n                WHERE data_pagamento BETWEEN ? AND ?\n                AND conta_despesa != 'Pagamentos' COLLATE NOCASE\n                GROUP BY ano_mes"
        },
        # 6. mostrar_grafico_principais_contas - Top 10
        {
            'pattern': r"(SELECT conta_despesa, SUM\(valor\) as total_valor\s+FROM despesas WHERE strftime\('%Y-%m', data_pagamento\) = \?\s+GROUP BY conta_despesa ORDER BY total_valor DESC LIMIT 10)",
            'replacement': r"SELECT conta_despesa, SUM(valor) as total_valor\n            FROM despesas WHERE strftime('%Y-%m', data_pagamento) = ?\n            AND conta_despesa != 'Pagamentos' COLLATE NOCASE\n            GROUP BY conta_despesa ORDER BY total_valor DESC LIMIT 10"
        },
       # 7. exportar_relatorio_excel
        {
            'pattern': r"(SELECT \s+conta_despesa as Categoria,\s+SUM\(valor\) as 'Total Valor',\s+COUNT\(\*\) as 'Quantidade'\s+FROM despesas\s+WHERE data_pagamento BETWEEN \? AND \?\s+GROUP BY conta_despesa)",
            'replacement': r"SELECT \n                conta_despesa as Categoria, \n                SUM(valor) as 'Total Valor',\n                COUNT(*) as 'Quantidade'\n            FROM despesas\n            WHERE data_pagamento BETWEEN ? AND ?\n            AND conta_despesa != 'Pagamentos' COLLATE NOCASE\n            GROUP BY conta_despesa"
        }
    ]
    
    # Aplicar cada modificação
    modified_content = content
    for i, mod in enumerate(modifications, 1):
        print(f"Aplicando modificação {i}...")
        modified_content = re.sub(mod['pattern'], mod['replacement'], modified_content, flags=re.MULTILINE | re.DOTALL)
    
    # Salvar o arquivo modificado
    with open('sistema_financeiro_v15.py', 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    print("\\n✅ Todas as modificações foram aplicadas com sucesso!")
    print("Arquivo salvo: sistema_financeiro_v15.py")

if __name__ == '__main__':
    apply_pagamentos_filter()
