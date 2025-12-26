import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime
import calendar
import locale
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from tkcalendar import DateEntry

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
    Janela para gerenciar o Fluxo de Caixa, permitindo consolidar balanços mensais
    e registrar eventos de caixa avulsos de forma independente.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title("Balanço e Lançamentos de Fluxo de Caixa")
        self.geometry("1220x750")

        self.db_path = 'fluxo_caixa.db'
        self._criar_banco()

        # Variáveis de controle do formulário de balanço
        self.id_var = tk.StringVar()
        self.ano_var = tk.IntVar(value=datetime.now().year)
        self.mes_var = tk.StringVar(value=calendar.month_name[datetime.now().month])
        self.entradas_var = tk.DoubleVar()
        self.saidas_var = tk.DoubleVar()
        self.saldo_var = tk.StringVar()
        self.obs_var = None

        # Variáveis para o formulário de eventos avulsos
        self.evento_id_var = tk.StringVar()
        self.evento_descricao_var = tk.StringVar()
        self.evento_valor_var = tk.DoubleVar()
        self.evento_data_entry = None

        self._criar_widgets()
        self._carregar_dados_treeview()
        self._carregar_eventos_treeview()
        self._atualizar_grafico()

    def _criar_banco(self):
        """Cria o banco de dados e as tabelas necessárias se não existirem."""
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
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS eventos_caixa_avulsos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data DATE NOT NULL,
                    descricao TEXT NOT NULL,
                    valor REAL NOT NULL
                )
            """)
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Erro ao criar tabelas: {e}", parent=self)

    def _criar_widgets(self):
        """Cria e organiza os widgets na janela."""
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # --- ABA 1: Balanço Mensal ---
        tab_balanco = ttk.Frame(notebook, padding=5)
        notebook.add(tab_balanco, text="Balanço Mensal Consolidado")

        frame_form = ttk.LabelFrame(tab_balanco, text="Formulário de Fluxo de Caixa Mensal", padding="10")
        frame_form.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), anchor='n')
        
        ttk.Label(frame_form, text="ID:").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Entry(frame_form, textvariable=self.id_var, state='readonly', width=10).grid(row=0, column=1, sticky="w", columnspan=2, pady=3)
        ttk.Label(frame_form, text="Ano:").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Spinbox(frame_form, from_=2020, to=2100, textvariable=self.ano_var, width=8).grid(row=1, column=1, sticky="w", columnspan=2, pady=3)
        ttk.Label(frame_form, text="Mês:").grid(row=2, column=0, sticky="w", pady=3)
        meses_nomes = [calendar.month_name[i] for i in range(1, 13)]; meses_nomes.insert(0,"")
        ttk.Combobox(frame_form, textvariable=self.mes_var, values=meses_nomes, state='readonly', width=15).grid(row=2, column=1, sticky="w", columnspan=2, pady=3)
        ttk.Button(frame_form, text="Calcular Entradas (Automático)", command=self._calcular_entradas_automaticamente).grid(row=3, column=0, columnspan=3, pady=(10, 5), sticky="ew")
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
        
        frame_dados = ttk.Frame(tab_balanco)
        frame_dados.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        frame_tabela = ttk.LabelFrame(frame_dados, text="Histórico de Fluxo de Caixa (Dê duplo clique para ver detalhes)", padding="5")
        frame_tabela.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        scrollbar = ttk.Scrollbar(frame_tabela)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree = ttk.Treeview(frame_tabela, yscrollcommand=scrollbar.set, selectmode="browse")
        self.tree['columns'] = ('id', 'mes_ano', 'entradas', 'saidas', 'saldo')
        self.tree.column("#0", width=0, stretch=tk.NO); self.tree.heading("#0", text="")
        for col in self.tree['columns']: self.tree.column(col, anchor=tk.CENTER, width=100); self.tree.heading(col, text=col.replace('_', ' ').title())
        self.tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tree.yview)
        self.tree.bind("<ButtonRelease-1>", self._selecionar_item_treeview)
        self.tree.bind("<Double-1>", self._mostrar_detalhes_mes)
        
        frame_grafico = ttk.LabelFrame(frame_dados, text="Evolução do Fluxo de Caixa", padding="5")
        frame_grafico.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        self.figura = plt.Figure(figsize=(7, 3), dpi=100)
        self.ax = self.figura.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figura, master=frame_grafico)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # --- ABA 2: Lançamentos de Caixa Avulsos ---
        tab_eventos_frame = ttk.Frame(notebook)
        notebook.add(tab_eventos_frame, text="Lançamentos de Caixa Avulsos")
        self.tree_eventos = ttk.Treeview(tab_eventos_frame, columns=('id', 'data', 'descricao', 'valor'), show='headings')
        self.tree_eventos.heading('id', text='ID'); self.tree_eventos.column('id', width=50, anchor='center')
        self.tree_eventos.heading('data', text='Data'); self.tree_eventos.column('data', width=100, anchor='center')
        self.tree_eventos.heading('descricao', text='Descrição'); self.tree_eventos.column('descricao', width=400)
        self.tree_eventos.heading('valor', text='Valor'); self.tree_eventos.column('valor', width=150, anchor='e')
        self.tree_eventos.bind("<ButtonRelease-1>", self._selecionar_evento_avulso)
        self.tree_eventos.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # --- Frame Inferior para registrar eventos de caixa avulsos ---
        frame_eventos_form = ttk.LabelFrame(main_frame, text="Registrar / Editar Evento de Caixa Avulso (Ex: Pagamento de Fatura)", padding="10")
        frame_eventos_form.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(frame_eventos_form, text="Data:").grid(row=0, column=0, padx=5, pady=5)
        self.evento_data_entry = DateEntry(frame_eventos_form, width=12, date_pattern='dd/mm/yyyy', locale='pt_BR')
        self.evento_data_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(frame_eventos_form, text="Descrição:").grid(row=0, column=2, padx=5, pady=5)
        ttk.Entry(frame_eventos_form, textvariable=self.evento_descricao_var, width=50).grid(row=0, column=3, padx=5, pady=5)
        ttk.Label(frame_eventos_form, text="Valor (R$):").grid(row=0, column=4, padx=5, pady=5)
        ttk.Entry(frame_eventos_form, textvariable=self.evento_valor_var).grid(row=0, column=5, padx=5, pady=5)
        
        botoes_eventos_frame = ttk.Frame(frame_eventos_form)
        botoes_eventos_frame.grid(row=0, column=6, padx=10)
        self.btn_registrar_evento = ttk.Button(botoes_eventos_frame, text="Registrar Saída", command=self.registrar_evento_avulso)
        self.btn_registrar_evento.pack(side=tk.LEFT, padx=5)
        self.btn_atualizar_evento = ttk.Button(botoes_eventos_frame, text="Atualizar", command=self._atualizar_evento_avulso, state="disabled")
        self.btn_atualizar_evento.pack(side=tk.LEFT, padx=5)
        self.btn_excluir_evento = ttk.Button(botoes_eventos_frame, text="Excluir", command=self._excluir_evento_avulso, state="disabled")
        self.btn_excluir_evento.pack(side=tk.LEFT, padx=5)
        ttk.Button(botoes_eventos_frame, text="Limpar", command=self._limpar_formulario_evento).pack(side=tk.LEFT, padx=5)

    def _executar_query(self, query, params=(), commit=False, fetch=None, db_path=None):
        db_path = db_path or self.db_path
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                if commit: conn.commit()
                if fetch == 'one': return cursor.fetchone()
                if fetch == 'all': return cursor.fetchall()
        except sqlite3.Error as e:
            messagebox.showerror("Erro de BD", f"Erro ao acessar '{db_path}':\n{e}", parent=self)
            return None

    def registrar_evento_avulso(self):
        data = self.evento_data_entry.get_date()
        descricao = self.evento_descricao_var.get().strip()
        valor = self.evento_valor_var.get()
        if not descricao or valor <= 0: messagebox.showerror("Erro", "Descrição e Valor (maior que zero) são obrigatórios.", parent=self); return
        query = "INSERT INTO eventos_caixa_avulsos (data, descricao, valor) VALUES (?, ?, ?)"
        self._executar_query(query, (data.strftime('%Y-%m-%d'), descricao, valor), commit=True)
        self._atualizar_balanco_com_valor_avulso(data.year, data.month, valor)
        self._limpar_formulario_evento()
        self._carregar_eventos_treeview()
        self._carregar_dados_treeview()
        self._atualizar_grafico()

    def _atualizar_balanco_com_valor_avulso(self, ano, mes, valor_diferenca):
        query_select = "SELECT id, total_saidas FROM balanco_mensal WHERE ano = ? AND mes = ?"
        balanco_existente = self._executar_query(query_select, (ano, mes), fetch='one')
        if balanco_existente:
            id_balanco, total_saidas_antigo = balanco_existente
            novo_total_saidas = total_saidas_antigo + valor_diferenca
            query_update = "UPDATE balanco_mensal SET total_saidas = ?, saldo_mes = total_entradas - ? WHERE id = ?"
            self._executar_query(query_update, (novo_total_saidas, novo_total_saidas, id_balanco), commit=True)
        else:
            saldo = -valor_diferenca
            query_insert = "INSERT INTO balanco_mensal (ano, mes, total_entradas, total_saidas, saldo_mes) VALUES (?, ?, ?, ?, ?)"
            self._executar_query(query_insert, (ano, mes, 0, valor_diferenca, saldo), commit=True)
        messagebox.showinfo("Sucesso", "Evento de caixa avulso processado e balanço mensal atualizado!", parent=self)

    def _carregar_eventos_treeview(self):
        for i in self.tree_eventos.get_children(): self.tree_eventos.delete(i)
        eventos = self._executar_query("SELECT id, strftime('%d/%m/%Y', data), descricao, valor FROM eventos_caixa_avulsos ORDER BY data DESC, id DESC", fetch='all')
        if eventos:
            for id_evento, data, desc, valor in eventos:
                self.tree_eventos.insert('', 'end', values=(id_evento, data, desc, locale.currency(valor, grouping=True)))

    def _limpar_formulario_evento(self):
        self.evento_id_var.set("")
        self.evento_descricao_var.set("")
        self.evento_valor_var.set(0.0)
        self.evento_data_entry.set_date(datetime.now())
        self.btn_registrar_evento.config(state="normal")
        self.btn_atualizar_evento.config(state="disabled")
        self.btn_excluir_evento.config(state="disabled")
        if self.tree_eventos.selection(): self.tree_eventos.selection_remove(self.tree_eventos.selection())

    def _selecionar_evento_avulso(self, event=None):
        selected_item = self.tree_eventos.focus()
        if not selected_item: return
        item_values = self.tree_eventos.item(selected_item, 'values')
        item_id = item_values[0]
        dados = self._executar_query("SELECT data, descricao, valor FROM eventos_caixa_avulsos WHERE id = ?", (item_id,), fetch='one')
        if dados:
            data_str, desc, valor = dados
            data_obj = datetime.strptime(data_str, '%Y-%m-%d')
            self.evento_id_var.set(item_id); self.evento_data_entry.set_date(data_obj)
            self.evento_descricao_var.set(desc); self.evento_valor_var.set(valor)
            self.btn_registrar_evento.config(state="disabled")
            self.btn_atualizar_evento.config(state="normal"); self.btn_excluir_evento.config(state="normal")

    def _atualizar_evento_avulso(self):
        item_id = self.evento_id_var.get()
        if not item_id: return
        valor_antigo_res = self._executar_query("SELECT valor, data FROM eventos_caixa_avulsos WHERE id=?", (item_id,), fetch='one')
        if not valor_antigo_res: return
        valor_antigo_val, data_antiga_str = valor_antigo_res
        data_antiga_obj = datetime.strptime(data_antiga_str, '%Y-%m-%d')
        data_nova = self.evento_data_entry.get_date(); descricao = self.evento_descricao_var.get().strip(); valor_novo = self.evento_valor_var.get()
        if not descricao or valor_novo <= 0: return
        query = "UPDATE eventos_caixa_avulsos SET data=?, descricao=?, valor=? WHERE id=?"
        self._executar_query(query, (data_nova.strftime('%Y-%m-%d'), descricao, valor_novo, item_id), commit=True)
        self._atualizar_balanco_com_valor_avulso(data_antiga_obj.year, data_antiga_obj.month, -valor_antigo_val)
        self._atualizar_balanco_com_valor_avulso(data_nova.year, data_nova.month, valor_novo)
        self._limpar_formulario_evento()
        self._carregar_eventos_treeview(); self._carregar_dados_treeview(); self._atualizar_grafico()

    def _excluir_evento_avulso(self):
        item_id = self.evento_id_var.get()
        if not item_id: return
        if messagebox.askyesno("Confirmar", "Deseja realmente excluir este evento?", parent=self):
            valor_a_remover = self._executar_query("SELECT valor, data FROM eventos_caixa_avulsos WHERE id=?", (item_id,), fetch='one')
            if not valor_a_remover: return
            valor, data_str = valor_a_remover
            data_obj = datetime.strptime(data_str, '%Y-%m-%d')
            self._executar_query("DELETE FROM eventos_caixa_avulsos WHERE id=?", (item_id,), commit=True)
            self._atualizar_balanco_com_valor_avulso(data_obj.year, data_obj.month, -valor)
            self._limpar_formulario_evento()
            self._carregar_eventos_treeview(); self._carregar_dados_treeview(); self._atualizar_grafico()

    def _carregar_dados_treeview(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        dados = self._executar_query("SELECT id, ano, mes, total_entradas, total_saidas, saldo_mes FROM balanco_mensal ORDER BY ano DESC, mes DESC", fetch='all')
        if dados:
            for row in dados:
                id_reg, ano, mes, entradas, saidas, saldo = row
                self.tree.insert("", "end", values=(id_reg, f"{mes:02d}/{ano}", locale.currency(entradas, grouping=True), locale.currency(saidas, grouping=True), locale.currency(saldo, grouping=True)))

    def _limpar_campos(self):
        self.id_var.set(""); self.ano_var.set(datetime.now().year); self.mes_var.set(calendar.month_name[datetime.now().month])
        self.entradas_var.set(0.0); self.saidas_var.set(0.0); self.saldo_var.set(locale.currency(0.0, grouping=True))
        if self.obs_var: self.obs_var.delete('1.0', tk.END)
        self.btn_atualizar.config(state="disabled"); self.btn_excluir.config(state="disabled")
        if self.tree.selection(): self.tree.selection_remove(self.tree.selection())

    def _salvar_balancoant(self):
        ano = self.ano_var.get(); mes = list(calendar.month_name).index(self.mes_var.get())
        entradas = self.entradas_var.get(); saidas = self.saidas_var.get(); saldo = entradas - saidas
        obs = self.obs_var.get("1.0", tk.END).strip()
        query = "INSERT INTO balanco_mensal (ano, mes, total_entradas, total_saidas, saldo_mes, observacoes) VALUES (?, ?, ?, ?, ?, ?)"
        try:
            self._executar_query(query, (ano, mes, entradas, saidas, saldo, obs), commit=True)
            messagebox.showinfo("Sucesso", "Balanço salvo!", parent=self)
            self._limpar_campos(); self._carregar_dados_treeview(); self._atualizar_grafico()
        except sqlite3.IntegrityError: messagebox.showerror("Erro", f"Já existe um registro para {mes:02d}/{ano}. Selecione-o na lista e use 'Atualizar'.", parent=self)

    def _salvar_balanco(self):
            """Salva um novo registro de balanço ou atualiza um existente se um ID já estiver carregado."""
            # --- CORREÇÃO ADICIONADA AQUI ---
            # Se um ID já está carregado no formulário, significa que o usuário
            # quer atualizar um registro existente. Em vez de dar erro,
            # simplesmente chamamos a função de atualização.
            if self.id_var.get():
                self._atualizar_balanco()
                return
            # --- FIM DA CORREÇÃO ---

            # O código abaixo (para inserir um novo registro) só será executado se não houver um ID carregado.
            ano = self.ano_var.get()
            try: 
                mes = list(calendar.month_name).index(self.mes_var.get())
                if mes == 0: # Impede que o campo de mês vazio seja salvo
                    messagebox.showerror("Erro", "Por favor, selecione um mês.", parent=self)
                    return
            except ValueError: 
                messagebox.showerror("Erro", "Mês inválido.", parent=self)
                return
                
            entradas = self.entradas_var.get()
            saidas = self.saidas_var.get()
            saldo = entradas - saidas
            obs = self.obs_var.get("1.0", tk.END).strip()
            query = "INSERT INTO balanco_mensal (ano, mes, total_entradas, total_saidas, saldo_mes, observacoes) VALUES (?, ?, ?, ?, ?, ?)"
            
            try:
                self._executar_query(query, (ano, mes, entradas, saidas, saldo, obs), commit=True)
                messagebox.showinfo("Sucesso", "Balanço salvo!", parent=self)
                self._limpar_campos()
                self._carregar_dados_treeview()
                self._atualizar_grafico()
            except sqlite3.IntegrityError: 
                messagebox.showerror("Erro", f"Já existe um registro para {mes:02d}/{ano}. Selecione-o na lista e use 'Atualizar'.", parent=self)





    def _selecionar_item_treeview(self, event=None):
        selected_item = self.tree.focus()
        if not selected_item: return
        item_id = self.tree.item(selected_item, 'values')[0]
        dados = self._executar_query("SELECT * FROM balanco_mensal WHERE id = ?", (item_id,), fetch='one')
        if dados:
            id_reg, ano, mes, entradas, saidas, saldo, obs = dados
            self.id_var.set(id_reg); self.ano_var.set(ano); self.mes_var.set(calendar.month_name[mes])
            self.entradas_var.set(entradas); self.saidas_var.set(saidas); self.saldo_var.set(locale.currency(saldo, grouping=True))
            self.obs_var.delete('1.0', tk.END); self.obs_var.insert('1.0', obs or "")
            self.btn_atualizar.config(state="normal"); self.btn_excluir.config(state="normal")

    def _atualizar_balanco(self):
        item_id = self.id_var.get();
        if not item_id: return
        ano = self.ano_var.get(); mes = list(calendar.month_name).index(self.mes_var.get())
        entradas = self.entradas_var.get(); saidas = self.saidas_var.get(); saldo = entradas - saidas
        obs = self.obs_var.get("1.0", tk.END).strip()
        query = "UPDATE balanco_mensal SET ano=?, mes=?, total_entradas=?, total_saidas=?, saldo_mes=?, observacoes=? WHERE id=?"
        self._executar_query(query, (ano, mes, entradas, saidas, saldo, obs, item_id), commit=True)
        messagebox.showinfo("Sucesso", "Registro atualizado!", parent=self)
        self._limpar_campos(); self._carregar_dados_treeview(); self._atualizar_grafico()

    def _excluir_balanco(self):
        item_id = self.id_var.get()
        if not item_id: return
        if messagebox.askyesno("Confirmar", "Deseja excluir este registro de balanço? Isso NÃO excluirá os eventos avulsos.", parent=self):
            self._executar_query("DELETE FROM balanco_mensal WHERE id=?", (item_id,), commit=True)
            self._limpar_campos(); self._carregar_dados_treeview(); self._atualizar_grafico()

    def _calcular_entradas_automaticamente(self):
        ano = self.ano_var.get(); mes = list(calendar.month_name).index(self.mes_var.get())
        mes_ano_str = f"{ano}-{mes:02d}"
        receitas = self._executar_query("SELECT SUM(valor) FROM receitas WHERE strftime('%Y-%m', data_recebimento) = ?", (mes_ano_str,), fetch='one', db_path='financas_receitas.db') or [0]
        self.entradas_var.set(round(receitas[0] or 0, 2))
        messagebox.showinfo("Cálculo", f"Total de Entradas para {self.mes_var.get()}/{ano} foi calculado.", parent=self)

    def _abrir_seletor_saidas(self):
        ano = self.ano_var.get(); mes = list(calendar.month_name).index(self.mes_var.get())
        mes_ano_str = f"{ano}-{mes:02d}"
        despesas = self._executar_query("SELECT strftime('%d/%m/%Y', data_pagamento), descricao, valor, meio_pagamento FROM despesas WHERE strftime('%Y-%m', data_pagamento) = ?", (mes_ano_str,), fetch='all', db_path='financas.db') or []
        win = tk.Toplevel(self); win.title(f"Selecione as Saídas de Caixa de {self.mes_var.get()}/{ano}")
        win.geometry("700x500"); win.transient(self); win.grab_set()
        frame = ttk.Frame(win, padding=10); frame.pack(fill=tk.BOTH, expand=True)
        tree_despesas = self._criar_treeview_detalhes(frame, ('data', 'descricao', 'valor', 'meio_pgto'))
        checkbox_vars = []
        for i, d in enumerate(despesas):
            var = tk.BooleanVar(value=False); checkbox_vars.append(var)
            formatted_row = list(d); formatted_row[2] = locale.currency(d[2], grouping=True)
            tree_despesas.insert('', 'end', iid=i, values=formatted_row, tags=('unchecked',))
        def on_click(event):
            item_id = tree_despesas.identify_row(event.y)
            if item_id: index = int(item_id); checkbox_vars[index].set(not checkbox_vars[index].get()); tree_despesas.item(item_id, tags=('checked' if checkbox_vars[index].get() else 'unchecked',))
        tree_despesas.tag_configure('checked', background='lightyellow'); tree_despesas.bind('<Button-1>', on_click)
        def aplicar_soma():
            soma = sum(despesas[i][2] for i, var in enumerate(checkbox_vars) if var.get())
            self.saidas_var.set(round(soma, 2))
            messagebox.showinfo("Soma Aplicada", f"Valor de {locale.currency(soma, grouping=True)} definido como Total de Saídas.", parent=win)
            win.destroy()
        btn_frame = ttk.Frame(frame); btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10,0))
        ttk.Button(btn_frame, text="Usar Soma dos Selecionados", command=aplicar_soma).pack(pady=5)

    def _mostrar_detalhes_mes(self, event=None):
        selected_item = self.tree.focus()
        if not selected_item: return
        mes_ano_str = self.tree.item(selected_item, 'values')[1]
        mes, ano = map(int, mes_ano_str.split('/'))
        yyyymm_str = f"{ano}-{mes:02d}"
        win = tk.Toplevel(self); win.title(f"Demonstrativo de {mes_ano_str}"); win.geometry("800x600"); win.transient(self); win.grab_set()
        notebook = ttk.Notebook(win, padding=10); notebook.pack(fill=tk.BOTH, expand=True)
        frame_entradas = ttk.Frame(notebook); notebook.add(frame_entradas, text="Entradas (Receitas)")
        tree_entradas = self._criar_treeview_detalhes(frame_entradas, ('data', 'descricao', 'valor'))
        receitas = self._executar_query("SELECT strftime('%d/%m/%Y', data_recebimento), descricao, valor FROM receitas WHERE strftime('%Y-%m', data_recebimento) = ?", (yyyymm_str,), fetch='all', db_path='financas_receitas.db') or []
        total_entradas = self._preencher_treeview_detalhes(tree_entradas, receitas)
        ttk.Label(frame_entradas, text=f"Total: {locale.currency(total_entradas, grouping=True)}", font=('Arial', 10, 'bold')).pack(pady=5, anchor='e')
        frame_saidas = ttk.Frame(notebook); notebook.add(frame_saidas, text="Saídas (Despesas)")
        tree_saidas = self._criar_treeview_detalhes(frame_saidas, ('data', 'descricao', 'valor', 'meio_pgto'))
        despesas = self._executar_query("SELECT strftime('%d/%m/%Y', data_pagamento), descricao, valor, meio_pagamento FROM despesas WHERE strftime('%Y-%m', data_pagamento) = ?", (yyyymm_str,), fetch='all', db_path='financas.db') or []
        total_saidas = self._preencher_treeview_detalhes(tree_saidas, despesas)
        ttk.Label(frame_saidas, text=f"Total: {locale.currency(total_saidas, grouping=True)}", font=('Arial', 10, 'bold')).pack(pady=5, anchor='e')
        frame_avulsos = ttk.Frame(notebook); notebook.add(frame_avulsos, text="Saídas (Eventos Avulsos)")
        tree_avulsos = self._criar_treeview_detalhes(frame_avulsos, ('data', 'descricao', 'valor'))
        avulsos = self._executar_query("SELECT strftime('%d/%m/%Y', data), descricao, valor FROM eventos_caixa_avulsos WHERE strftime('%Y-%m', data) = ?", (yyyymm_str,), fetch='all') or []
        total_avulsos = self._preencher_treeview_detalhes(tree_avulsos, avulsos)
        ttk.Label(frame_avulsos, text=f"Total: {locale.currency(total_avulsos, grouping=True)}", font=('Arial', 10, 'bold')).pack(pady=5, anchor='e')

    def _criar_treeview_detalhes(self, parent_frame, columns):
        frame = ttk.Frame(parent_frame); frame.pack(fill=tk.BOTH, expand=True, pady=5)
        tree = ttk.Treeview(frame, columns=columns, show='headings')
        for col in columns: tree.heading(col, text=col.replace('_', ' ').title())
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview); scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scrollbar.set)
        return tree

    def _preencher_treeview_detalhes(self, tree, data):
        total = 0
        for row in data: total += row[2]; formatted_row = list(row); formatted_row[2] = locale.currency(row[2], grouping=True); tree.insert('', 'end', values=formatted_row)
        return total

    def _atualizar_grafico(self):
        self.figura.clear(); self.ax = self.figura.add_subplot(111)
        dados = self._executar_query("SELECT ano, mes, total_entradas, total_saidas, saldo_mes FROM balanco_mensal ORDER BY ano, mes", fetch='all')
        if not dados: self.ax.text(0.5, 0.5, "Sem dados para exibir", ha='center', va='center'); self.canvas.draw(); return
        labels = [f"{mes:02d}/{ano}" for ano, mes, _, _, _ in dados]; entradas = [e for _, _, e, _, _ in dados]; saidas = [s for _, _, _, s, _ in dados]; saldos = [s for _, _, _, _, s in dados]
        x = np.arange(len(labels)); bar_width = 0.35; ax2 = self.ax.twinx()
        bar1 = self.ax.bar(x - bar_width/2, entradas, bar_width, label='Entradas', color='mediumseagreen')
        bar2 = self.ax.bar(x + bar_width/2, saidas, bar_width, label='Saídas', color='coral')
        self.ax.bar_label(bar1, padding=3, fmt=lambda v: locale.currency(v, symbol=False, grouping=True), fontsize=8)
        self.ax.bar_label(bar2, padding=3, fmt=lambda v: locale.currency(v, symbol=False, grouping=True), fontsize=8)
        ax2.plot(x, saldos, label='Saldo do Mês', color='royalblue', linestyle='--', marker='o')
        self.ax.set_ylabel('Valor Entradas/Saídas (R$)'); ax2.set_ylabel('Valor Saldo (R$)')
        self.ax.set_title('Evolução do Fluxo de Caixa Mensal'); self.ax.set_xticks(x); self.ax.set_xticklabels(labels, rotation=45, ha='right')
        handles1, labels1 = self.ax.get_legend_handles_labels(); handles2, labels2 = ax2.get_legend_handles_labels()
        self.ax.legend(handles1 + handles2, labels1 + labels2, loc='upper left'); self.ax.grid(axis='y', linestyle='--', alpha=0.7)
        self.figura.tight_layout(); self.canvas.draw()

def iniciar_relatorio_balanco(parent_window):
    RelatorioBalanco(parent_window)