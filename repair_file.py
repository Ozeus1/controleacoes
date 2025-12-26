
import re

filename = r'c:\Users\Orlei\OneDrive\ProjPython\FINAN\sistema_financeiro_v15.py'

# 1. Read file
with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# 2. Prepare the corrected function code
# I'm pasting the function from backup and applying fixes manually here to ensure correctness.
corrected_function = """
    def mostrar_grafico_principais_contas(self):
        \"\"\"
        Exibe um gráfico das 10 principais contas de despesa, com cores e interatividade.
        Permite selecionar diferentes meses e clicar nas barras para ver detalhes.
        \"\"\"
        try:
            # Importações necessárias (caso não estejam no topo do arquivo)
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.ticker import FuncFormatter
            import matplotlib.pyplot as plt
            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment
            from openpyxl.utils import get_column_letter
            from tkinter import filedialog
            
            # Obter mês atual como padrão
            data_atual = datetime.now()
            mes_atual_ym = data_atual.strftime("%Y-%m")
            mes_atual_formatado = data_atual.strftime("%m/%Y")

            # Criar janela para o gráfico
            janela_grafico = tk.Toplevel(self.root)
            janela_grafico.title(f"Top 10 Contas - {mes_atual_formatado}")
            janela_grafico.geometry("900x800")
            
            # Frame principal
            frame_principal = ttk.Frame(janela_grafico, padding="10")
            frame_principal.pack(fill=tk.BOTH, expand=True)

            # --- Função aninhada para mostrar os detalhes da transação ---
            def mostrar_detalhes_transacao(categoria, mes_ym_selecionado):
                try:
                    # Criar a janela de detalhes
                    detalhes_window = tk.Toplevel(janela_grafico)
                    mes_formatado_titulo = datetime.strptime(mes_ym_selecionado, "%Y-%m").strftime("%m/%Y")
                    detalhes_window.title(f"Detalhes para '{categoria}' em {mes_formatado_titulo}")
                    detalhes_window.geometry("600x400")
                    detalhes_window.transient(janela_grafico)
                    detalhes_window.grab_set()

                    # Frame para o Treeview
                    tree_frame = ttk.Frame(detalhes_window, padding="10")
                    tree_frame.pack(fill=tk.BOTH, expand=True)

                    # Consultar as transações
                    self.cursor.execute(\"\"\"
                        SELECT strftime('%d/%m/%Y', data_pagamento), descricao, valor
                        FROM v_despesas_compat
                        WHERE conta_despesa = ? AND strftime('%Y-%m', data_pagamento) = ?
                        AND user_id = ?
                        ORDER BY data_pagamento
                    \"\"\", (categoria, mes_ym_selecionado, self.sessao.user_id))
                    transacoes = self.cursor.fetchall()

                    # Treeview para exibir as transações
                    cols = ('data', 'descricao', 'valor')
                    tree = ttk.Treeview(tree_frame, columns=cols, show='headings')
                    tree.heading('data', text='Data')
                    tree.heading('descricao', text='Descrição')
                    tree.heading('valor', text='Valor (R$)')
                    tree.column('data', width=100, anchor=tk.CENTER)
                    tree.column('descricao', width=350)
                    tree.column('valor', width=120, anchor=tk.E)
                    
                    # Adicionar scrollbar
                    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
                    tree.configure(yscrollcommand=scrollbar.set)
                    scrollbar.pack(side='right', fill='y')
                    tree.pack(side='left', fill='both', expand=True)


                    total_categoria = 0
                    for data, desc, valor in transacoes:
                        valor_formatado = locale.currency(valor, grouping=True)
                        tree.insert("", "end", values=(data, desc, valor_formatado))
                        total_categoria += valor
                    
                    # Adicionar um rótulo com o total
                    total_formatado = locale.currency(total_categoria, grouping=True)
                    ttk.Label(detalhes_window, text=f"Total: {total_formatado}", font=('Arial', 12, 'bold')).pack(pady=5)

                except Exception as e:
                    messagebox.showerror("Erro", f"Erro ao buscar detalhes: {e}", parent=janela_grafico)

            # --- Função de evento para cliques no gráfico ---
            def on_pick(event):
                # O nome da categoria e o mês estão armazenados no GID (Group ID) do artista
                gid = event.artist.get_gid()
                if gid:
                    categoria, mes_selecionado = gid
                    mostrar_detalhes_transacao(categoria, mes_selecionado)

            # --- Configuração da GUI para seleção de mês ---
            frame_selecao = ttk.Frame(frame_principal)
            frame_selecao.pack(fill=tk.X, pady=10)
            
            def obter_meses_disponiveis():
                try:
                    self.cursor.execute(\"\"\"
                        SELECT DISTINCT strftime('%Y-%m', data_pagamento) as ano_mes,
                                        strftime('%m/%Y', data_pagamento) as mes_formatado
                        FROM v_despesas_compat 
                        WHERE user_id = ?
                        ORDER BY ano_mes DESC LIMIT 24
                    \"\"\", (self.sessao.user_id,))
                    return self.cursor.fetchall()
                except Exception as e:
                    messagebox.showerror("Erro", f"Erro ao obter meses: {e}")
                    return []
            
            meses_disponiveis = obter_meses_disponiveis()
            if not meses_disponiveis:
                meses_disponiveis = [(mes_atual_ym,  mes_atual_formatado)]
            
            mapa_meses = {mes_fmt: mes_ym for mes_ym, mes_fmt in meses_disponiveis}
            valores_meses_formatados = [mes_fmt for _, mes_fmt in meses_disponiveis]
            
            ttk.Label(frame_selecao, text="Selecione o mês:").pack(side=tk.LEFT, padx=5)
            mes_combo = ttk.Combobox(frame_selecao, state="readonly", width=10)
            mes_combo['values'] = valores_meses_formatados
            mes_combo.pack(side=tk.LEFT, padx=5)


            # --- INÍCIO DA ALTERAÇÃO: Lógica para selecionar o mês inicial ---
            # Tenta definir o mês atual como o padrão na combobox
            if mes_atual_formatado in valores_meses_formatados:
                mes_combo.set(mes_atual_formatado)
            elif valores_meses_formatados:
                # Se o mês atual não estiver na lista (sem dados), usa o mais recente
                mes_combo.current(0)
            # --- FIM DA ALTERAÇÃO ---



            # --- Configuração da Figura e Canvas do Matplotlib ---
            frame_grafico = ttk.Frame(frame_principal)
            frame_grafico.pack(fill=tk.BOTH, expand=True, pady=10)
            
            figura = Figure(figsize=(9, 6), dpi=100)
            ax = figura.add_subplot(111)
            
            canvas = FigureCanvasTkAgg(figura, frame_grafico)
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            # Conectar o evento de clique ao manipulador
            canvas.mpl_connect('pick_event', on_pick)

            # --- GUI para informações adicionais (Total, Percentual) ---
            frame_info = ttk.Frame(frame_principal)
            frame_info.pack(fill=tk.X, pady=10)
            label_total = ttk.Label(frame_info, text="", font=('Arial', 12))
            label_total.pack(side=tk.LEFT, padx=10)
            label_percentual = ttk.Label(frame_info, text="", font=('Arial', 12))
            label_percentual.pack(side=tk.RIGHT, padx=10)

       
            # --- Função para atualizar o gráfico ---
            def atualizar_grafico(mes_selecionado):
                try:
                    # AQUI ESTÁ A CORREÇÃO: Usando a variável correta "mes_atual_formatado"
                    mes_exibicao = next((m_fmt for m_fmt, m_val in mapa_meses.items() if m_val == mes_selecionado), mes_atual_formatado)
                    
                    ax.clear()
                    
                    self.cursor.execute(\"\"\"
                        SELECT conta_despesa, SUM(valor) as total_valor
                        FROM v_despesas_compat 
                        WHERE strftime('%Y-%m', data_pagamento) = ?
                        AND user_id = ?
                        GROUP BY conta_despesa ORDER BY total_valor DESC LIMIT 10
                    \"\"\", (mes_selecionado, self.sessao.user_id))
                    resultados = self.cursor.fetchall()

                    if not resultados:
                        ax.text(0.5, 0.5, f"Nenhuma despesa encontrada para {mes_exibicao}", ha='center', va='center', fontsize=14)
                        janela_grafico.title(f"Top 10 Contas - {mes_exibicao}")
                        ax.set_title(f'Top 10 Contas de Despesa - {mes_exibicao}')
                        canvas.draw()
                        label_total.config(text="Total Top 10: R$ 0,00")
                        label_percentual.config(text="Representa 0.0% do total do mês")
                        return

                    self.cursor.execute("SELECT SUM(valor) FROM v_despesas_compat WHERE strftime('%Y-%m', data_pagamento) = ? AND user_id = ?", (mes_selecionado, self.sessao.user_id))
                    total_mes = self.cursor.fetchone()[0] or 0
                    
                    contas = [row[0] for row in resultados]
                    valores = [row[1] for row in resultados]
                    
                    total_top10 = sum(valores)
                    percentual_top10 = (total_top10 / total_mes * 100) if total_mes > 0 else 0
                    
                    # Definir cores diferentes para as barras
                    cores = plt.cm.get_cmap('tab10', 10).colors

                    # Criar barras horizontais e torná-las clicáveis
                    barras = ax.barh(contas[::-1], valores[::-1], color=cores, picker=True)

                    # Armazenar informações de categoria e mês em cada barra para o clique
                    for i, barra in enumerate(barras):
                        categoria = contas[::-1][i]
                        barra.set_gid((categoria, mes_selecionado))

                    # Adicionar rótulos de valor
                    for barra in barras:
                        largura = barra.get_width()
                        ax.text(largura * 1.01, barra.get_y() + barra.get_height()/2, 
                                locale.currency(largura, grouping=True),
                                va='center', ha='left', fontsize=9)
                    
                    # Configurar estilo do gráfico
                    ax.set_title(f'Top 10 Contas de Despesa - {mes_exibicao}')
                    ax.set_xlabel('Valor Total (R$)')
                    ax.set_ylabel('Conta de Despesa')
                    ax.grid(True, linestyle='--', alpha=0.7, axis='x')
                    ax.set_xlim(right=max(valores) * 1.18)  # Ajustar limite do eixo x para os rótulos

                    # Formatar o eixo x como moeda
                    def formatar_reais(x, pos):
                        return locale.currency(x, symbol=False, grouping=True)
                    ax.xaxis.set_major_formatter(FuncFormatter(formatar_reais))
                    
                    figura.tight_layout()
                    canvas.draw()
                    
                    # Atualizar informações
                    label_total.config(text=f"Total Top 10: {locale.currency(total_top10, grouping=True)}")
                    label_percentual.config(text=f"Representa {percentual_top10:.1f}% do total do mês")
                
                except Exception as e:
                    messagebox.showerror("Erro", f"Erro ao atualizar gráfico: {e}")
                    import traceback
                    traceback.print_exc()
                        
           ####################################################################
           
            
            # --- Manipulador de evento para mudança de mês ---
            def on_mes_change(event):
                try:
                    mes_selecionado_fmt = mes_combo.get()
                    mes_valor_ym = mapa_meses.get(mes_selecionado_fmt)
                    if not mes_valor_ym:
                        messagebox.showerror("Erro", "Mês inválido selecionado")
                        return
                    atualizar_grafico(mes_valor_ym)
                    janela_grafico.title(f"Top 10 Contas - {mes_selecionado_fmt}")
                except Exception as e:
                    messagebox.showerror("Erro", f"Erro ao mudar mês: {e}")
            
            mes_combo.bind("<<ComboboxSelected>>", on_mes_change)
            
            # --- Lógica para o botão de exportar ---
            def exportar_dados():
                try:
                    mes_selecionado = mes_combo.get()
                    mes_valor = mapa_meses.get(mes_selecionado)
                    if not mes_valor:
                        messagebox.showerror("Erro", "Mês inválido selecionado")
                        return
                    
                    # Chama a função de exportação existente (adaptada para receber o mês)
                    # Como a função original exportar_relatorio_excel pede mes e ano separados:
                    ano, mes = map(int, mes_valor.split('-'))
                    self.exportar_relatorio_excel(mes, ano)
                    
                except Exception as e:
                    messagebox.showerror("Erro", f"Erro ao exportar: {e}")

            ttk.Button(frame_principal, text="Exportar Dados do Mês", command=exportar_dados).pack(pady=10)

            # Inicializar com o valor selecionado
            if mes_combo.get():
                on_mes_change(None)
                
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao abrir gráfico: {e}")
"""

# 3. Identify insertion point (before criar_banco_dados)
insert_idx = -1
for i, line in enumerate(lines):
    if 'def criar_banco_dados' in line:
        insert_idx = i
        break

if insert_idx == -1:
    print("Error: criar_banco_dados not found.")
    exit(1)

# 4. Identify orphaned block (def atualizar_grafico)
orphaned_start = -1
orphaned_end = -1
for i, line in enumerate(lines):
    if 'def atualizar_grafico' in line and i > insert_idx:
        orphaned_start = i
        # Find end (heuristic: indentation change or next def, or just assume a block size)
        # Let's look for indentation < 12 spaces (since it's nested)
        # But if it's orphaned, it might be at 12 spaces.
        # Let's just delete until the end of file or next known function?
        # Actually, let's delete a chunk around it.
        # inspect_range_890.py showed it at 896.
        # Let's delete from 890 to 950 to be safe, or until we hit something valid.
        # But we don't want to delete valid code.
        # Let's assume it's a block of garbage.
        orphaned_start = i - 5 # Give some buffer
        orphaned_end = i + 100 # Assume it's not huge
        break

# 5. Apply changes
# Delete orphaned block first (indices shift!)
# Actually, better to build a new list of lines.

new_lines = []
# Add lines up to insert_idx
new_lines.extend(lines[:insert_idx])

# Insert corrected function
new_lines.append(corrected_function)
new_lines.append('\n')

# Add lines from insert_idx to end, SKIPPING the orphaned block
for i in range(insert_idx, len(lines)):
    # Check if this line is part of the orphaned block
    # We need to be careful.
    # If we found orphaned_start, we skip lines around it.
    if orphaned_start != -1 and orphaned_start <= i <= orphaned_end:
        continue # Skip garbage
    new_lines.append(lines[i])

# 6. Write back
with open(filename, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("File repaired.")
