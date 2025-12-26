
import os

file_path = r'c:\Users\Orlei\OneDrive\ProjPython\FINAN\sistema_financeiro_v15.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Block 3 Replacement
block3_old = """            self.cursor.execute(\"\"\"
                SELECT 
                    strftime('%m/%Y', data_pagamento) as 'Mês/Ano',
                    SUM(valor) as 'Total Valor',
                    COUNT(*) as 'Quantidade'
                FROM despesas
                WHERE conta_despesa = ?
                GROUP BY strftime('%Y-%m', data_pagamento)
                ORDER BY strftime('%Y-%m', data_pagamento) DESC
            \"\"\", (categoria,))"""

block3_new = """            self.cursor.execute(\"\"\"
                SELECT 
                    strftime('%m/%Y', data_pagamento) as 'Mês/Ano',
                    SUM(valor) as 'Total Valor',
                    COUNT(*) as 'Quantidade'
                FROM v_despesas_compat
                WHERE conta_despesa = ?
                AND user_id = ?
                GROUP BY strftime('%Y-%m', data_pagamento)
                ORDER BY strftime('%Y-%m', data_pagamento) DESC
            \"\"\", (categoria, self.sessao.user_id))"""

# Block 4 Replacement
block4_old = """            self.cursor.execute(\"\"\"
                SELECT 
                    id as ID,
                    descricao as Descrição,
                    meio_pagamento as 'Meio de Pagamento',
                    valor as 'Valor (R$)',
                    num_parcelas as Parcelas,
                    strftime('%d/%m/%Y', data_pagamento) as 'Data de Pagamento'
                FROM despesas
                WHERE conta_despesa = ?
                ORDER BY data_pagamento DESC
            \"\"\", (categoria,))"""

block4_new = """            self.cursor.execute(\"\"\"
                SELECT 
                    id as ID,
                    descricao as Descrição,
                    meio_pagamento as 'Meio de Pagamento',
                    valor as 'Valor (R$)',
                    num_parcelas as Parcelas,
                    strftime('%d/%m/%Y', data_pagamento) as 'Data de Pagamento'
                FROM v_despesas_compat
                WHERE conta_despesa = ?
                AND user_id = ?
                ORDER BY data_pagamento DESC
            \"\"\", (categoria, self.sessao.user_id))"""

if block3_old in content:
    content = content.replace(block3_old, block3_new)
    print("Block 3 replaced.")
else:
    print("Block 3 NOT found.")

if block4_old in content:
    content = content.replace(block4_old, block4_new)
    print("Block 4 replaced.")
else:
    print("Block 4 NOT found.")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
