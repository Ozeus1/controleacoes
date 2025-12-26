import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime
import calendar
import locale
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkcalendar import DateEntry # É necessário ter o tkcalendar instalado (pip install tkcalendar)
import numpy as np # <-- ADICIONE ESTA LINHA

# Configura a localização para o formato de moeda brasileiro (BRL)
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        print("Aviso de Locale: 'pt_BR' não encontrado. A formatação pode estar incorreta.")

class RelatorioBalanco(tk.Toplevel):
    """
    Janela para gerenciar e visualizar o FLUXO DE CAIXA mensal (entradas vs. saídas).
    Opera em um banco de dados separado (fluxo_caixa.db).
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title("Balanço de Fluxo de Caixa Mensal (Entradas x Saídas)")
        self.geometry("1150x750") # Aumentei um pouco a altura para o novo formulário

        self.db_path = 'fluxo_caixa.db'
        self._criar_banco()

        # Variáveis de controle do formulário principal
        self.id_var = tk.StringVar()
        self.ano_var = tk.IntVar(value=datetime.now().year)
        self.mes_var = tk.StringVar(value=calendar.month_name[datetime.now().month])
        self.entradas_var = tk.DoubleVar()
        self.saidas_var = tk.DoubleVar()
        self.saldo_var = tk.StringVar()
        self.obs_var = None

        # --- NOVO: Variáveis para o formulário de eventos avulsos ---
        self.evento_descricao_var = tk.StringVar()
        self.evento_valor_var = tk.DoubleVar()
        self.evento_data_entry = None

        self._criar_widgets()
        self._carregar_dados_treeview()
        self._atualizar_grafico()

    def _criar_banco(self):
        """Cria o banco de dados e as tabelas se não existirem."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS balanco_mensal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ano INTEGER NOT NULL,
                    mes INTEGER NOT NULL,
                    total_entradas REAL DEFAULT 0,
                    total_saidas REAL DEFAULT 0,
                    saldo_mes REAL DEFAULT 0,
                    observacoes TEXT,
                    UNIQUE(ano, mes)
                )
            """)
            # --- NOVO: Tabela para registrar eventos de caixa avulsos ---
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS eventos_caixa_avulsos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data DATE NOT NULL,
                    descricao TEXT NOT NULL,
                    valor REAL NOT NULL
                )
            """)
            try:
                cursor.execute("ALTER TABLE balanco_mensal RENAME COLUMN total_receitas TO total_entradas")
                cursor.execute("ALTER TABLE balanco_mensal RENAME COLUMN total_despesas TO total_saidas")
            except sqlite3.OperationalError:
                pass 
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Erro ao criar o banco de fluxo_caixa.db: {e}", parent=self)

    def _criar_widgets(self):
        """Cria e organiza os widgets na janela."""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Frame Superior (Formulário Principal + Gráfico) ---
        frame_superior = ttk.Frame(main_frame)
        frame_superior.pack(fill=tk.BOTH, expand=True)

        frame_form = ttk.LabelFrame(frame_superior, text="Formulário de Fluxo de Caixa Mensal", padding="10")
        frame_form.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), anchor='n')

        # (O conteúdo do formulário principal permanece o mesmo)
        ttk.Label(frame_form, text="ID:").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Entry(frame_form, textvariable=self.id_var, state='readonly', width=10).grid(row=0, column=1, sticky="w", columnspan=2, pady=3)
        ttk.Label(frame_form, text="Ano:").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Spinbox(frame_form, from_=2020, to=2100, textvariable=self.ano_var, width=8).grid(row=1, column=1, sticky="w", columnspan=2, pady=3)
        ttk.Label(frame_form, text="Mês:").grid(row=2, column=0, sticky="w", pady=3)
        meses_nomes = [calendar.month_name[i] for i in range(1, 13)]
        ttk.Combobox(frame_form, textvariable=self.mes_var, values=meses_nomes, state='readonly', width=15).grid(row=2, column=1, sticky="w", columnspan=2, pady=3)
        ttk.Button(frame_form, text="Calcular Entradas (Automático)", command=self._calcular_automaticamente).grid(row=3, column=0, columnspan=3, pady=(10, 5), sticky="ew")
        ttk.Label(frame_form, text="Total de Entradas (R$):").grid(row=4, column=0, sticky="w", pady=3)
        ttk.Entry(frame_form, textvariable=self.entradas_var, width=20).grid(row=4, column=1, sticky="w", columnspan=2, pady=3)
        ttk.Label(frame_form, text="Total de Saídas (R$):").grid(row=5, column=0, sticky="w", pady=3)
        ttk.Entry(frame_form, textvariable=self.saidas_var, width=20).grid(row=5, column=1, sticky="w", pady=3)
        ttk.Button(frame_form, text="Selecionar Saídas...", command=self._abrir_seletor_saidas).grid(row=5, column=2, padx=5)
        ttk.Label(frame_form, text="Saldo do Mês (R$):").grid(row=6, column=0, sticky="w", pady=3)
        ttk.Entry(frame_form, textvariable=self.saldo_var, state='readonly', width=20).grid(row=6, column=1, sticky="w", columnspan=2, pady=3)
        ttk.Label(frame_form, text="Observações:").grid(row=7, column=0, sticky="nw", pady=3)
        self.obs_var = tk.Text(frame_form, height=5, width=40)
        self.obs_var.grid(row=7, column=1, sticky="w", columnspan=2, pady=3)
        frame_botoes = ttk.Frame(frame_form)
        frame_botoes.grid(row=8, column=0, columnspan=3, pady=15)
        ttk.Button(frame_botoes, text="Salvar", command=self._salvar_balanco).pack(side=tk.LEFT, padx=5)
        self.btn_atualizar = ttk.Button(frame_botoes, text="Atualizar", command=self._atualizar_balanco, state="disabled")
        self.btn_atualizar.pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botoes, text="Limpar", command=self._limpar_campos).pack(side=tk.LEFT, padx=5)
        self.btn_excluir = ttk.Button(frame_botoes, text="Excluir", command=self._excluir_balanco, state="disabled")
        self.btn_excluir.pack(side=tk.LEFT, padx=5)
        
        frame_dados = ttk.Frame(frame_superior)
        frame_dados.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        frame_tabela = ttk.LabelFrame(frame_dados, text="Histórico de Fluxo de Caixa", padding="5")
        frame_tabela.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        scrollbar = ttk.Scrollbar(frame_tabela)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree = ttk.Treeview(frame_tabela, yscrollcommand=scrollbar.set, selectmode="browse")
        self.tree['columns'] = ('id', 'mes_ano', 'entradas', 'saidas', 'saldo')
        self.tree.column("#0", width=0, stretch=tk.NO)
        self.tree.heading("#0", text="")
        for col in self.tree['columns']:
            self.tree.column(col, anchor=tk.CENTER, width=100)
            self.tree.heading(col, text=col.replace('_', ' ').title())
        self.tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tree.yview)
        self.tree.bind("<ButtonRelease-1>", self._selecionar_item_treeview)
        frame_grafico = ttk.LabelFrame(frame_dados, text="Evolução do Fluxo de Caixa", padding="5")
        frame_grafico.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        self.figura = plt.Figure(figsize=(7, 3), dpi=100)
        self.ax = self.figura.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figura, master=frame_grafico)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # --- NOVO: Frame Inferior para registrar eventos de caixa avulsos ---
        frame_eventos = ttk.LabelFrame(main_frame, text="Registrar Evento de Caixa Avulso (Ex: Pagamento de Fatura)", padding="10")
        frame_eventos.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(frame_eventos, text="Data:").grid(row=0, column=0, padx=5, pady=5)
        self.evento_data_entry = DateEntry(frame_eventos, width=12, date_pattern='dd/mm/yyyy', locale='pt_BR')
        self.evento_data_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(frame_eventos, text="Descrição:").grid(row=0, column=2, padx=5, pady=5)
        ttk.Entry(frame_eventos, textvariable=self.evento_descricao_var, width=50).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(frame_eventos, text="Valor (R$):").grid(row=0, column=4, padx=5, pady=5)
        ttk.Entry(frame_eventos, textvariable=self.evento_valor_var).grid(row=0, column=5, padx=5, pady=5)

        ttk.Button(frame_eventos, text="Registrar Saída de Caixa", command=self.registrar_evento_avulso).grid(row=0, column=6, padx=10, pady=5)


    def _executar_query(self, query, params=(), commit=False, fetch=None):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query, params)
            if commit: conn.commit()
            result = None
            if fetch == 'one': result = cursor.fetchone()
            if fetch == 'all': result = cursor.fetchall()
            return result
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Erro: {e}", parent=self)
            return None
        finally:
            if conn: conn.close()
    
    # --- NOVO: Método para registrar o evento de caixa avulso ---
    def registrar_evento_avulso(self):
        """Salva um novo evento de caixa e atualiza o balanço do mês correspondente."""
        data_evento = self.evento_data_entry.get_date()
        descricao = self.evento_descricao_var.get().strip()
        valor = self.evento_valor_var.get()

        if not descricao or valor <= 0:
            messagebox.showerror("Erro de Validação", "Descrição e Valor (maior que zero) são obrigatórios.", parent=self)
            return

        # 1. Insere o evento avulso no banco de dados
        query_evento = "INSERT INTO eventos_caixa_avulsos (data, descricao, valor) VALUES (?, ?, ?)"
        self._executar_query(query_evento, (data_evento.strftime('%Y-%m-%d'), descricao, valor), commit=True)

        # 2. Atualiza o balanço do mês correspondente
        ano, mes = data_evento.year, data_evento.month
        
        # Verifica se já existe um balanço para o mês
        query_select = "SELECT id, total_saidas FROM balanco_mensal WHERE ano = ? AND mes = ?"
        balanco_existente = self._executar_query(query_select, (ano, mes), fetch='one')

        if balanco_existente:
            id_balanco, total_saidas_antigo = balanco_existente
            novo_total_saidas = total_saidas_antigo + valor
            query_update = "UPDATE balanco_mensal SET total_saidas = ?, saldo_mes = total_entradas - ? WHERE id = ?"
            self._executar_query(query_update, (novo_total_saidas, novo_total_saidas, id_balanco), commit=True)
        else:
            # Cria um novo registro de balanço para o mês se não existir
            saldo = -valor
            query_insert = "INSERT INTO balanco_mensal (ano, mes, total_entradas, total_saidas, saldo_mes) VALUES (?, ?, ?, ?, ?)"
            self._executar_query(query_insert, (ano, mes, 0, valor, saldo), commit=True)

        messagebox.showinfo("Sucesso", f"Saída de caixa '{descricao}' registrada com sucesso!", parent=self)

        # Limpa os campos do formulário de evento
        self.evento_descricao_var.set("")
        self.evento_valor_var.set(0.0)

        # Atualiza a tela
        self._carregar_dados_treeview()
        self._atualizar_grafico()
        # Se o evento foi no mês atual em exibição, atualiza os campos
        if ano == self.ano_var.get() and mes == list(calendar.month_name).index(self.mes_var.get()):
            self._selecionar_item_treeview()


    # (O restante dos métodos permanece o mesmo, sem alterações)
    def _carregar_dados_treeview(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        dados = self._executar_query("SELECT id, ano, mes, total_entradas, total_saidas, saldo_mes FROM balanco_mensal ORDER BY ano DESC, mes DESC", fetch='all')
        if dados:
            for row in dados:
                id, ano, mes, entradas, saidas, saldo = row
                self.tree.insert("", "end", values=(
                    id, f"{mes:02d}/{ano}", 
                    locale.currency(entradas, grouping=True),
                    locale.currency(saidas, grouping=True),
                    locale.currency(saldo, grouping=True)
                ))

    def _limpar_campos(self):
        self.id_var.set("")
        self.ano_var.set(datetime.now().year)
        self.mes_var.set(calendar.month_name[datetime.now().month])
        self.entradas_var.set(0.0)
        self.saidas_var.set(0.0)
        self.saldo_var.set(locale.currency(0.0, grouping=True))
        self.obs_var.delete('1.0', tk.END)
        self.btn_atualizar.config(state="disabled")
        self.btn_excluir.config(state="disabled")
        if self.tree.selection(): self.tree.selection_remove(self.tree.selection())

    def _salvar_balanco(self):
        ano = self.ano_var.get()
        try: mes = list(calendar.month_name).index(self.mes_var.get())
        except ValueError: messagebox.showerror("Erro", "Mês inválido.", parent=self); return
        entradas = self.entradas_var.get()
        saidas = self.saidas_var.get()
        saldo = entradas - saidas
        obs = self.obs_var.get("1.0", tk.END).strip()
        query = "INSERT INTO balanco_mensal (ano, mes, total_entradas, total_saidas, saldo_mes, observacoes) VALUES (?, ?, ?, ?, ?, ?)"
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query, (ano, mes, entradas, saidas, saldo, obs))
            conn.commit()
            messagebox.showinfo("Sucesso", "Balanço salvo!", parent=self)
            self._limpar_campos(); self._carregar_dados_treeview(); self._atualizar_grafico()
        except sqlite3.IntegrityError: messagebox.showerror("Erro", f"Já existe registro para {mes:02d}/{ano}.", parent=self)
        except sqlite3.Error as e: messagebox.showerror("Erro", f"Erro ao salvar: {e}", parent=self)
        finally:
            if conn: conn.close()

    def _selecionar_item_treeview(self, event=None):
        selected_item = self.tree.focus()
        if not selected_item: return
        item_id = self.tree.item(selected_item, 'values')[0]
        dados = self._executar_query("SELECT * FROM balanco_mensal WHERE id = ?", (item_id,), fetch='one')
        if dados:
            _, ano, mes, entradas, saidas, saldo, obs = dados
            self.id_var.set(item_id); self.ano_var.set(ano); self.mes_var.set(calendar.month_name[mes])
            self.entradas_var.set(entradas); self.saidas_var.set(saidas)
            self.saldo_var.set(locale.currency(saldo, grouping=True))
            self.obs_var.delete('1.0', tk.END); self.obs_var.insert('1.0', obs or "")
            self.btn_atualizar.config(state="normal"); self.btn_excluir.config(state="normal")

    def _atualizar_balanco(self):
        item_id = self.id_var.get();
        if not item_id: return
        ano = self.ano_var.get(); mes = list(calendar.month_name).index(self.mes_var.get())
        entradas = self.entradas_var.get(); saidas = self.saidas_var.get()
        saldo = entradas - saidas
        obs = self.obs_var.get("1.0", tk.END).strip()
        query = "UPDATE balanco_mensal SET ano=?, mes=?, total_entradas=?, total_saidas=?, saldo_mes=?, observacoes=? WHERE id=?"
        self._executar_query(query, (ano, mes, entradas, saidas, saldo, obs, item_id), commit=True)
        messagebox.showinfo("Sucesso", "Registro atualizado!", parent=self)
        self._limpar_campos(); self._carregar_dados_treeview(); self._atualizar_grafico()

    def _excluir_balanco(self):
        item_id = self.id_var.get()
        if not item_id: return
        if messagebox.askyesno("Confirmar", "Deseja excluir este registro?", parent=self):
            self._executar_query("DELETE FROM balanco_mensal WHERE id=?", (item_id,), commit=True)
            messagebox.showinfo("Sucesso", "Registro excluído!", parent=self)
            self._limpar_campos(); self._carregar_dados_treeview(); self._atualizar_grafico()

    def _calcular_automaticamente(self):
        ano = self.ano_var.get(); mes = list(calendar.month_name).index(self.mes_var.get())
        mes_ano_str = f"{ano}-{mes:02d}"
        total_entradas = 0.0
        try:
            conn_r = sqlite3.connect('financas_receitas.db')
            cursor_r = conn_r.cursor()
            cursor_r.execute("SELECT SUM(valor) FROM receitas WHERE strftime('%Y-%m', data_recebimento) = ?", (mes_ano_str,))
            resultado = cursor_r.fetchone()
            total_entradas = resultado[0] if resultado and resultado[0] is not None else 0.0
            conn_r.close()
            self.entradas_var.set(round(total_entradas, 2))
            messagebox.showinfo("Cálculo de Entradas", f"Total de ENTRADAS para {self.mes_var.get()}/{ano} foi calculado.\n\nUse o botão 'Selecionar Saídas...' para definir o total de saídas de caixa.", parent=self)
        except sqlite3.Error as e:
            messagebox.showwarning("Aviso", f"Não foi possível calcular o total de entradas.\nErro: {e}", parent=self)

    def _abrir_seletor_saidas(self):
        """Abre uma janela interativa para o usuário selecionar as saídas de caixa a partir das despesas lançadas."""
        ano = self.ano_var.get()
        mes_nome = self.mes_var.get()
        mes = list(calendar.month_name).index(mes_nome)
        mes_ano_str = f"{ano}-{mes:02d}"

        try:
            conn_d = sqlite3.connect('financas.db')
            cursor_d = conn_d.cursor()
            cursor_d.execute("SELECT strftime('%d/%m/%Y', data_pagamento), descricao, valor, meio_pagamento FROM despesas WHERE strftime('%Y-%m', data_pagamento) = ? ORDER BY data_pagamento", (mes_ano_str,))
            despesas = cursor_d.fetchall()
            conn_d.close()
        except sqlite3.Error as e:
            messagebox.showerror("Erro BD Despesas", f"Não foi possível acessar as despesas.\nErro: {e}", parent=self)
            return

        win = tk.Toplevel(self)
        win.title(f"Selecione as Saídas de Caixa de {mes_nome}/{ano}")
        win.geometry("700x500")
        win.transient(self); win.grab_set()
        
        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        style = ttk.Style(win)
        style.configure("Custom.Treeview")
        style.map("Custom.Treeview", background=[("selected", style.lookup("TTreeview", "background"))])

        tree_despesas = ttk.Treeview(frame, style="Custom.Treeview", columns=('data', 'descricao', 'valor', 'meio_pgto'), show='headings')
        tree_despesas.heading('data', text='Data'); tree_despesas.column('data', width=80, anchor='center')
        tree_despesas.heading('descricao', text='Descrição'); tree_despesas.column('descricao', width=300)
        tree_despesas.heading('valor', text='Valor'); tree_despesas.column('valor', width=100, anchor='e')
        tree_despesas.heading('meio_pgto', text='Meio Pgto'); tree_despesas.column('meio_pgto', width=120)
        
        checkbox_vars = []
        for i, d in enumerate(despesas):
            var = tk.BooleanVar(value=False)
            checkbox_vars.append(var)
            tree_despesas.insert('', 'end', iid=i, values=(d[0], d[1], locale.currency(d[2], grouping=True), d[3]), tags=('unchecked',))
        
        tree_despesas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        def on_click(event):
            item_id = tree_despesas.identify_row(event.y)
            if item_id:
                index = int(item_id)
                checkbox_vars[index].set(not checkbox_vars[index].get())
                tag = 'checked' if checkbox_vars[index].get() else 'unchecked'
                tree_despesas.item(item_id, tags=(tag,))
        
        tree_despesas.tag_configure('checked', background='lightyellow')
        tree_despesas.bind('<Button-1>', on_click)
        
        def aplicar_soma():
            soma_selecionada = 0.0
            for i, var in enumerate(checkbox_vars):
                if var.get():
                    soma_selecionada += despesas[i][2]
            
            self.saidas_var.set(round(soma_selecionada, 2))
            messagebox.showinfo("Soma Aplicada", f"O valor de {locale.currency(soma_selecionada, grouping=True)} foi definido como o Total de Saídas.", parent=win)
            win.destroy()

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10,0))
        ttk.Button(btn_frame, text="Usar Soma dos Selecionados como Saída", command=aplicar_soma).pack(pady=5)
        ttk.Label(btn_frame, text="Clique nas linhas para selecionar/desselecionar as saídas de caixa.", wraplength=650, justify='center').pack()

    def _atualizar_grafico1(self):
        self.ax.clear()
        dados = self._executar_query("SELECT ano, mes, total_entradas, total_saidas, saldo_mes FROM balanco_mensal ORDER BY ano, mes", fetch='all')
        if dados:
            labels = [f"{mes:02d}/{ano}" for ano, mes, _, _, _ in dados]
            entradas = [r for _, _, r, _, _ in dados]
            saidas = [d for _, _, _, d, _ in dados]
            saldos = [s for _, _, _, _, s in dados]
            self.ax.plot(labels, entradas, marker='o', linestyle='-', color='g', label='Entradas')
            self.ax.plot(labels, saidas, marker='o', linestyle='-', color='r', label='Saídas')
            self.ax.plot(labels, saldos, marker='s', linestyle='--', color='b', label='Saldo do Mês')
            self.ax.legend(); self.ax.grid(True, linestyle='--', alpha=0.6)
            plt.setp(self.ax.get_xticklabels(), rotation=45, ha="right")
        else:
            self.ax.text(0.5, 0.5, "Sem dados para exibir", ha='center', va='center')
        self.ax.set_title("Evolução do Fluxo de Caixa Mensal", fontsize=10)
        self.ax.set_ylabel("Valor (R$)"); self.figura.tight_layout(); self.canvas.draw()


    def _atualizar_grafico(self):
        """
        Atualiza o gráfico para um formato de combinação com barras para entradas/saídas
        e uma linha para o saldo, utilizando um eixo secundário.
        """
        self.ax.clear()
        
        dados = self._executar_query("SELECT ano, mes, total_entradas, total_saidas, saldo_mes FROM balanco_mensal ORDER BY ano, mes", fetch='all')
        
        if not dados:
            self.ax.text(0.5, 0.5, "Sem dados para exibir", ha='center', va='center')
            self.canvas.draw()
            return
            
        labels = [f"{mes:02d}/{ano}" for ano, mes, _, _, _ in dados]
        entradas = [e for _, _, e, _, _ in dados]
        saidas = [s for _, _, _, s, _ in dados]
        saldos = [s for _, _, _, _, s in dados]

        x = np.arange(len(labels))  # Localização das labels
        bar_width = 0.35  # Largura das barras

        # Criação do eixo secundário para a linha de saldo
        ax2 = self.ax.twinx()

        # Plotar as barras no eixo principal (ax)
        bar1 = self.ax.bar(x - bar_width/2, entradas, bar_width, label='Entradas', color='mediumseagreen')
        bar2 = self.ax.bar(x + bar_width/2, saidas, bar_width, label='Saídas', color='coral')

        # Adicionar rótulos de valor em cima das barras
        self.ax.bar_label(bar1, padding=3, fmt=lambda v: locale.currency(v, symbol=False, grouping=True), fontsize=8)
        self.ax.bar_label(bar2, padding=3, fmt=lambda v: locale.currency(v, symbol=False, grouping=True), fontsize=8)

        # Plotar a linha no eixo secundário (ax2)
        line1, = ax2.plot(x, saldos, label='Saldo do Mês', color='royalblue', linestyle='--', marker='o')

        # Configurações do Gráfico
        self.ax.set_ylabel('Valor Entradas/Saídas (R$)')
        ax2.set_ylabel('Valor Saldo (R$)')
        self.ax.set_title('Evolução do Fluxo de Caixa Mensal')
        self.ax.set_xticks(x)
        self.ax.set_xticklabels(labels, rotation=45, ha='right')
        
        # Unir as legendas dos dois eixos
        handles1, labels1 = self.ax.get_legend_handles_labels()
        handles2, labels2 = ax2.get_legend_handles_labels()
        self.ax.legend(handles1 + handles2, labels1 + labels2, loc='upper left')

        self.ax.grid(axis='y', linestyle='--', alpha=0.7)
        self.figura.tight_layout()
        self.canvas.draw()
    # =================== FIM DA ALTERAÇÃO DO GRÁFICO ===================



def iniciar_relatorio_balanco(parent_window):
    RelatorioBalanco(parent_window)