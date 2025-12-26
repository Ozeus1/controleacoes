
import os

file_path = r'c:\Users\Orlei\OneDrive\ProjPython\FINAN\sistema_financeiro_v15.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Block 1 Replacement
block1_old = """            self.cursor.execute(\"\"\"
                SELECT 
                    conta_despesa as Categoria, 
                    SUM(valor) as 'Total Valor',
                    COUNT(*) as 'Quantidade'
                FROM despesas
                WHERE data_pagamento BETWEEN ? AND ?
                GROUP BY conta_despesa
                ORDER BY 'Total Valor' DESC
            \"\"\", (primeiro_dia, ultimo_dia))"""

block1_new = """            self.cursor.execute(\"\"\"
                SELECT 
                    conta_despesa as Categoria, 
                    SUM(valor) as 'Total Valor',
                    COUNT(*) as 'Quantidade'
                FROM v_despesas_compat
                WHERE data_pagamento BETWEEN ? AND ?
                AND user_id = ?
                GROUP BY conta_despesa
                ORDER BY 'Total Valor' DESC
            \"\"\", (primeiro_dia, ultimo_dia, self.sessao.user_id))"""

# Block 2 Replacement
block2_old = """            self.cursor.execute(\"\"\"
                SELECT 
                    id as ID,
                    descricao as Descrição,
                    meio_pagamento as 'Meio de Pagamento',
                    conta_despesa as Categoria,
                    valor as 'Valor (R$)',
                    num_parcelas as Parcelas,
                    strftime('%d/%m/%Y', data_pagamento) as 'Data de Pagamento'
                FROM despesas
                WHERE data_pagamento BETWEEN ? AND ?
                ORDER BY data_pagamento
            \"\"\", (primeiro_dia, ultimo_dia))"""

block2_new = """            self.cursor.execute(\"\"\"
                SELECT 
                    id as ID,
                    descricao as Descrição,
                    meio_pagamento as 'Meio de Pagamento',
                    conta_despesa as Categoria,
                    valor as 'Valor (R$)',
                    num_parcelas as Parcelas,
                    strftime('%d/%m/%Y', data_pagamento) as 'Data de Pagamento'
                FROM v_despesas_compat
                WHERE data_pagamento BETWEEN ? AND ?
                AND user_id = ?
                ORDER BY data_pagamento
            \"\"\", (primeiro_dia, ultimo_dia, self.sessao.user_id))"""

if block1_old in content:
    content = content.replace(block1_old, block1_new)
    print("Block 1 replaced.")
else:
    print("Block 1 NOT found.")

if block2_old in content:
    content = content.replace(block2_old, block2_new)
    print("Block 2 replaced.")
else:
    print("Block 2 NOT found.")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
