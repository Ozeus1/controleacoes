
import os

file_path = r'c:\Users\Orlei\OneDrive\ProjPython\FINAN\sistema_financeiro_v15.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. mostrar_detalhes_transacao
block1_old = """                    self.cursor.execute(\"\"\"
                        SELECT strftime('%d/%m/%Y', data_pagamento), descricao, valor
                        FROM despesas
                        WHERE conta_despesa = ? AND strftime('%Y-%m', data_pagamento) = ?
                        ORDER BY data_pagamento
                    \"\"\", (categoria, mes_ym_selecionado))"""

block1_new = """                    self.cursor.execute(\"\"\"
                        SELECT strftime('%d/%m/%Y', data_pagamento), descricao, valor
                        FROM v_despesas_compat
                        WHERE conta_despesa = ? AND strftime('%Y-%m', data_pagamento) = ?
                        AND user_id = ?
                        ORDER BY data_pagamento
                    \"\"\", (categoria, mes_ym_selecionado, self.sessao.user_id))"""

# 2. obter_meses_disponiveis
block2_old = """                    self.cursor.execute(\"\"\"
                        SELECT DISTINCT strftime('%Y-%m', data_pagamento) as ano_mes,
                                        strftime('%m/%Y', data_pagamento) as mes_formatado
                        FROM despesas ORDER BY ano_mes DESC LIMIT 24
                    \"\"\")"""

block2_new = """                    self.cursor.execute(\"\"\"
                        SELECT DISTINCT strftime('%Y-%m', data_pagamento) as ano_mes,
                                        strftime('%m/%Y', data_pagamento) as mes_formatado
                        FROM v_despesas_compat
                        WHERE user_id = ?
                        ORDER BY ano_mes DESC LIMIT 24
                    \"\"\", (self.sessao.user_id,))"""

# 3. atualizar_grafico (query 1)
block3_old = """                    self.cursor.execute(\"\"\"
                        SELECT conta_despesa, SUM(valor) as total_valor
                        FROM despesas WHERE strftime('%Y-%m', data_pagamento) = ? AND conta_despesa != 'Pagamentos' COLLATE NOCASE
                        GROUP BY conta_despesa ORDER BY total_valor DESC LIMIT 10
                    \"\"\", (mes_selecionado,))"""

block3_new = """                    self.cursor.execute(\"\"\"
                        SELECT conta_despesa, SUM(valor) as total_valor
                        FROM v_despesas_compat
                        WHERE strftime('%Y-%m', data_pagamento) = ? AND conta_despesa != 'Pagamentos' COLLATE NOCASE
                        AND user_id = ?
                        GROUP BY conta_despesa ORDER BY total_valor DESC LIMIT 10
                    \"\"\", (mes_selecionado, self.sessao.user_id))"""

# 4. atualizar_grafico (query 2)
block4_old = """                    self.cursor.execute("SELECT SUM(valor) FROM despesas WHERE strftime('%Y-%m', data_pagamento) = ? AND conta_despesa != 'Pagamentos' COLLATE NOCASE", (mes_selecionado,))"""

block4_new = """                    self.cursor.execute("SELECT SUM(valor) FROM v_despesas_compat WHERE strftime('%Y-%m', data_pagamento) = ? AND conta_despesa != 'Pagamentos' COLLATE NOCASE AND user_id = ?", (mes_selecionado, self.sessao.user_id))"""

# 5. exportar_dados (query 1)
block5_old = """                    self.cursor.execute(\"\"\"
                        SELECT conta_despesa, SUM(valor) as total_valor, COUNT(*) as total_registros
                        FROM despesas WHERE strftime('%Y-%m', data_pagamento) = ? AND conta_despesa != 'Pagamentos' COLLATE NOCASE
                        GROUP BY conta_despesa ORDER BY total_valor DESC
                    \"\"\", (mes_valor,))"""

block5_new = """                    self.cursor.execute(\"\"\"
                        SELECT conta_despesa, SUM(valor) as total_valor, COUNT(*) as total_registros
                        FROM v_despesas_compat
                        WHERE strftime('%Y-%m', data_pagamento) = ? AND conta_despesa != 'Pagamentos' COLLATE NOCASE
                        AND user_id = ?
                        GROUP BY conta_despesa ORDER BY total_valor DESC
                    \"\"\", (mes_valor, self.sessao.user_id))"""

# 6. exportar_dados (query 2)
block6_old = """                    self.cursor.execute("SELECT SUM(valor) FROM despesas WHERE strftime('%Y-%m', data_pagamento) = ? AND conta_despesa != 'Pagamentos' COLLATE NOCASE", (mes_valor,))"""

block6_new = """                    self.cursor.execute("SELECT SUM(valor) FROM v_despesas_compat WHERE strftime('%Y-%m', data_pagamento) = ? AND conta_despesa != 'Pagamentos' COLLATE NOCASE AND user_id = ?", (mes_valor, self.sessao.user_id))"""


replacements = [
    (block1_old, block1_new, "Block 1"),
    (block2_old, block2_new, "Block 2"),
    (block3_old, block3_new, "Block 3"),
    (block4_old, block4_new, "Block 4"),
    (block5_old, block5_new, "Block 5"),
    (block6_old, block6_new, "Block 6")
]

for old, new, name in replacements:
    if old in content:
        content = content.replace(old, new)
        print(f"{name} replaced.")
    else:
        print(f"{name} NOT found.")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
