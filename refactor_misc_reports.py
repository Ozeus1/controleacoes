
import os

file_path = r'c:\Users\Orlei\OneDrive\ProjPython\FINAN\sistema_financeiro_v15.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Block 5 Replacement
block5_old = """            self.cursor.execute(\"\"\"
                SELECT 
                    strftime('%Y-%m', data_pagamento) as mes_ano,
                    strftime('%m/%Y', data_pagamento) as mes_ano_formatado,
                    SUM(valor) as total_valor
                FROM despesas
                WHERE conta_despesa = ?
                GROUP BY mes_ano
                ORDER BY mes_ano DESC
            \"\"\", (categoria,))"""

block5_new = """            self.cursor.execute(\"\"\"
                SELECT 
                    strftime('%Y-%m', data_pagamento) as mes_ano,
                    strftime('%m/%Y', data_pagamento) as mes_ano_formatado,
                    SUM(valor) as total_valor
                FROM v_despesas_compat
                WHERE conta_despesa = ?
                AND user_id = ?
                GROUP BY mes_ano
                ORDER BY mes_ano DESC
            \"\"\", (categoria, self.sessao.user_id))"""

# Block 6 Replacement
block6_old = """            self.cursor.execute(\"\"\"
                SELECT 
                    id, descricao, meio_pagamento, conta_despesa, valor, 
                    num_parcelas, strftime('%d/%m/%Y', data_pagamento) as data_pagamento,
                    strftime('%d/%m/%Y', data_registro) as data_registro
                FROM despesas
                ORDER BY data_pagamento DESC
            \"\"\")"""

block6_new = """            self.cursor.execute(\"\"\"
                SELECT 
                    id, descricao, meio_pagamento, conta_despesa, valor, 
                    num_parcelas, strftime('%d/%m/%Y', data_pagamento) as data_pagamento,
                    strftime('%d/%m/%Y', data_registro) as data_registro
                FROM v_despesas_compat
                WHERE user_id = ?
                ORDER BY data_pagamento DESC
            \"\"\", (self.sessao.user_id,))"""

if block5_old in content:
    content = content.replace(block5_old, block5_new)
    print("Block 5 replaced.")
else:
    print("Block 5 NOT found.")

if block6_old in content:
    content = content.replace(block6_old, block6_new)
    print("Block 6 replaced.")
else:
    print("Block 6 NOT found.")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
