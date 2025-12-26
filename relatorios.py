# relatorios_financeiros.py (Versão Corrigida e Configurável)
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime

class RelatoriosFinanceirosApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Relatórios Financeiros Dinâmicos")
        self.root.geometry("850x600")

        # ==================================================================
        # CONFIGURAÇÃO - PONTO DE AJUSTE
        # Altere 'data' abaixo para o nome exato da sua coluna de datas.
        # Por exemplo: 'data_despesa', 'data_compra', etc.
        self.NOME_COLUNA_DATA = 'data_pagamento' 
        # ==================================================================

        # Estilo
        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")
        self.style.configure("TButton", padding=6, relief="flat", background="#0078D7", foreground="white")
        self.style.map("TButton", background=[('active', '#005a9e')])
        self.style.configure("Treeview.Heading", font=('Helvetica', 10, 'bold'))

        # Conexão com o BD
        self.conn = self.conectar_bd()

        # Frame de controles
        self.frame_controles = ttk.Frame(self.root, padding="10")
        self.frame_controles.pack(fill=tk.X)

        # Widgets de filtro (Ano e Mês)
        self.criar_filtros()

        # Botões de Relatório
        self.criar_botoes()

        # Frame de relatórios (tabela)
        self.frame_relatorio = ttk.Frame(self.root, padding="10")
        self.frame_relatorio.pack(expand=True, fill=tk.BOTH)
        
        # Título do relatório
        self.label_titulo_relatorio = ttk.Label(self.frame_relatorio, text="Selecione um Relatório", font=('Helvetica', 12, 'bold'))
        self.label_titulo_relatorio.pack(pady=5)
        
        # Tabela (Treeview) para exibir os dados
        self.criar_tabela_relatorio()

        self.root.protocol("WM_DELETE_WINDOW", self.ao_fechar)

    def conectar_bd(self):
        """Conecta ao banco de dados SQLite."""
        try:
            conn = sqlite3.connect('financas.db')
            return conn
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Não foi possível conectar ao 'financas.db': {e}")
            self.root.quit()
            return None

    def criar_filtros(self):
        """Cria os dropdowns de Mês e Ano."""
        ttk.Label(self.frame_controles, text="Ano:").pack(side=tk.LEFT, padx=(0, 5))
        self.ano_selecionado = tk.StringVar()
        anos = self.obter_anos_disponiveis()
        self.combo_ano = ttk.Combobox(self.frame_controles, textvariable=self.ano_selecionado, values=anos, width=8)
        if anos:
            self.combo_ano.set(anos[0])
        self.combo_ano.pack(side=tk.LEFT, padx=5)

        ttk.Label(self.frame_controles, text="Mês:").pack(side=tk.LEFT, padx=(10, 5))
        self.mes_selecionado = tk.StringVar()
        meses = {
            "Janeiro": "01", "Fevereiro": "02", "Março": "03", "Abril": "04", 
            "Maio": "05", "Junho": "06", "Julho": "07", "Agosto": "08", 
            "Setembro": "09", "Outubro": "10", "Novembro": "11", "Dezembro": "12"
        }
        self.combo_mes = ttk.Combobox(self.frame_controles, textvariable=self.mes_selecionado, values=list(meses.keys()), width=12)
        mes_atual_nome = [nome for nome, num in meses.items() if num == datetime.now().strftime('%m')][0]
        self.combo_mes.set(mes_atual_nome)
        self.meses_dict = meses
        self.combo_mes.pack(side=tk.LEFT, padx=5)

    def criar_botoes(self):
        """Cria os botões para gerar os relatórios."""
        ttk.Button(self.frame_controles, text="Por Categoria", command=self.gerar_relatorio_categoria).pack(side=tk.LEFT, padx=10)
        ttk.Button(self.frame_controles, text="Por Meio de Pagamento", command=self.gerar_relatorio_meio_pagamento).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.frame_controles, text="Extrato Detalhado", command=self.gerar_relatorio_detalhado).pack(side=tk.LEFT, padx=5)

    def criar_tabela_relatorio(self):
        """Cria a Treeview para mostrar os dados."""
        self.tree = ttk.Treeview(self.frame_relatorio, columns=('col1', 'col2', 'col3', 'col4'), show='headings')
        self.tree.pack(expand=True, fill=tk.BOTH, side=tk.LEFT)
        scrollbar = ttk.Scrollbar(self.frame_relatorio, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def limpar_tabela(self):
        """Limpa todos os dados da tabela."""
        for i in self.tree.get_children():
            self.tree.delete(i)

    def executar_consulta(self, query, params=None):
        """Executa uma consulta SQL e retorna os resultados."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params or [])
            return cursor.fetchall()
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Consulta", f"Ocorreu um erro ao consultar o banco de dados: {e}")
            return []
            
    def obter_anos_disponiveis(self):
        """Obtém uma lista de anos únicos da tabela de despesas."""
        query = f"SELECT DISTINCT strftime('%Y', {self.NOME_COLUNA_DATA}) FROM despesas ORDER BY strftime('%Y', {self.NOME_COLUNA_DATA}) DESC"
        resultados = self.executar_consulta(query)
        return [r[0] for r in resultados]

    def _obter_periodo_selecionado(self):
        """Retorna o ano e mês formatados (YYYY-MM)."""
        ano = self.ano_selecionado.get()
        mes_nome = self.mes_selecionado.get()
        if not ano or not mes_nome:
            messagebox.showwarning("Filtro Incompleto", "Por favor, selecione Ano e Mês.")
            return None
        mes_num = self.meses_dict[mes_nome]
        return f"{ano}-{mes_num}", mes_nome, ano

    def gerar_relatorio_categoria(self):
        """Gera um relatório agregado por categoria."""
        periodo_info = self._obter_periodo_selecionado()
        if not periodo_info: return
        periodo, mes_nome, ano = periodo_info

        self.label_titulo_relatorio.config(text=f"Relatório por Categoria - {mes_nome}/{ano}")
        self.limpar_tabela()
        
        self.tree.config(columns=('categoria', 'valor'))
        self.tree.heading('categoria', text='Categoria')
        self.tree.heading('valor', text='Valor Total (R$)')
        self.tree.column('categoria', width=300, anchor=tk.W)
        self.tree.column('valor', width=150, anchor=tk.E)

        query = f"""
            SELECT conta_despesa, printf('%.2f', SUM(valor))
            FROM despesas
            WHERE strftime('%Y-%m', {self.NOME_COLUNA_DATA}) = ?
            GROUP BY conta_despesa
            ORDER BY SUM(valor) DESC;
        """
        resultados = self.executar_consulta(query, (periodo,))
        
        total = 0.0
        for categoria, valor in resultados:
            self.tree.insert('', tk.END, values=(categoria, valor))
            total += float(valor)
            
        self.tree.insert('', tk.END, values=("", ""), tags=('total_separator',))
        self.tree.insert('', tk.END, values=("TOTAL", f"{total:.2f}"), tags=('total',))
        self.style.configure("Treeview", rowheight=25)
        self.tree.tag_configure('total', font=('Helvetica', 10, 'bold'))

    def gerar_relatorio_meio_pagamento(self):
        """Gera um relatório agregado por meio de pagamento."""
        periodo_info = self._obter_periodo_selecionado()
        if not periodo_info: return
        periodo, mes_nome, ano = periodo_info
        
        self.label_titulo_relatorio.config(text=f"Relatório por Meio de Pagamento - {mes_nome}/{ano}")
        self.limpar_tabela()

        self.tree.config(columns=('meio_pagamento', 'valor'))
        self.tree.heading('meio_pagamento', text='Meio de Pagamento')
        self.tree.heading('valor', text='Valor Total (R$)')
        self.tree.column('meio_pagamento', width=300, anchor=tk.W)
        self.tree.column('valor', width=150, anchor=tk.E)

        query = f"""
            SELECT meio_pagamento, printf('%.2f', SUM(valor))
            FROM despesas
            WHERE strftime('%Y-%m', {self.NOME_COLUNA_DATA}) = ?
            GROUP BY meio_pagamento
            ORDER BY SUM(valor) DESC;
        """
        resultados = self.executar_consulta(query, (periodo,))
        
        total = 0.0
        for meio, valor in resultados:
            self.tree.insert('', tk.END, values=(meio, valor))
            total += float(valor)

        self.tree.insert('', tk.END, values=("", ""), tags=('total_separator',))
        self.tree.insert('', tk.END, values=("TOTAL", f"{total:.2f}"), tags=('total',))

    def gerar_relatorio_detalhado(self):
        """Lista todas as despesas do período selecionado."""
        periodo_info = self._obter_periodo_selecionado()
        if not periodo_info: return
        periodo, mes_nome, ano = periodo_info
        
        self.label_titulo_relatorio.config(text=f"Extrato Detalhado - {mes_nome}/{ano}")
        self.limpar_tabela()

        self.tree.config(columns=('data', 'descricao', 'categoria', 'valor'))
        self.tree.heading('data', text='Data')
        self.tree.heading('descricao', text='Descrição')
        self.tree.heading('categoria', text='Categoria')
        self.tree.heading('valor', text='Valor (R$)')
        self.tree.column('data', width=100, anchor=tk.CENTER)
        self.tree.column('descricao', width=300, anchor=tk.W)
        self.tree.column('categoria', width=150, anchor=tk.W)
        self.tree.column('valor', width=120, anchor=tk.E)

        query = f"""
            SELECT strftime('%d/%m/%Y', {self.NOME_COLUNA_DATA}), descricao, conta_despesa, printf('%.2f', valor)
            FROM despesas
            WHERE strftime('%Y-%m', {self.NOME_COLUNA_DATA}) = ?
            ORDER BY {self.NOME_COLUNA_DATA};
        """
        resultados = self.executar_consulta(query, (periodo,))
        
        for row in resultados:
            self.tree.insert('', tk.END, values=row)

    def ao_fechar(self):
        """Fecha a conexão com o BD ao sair."""
        if self.conn:
            self.conn.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = RelatoriosFinanceirosApp(root)
    root.mainloop()