# relclaude1.py (Versão Corrigida para Múltiplos Usuários)

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns
from datetime import datetime
import numpy as np
from tkinter import font

# Configurar estilo dos gráficos
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

class RelatoriosFinanceiros:
    # ALTERADO: O construtor agora aceita o user_id
    def __init__(self, root, user_id):
        self.root = root
        self.user_id = user_id  # Armazena o ID do usuário logado
        self.root.title("Sistema de Relatórios Financeiros Avançado")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')

        self.font_title = font.Font(family="Helvetica", size=14, weight="bold")
        self.font_normal = font.Font(family="Helvetica", size=10)

        self.db_path = "financas.db"
        self.table_name = "despesas"

        self.setup_ui()
        if self.verificar_conexao_bd():
            self.atualizar_periodo_disponivel()

    def verificar_conexao_bd(self):
        try:
            import os
            if not os.path.exists(self.db_path):
                messagebox.showerror("Erro de Conexão", f"Arquivo de banco de dados '{self.db_path}' não encontrado!")
                return False

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (self.table_name,))
            if cursor.fetchone() is None:
                messagebox.showerror("Erro de Tabela", f"A tabela principal '{self.table_name}' não foi encontrada no banco de dados.")
                conn.close()
                return False
            conn.close()
            return True
        except Exception as e:
            messagebox.showerror("Erro de Conexão", f"Erro ao verificar o banco de dados: {e}")
            return False

    def setup_ui(self):
        """Configura a interface do usuário"""
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        title_label = tk.Label(main_frame, text="Análise Avançada de Finanças",
                              font=self.font_title, bg='#f0f0f0', fg='#2c3e50')
        title_label.pack(pady=(0, 20))

        controls_frame = tk.LabelFrame(main_frame, text="Controles de Relatório",
                                     font=self.font_normal, bg='#f0f0f0')
        controls_frame.pack(fill=tk.X, pady=(0, 10))

        row1_frame = tk.Frame(controls_frame, bg='#f0f0f0')
        row1_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(row1_frame, text="Tipo de Relatório:", font=self.font_normal, bg='#f0f0f0').pack(side=tk.LEFT)
        self.tipo_relatorio = ttk.Combobox(row1_frame, width=22, font=self.font_normal, state="readonly")
        self.tipo_relatorio['values'] = [
            'Por Categoria', 'Por Meio de Pagamento', 'Evolução Temporal',
            'Resumo Mensal', 'Top 10 Despesas', 'Comparativo Anual'
        ]
        self.tipo_relatorio.set('Por Categoria')
        self.tipo_relatorio.pack(side=tk.LEFT, padx=(5, 20))

        tk.Label(row1_frame, text="Período:", font=self.font_normal, bg='#f0f0f0').pack(side=tk.LEFT)
        self.periodo_var = tk.StringVar()
        self.periodo_combo = ttk.Combobox(row1_frame, textvariable=self.periodo_var,
                                        width=15, font=self.font_normal, state="readonly")
        self.periodo_combo.pack(side=tk.LEFT, padx=(5, 20))

        btn_frame = tk.Frame(row1_frame, bg='#f0f0f0')
        btn_frame.pack(side=tk.RIGHT)

        tk.Button(btn_frame, text="Gerar Relatório", command=self.gerar_relatorio,
                 bg='#3498db', fg='white', font=self.font_normal, width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Exportar Excel", command=self.exportar_excel,
                 bg='#27ae60', fg='white', font=self.font_normal, width=12).pack(side=tk.LEFT, padx=5)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=10)

        self.frame_grafico = tk.Frame(self.notebook, bg='white')
        self.frame_tabela = tk.Frame(self.notebook, bg='white')
        self.frame_stats = tk.Frame(self.notebook, bg='white')

        self.notebook.add(self.frame_grafico, text="📊 Gráficos")
        self.notebook.add(self.frame_tabela, text="📋 Dados Detalhados")
        self.notebook.add(self.frame_stats, text="📈 Estatísticas")

        self.setup_treeview()

    def setup_treeview(self):
        tree_frame = tk.Frame(self.frame_tabela)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        self.tree = ttk.Treeview(tree_frame, yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        v_scrollbar.config(command=self.tree.yview)
        h_scrollbar.config(command=self.tree.xview)
        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

    def atualizar_periodo_disponivel(self):
        try:
            conn = sqlite3.connect(self.db_path)
            # ALTERADO: A query agora filtra os períodos pelo user_id logado
            query = f"SELECT DISTINCT strftime('%Y-%m', data_pagamento) as periodo FROM {self.table_name} WHERE data_pagamento IS NOT NULL AND user_id = ? ORDER BY periodo DESC"
            df_periodos = pd.read_sql_query(query, conn, params=(self.user_id,))
            conn.close()
            
            periodos = df_periodos['periodo'].dropna().tolist()
            if periodos:
                self.periodo_combo['values'] = ['Todos'] + periodos
                self.periodo_combo.set(periodos[0])
            else:
                self.periodo_combo['values'] = ['Nenhum']
                self.periodo_combo.set('Nenhum')
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao atualizar períodos: {e}")

    def obter_dados_financeiros(self, filtro_periodo=None):
        try:
            conn = sqlite3.connect(self.db_path)
            # ALTERADO: A query agora busca dados apenas do user_id logado
            query = f"SELECT * FROM {self.table_name} WHERE user_id = ?"
            df = pd.read_sql_query(query, conn, params=(self.user_id,))
            conn.close()

            if df.empty:
                return pd.DataFrame()

            df = df.rename(columns={'data_pagamento': 'data'})
            df['data'] = pd.to_datetime(df['data'], errors='coerce')
            df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
            df.dropna(subset=['data', 'valor'], inplace=True)

            if filtro_periodo and filtro_periodo != 'Todos':
                df = df[df['data'].dt.strftime('%Y-%m') == filtro_periodo]
            return df
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao obter dados: {e}")
            return pd.DataFrame()

    def gerar_relatorio(self):
        tipo = self.tipo_relatorio.get()
        periodo = self.periodo_var.get()
        
        if not hasattr(plt.Axes, 'bar_label'):
             messagebox.showerror("Versão Incompatível", "Sua versão da biblioteca 'matplotlib' é antiga. Por favor, atualize-a com:\npip install --upgrade matplotlib")
             return

        df = self.obter_dados_financeiros(periodo)

        if df.empty:
            messagebox.showinfo("Info", "Nenhum dado encontrado para o período selecionado.")
            return

        self.limpar_frames()
        try:
            mapa_relatorios = {
                'Por Categoria': self.relatorio_por_categoria,
                'Por Meio de Pagamento': self.relatorio_por_meio_pagamento,
                'Evolução Temporal': self.relatorio_evolucao_temporal,
                'Resumo Mensal': self.relatorio_resumo_mensal,
                'Top 10 Despesas': self.relatorio_top_despesas,
                'Comparativo Anual': self.relatorio_comparativo_anual
            }
            funcao_relatorio = mapa_relatorios.get(tipo)
            if funcao_relatorio:
                funcao_relatorio(df)
            self.atualizar_tabela_dados(df)
            self.gerar_estatisticas(df)
        except Exception as e:
            messagebox.showerror("Erro ao Gerar Relatório", f"Ocorreu um erro: {e}")

    def limpar_frames(self):
        for frame in [self.frame_grafico, self.frame_stats]:
            for widget in frame.winfo_children():
                widget.destroy()

    def formatar_valor(self, valor):
        if valor is None or not isinstance(valor, (int, float, np.number)):
            return ""
        return f'R$ {valor:,.2f}'.replace(",", "X").replace(".", ",").replace("X", ".")

    def relatorio_por_categoria(self, df):
        resumo = df.groupby('conta_despesa')['valor'].agg(['sum', 'count']).round(2).sort_values(by='sum', ascending=False)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw={'width_ratios': [1, 1.5]})
        
        top_5 = resumo.head(5).copy()
        if len(resumo) > 5:
             outros_sum = resumo['sum'][5:].sum()
             top_5.loc['Outros'] = {'sum': outros_sum, 'count': 0}

        ax1.pie(top_5['sum'], labels=top_5.index, autopct='%1.1f%%', startangle=90, wedgeprops=dict(width=0.4))
        ax1.set_title('Distribuição de Gastos (%)', fontweight='bold')
        
        resumo['sum'].plot(kind='barh', ax=ax2, color='skyblue')
        ax2.set_title('Total Gasto por Categoria (R$)', fontweight='bold')
        ax2.set_xlabel('Valor (R$)')
        
        if ax2.containers:
            ax2.bar_label(ax2.containers[0], fmt=self.formatar_valor, padding=3, fontsize=9)
        
        plt.tight_layout()
        self.mostrar_grafico(fig)

    def relatorio_por_meio_pagamento(self, df):
        resumo = df.groupby('meio_pagamento')['valor'].agg(['sum', 'count']).round(2).sort_values(by='sum', ascending=False)
        fig, ax = plt.subplots(figsize=(12, 6))
        
        resumo['sum'].plot(kind='bar', ax=ax, color='lightgreen')
        ax.set_title('Total Gasto por Meio de Pagamento', fontweight='bold')
        ax.set_ylabel('Valor (R$)')
        ax.tick_params(axis='x', rotation=45)
        
        if ax.containers:
            ax.bar_label(ax.containers[0], fmt=self.formatar_valor, fontsize=9, rotation=45, padding=3)

        plt.tight_layout()
        self.mostrar_grafico(fig)
        
    def relatorio_evolucao_temporal(self, df):
        df_diario = df.set_index('data').resample('D')['valor'].sum().reset_index()
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(df_diario['data'], df_diario['valor'], marker='.', linestyle='-', markersize=5)
        ax.set_title('Evolução dos Gastos Diários', fontweight='bold')
        ax.set_ylabel('Valor (R$)')
        fig.autofmt_xdate()
        plt.tight_layout()
        self.mostrar_grafico(fig)

    def relatorio_top_despesas(self, df):
        top_despesas = df.nlargest(10, 'valor')[['descricao', 'valor', 'data']].sort_values('valor', ascending=True)
        fig, ax = plt.subplots(figsize=(12, 8))
        
        bars = ax.barh(np.arange(len(top_despesas)), top_despesas['valor'], color='salmon', alpha=0.9)
        ax.set_yticks(np.arange(len(top_despesas)))
        labels = [f"{desc[:35]}..." if len(str(desc or ''))>35 else str(desc) for desc in top_despesas['descricao']]
        ax.set_yticklabels(labels)
        ax.set_xlabel('Valor (R$)')
        ax.set_title('Top 10 Maiores Despesas no Período', fontweight='bold')
        
        ax.bar_label(bars, fmt=self.formatar_valor, padding=3, fontsize=9)
        
        plt.tight_layout()
        self.mostrar_grafico(fig)

    def relatorio_resumo_mensal(self, df):
        # Para o resumo mensal, sempre usamos todos os dados do usuário, ignorando o filtro de período.
        df_full = self.obter_dados_financeiros('Todos') 
        resumo = df_full.set_index('data').resample('M')['valor'].sum().reset_index()
        resumo['mes_ano'] = resumo['data'].dt.strftime('%Y-%m')
        fig, ax = plt.subplots(figsize=(12, 6))
        
        bars = ax.bar(resumo['mes_ano'], resumo['valor'], color='cornflowerblue')
        ax.set_title('Resumo de Gastos Mensais', fontweight='bold')
        ax.set_ylabel('Valor Total (R$)')
        ax.tick_params(axis='x', rotation=45)
        
        ax.bar_label(bars, fmt=self.formatar_valor, fontsize=9, rotation=45, padding=3)

        plt.tight_layout()
        self.mostrar_grafico(fig)

    def relatorio_comparativo_anual(self, df):
        # Para o comparativo anual, sempre usamos todos os dados do usuário.
        df_full = self.obter_dados_financeiros('Todos')
        df_full['mes'] = df_full['data'].dt.month
        df_full['ano'] = df_full['data'].dt.year
        comparativo = df_full.pivot_table(index='mes', columns='ano', values='valor', aggfunc='sum')
        fig, ax = plt.subplots(figsize=(12, 6))
        
        comparativo.plot(kind='bar', ax=ax, width=0.8)
        ax.set_xlabel('Mês')
        ax.set_ylabel('Valor Total (R$)')
        ax.set_title('Comparativo de Gastos Mensais por Ano', fontweight='bold')
        ax.set_xticklabels(['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'], rotation=0)
        ax.legend(title='Ano')
        
        for container in ax.containers:
            ax.bar_label(container, fmt=lambda x: self.formatar_valor(x) if x > 0 else '', label_type='edge', fontsize=8, rotation=90, padding=3)

        plt.tight_layout()
        self.mostrar_grafico(fig)

    def mostrar_grafico(self, fig):
        canvas = FigureCanvasTkAgg(fig, self.frame_grafico)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        # Garante que a figura seja fechada ao destruir o widget para liberar memória
        canvas.get_tk_widget().bind("<Destroy>", lambda e, f=fig: plt.close(f))

    def atualizar_tabela_dados(self, df):
        for item in self.tree.get_children(): self.tree.delete(item)
        if df.empty: return
        
        colunas_exibir = ['data', 'descricao', 'valor', 'conta_despesa', 'meio_pagamento', 'num_parcelas']
        colunas_df = [col for col in colunas_exibir if col in df.columns]
        
        self.tree['columns'] = colunas_df
        self.tree['show'] = 'headings'
        for col in colunas_df:
            self.tree.heading(col, text=col.replace('_', ' ').title())
            self.tree.column(col, width=120, anchor='w')
        self.tree.column('valor', anchor='e'); self.tree.column('descricao', width=250)
        df_sorted = df.sort_values(by='data', ascending=False)
        for _, row in df_sorted.iterrows():
            valores = []
            for col in colunas_df:
                valor_celula = row.get(col, '')
                if pd.isna(valor_celula): valor_celula = ''
                
                if col == 'valor': valor_celula = self.formatar_valor(float(valor_celula))
                elif col == 'data' and isinstance(valor_celula, pd.Timestamp): valor_celula = valor_celula.strftime('%d/%m/%Y')
                
                valores.append(str(valor_celula))
            self.tree.insert('', 'end', values=valores)

    def gerar_estatisticas(self, df):
        if df.empty: return
        stats_main_frame = tk.Frame(self.frame_stats, bg='white')
        stats_main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        tk.Label(stats_main_frame, text="Estatísticas do Período", font=self.font_title, bg='white', fg='#2c3e50').pack(pady=(0, 20))
        cards_frame = tk.Frame(stats_main_frame, bg='white')
        cards_frame.pack(fill=tk.X, pady=(0, 20))
        stats_data = [
            ("Total de Gastos", self.formatar_valor(df['valor'].sum()), "#e74c3c"),
            ("Média por Transação", self.formatar_valor(df['valor'].mean()), "#3498db"),
            ("Maior Gasto", self.formatar_valor(df['valor'].max()), "#e67e22"),
            ("Total de Transações", str(len(df)), "#34495e")
        ]
        for i, (titulo, valor, cor) in enumerate(stats_data):
            card_frame = tk.Frame(cards_frame, bg=cor, relief='raised', bd=2, height=80)
            card_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=5)
            tk.Label(card_frame, text=titulo, font=('Helvetica', 10, 'bold'), bg=cor, fg='white').pack(pady=(10, 5))
            tk.Label(card_frame, text=valor, font=('Helvetica', 14, 'bold'), bg=cor, fg='white').pack(pady=(0, 10))

    def exportar_excel(self):
        periodo = self.periodo_var.get()
        df = self.obter_dados_financeiros(periodo)
        if df.empty: messagebox.showinfo("Info", "Nenhum dado para exportar."); return
        arquivo = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Arquivos Excel", "*.xlsx")], title="Salvar Relatório", initialfile=f"Relatorio_{periodo.replace('-', '')}.xlsx")
        if not arquivo: return
        try:
            with pd.ExcelWriter(arquivo, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Dados Detalhados', index=False)
                resumo = df.groupby('conta_despesa')['valor'].agg(['sum', 'count']).round(2)
                resumo.to_excel(writer, sheet_name='Resumo por Categoria')
            messagebox.showinfo("Sucesso", f"Relatório exportado para:\n{arquivo}")
        except Exception as e:
            messagebox.showerror("Erro de Exportação", f"Não foi possível salvar: {e}")

# ALTERADO: A função de inicialização agora aceita e repassa o user_id
def iniciar_relatorios_avancados(parent_root, user_id):
    advanced_window = tk.Toplevel(parent_root)
    app = RelatoriosFinanceiros(advanced_window, user_id)
    advanced_window.grab_set()

if __name__ == "__main__":
    # Para teste standalone, um user_id de teste (ex: 1 para o admin) deve ser passado
    class MockRoot(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("Janela Principal (Teste)")
            ttk.Button(self, text="Abrir Relatórios Avançados (Usuário 1)", 
                       command=lambda: iniciar_relatorios_avancados(self, 1)).pack(pady=50)

    root = MockRoot()
    
    def on_closing():
        plt.close('all')
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()