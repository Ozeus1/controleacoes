import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import calendar
import locale
import pandas as pd
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
        self.geometry("1220x900")

        self.db_path = 'fluxo_caixa.db'
        self.db_receitas_path = 'financas_receitas.db'
        self.db_despesas_path = 'financas.db'

        self._criar_banco()
       # self._verificar_e_migrar_tabelas() # Adiciona colunas user_id se não existirem

        # Variáveis de controle
        self.id_var = tk.StringVar()
        self.ano_var = tk.IntVar(value=datetime.now().year)
        self.mes_var = tk.StringVar(value=calendar.month_name[datetime.now().month])
        self.entradas_var = tk.DoubleVar()
        self.saidas_var = tk.DoubleVar()
        self.saldo_var = tk.StringVar()
        self.obs_var = None

        self.evento_id_var = tk.StringVar()
        self.evento_descricao_var = tk.StringVar()
        self.evento_valor_var = tk.DoubleVar()
        self.evento_data_entry = None

        # --- NOVO: Variáveis para o filtro do gráfico ---
        data_fim_default = date.today()
        data_inicio_default = data_fim_default - relativedelta(months=11)
        self.ano_inicio_var = tk.IntVar(value=data_inicio_default.year)
        self.mes_inicio_var = tk.StringVar(value=calendar.month_name[data_inicio_default.month])
        self.ano_fim_var = tk.IntVar(value=data_fim_default.year)
        self.mes_fim_var = tk.StringVar(value=calendar.month_name[data_fim_default.month])

        self._criar_widgets()
        
        self._recalcular_fluxo_caixa_geral()
        
        self._carregar_dados_treeview()
        self._carregar_eventos_treeview()
        self._atualizar_grafico()
        

    def _criar_banco(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Tabelas originais (sem user_id, para compatibilidade inicial)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS balanco_mensal (
                    id INTEGER PRIMARY KEY, ano INTEGER NOT NULL, mes INTEGER NOT NULL,
                    total_entradas REAL DEFAULT 0, total_saidas REAL DEFAULT 0,
                    saldo_mes REAL DEFAULT 0, observacoes TEXT, UNIQUE(ano, mes)
                )""")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS eventos_caixa_avulsos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, data DATE NOT NULL,
                    descricao TEXT NOT NULL, valor REAL NOT NULL
                )""")
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Erro ao criar tabelas: {e}", parent=self)

    def _verificar_e_migrar_tabelas(self):

        return
   
    def check_receitas_user_id(self):
        """Verifica se a tabela receitas tem a coluna user_id."""
        return False

    def _criar_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        tab_balanco = ttk.Frame(notebook, padding=5)
        notebook.add(tab_balanco, text="Balanço Mensal Consolidado")

        # --- Frame do Formulário (Esquerda) ---
        frame_form = ttk.LabelFrame(tab_balanco, text="Formulário de Fluxo de Caixa Mensal", padding="10")
        frame_form.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), anchor='n')
        
        ttk.Label(frame_form, text="ID:").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Entry(frame_form, textvariable=self.id_var, state='readonly', width=10).grid(row=0, column=1, sticky="w", columnspan=3, pady=3)
        ttk.Label(frame_form, text="Ano:").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Spinbox(frame_form, from_=2020, to=2100, textvariable=self.ano_var, width=8).grid(row=1, column=1, sticky="w", columnspan=3, pady=3)
        ttk.Label(frame_form, text="Mês:").grid(row=2, column=0, sticky="w", pady=3)
        meses_nomes = [calendar.month_name[i] for i in range(1, 13)]; meses_nomes.insert(0,"")
        ttk.Combobox(frame_form, textvariable=self.mes_var, values=meses_nomes, state='readonly', width=15).grid(row=2, column=1, sticky="w", columnspan=3, pady=3)
        ttk.Button(frame_form, text="Calcular Entradas (Auto)", command=self._calcular_entradas_automaticamente).grid(row=3, column=0, columnspan=2, pady=(10, 5), sticky="ew")
        ttk.Button(frame_form, text="Calcular Saídas (Auto)", command=self._calcular_saidas_automaticamente).grid(row=3, column=2, columnspan=2, pady=(10, 5), sticky="ew")
        ttk.Label(frame_form, text="Total de Entradas (R$):").grid(row=4, column=0, sticky="w", pady=3, columnspan=2)
        ttk.Entry(frame_form, textvariable=self.entradas_var, width=22).grid(row=4, column=2, sticky="w", columnspan=2, pady=3)
        ttk.Label(frame_form, text="Total de Saídas (R$):").grid(row=5, column=0, sticky="w", pady=3, columnspan=2)
        ttk.Entry(frame_form, textvariable=self.saidas_var, width=22).grid(row=5, column=2, sticky="w", columnspan=2, pady=3)
        ttk.Label(frame_form, text="Saldo do Mês (R$):").grid(row=6, column=0, sticky="w", pady=3, columnspan=2)
        ttk.Entry(frame_form, textvariable=self.saldo_var, state='readonly', width=22).grid(row=6, column=2, sticky="w", columnspan=2, pady=3)
        ttk.Label(frame_form, text="Observações:").grid(row=7, column=0, sticky="nw", pady=3, columnspan=2)
        self.obs_var = tk.Text(frame_form, height=5, width=30)
        self.obs_var.grid(row=7, column=2, sticky="w", columnspan=2, pady=3)
        frame_botoes = ttk.Frame(frame_form)
        frame_botoes.grid(row=8, column=0, columnspan=4, pady=15)
        ttk.Button(frame_botoes, text="Salvar Manual", command=self._salvar_balanco).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botoes, text="Limpar", command=self._limpar_campos).pack(side=tk.LEFT, padx=5)
        self.btn_excluir = ttk.Button(frame_botoes, text="Excluir", command=self._excluir_balanco, state="disabled")
        self.btn_excluir.pack(side=tk.LEFT, padx=5)
        self.btn_export_excel = ttk.Button(frame_form, text="Exportar para Excel", command=self._exportar_para_excel, state="disabled")
        self.btn_export_excel.grid(row=9, column=0, columnspan=4, pady=10, sticky="ew")

        # --- Frame de Dados (Direita) ---
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
        
        # --- NOVO: Frame para Filtros do Gráfico ---
        frame_filtro_grafico = ttk.LabelFrame(frame_dados, text="Filtros do Gráfico", padding="5")
        frame_filtro_grafico.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(frame_filtro_grafico, text="De:").grid(row=0, column=0, padx=5, pady=5)
        ttk.Combobox(frame_filtro_grafico, textvariable=self.mes_inicio_var, values=meses_nomes[1:], state='readonly', width=12).grid(row=0, column=1, padx=2, pady=5)
        ttk.Spinbox(frame_filtro_grafico, from_=2020, to=2100, textvariable=self.ano_inicio_var, width=6).grid(row=0, column=2, padx=5, pady=5)
        ttk.Label(frame_filtro_grafico, text="Até:").grid(row=0, column=3, padx=5, pady=5)
        ttk.Combobox(frame_filtro_grafico, textvariable=self.mes_fim_var, values=meses_nomes[1:], state='readonly', width=12).grid(row=0, column=4, padx=2, pady=5)
        ttk.Spinbox(frame_filtro_grafico, from_=2020, to=2100, textvariable=self.ano_fim_var, width=6).grid(row=0, column=5, padx=5, pady=5)
        ttk.Button(frame_filtro_grafico, text="Aplicar Filtro", command=self._atualizar_grafico).grid(row=0, column=6, padx=10, pady=5)

        # --- Frame do Gráfico ---
        frame_grafico = ttk.LabelFrame(frame_dados, text="Evolução do Fluxo de Caixa", padding="5")
        frame_grafico.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        self.figura = plt.Figure(figsize=(7, 3), dpi=100)
        self.ax = self.figura.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figura, master=frame_grafico)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # --- Demais abas e formulários ---
        tab_eventos_frame = ttk.Frame(notebook)
        notebook.add(tab_eventos_frame, text="Lançamentos de Caixa Avulsos")
        self.tree_eventos = ttk.Treeview(tab_eventos_frame, columns=('id', 'data', 'descricao', 'valor'), show='headings')
        self.tree_eventos.heading('id', text='ID'); self.tree_eventos.column('id', width=50, anchor='center')
        self.tree_eventos.heading('data', text='Data'); self.tree_eventos.column('data', width=100, anchor='center')
        self.tree_eventos.heading('descricao', text='Descrição'); self.tree_eventos.column('descricao', width=400)
        self.tree_eventos.heading('valor', text='Valor'); self.tree_eventos.column('valor', width=150, anchor='e')
        self.tree_eventos.bind("<ButtonRelease-1>", self._selecionar_evento_avulso)
        self.tree_eventos.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
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
            if "no such table" not in str(e):
                messagebox.showerror("Erro de BD", f"Erro ao acessar '{db_path}':\n{e}", parent=self)
            return None

    def _recalcular_fluxo_caixa_geral(self):
        meses_a_processar = set()
        
        # Receitas (sem filtro por usuário)
        q_receitas = """
            SELECT DISTINCT
                strftime('%Y', data_recebimento),
                strftime('%m', data_recebimento)
            FROM receitas
        """
        receitas_meses = self._executar_query(
            q_receitas,
            db_path=self.db_receitas_path,
            fetch='all'
        ) or []

        # Despesas (v_despesas_compat) – sem user_id
        q_despesas = """
            SELECT DISTINCT
                strftime('%Y', data_pagamento),
                strftime('%m', data_pagamento)
            FROM v_despesas_compat
        """
        despesas_meses = self._executar_query(
            q_despesas,
            db_path=self.db_despesas_path,
            fetch='all'
        ) or []

        # Avulsos – sem user_id
        q_avulsos = """
            SELECT DISTINCT
                strftime('%Y', data),
                strftime('%m', data)
            FROM eventos_caixa_avulsos
        """
        avulsos_meses = self._executar_query(
            q_avulsos,
            db_path=self.db_path,
            fetch='all'
        ) or []
        
        for ano, mes in receitas_meses:
            meses_a_processar.add((int(ano), int(mes)))
        for ano, mes in despesas_meses:
            meses_a_processar.add((int(ano), int(mes)))
        for ano, mes in avulsos_meses:
            meses_a_processar.add((int(ano), int(mes)))
        
        # Limpa todo o balanço (agora é single user)
        self._executar_query(
            "DELETE FROM balanco_mensal",
            commit=True
        )
        
        for ano, mes in sorted(list(meses_a_processar)):
            self._recalcular_e_salvar_balanco_para_mes(ano, mes)

        messagebox.showinfo(
            "Sincronização",
            "Fluxo de caixa recalculado e sincronizado com sucesso!",
            parent=self
        )

    def _recalcular_e_salvar_balanco_para_mes(self, ano, mes):
        mes_ano_str = f"{ano}-{mes:02d}"
        
        # Receitas (sem user_id)
        total_entradas_res = self._executar_query(
            "SELECT SUM(valor) FROM receitas "
            "WHERE strftime('%Y-%m', data_recebimento) = ?",
            (mes_ano_str,),
            fetch='one',
            db_path=self.db_receitas_path
        )
        total_entradas = (total_entradas_res[0] or 0) if total_entradas_res else 0
        
        # Despesas (somente meios que afetam caixa)
        meios_pagamento_caixa = ('Boleto', 'Dinheiro', 'PIX/Transferência', 'Débito em Conta')
        query_despesas = (
            "SELECT SUM(valor) FROM v_despesas_compat "
            "WHERE strftime('%Y-%m', data_pagamento) = ? "
            f"AND meio_pagamento IN ({','.join(['?']*len(meios_pagamento_caixa))})"
        )
        params = (mes_ano_str,) + meios_pagamento_caixa
        total_saidas_despesas_res = self._executar_query(
            query_despesas,
            params,
            fetch='one',
            db_path=self.db_despesas_path
        )
        total_saidas_despesas = (total_saidas_despesas_res[0] or 0) if total_saidas_despesas_res else 0
        
        # Avulsos (sem user_id)
        total_saidas_avulsos_res = self._executar_query(
            "SELECT SUM(valor) FROM eventos_caixa_avulsos "
            "WHERE strftime('%Y-%m', data) = ?",
            (mes_ano_str,),
            fetch='one',
            db_path=self.db_path
        )
        total_saidas_avulsos = (total_saidas_avulsos_res[0] or 0) if total_saidas_avulsos_res else 0
        
        total_saidas = total_saidas_despesas + total_saidas_avulsos
        saldo_mes = total_entradas - total_saidas
        
        # Como agora a tabela não tem mais user_id, a chave é só (ano, mes)
        self._executar_query(
            "DELETE FROM balanco_mensal WHERE ano = ? AND mes = ?",
            (ano, mes),
            commit=True
        )
        
        query_insert = (
            "INSERT INTO balanco_mensal "
            "(ano, mes, total_entradas, total_saidas, saldo_mes) "
            "VALUES (?, ?, ?, ?, ?)"
        )
        self._executar_query(
            query_insert,
            (ano, mes, total_entradas, total_saidas, saldo_mes),
            commit=True
        )

          
    def registrar_evento_avulso(self):
        data = self.evento_data_entry.get_date()
        descricao = self.evento_descricao_var.get().strip()
        valor = self.evento_valor_var.get()

        if not descricao or valor <= 0:
            messagebox.showerror(
                "Erro",
                "Descrição e Valor (maior que zero) são obrigatórios.",
                parent=self
            )
            return

        # sem coluna user_id
        query = "INSERT INTO eventos_caixa_avulsos (data, descricao, valor) VALUES (?, ?, ?)"
        self._executar_query(
            query,
            (data.strftime('%Y-%m-%d'), descricao, valor),
            commit=True
        )

        self._recalcular_e_salvar_balanco_para_mes(data.year, data.month)
        messagebox.showinfo("Sucesso", "Evento registrado e balanço mensal atualizado!", parent=self)
        self._limpar_formulario_evento()
        self._carregar_eventos_treeview()
        self._carregar_dados_treeview()
        self._atualizar_grafico()


    def _atualizar_evento_avulso(self):
        item_id = self.evento_id_var.get()
        if not item_id:
            return

        # sem filtro por user_id
        res = self._executar_query(
            "SELECT data FROM eventos_caixa_avulsos WHERE id = ?",
            (item_id,),
            fetch='one'
        )
        if not res:
            return

        data_antiga_obj = datetime.strptime(res[0], '%Y-%m-%d')
        data_nova = self.evento_data_entry.get_date()
        descricao = self.evento_descricao_var.get().strip()
        valor_novo = self.evento_valor_var.get()

        if not descricao or valor_novo <= 0:
            return

        query = "UPDATE eventos_caixa_avulsos SET data = ?, descricao = ?, valor = ? WHERE id = ?"
        self._executar_query(
            query,
            (data_nova.strftime('%Y-%m-%d'), descricao, valor_novo, item_id),
            commit=True
        )

        self._recalcular_e_salvar_balanco_para_mes(data_antiga_obj.year, data_antiga_obj.month)
        if (data_antiga_obj.year, data_antiga_obj.month) != (data_nova.year, data_nova.month):
            self._recalcular_e_salvar_balanco_para_mes(data_nova.year, data_nova.month)

        messagebox.showinfo("Sucesso", "Evento atualizado e balanço mensal recalculado!", parent=self)
        self._limpar_formulario_evento()
        self._carregar_eventos_treeview()
        self._carregar_dados_treeview()
        self._atualizar_grafico()


    def _excluir_evento_avulso(self):
        item_id = self.evento_id_var.get()
        if not item_id:
            return

        if messagebox.askyesno("Confirmar", "Deseja realmente excluir este evento?", parent=self):
            # sem user_id
            res = self._executar_query(
                "SELECT data FROM eventos_caixa_avulsos WHERE id = ?",
                (item_id,),
                fetch='one'
            )
            if not res:
                return

            data_obj = datetime.strptime(res[0], '%Y-%m-%d')

            self._executar_query(
                "DELETE FROM eventos_caixa_avulsos WHERE id = ?",
                (item_id,),
                commit=True
            )

            self._recalcular_e_salvar_balanco_para_mes(data_obj.year, data_obj.month)
            messagebox.showinfo("Sucesso", "Evento excluído e balanço mensal atualizado!", parent=self)
            self._limpar_formulario_evento()
            self._carregar_eventos_treeview()
            self._carregar_dados_treeview()
            self._atualizar_grafico()

    def _carregar_eventos_treeview(self):
        # Limpa a lista
        for i in self.tree_eventos.get_children():
            self.tree_eventos.delete(i)

        # Agora sem filtro por user_id
        eventos = self._executar_query(
            "SELECT id, strftime('%d/%m/%Y', data), descricao, valor "
            "FROM eventos_caixa_avulsos "
            "ORDER BY data DESC, id DESC",
            fetch='all'
        )

        if eventos:
            for id_evento, data, desc, valor in eventos:
                self.tree_eventos.insert(
                    '',
                    'end',
                    values=(id_evento, data, desc, locale.currency(valor, grouping=True))
                )


    def _limpar_formulario_evento(self):
        self.evento_id_var.set("")
        self.evento_descricao_var.set("")
        self.evento_valor_var.set(0.0)
        self.evento_data_entry.set_date(datetime.now())
        self.btn_registrar_evento.config(state="normal")
        self.btn_atualizar_evento.config(state="disabled")
        self.btn_excluir_evento.config(state="disabled")
        if self.tree_eventos.selection():
            self.tree_eventos.selection_remove(self.tree_eventos.selection())


    def _selecionar_evento_avulso(self, event=None):
        selected_item = self.tree_eventos.focus()
        if not selected_item:
            return

        item_values = self.tree_eventos.item(selected_item, 'values')
        item_id = item_values[0]

        # Sem user_id
        dados = self._executar_query(
            "SELECT data, descricao, valor FROM eventos_caixa_avulsos WHERE id = ?",
            (item_id,),
            fetch='one'
        )

        if dados:
            data_str, desc, valor = dados
            data_obj = datetime.strptime(data_str, '%Y-%m-%d')
            self.evento_id_var.set(item_id)
            self.evento_data_entry.set_date(data_obj)
            self.evento_descricao_var.set(desc)
            self.evento_valor_var.set(valor)
            self.btn_registrar_evento.config(state="disabled")
            self.btn_atualizar_evento.config(state="normal")
            self.btn_excluir_evento.config(state="normal")


    def _carregar_dados_treeview(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        # Sem filtro por user_id
        dados = self._executar_query(
            "SELECT id, ano, mes, total_entradas, total_saidas, saldo_mes "
            "FROM balanco_mensal "
            "ORDER BY ano DESC, mes DESC",
            fetch='all'
        )

        if dados:
            for row in dados:
                id_reg, ano, mes, entradas, saidas, saldo = row
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        id_reg,
                        f"{mes:02d}/{ano}",
                        locale.currency(entradas, grouping=True),
                        locale.currency(saidas, grouping=True),
                        locale.currency(saldo, grouping=True)
                    )
                )


    def _limpar_campos(self):
        self.id_var.set("")
        self.ano_var.set(datetime.now().year)
        self.mes_var.set(calendar.month_name[datetime.now().month])
        self.entradas_var.set(0.0)
        self.saidas_var.set(0.0)
        self.saldo_var.set(locale.currency(0.0, grouping=True))
        if self.obs_var:
            self.obs_var.delete('1.0', tk.END)
        self.btn_excluir.config(state="disabled")
        self.btn_export_excel.config(state="disabled")
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())


    def _salvar_balanco(self):
        item_id = self.id_var.get()
        ano = self.ano_var.get()

        try:
            mes = list(calendar.month_name).index(self.mes_var.get())
            if mes == 0:
                messagebox.showerror("Erro", "Por favor, selecione um mês.", parent=self)
                return
        except ValueError:
            messagebox.showerror("Erro", "Mês inválido.", parent=self)
            return

        entradas = self.entradas_var.get()
        saidas = self.saidas_var.get()
        saldo = entradas - saidas
        obs = self.obs_var.get("1.0", tk.END).strip()

        if not item_id:
            # Agora a duplicidade é só por (ano, mes)
            existe = self._executar_query(
                "SELECT id FROM balanco_mensal WHERE ano = ? AND mes = ?",
                (ano, mes),
                fetch='one'
            )
            if existe:
                messagebox.showerror(
                    "Erro de Duplicidade",
                    f"Já existe um registro para {mes:02d}/{ano}. "
                    "Use a função de recálculo ou edite o registro existente.",
                    parent=self
                )
                return

            query = (
                "INSERT INTO balanco_mensal "
                "(ano, mes, total_entradas, total_saidas, saldo_mes, observacoes) "
                "VALUES (?, ?, ?, ?, ?, ?)"
            )
            params = (ano, mes, entradas, saidas, saldo, obs)
            msg = "Balanço salvo manualmente!"
        else:
            query = (
                "UPDATE balanco_mensal SET ano = ?, mes = ?, total_entradas = ?, "
                "total_saidas = ?, saldo_mes = ?, observacoes = ? "
                "WHERE id = ?"
            )
            params = (ano, mes, entradas, saidas, saldo, obs, item_id)
            msg = "Registro atualizado manualmente!"

        try:
            self._executar_query(query, params, commit=True)
            messagebox.showinfo("Sucesso", msg, parent=self)
            self._limpar_campos()
            self._carregar_dados_treeview()
            self._atualizar_grafico()
        except sqlite3.IntegrityError:
            messagebox.showerror(
                "Erro de Duplicidade",
                f"Já existe um registro para {mes:02d}/{ano}.",
                parent=self
            )


    def _selecionar_item_treeview(self, event=None):
        selected_item = self.tree.focus()
        if not selected_item:
            self.btn_export_excel.config(state="disabled")
            return

        item_id = self.tree.item(selected_item, 'values')[0]

        # Sem user_id
        dados = self._executar_query(
            "SELECT * FROM balanco_mensal WHERE id = ?",
            (item_id,),
            fetch='one'
        )

        if dados:
            # Estrutura: id, ano, mes, total_entradas, total_saidas, saldo_mes, observacoes
            id_reg = dados[0]
            ano = dados[1]
            mes = dados[2]
            entradas = dados[3]
            saidas = dados[4]
            saldo = dados[5]
            obs = dados[6]

            self.id_var.set(id_reg)
            self.ano_var.set(ano)
            self.mes_var.set(calendar.month_name[mes])
            self.entradas_var.set(entradas)
            self.saidas_var.set(saidas)
            self.saldo_var.set(locale.currency(saldo, grouping=True))
            self.obs_var.delete('1.0', tk.END)
            self.obs_var.insert('1.0', obs or "")
            self.btn_excluir.config(state="normal")
            self.btn_export_excel.config(state="normal")


    def _excluir_balanco(self):
        item_id = self.id_var.get()
        if not item_id:
            return

        if messagebox.askyesno(
            "Confirmar",
            "Deseja excluir este registro de balanço? Isso NÃO excluirá os lançamentos originais.",
            parent=self
        ):
            # Sem user_id
            self._executar_query(
                "DELETE FROM balanco_mensal WHERE id = ?",
                (item_id,),
                commit=True
            )
            self._limpar_campos()
            self._carregar_dados_treeview()
            self._atualizar_grafico()


    def _calcular_entradas_automaticamente(self):
        try:
            ano = self.ano_var.get()
            mes = list(calendar.month_name).index(self.mes_var.get())
        except ValueError:
            messagebox.showerror("Erro", "Mês inválido selecionado.", parent=self)
            return

        mes_ano_str = f"{ano}-{mes:02d}"

        # Sem user_id
        receitas = self._executar_query(
            "SELECT SUM(valor) FROM receitas "
            "WHERE strftime('%Y-%m', data_recebimento) = ?",
            (mes_ano_str,),
            fetch='one',
            db_path=self.db_receitas_path
        ) or (0,)

        self.entradas_var.set(round(receitas[0] or 0, 2))
        messagebox.showinfo(
            "Cálculo",
            f"Total de Entradas para {self.mes_var.get()}/{ano} foi calculado e preenchido.",
            parent=self
        )

    def _calcular_saidas_automaticamente(self):
        try:
            ano = self.ano_var.get()
            mes = list(calendar.month_name).index(self.mes_var.get())
        except ValueError:
            messagebox.showerror("Erro", "Mês inválido selecionado.", parent=self)
            return

        mes_ano_str = f"{ano}-{mes:02d}"

        meios_pagamento_caixa = ('Boleto', 'Dinheiro', 'PIX/Transferência', 'Débito em Conta')

        # DESPESAS (sem user_id)
        query_despesas = (
            "SELECT SUM(valor) FROM v_despesas_compat "
            "WHERE strftime('%Y-%m', data_pagamento) = ? "
            f"AND meio_pagamento IN ({','.join(['?']*len(meios_pagamento_caixa))})"
        )
        params = (mes_ano_str,) + meios_pagamento_caixa
        total_saidas_despesas_res = self._executar_query(
            query_despesas,
            params,
            fetch='one',
            db_path=self.db_despesas_path
        )
        total_saidas_despesas = (total_saidas_despesas_res[0] or 0) if total_saidas_despesas_res else 0

        # AVULSOS (sem user_id)
        total_saidas_avulsos_res = self._executar_query(
            "SELECT SUM(valor) FROM eventos_caixa_avulsos "
            "WHERE strftime('%Y-%m', data) = ?",
            (mes_ano_str,),
            fetch='one'
        )
        total_saidas_avulsos = (total_saidas_avulsos_res[0] or 0) if total_saidas_avulsos_res else 0

        self.saidas_var.set(round(total_saidas_despesas + total_saidas_avulsos, 2))
        messagebox.showinfo(
            "Cálculo",
            f"Total de Saídas para {self.mes_var.get()}/{ano} foi calculado e preenchido.",
            parent=self
        )

   
    def _exportar_para_excel(self):
        """Exporta os detalhes do mês selecionado para um arquivo Excel, filtrando as saídas de caixa."""
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Aviso", "Nenhum mês selecionado para exportar.", parent=self)
            return

        mes_ano_str = self.tree.item(selected_item, 'values')[1]
        mes, ano = map(int, mes_ano_str.split('/'))
        yyyymm_str = f"{ano}-{mes:02d}"

        caminho_arquivo = filedialog.asksaveasfilename(
            initialfile=f"Relatorio_Caixa_{ano}_{mes:02d}.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Arquivos Excel", "*.xlsx"), ("Todos os arquivos", "*.*")]
        )
        if not caminho_arquivo:
            return

        try:
            # RECEITAS
            if self.check_receitas_user_id():
                # hoje, na prática, nunca cai aqui, mas deixei por compatibilidade
                receitas = self._executar_query(
                    "SELECT data_recebimento, descricao, valor "
                    "FROM receitas "
                    "WHERE strftime('%Y-%m', data_recebimento) = ?",
                    (yyyymm_str,),
                    fetch='all',
                    db_path=self.db_receitas_path
                ) or []
            else:
                receitas = self._executar_query(
                    "SELECT data_recebimento, descricao, valor "
                    "FROM receitas "
                    "WHERE strftime('%Y-%m', data_recebimento) = ?",
                    (yyyymm_str,),
                    fetch='all',
                    db_path=self.db_receitas_path
                ) or []

            # DESPESAS (somente saídas de caixa) – sem user_id
            meios_pagamento_caixa = ('Boleto', 'Dinheiro', 'PIX/Transferência', 'Débito em Conta')
            query_despesas = (
                "SELECT data_pagamento, descricao, valor, meio_pagamento "
                "FROM v_despesas_compat "
                "WHERE strftime('%Y-%m', data_pagamento) = ? "
                f"AND meio_pagamento IN ({','.join(['?']*len(meios_pagamento_caixa))})"
            )
            params_despesas = (yyyymm_str,) + meios_pagamento_caixa
            despesas_caixa = self._executar_query(
                query_despesas,
                params_despesas,
                fetch='all',
                db_path=self.db_despesas_path
            ) or []

            # AVULSOS – sem user_id
            avulsos = self._executar_query(
                "SELECT data, descricao, valor "
                "FROM eventos_caixa_avulsos "
                "WHERE strftime('%Y-%m', data) = ?",
                (yyyymm_str,),
                fetch='all'
            ) or []

            df_receitas = pd.DataFrame(receitas, columns=['Data', 'Descrição', 'Valor'])
            df_despesas_caixa = pd.DataFrame(despesas_caixa, columns=['Data', 'Descrição', 'Valor', 'Meio de Pagamento'])
            df_avulsos = pd.DataFrame(avulsos, columns=['Data', 'Descrição', 'Valor'])

            with pd.ExcelWriter(caminho_arquivo, engine='openpyxl') as writer:
                df_receitas.to_excel(writer, sheet_name='Entradas (Receitas)', index=False)
                df_despesas_caixa.to_excel(writer, sheet_name='Saídas (Despesas de Caixa)', index=False)
                df_avulsos.to_excel(writer, sheet_name='Saídas (Avulsos)', index=False)

            messagebox.showinfo("Sucesso", f"Relatório exportado para:\n{caminho_arquivo}", parent=self)
        except Exception as e:
            messagebox.showerror("Erro na Exportação", f"Ocorreu um erro ao gerar o arquivo Excel:\n{e}", parent=self)

    def _mostrar_detalhes_mes(self, event=None):
        selected_item = self.tree.focus()
        if not selected_item:
            return

        mes_ano_str = self.tree.item(selected_item, 'values')[1]
        mes, ano = map(int, mes_ano_str.split('/'))
        yyyymm_str = f"{ano}-{mes:02d}"

        win = tk.Toplevel(self)
        win.title(f"Demonstrativo de {mes_ano_str}")
        win.geometry("800x700")
        win.transient(self)
        win.grab_set()

        notebook = ttk.Notebook(win, padding=10)
        notebook.pack(fill=tk.BOTH, expand=True)

        # --- Entradas (Receitas) ---
        frame_entradas = ttk.Frame(notebook)
        notebook.add(frame_entradas, text="Entradas (Receitas)")
        tree_entradas = self._criar_treeview_detalhes(frame_entradas, ('data', 'descricao', 'valor'))

        if self.check_receitas_user_id():
            receitas = self._executar_query(
                "SELECT strftime('%d/%m/%Y', data_recebimento), descricao, valor "
                "FROM receitas "
                "WHERE strftime('%Y-%m', data_recebimento) = ?",
                (yyyymm_str,),
                fetch='all',
                db_path=self.db_receitas_path
            ) or []
        else:
            receitas = self._executar_query(
                "SELECT strftime('%d/%m/%Y', data_recebimento), descricao, valor "
                "FROM receitas "
                "WHERE strftime('%Y-%m', data_recebimento) = ?",
                (yyyymm_str,),
                fetch='all',
                db_path=self.db_receitas_path
            ) or []

        total_entradas = self._preencher_treeview_detalhes(tree_entradas, receitas)
        ttk.Label(
            frame_entradas,
            text=f"Total: {locale.currency(total_entradas, grouping=True)}",
            font=('Arial', 10, 'bold')
        ).pack(pady=5, anchor='e')

        # --- Saídas (Despesas) ---
        frame_saidas = ttk.Frame(notebook)
        notebook.add(frame_saidas, text="Saídas (Despesas)")
        tree_saidas = self._criar_treeview_detalhes(frame_saidas, ('data', 'descricao', 'valor', 'meio_pgto'))

        meios_pagamento_caixa = ('Boleto', 'Dinheiro', 'PIX/Transferência', 'Débito em Conta')
        query_despesas = (
            "SELECT strftime('%d/%m/%Y', data_pagamento), descricao, valor, meio_pagamento "
            "FROM v_despesas_compat "
            "WHERE strftime('%Y-%m', data_pagamento) = ? "
            f"AND meio_pagamento IN ({','.join(['?']*len(meios_pagamento_caixa))})"
        )
        params_despesas = (yyyymm_str,) + meios_pagamento_caixa
        despesas = self._executar_query(
            query_despesas,
            params_despesas,
            fetch='all',
            db_path=self.db_despesas_path
        ) or []

        total_saidas = self._preencher_treeview_detalhes(tree_saidas, despesas)
        ttk.Label(
            frame_saidas,
            text=f"Total: {locale.currency(total_saidas, grouping=True)}",
            font=('Arial', 10, 'bold')
        ).pack(pady=5, anchor='e')

        # --- Saídas (Eventos Avulsos) ---
        frame_avulsos = ttk.Frame(notebook)
        notebook.add(frame_avulsos, text="Saídas (Eventos Avulsos)")
        tree_avulsos = self._criar_treeview_detalhes(frame_avulsos, ('data', 'descricao', 'valor'))

        avulsos = self._executar_query(
            "SELECT strftime('%d/%m/%Y', data), descricao, valor "
            "FROM eventos_caixa_avulsos "
            "WHERE strftime('%Y-%m', data) = ?",
            (yyyymm_str,),
            fetch='all'
        ) or []

        total_avulsos = self._preencher_treeview_detalhes(tree_avulsos, avulsos)
        ttk.Label(
            frame_avulsos,
            text=f"Total: {locale.currency(total_avulsos, grouping=True)}",
            font=('Arial', 10, 'bold')
        ).pack(pady=5, anchor='e')

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
        for row in data: 
            if len(row) > 2 and isinstance(row[2], (int, float)):
                total += row[2]
                formatted_row = list(row); formatted_row[2] = locale.currency(row[2], grouping=True); tree.insert('', 'end', values=formatted_row)
        return total

    def _atualizar_grafico(self):
        """Atualiza o gráfico de acordo com o filtro de período selecionado."""
        self.figura.clear()
        self.ax = self.figura.add_subplot(111)

        try:
            mes_inicio_num = list(calendar.month_name).index(self.mes_inicio_var.get())
            ano_inicio = self.ano_inicio_var.get()
            mes_fim_num = list(calendar.month_name).index(self.mes_fim_var.get())
            ano_fim = self.ano_fim_var.get()
        except ValueError:
            messagebox.showerror("Erro de Filtro", "Mês inválido selecionado no filtro.", parent=self)
            return

        start_yyyymm = f"{ano_inicio}{mes_inicio_num:02d}"
        end_yyyymm = f"{ano_fim}{mes_fim_num:02d}"

        if start_yyyymm > end_yyyymm:
            messagebox.showwarning(
                "Filtro Inválido",
                "A data de início não pode ser posterior à data de fim.",
                parent=self
            )
            return

        # Sem user_id
        query = (
            "SELECT ano, mes, total_entradas, total_saidas, saldo_mes "
            "FROM balanco_mensal "
            "WHERE (ano || printf('%02d', mes)) BETWEEN ? AND ? "
            "ORDER BY ano, mes"
        )
        dados = self._executar_query(
            query,
            (start_yyyymm, end_yyyymm),
            fetch='all'
        )

        if not dados:
            self.ax.text(0.5, 0.5, "Sem dados para exibir no período", ha='center', va='center')
            self.canvas.draw()
            return

        labels = [f"{mes:02d}/{ano}" for ano, mes, _, _, _ in dados]
        entradas = [e for _, _, e, _, _ in dados]
        saidas = [s for _, _, _, s, _ in dados]
        saldos = [s for _, _, _, _, s in dados]

        x = np.arange(len(labels))
        bar_width = 0.35
        ax2 = self.ax.twinx()

        bar1 = self.ax.bar(x - bar_width/2, entradas, bar_width, label='Entradas', color='mediumseagreen')
        bar2 = self.ax.bar(x + bar_width/2, saidas, bar_width, label='Saídas', color='coral')

        self.ax.bar_label(
            bar1,
            padding=3,
            fmt=lambda v: locale.currency(v, symbol=False, grouping=True),
            fontsize=8
        )
        self.ax.bar_label(
            bar2,
            padding=3,
            fmt=lambda v: locale.currency(v, symbol=False, grouping=True),
            fontsize=8
        )

        ax2.plot(x, saldos, label='Saldo do Mês', color='royalblue', linestyle='--', marker='o')

        self.ax.set_ylabel('Valor Entradas/Saídas (R$)')
        ax2.set_ylabel('Valor Saldo (R$)')
        self.ax.set_title('Evolução do Fluxo de Caixa Mensal')
        self.ax.set_xticks(x)
        self.ax.set_xticklabels(labels, rotation=45, ha='right')

        handles1, labels1 = self.ax.get_legend_handles_labels()
        handles2, labels2 = ax2.get_legend_handles_labels()
        self.ax.legend(handles1 + handles2, labels1 + labels2, loc='upper left')
        self.ax.grid(axis='y', linestyle='--', alpha=0.7)

        self.figura.tight_layout()
        self.canvas.draw()


def iniciar_relatorio_balanco(parent_window):
    RelatorioBalanco(parent_window)