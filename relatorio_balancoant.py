import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import calendar
import locale

class RelatorioBalancoMensalApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Balanço Mensal (Receita x Despesa)")
        self.root.geometry("750x550")

        # Configuração de Localidade para Moeda
        try:
            locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
        except locale.Error:
            locale.setlocale(locale.LC_ALL, '') # Usa a localidade padrão do sistema

        # Estilo
        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")
        self.style.configure("TButton", padding=6, relief="flat", background="#0078D7", foreground="white")
        self.style.map("TButton", background=[('active', '#005a9e')])
        self.style.configure("Treeview.Heading", font=('Helvetica', 10, 'bold'))
        self.style.configure("Green.TLabel", foreground="green", font=('Helvetica', 10, 'bold'))
        self.style.configure("Red.TLabel", foreground="red", font=('Helvetica', 10, 'bold'))
        self.style.configure("Total.Treeview", font=('Helvetica', 10, 'bold'))

        # Conexão com os Bancos de Dados
        self.conn_despesas, self.conn_receitas = self.conectar_bds()

        # Frame de controles
        self.frame_controles = ttk.Frame(self.root, padding="10")
        self.frame_controles.pack(fill=tk.X)

        # Widgets de filtro (Apenas Ano)
        self.criar_filtros()

        # Frame de relatório (tabela)
        self.frame_relatorio = ttk.Frame(self.root, padding="10")
        self.frame_relatorio.pack(expand=True, fill=tk.BOTH)
        
        self.label_titulo_relatorio = ttk.Label(self.frame_relatorio, text="Selecione um ano e gere o relatório", font=('Helvetica', 12, 'bold'))
        self.label_titulo_relatorio.pack(pady=5)
        
        self.criar_tabela_relatorio()

        self.root.protocol("WM_DELETE_WINDOW", self.ao_fechar)

    def conectar_bds(self):
        """Conecta aos bancos de dados de despesas e receitas."""
        try:
            conn_d = sqlite3.connect('financas.db')
            conn_r = sqlite3.connect('financas_receitas.db')
            return conn_d, conn_r
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Não foi possível conectar aos bancos de dados: {e}")
            self.root.quit()
            return None, None

    def criar_filtros(self):
        """Cria o dropdown de Ano e o botão de gerar."""
        ttk.Label(self.frame_controles, text="Ano:").pack(side=tk.LEFT, padx=(0, 5))
        self.ano_selecionado = tk.StringVar()
        anos = self.obter_anos_disponiveis()
        self.combo_ano = ttk.Combobox(self.frame_controles, textvariable=self.ano_selecionado, values=anos, width=8, state="readonly")
        if anos:
            self.combo_ano.set(anos[0])
        self.combo_ano.pack(side=tk.LEFT, padx=5)

        ttk.Button(self.frame_controles, text="Gerar Relatório Anual", command=self.gerar_relatorio).pack(side=tk.LEFT, padx=10)

    def criar_tabela_relatorio(self):
        """Cria a Treeview para mostrar os dados do balanço."""
        self.tree = ttk.Treeview(self.frame_relatorio, show='headings')
        self.tree.pack(expand=True, fill=tk.BOTH, side=tk.LEFT)
        scrollbar = ttk.Scrollbar(self.frame_relatorio, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configurar colunas
        self.tree['columns'] = ('mes', 'receitas', 'despesas', 'saldo')
        self.tree.heading('mes', text='Mês')
        self.tree.heading('receitas', text='Total Receitas (R$)')
        self.tree.heading('despesas', text='Total Despesas (R$)')
        self.tree.heading('saldo', text='Saldo (R$)')
        
        self.tree.column('mes', width=120, anchor=tk.W)
        self.tree.column('receitas', width=150, anchor=tk.E)
        self.tree.column('despesas', width=150, anchor=tk.E)
        self.tree.column('saldo', width=150, anchor=tk.E)

        # Configurar tags para colorir o saldo
        self.tree.tag_configure('lucro', foreground='green', font=('Helvetica', 10, 'bold'))
        self.tree.tag_configure('prejuizo', foreground='red', font=('Helvetica', 10, 'bold'))
        self.tree.tag_configure('total_anual', font=('Helvetica', 11, 'bold'))

    def obter_anos_disponiveis(self):
        """Obtém anos de ambos os bancos de dados."""
        anos = set()
        try:
            # Anos das Despesas
            cursor_d = self.conn_despesas.cursor()
            cursor_d.execute("SELECT DISTINCT strftime('%Y', data_pagamento) FROM despesas")
            for ano in cursor_d.fetchall():
                anos.add(ano[0])
            
            # Anos das Receitas
            cursor_r = self.conn_receitas.cursor()
            cursor_r.execute("SELECT DISTINCT strftime('%Y', data_recebimento) FROM receitas")
            for ano in cursor_r.fetchall():
                anos.add(ano[0])

        except sqlite3.Error as e:
            messagebox.showerror("Erro de Consulta", f"Erro ao buscar anos disponíveis: {e}")
        
        return sorted(list(anos), reverse=True)

    def gerar_relatorio(self):
        """Busca os dados, calcula o balanço e exibe na tabela."""
        ano = self.ano_selecionado.get()
        if not ano:
            messagebox.showwarning("Filtro Incompleto", "Por favor, selecione um Ano.")
            return

        self.label_titulo_relatorio.config(text=f"Balanço de Receitas x Despesas - Ano {ano}")
        for i in self.tree.get_children():
            self.tree.delete(i)

        try:
            # Buscar despesas do ano
            cursor_d = self.conn_despesas.cursor()
            cursor_d.execute("""
                SELECT strftime('%m', data_pagamento), SUM(valor) 
                FROM despesas WHERE strftime('%Y', data_pagamento) = ? 
                GROUP BY strftime('%m', data_pagamento)
            """, (ano,))
            despesas_mes = {mes: valor for mes, valor in cursor_d.fetchall()}

            # Buscar receitas do ano
            cursor_r = self.conn_receitas.cursor()
            cursor_r.execute("""
                SELECT strftime('%m', data_recebimento), SUM(valor) 
                FROM receitas WHERE strftime('%Y', data_recebimento) = ? 
                GROUP BY strftime('%m', data_recebimento)
            """, (ano,))
            receitas_mes = {mes: valor for mes, valor in cursor_r.fetchall()}
            
            total_receitas_ano = 0
            total_despesas_ano = 0
            
            # Processar e exibir cada mês
            for i in range(1, 13):
                mes_str = f"{i:02d}"
                nome_mes = calendar.month_name[i]
                
                receita = receitas_mes.get(mes_str, 0.0)
                despesa = despesas_mes.get(mes_str, 0.0)
                saldo = receita - despesa
                
                total_receitas_ano += receita
                total_despesas_ano += despesa
                
                tag_saldo = 'lucro' if saldo >= 0 else 'prejuizo'
                
                self.tree.insert('', tk.END, values=(
                    nome_mes,
                    locale.currency(receita, grouping=True),
                    locale.currency(despesa, grouping=True),
                    locale.currency(saldo, grouping=True)
                ), tags=(tag_saldo,))

            # Inserir linha de total
            saldo_anual = total_receitas_ano - total_despesas_ano
            tag_saldo_anual = 'lucro' if saldo_anual >= 0 else 'prejuizo'

            self.tree.insert('', tk.END, values=("", "", "", ""), tags=('separator',)) # Linha em branco
            self.tree.insert('', tk.END, values=(
                "TOTAL ANUAL",
                locale.currency(total_receitas_ano, grouping=True),
                locale.currency(total_despesas_ano, grouping=True),
                locale.currency(saldo_anual, grouping=True)
            ), tags=(tag_saldo_anual, 'total_anual'))
            
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Relatório", f"Não foi possível gerar o relatório: {e}")

    def ao_fechar(self):
        """Fecha as conexões com os BDs ao sair."""
        if self.conn_despesas:
            self.conn_despesas.close()
        if self.conn_receitas:
            self.conn_receitas.close()
        self.root.destroy()

def iniciar_relatorio_balanco(parent_root):
    """
    Cria uma nova janela (Toplevel) para a interface do relatório de balanço.
    """
    relatorio_window = tk.Toplevel(parent_root)
    app = RelatorioBalancoMensalApp(relatorio_window)
    relatorio_window.grab_set()

# Para testes standalone (executar este arquivo diretamente)
if __name__ == "__main__":
    # Criando bancos de dados de exemplo para teste
    def criar_dados_teste():
        conn_d = sqlite3.connect('financas.db')
        cur_d = conn_d.cursor()
        cur_d.execute('CREATE TABLE IF NOT EXISTS despesas (id INTEGER PRIMARY KEY, data_pagamento DATE, conta_despesa TEXT, valor REAL)')
        cur_d.execute("INSERT INTO despesas (data_pagamento, conta_despesa, valor) VALUES ('2025-01-10', 'Supermercado', 550.75)")
        cur_d.execute("INSERT INTO despesas (data_pagamento, conta_despesa, valor) VALUES ('2025-01-15', 'Luz', 150.25)")
        cur_d.execute("INSERT INTO despesas (data_pagamento, conta_despesa, valor) VALUES ('2025-02-10', 'Aluguel', 1200.00)")
        conn_d.commit()
        conn_d.close()

        conn_r = sqlite3.connect('financas_receitas.db')
        cur_r = conn_r.cursor()
        cur_r.execute('CREATE TABLE IF NOT EXISTS receitas (id INTEGER PRIMARY KEY, data_recebimento DATE, conta_receita TEXT, valor REAL)')
        cur_r.execute("INSERT INTO receitas (data_recebimento, conta_receita, valor) VALUES ('2025-01-05', 'Salário', 4000.00)")
        cur_r.execute("INSERT INTO receitas (data_recebimento, conta_receita, valor) VALUES ('2025-02-05', 'Salário', 4000.00)")
        cur_r.execute("INSERT INTO receitas (data_recebimento, conta_receita, valor) VALUES ('2025-02-20', 'Freelance', 800.00)")
        conn_r.commit()
        conn_r.close()
    
    criar_dados_teste()
    
    root = tk.Tk()
    root.title("Janela Principal (Teste)")
    
    # Botão para abrir o relatório de balanço
    ttk.Button(root, text="Abrir Relatório de Balanço", command=lambda: iniciar_relatorio_balanco(root)).pack(padx=50, pady=50)
    
    root.mainloop()