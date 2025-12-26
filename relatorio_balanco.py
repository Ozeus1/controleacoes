import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import calendar
import locale

class RelatorioBalancoMensalApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Balanço Detalhado (Receita x Despesa)")
        self.root.geometry("850x650")

        # Configuração de Localidade para Moeda
        try:
            locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
        except locale.Error:
            try:
                locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
            except locale.Error:
                locale.setlocale(locale.LC_ALL, '')

        # Estilo
        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")
        self.style.configure(
            "TButton",
            padding=6,
            relief="flat",
            background="#0078D7",
            foreground="white"
        )
        self.style.map("TButton", background=[('active', '#005a9e')])
        self.style.configure("Treeview.Heading", font=('Helvetica', 10, 'bold'))
        
        # Conexão com os Bancos de Dados
        self.conn_despesas, self.conn_receitas = self.conectar_bds()

        # --- UI ---
        self.frame_controles = ttk.Frame(self.root, padding="10")
        self.frame_controles.pack(fill=tk.X)
        self.criar_filtros()

        self.frame_relatorio = ttk.Frame(self.root, padding="10")
        self.frame_relatorio.pack(expand=True, fill=tk.BOTH)
        
        self.label_titulo_relatorio = ttk.Label(
            self.frame_relatorio,
            text="Selecione um ano e gere o relatório",
            font=('Helvetica', 12, 'bold')
        )
        self.label_titulo_relatorio.pack(pady=5)
        
        self.criar_tabela_relatorio()

        self.root.protocol("WM_DELETE_WINDOW", self.ao_fechar)

    def conectar_bds(self):
        try:
            conn_d = sqlite3.connect('financas.db')
            conn_r = sqlite3.connect('financas_receitas.db')
            return conn_d, conn_r
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Não foi possível conectar: {e}")
            self.root.quit()
            return None, None

    def criar_filtros(self):
        ttk.Label(self.frame_controles, text="Ano:").pack(side=tk.LEFT, padx=(0, 5))
        self.ano_selecionado = tk.StringVar()
        anos = self.obter_anos_disponiveis()
        self.combo_ano = ttk.Combobox(
            self.frame_controles,
            textvariable=self.ano_selecionado,
            values=anos,
            width=8,
            state="readonly"
        )
        if anos:
            self.combo_ano.set(anos[0])
        self.combo_ano.pack(side=tk.LEFT, padx=5)
        ttk.Button(
            self.frame_controles,
            text="Gerar Relatório Anual",
            command=self.gerar_relatorio
        ).pack(side=tk.LEFT, padx=10)

    def criar_tabela_relatorio(self):
        # 'show' agora é 'tree headings' para mostrar árvore e cabeçalhos
        self.tree = ttk.Treeview(self.frame_relatorio, show='tree headings')
        self.tree.pack(expand=True, fill=tk.BOTH, side=tk.LEFT)
        scrollbar = ttk.Scrollbar(
            self.frame_relatorio,
            orient=tk.VERTICAL,
            command=self.tree.yview
        )
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Coluna da árvore (#0)
        self.tree.heading('#0', text='Mês / Categoria')
        self.tree.column('#0', width=350, anchor=tk.W, stretch=tk.YES)
        
        # Outras colunas
        self.tree['columns'] = ('receitas', 'despesas', 'saldo')
        self.tree.heading('receitas', text='Receitas (R$)')
        self.tree.heading('despesas', text='Despesas (R$)')
        self.tree.heading('saldo', text='Saldo (R$)')
        
        self.tree.column('receitas', width=150, anchor=tk.E)
        self.tree.column('despesas', width=150, anchor=tk.E)
        self.tree.column('saldo', width=150, anchor=tk.E)

        self.tree.tag_configure('lucro', foreground='green', font=('Helvetica', 10, 'bold'))
        self.tree.tag_configure('prejuizo', foreground='red', font=('Helvetica', 10, 'bold'))
        self.tree.tag_configure('total_anual', font=('Helvetica', 11, 'bold'))
        self.tree.tag_configure('subheader', font=('Helvetica', 9, 'bold'), background='#f0f0f0')

    def check_receitas_user_id(self, cursor):
        """Apenas detecta se existe coluna user_id em receitas (sem filtrar por usuário)."""
        try:
            cursor.execute("PRAGMA table_info(receitas)")
            colunas = [row[1] for row in cursor.fetchall()]
            return 'user_id' in colunas
        except sqlite3.Error:
            return False

    def obter_anos_disponiveis(self):
        anos = set()
        try:
            cursor_d = self.conn_despesas.cursor()
            cursor_d.execute("""
                SELECT DISTINCT strftime('%Y', data_pagamento)
                FROM v_despesas_compat
            """)
            for ano in cursor_d.fetchall():
                anos.add(ano[0])
            
            cursor_r = self.conn_receitas.cursor()
            # Aqui não filtramos por user_id, apenas usamos a coluna de data
            cursor_r.execute("""
                SELECT DISTINCT strftime('%Y', data_recebimento)
                FROM receitas
            """)
            for ano in cursor_r.fetchall():
                anos.add(ano[0])
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Consulta", f"Erro ao buscar anos: {e}")
        return sorted(list(anos), reverse=True)

    def gerar_relatorio(self):
        ano = self.ano_selecionado.get()
        if not ano:
            messagebox.showwarning("Filtro Incompleto", "Por favor, selecione um Ano.")
            return

        self.label_titulo_relatorio.config(
            text=f"Balanço Detalhado de Receitas x Despesas - Ano {ano}"
        )
        for i in self.tree.get_children():
            self.tree.delete(i)

        try:
            cursor_d = self.conn_despesas.cursor()
            cursor_r = self.conn_receitas.cursor()
            
            # Despesas por mês (sem user_id)
            cursor_d.execute("""
                SELECT strftime('%m', data_pagamento), SUM(valor)
                FROM v_despesas_compat
                WHERE strftime('%Y', data_pagamento) = ?
                GROUP BY strftime('%m', data_pagamento)
            """, (ano,))
            despesas_mes = {mes: valor for mes, valor in cursor_d.fetchall()}
            
            # Receitas por mês (sem filtragem por user_id)
            cursor_r.execute("""
                SELECT strftime('%m', data_recebimento), SUM(valor)
                FROM receitas
                WHERE strftime('%Y', data_recebimento) = ?
                GROUP BY strftime('%m', data_recebimento)
            """, (ano,))
            receitas_mes = {mes: valor for mes, valor in cursor_r.fetchall()}
            
            total_receitas_ano, total_despesas_ano = 0, 0
            
            for i in range(1, 13):
                mes_str = f"{i:02d}"
                nome_mes = calendar.month_name[i]
                
                receita_total_mes = receitas_mes.get(mes_str, 0.0)
                despesa_total_mes = despesas_mes.get(mes_str, 0.0)
                
                if receita_total_mes == 0 and despesa_total_mes == 0:
                    continue

                saldo_mes = receita_total_mes - despesa_total_mes
                total_receitas_ano += receita_total_mes
                total_despesas_ano += despesa_total_mes
                
                tag_saldo = 'lucro' if saldo_mes >= 0 else 'prejuizo'

                # Linha do mês
                parent_iid = self.tree.insert(
                    '',
                    tk.END,
                    text=nome_mes,
                    values=(
                        locale.currency(receita_total_mes, grouping=True),
                        locale.currency(despesa_total_mes, grouping=True),
                        locale.currency(saldo_mes, grouping=True)
                    ),
                    tags=(tag_saldo,)
                )

                # Detalhamento de receitas
                if receita_total_mes > 0:
                    self.tree.insert(
                        parent_iid,
                        tk.END,
                        text="  (+) Receitas",
                        values=("", "", ""),
                        tags=('subheader',)
                    )
                    cursor_r.execute("""
                        SELECT conta_receita, SUM(valor)
                        FROM receitas
                        WHERE strftime('%Y-%m', data_recebimento) = ?
                        GROUP BY conta_receita
                        ORDER BY SUM(valor) DESC
                    """, (f"{ano}-{mes_str}",))
                    
                    for categoria, valor in cursor_r.fetchall():
                        self.tree.insert(
                            parent_iid,
                            tk.END,
                            text=f"      {categoria}",
                            values=(locale.currency(valor, grouping=True), "", "")
                        )

                # Detalhamento de despesas
                if despesa_total_mes > 0:
                    self.tree.insert(
                        parent_iid,
                        tk.END,
                        text="  (-) Despesas",
                        values=("", "", ""),
                        tags=('subheader',)
                    )
                    cursor_d.execute("""
                        SELECT conta_despesa, SUM(valor)
                        FROM v_despesas_compat
                        WHERE strftime('%Y-%m', data_pagamento) = ?
                        GROUP BY conta_despesa
                        ORDER BY SUM(valor) DESC
                    """, (f"{ano}-{mes_str}",))
                    for categoria, valor in cursor_d.fetchall():
                        self.tree.insert(
                            parent_iid,
                            tk.END,
                            text=f"      {categoria}",
                            values=("", locale.currency(valor, grouping=True), "")
                        )

            # Totais anuais
            saldo_anual = total_receitas_ano - total_despesas_ano
            tag_saldo_anual = 'lucro' if saldo_anual >= 0 else 'prejuizo'
            self.tree.insert('', tk.END, values=("", "", "", ""), tags=('separator',))
            
            self.tree.insert(
                '',
                tk.END,
                text="TOTAL ANUAL",
                values=(
                    locale.currency(total_receitas_ano, grouping=True),
                    locale.currency(total_despesas_ano, grouping=True),
                    locale.currency(saldo_anual, grouping=True)
                ),
                tags=(tag_saldo_anual, 'total_anual')
            )
            
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Relatório", f"Não foi possível gerar o relatório: {e}")

    def ao_fechar(self):
        if self.conn_despesas:
            self.conn_despesas.close()
        if self.conn_receitas:
            self.conn_receitas.close()
        self.root.destroy()


def iniciar_relatorio_balanco(parent_root):
    relatorio_window = tk.Toplevel(parent_root)
    app = RelatorioBalancoMensalApp(relatorio_window)
    relatorio_window.grab_set()


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Janela Principal (Teste)")
    # ttk.Button(root, text="Abrir Relatório de Balanço",
    #            command=lambda: iniciar_relatorio_balanco(root)).pack(padx=50, pady=50)
    root.mainloop()
