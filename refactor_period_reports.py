
import os

file_path = r'c:\Users\Orlei\OneDrive\ProjPython\FINAN\sistema_financeiro_v15.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Block 7 Replacement
block7_old = """            self.cursor.execute(\"\"\"
                SELECT 
                    conta_despesa, 
                    SUM(valor) as total_valor,
                    COUNT(*) as total_registros
                FROM despesas
                WHERE data_pagamento BETWEEN ? AND ?
                GROUP BY conta_despesa
                ORDER BY total_valor DESC
            \"\"\", (data_inicial, data_final))"""

block7_new = """            self.cursor.execute(\"\"\"
                SELECT 
                    conta_despesa, 
                    SUM(valor) as total_valor,
                    COUNT(*) as total_registros
                FROM v_despesas_compat
                WHERE data_pagamento BETWEEN ? AND ?
                AND user_id = ?
                GROUP BY conta_despesa
                ORDER BY total_valor DESC
            \"\"\", (data_inicial, data_final, self.sessao.user_id))"""

# Block 8 Replacement
block8_old = """            self.cursor.execute(\"\"\"
                SELECT 
                    strftime('%Y-%m', data_pagamento) as ano_mes,
                    strftime('%m/%Y', data_pagamento) as mes_ano_formatado,
                    SUM(valor) as total_valor,
                    COUNT(*) as total_registros
                FROM despesas
                WHERE data_pagamento BETWEEN ? AND ?
                GROUP BY ano_mes
                ORDER BY ano_mes
            \"\"\", (data_inicial, data_final))"""

block8_new = """            self.cursor.execute(\"\"\"
                SELECT 
                    strftime('%Y-%m', data_pagamento) as ano_mes,
                    strftime('%m/%Y', data_pagamento) as mes_ano_formatado,
                    SUM(valor) as total_valor,
                    COUNT(*) as total_registros
                FROM v_despesas_compat
                WHERE data_pagamento BETWEEN ? AND ?
                AND user_id = ?
                GROUP BY ano_mes
                ORDER BY ano_mes
            \"\"\", (data_inicial, data_final, self.sessao.user_id))"""

# Block 9 Replacement
block9_old = """                self.cursor.execute(\"\"\"
                    SELECT 
                        conta_despesa,
                        SUM(valor) as total_valor,
                        COUNT(*) as total_registros
                    FROM despesas
                    WHERE strftime('%Y-%m', data_pagamento) = ?
                    GROUP BY conta_despesa
                    ORDER BY total_valor DESC
                \"\"\", (ano_mes,))"""

block9_new = """                self.cursor.execute(\"\"\"
                    SELECT 
                        conta_despesa,
                        SUM(valor) as total_valor,
                        COUNT(*) as total_registros
                    FROM v_despesas_compat
                    WHERE strftime('%Y-%m', data_pagamento) = ?
                    AND user_id = ?
                    GROUP BY conta_despesa
                    ORDER BY total_valor DESC
                \"\"\", (ano_mes, self.sessao.user_id))"""

if block7_old in content:
    content = content.replace(block7_old, block7_new)
    print("Block 7 replaced.")
else:
    print("Block 7 NOT found.")

if block8_old in content:
    content = content.replace(block8_old, block8_new)
    print("Block 8 replaced.")
else:
    print("Block 8 NOT found.")

if block9_old in content:
    content = content.replace(block9_old, block9_new)
    print("Block 9 replaced.")
else:
    print("Block 9 NOT found.")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
