
import os

file_path = r'c:\Users\Orlei\OneDrive\ProjPython\FINAN\sistema_financeiro_v15.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Block 10 Replacement (gerar_relatorio_meio_pagamento)
block10_old = """            self.cursor.execute("SELECT DISTINCT meio_pagamento FROM despesas ORDER BY meio_pagamento")"""

block10_new = """            self.cursor.execute("SELECT DISTINCT meio_pagamento FROM v_despesas_compat WHERE user_id = ? ORDER BY meio_pagamento", (self.sessao.user_id,))"""

# Block 11 Replacement (mostrar_relatorio_meio_pagamento)
block11_old = """            self.cursor.execute(\"\"\"
                SELECT 
                    strftime('%Y-%m', data_pagamento) as mes_ano,
                    strftime('%m/%Y', data_pagamento) as mes_ano_formatado,
                    SUM(valor) as total_valor
                FROM despesas
                WHERE meio_pagamento = ?
                GROUP BY mes_ano
                ORDER BY mes_ano DESC
            \"\"\", (meio_pagamento,))"""

block11_new = """            self.cursor.execute(\"\"\"
                SELECT 
                    strftime('%Y-%m', data_pagamento) as mes_ano,
                    strftime('%m/%Y', data_pagamento) as mes_ano_formatado,
                    SUM(valor) as total_valor
                FROM v_despesas_compat
                WHERE meio_pagamento = ?
                AND user_id = ?
                GROUP BY mes_ano
                ORDER BY mes_ano DESC
            \"\"\", (meio_pagamento, self.sessao.user_id))"""

# Block 12 Replacement (exportar_meio_pagamento_excel)
# Note: The query is identical to Block 11, so we need to be careful.
# Since we replace all occurrences, Block 11 replacement might handle both if they are identical.
# Let's check if they are identical.
# Yes, they look identical in the views.
# So `content.replace(block11_old, block11_new)` should replace both.

if block10_old in content:
    content = content.replace(block10_old, block10_new)
    print("Block 10 replaced.")
else:
    print("Block 10 NOT found.")

if block11_old in content:
    # Count occurrences
    count = content.count(block11_old)
    content = content.replace(block11_old, block11_new)
    print(f"Block 11 replaced {count} times.")
else:
    print("Block 11 NOT found.")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
