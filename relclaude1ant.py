# relclaude.py (Versão ajustada para ser chamada por outro programa)

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
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Relatórios Financeiros Avançado")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')

        self.font_title = font.Font(family="Helvetica", size=14, weight="bold")
        self.font_normal = font.Font(family="Helvetica", size=10)

        self.db_path = "financas.db"
        self.table_name = "despesas"  # Focar na tabela principal

        self.setup_ui()
        if self.verificar_conexao_bd():
            self.atualizar_periodo_disponivel()

    def verificar_conexao_bd(self):
        """Verifica se o banco de dados e a tabela principal existem."""
        try:
            import os
            if not os.path.exists(self.db_path):
                messagebox.showerror("Erro de Conexão", f"Arquivo '{self.db_path}' não encontrado!")
                return False

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (self.table_name,))
            if cursor.fetchone() is None:
                messagebox.showerror("Erro de Tabela", f"A tabela '{self.table_name}' não foi encontrada.")
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
            # A coluna de data no seu BD principal é 'data_pagamento'
            query = f"SELECT DISTINCT strftime('%Y-%m', data_pagamento) as periodo FROM {self.table_name} WHERE data_pagamento IS NOT NULL ORDER BY periodo DESC"
            df_periodos = pd.read_sql_query(query, conn)
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
            query = f"SELECT * FROM {self.table_name}"
            df = pd.read_sql_query(query, conn)
            conn.close()

            if df.empty:
                return pd.DataFrame()

            # Renomear 'data_pagamento' para 'data' para padronizar
            df = df.rename(columns={'data_pagamento': 'data'})

            df['data'] = pd.to_datetime(df['data'], errors='coerce')
            df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
            df = df.dropna(subset=['data', 'valor'])

            if filtro_periodo and filtro_periodo != 'Todos':
                df = df[df['data'].dt.strftime('%Y-%m') == filtro_periodo]
            return df
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao obter dados: {e}")
            return pd.DataFrame()

    def gerar_relatorio(self):
        tipo = self.tipo_relatorio.get()
        periodo = self.periodo_var.get()
        df = self.obter_dados_financeiros(periodo)

        if df.empty:
            messagebox.showinfo("Info", "Nenhum dado para o período.")
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
            messagebox.showerror("Erro", f"Erro ao gerar relatório: {e}")

    def limpar_frames(self):
        for frame in [self.frame_grafico, self.frame_stats]:
            for widget in frame.winfo_children():
                widget.destroy()

    def relatorio_por_categoria(self, df):
        if 'conta_despesa' not in df.columns:
            messagebox.showinfo("Info", "Coluna 'conta_despesa' não encontrada.")
            return

        resumo = df.groupby('conta_despesa')['valor'].agg(['sum', 'count']).round(2).sort_values(by='sum', ascending=False)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw={'width_ratios': [1, 1.5]})
        top_5 = resumo.head(5)
        if len(resumo) > 5:
             outros_sum = resumo['sum'][5:].sum()
             top_5.loc['Outros'] = [outros_sum, 0]
        ax1.pie(top_5['sum'], labels=top_5.index, autopct='%1.1f%%', startangle=90, wedgeprops=dict(width=0.4))
        ax1.set_title('Distribuição de Gastos (%)', fontweight='bold')
        resumo['sum'].plot(kind='barh', ax=ax2, color='skyblue')
        ax2.set_title('Total Gasto por Categoria (R$)', fontweight='bold')
        ax2.set_xlabel('Valor (R$)')
        plt.tight_layout()
        self.mostrar_grafico(fig)

    def relatorio_por_meio_pagamento(self, df):
        if 'meio_pagamento' not in df.columns:
            messagebox.showinfo("Info", "Coluna 'meio_pagamento' não encontrada.")
            return
        resumo = df.groupby('meio_pagamento')['valor'].agg(['sum', 'count']).round(2).sort_values(by='sum', ascending=False)
        fig, ax = plt.subplots(figsize=(12, 6))
        resumo['sum'].plot(kind='bar', ax=ax, color='lightgreen')
        ax.set_title('Total Gasto por Meio de Pagamento', fontweight='bold')
        ax.set_ylabel('Valor (R$)')
        ax.tick_params(axis='x', rotation=45)
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
        y_pos = np.arange(len(top_despesas))
        bars = ax.barh(y_pos, top_despesas['valor'], color='salmon', alpha=0.9)
        ax.set_yticks(y_pos)
        labels = [f"{desc[:35]}..." if len(desc)>35 else desc for desc in top_despesas['descricao']]
        ax.set_yticklabels(labels)
        ax.set_xlabel('Valor (R$)')
        ax.set_title('Top 10 Maiores Despesas no Período', fontweight='bold')
        for bar in bars:
            ax.text(bar.get_width(), bar.get_y() + bar.get_height()/2, f' R$ {bar.get_width():,.2f}'.replace(",", "X").replace(".", ",").replace("X", "."), va='center', ha='left')
        plt.tight_layout()
        self.mostrar_grafico(fig)

    def relatorio_resumo_mensal(self, df):
        df_full = self.obter_dados_financeiros()
        resumo = df_full.set_index('data').resample('M')['valor'].sum().reset_index()
        resumo['mes_ano'] = resumo['data'].dt.strftime('%Y-%m')
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.bar(resumo['mes_ano'], resumo['valor'], color='cornflowerblue')
        ax.set_title('Resumo de Gastos Mensais', fontweight='bold')
        ax.set_ylabel('Valor Total (R$)')
        ax.tick_params(axis='x', rotation=45)
        plt.tight_layout()
        self.mostrar_grafico(fig)

    def relatorio_comparativo_anual(self, df):
        df_full = self.obter_dados_financeiros()
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
        plt.tight_layout()
        self.mostrar_grafico(fig)

    def mostrar_grafico(self, fig):
        canvas = FigureCanvasTkAgg(fig, self.frame_grafico)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def atualizar_tabela_dados(self, df):
        for item in self.tree.get_children():
            self.tree.delete(item)
        if df.empty: return
        
        # Usa 'conta_despesa' pois é o nome original no DB
        colunas_exibir = ['data', 'descricao', 'valor', 'conta_despesa', 'meio_pagamento', 'num_parcelas']
        colunas_df = [col for col in colunas_exibir if col in df.columns]
        
        self.tree['columns'] = colunas_df
        self.tree['show'] = 'headings'
        for col in colunas_df:
            self.tree.heading(col, text=col.replace('_', ' ').title())
            self.tree.column(col, width=120, anchor='w')
        self.tree.column('valor', anchor='e')
        df_sorted = df.sort_values(by='data', ascending=False)
        for _, row in df_sorted.iterrows():
            valores = []
            for col in colunas_df:
                valor = row.get(col, '')
                if pd.isna(valor): valor = ''
                if col == 'valor': valor = f'R$ {float(valor):,.2f}'.replace(",", "X").replace(".", ",").replace("X", ".")
                elif col == 'data': valor = valor.strftime('%d/%m/%Y')
                valores.append(str(valor))
            self.tree.insert('', 'end', values=valores)

    def gerar_estatisticas(self, df):
        if df.empty: return
        stats_main_frame = tk.Frame(self.frame_stats, bg='white')
        stats_main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        title_label = tk.Label(stats_main_frame, text="Estatísticas do Período", font=self.font_title, bg='white', fg='#2c3e50')
        title_label.pack(pady=(0, 20))
        cards_frame = tk.Frame(stats_main_frame, bg='white')
        cards_frame.pack(fill=tk.X, pady=(0, 20))
        stats_data = [
            ("Total de Gastos", f"R$ {df['valor'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), "#e74c3c"),
            ("Média por Transação", f"R$ {df['valor'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), "#3498db"),
            ("Maior Gasto", f"R$ {df['valor'].max():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), "#e67e22"),
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
        if df.empty:
            messagebox.showinfo("Info", "Nenhum dado para exportar.")
            return
        arquivo = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Arquivos Excel", "*.xlsx")],
            title="Salvar Relatório em Excel",
            initialfile=f"Relatorio_{periodo.replace('-', '')}.xlsx"
        )
        if not arquivo: return
        try:
            with pd.ExcelWriter(arquivo, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Dados Detalhados', index=False)
                resumo = df.groupby('conta_despesa')['valor'].agg(['sum', 'count']).round(2)
                resumo.to_excel(writer, sheet_name='Resumo por Categoria')
            messagebox.showinfo("Sucesso", f"Relatório exportado para:\n{arquivo}")
        except Exception as e:
            messagebox.showerror("Erro de Exportação", f"Não foi possível salvar: {e}")

# --- FUNÇÃO PARA CHAMAR ESTE MÓDULO ---
def iniciar_relatorios_avancados(parent_root):
    """
    Cria uma nova janela (Toplevel) para a interface de relatórios avançados.
    Isso permite que ela coexista com a janela principal.
    """
    advanced_window = tk.Toplevel(parent_root)
    advanced_window.title("Relatórios Avançados")
    app = RelatoriosFinanceiros(advanced_window)
    # Garante que a janela de relatórios fique na frente
    advanced_window.grab_set()

# Bloco para execução direta do script (para testes)
if __name__ == "__main__":
    root = tk.Tk()
    app = RelatoriosFinanceiros(root)
    
    def on_closing():
        plt.close('all')
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()