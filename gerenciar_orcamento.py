import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

class GerenciadorOrcamento:
    """
    Interface gráfica para gerenciar a tabela de orçamentos,
    associando um valor orçado a uma conta de despesa (categoria).
    """
    def __init__(self, parent):
        # Configuração da janela principal (Toplevel)
        self.root = tk.Toplevel(parent)
        self.root.title("Gerenciar Orçamento por Categoria")
        self.root.geometry("600x450")
        self.root.resizable(False, False)
        # Garante que esta janela fique em foco
        self.root.transient(parent)
        self.root.grab_set()

        # Variáveis
        self.id_orcamento = tk.StringVar()
        self.conta_despesa = tk.StringVar()
        self.valor_orcado = tk.DoubleVar()

        # Conexão com o banco de dados e criação da tabela
        self.db_conn = sqlite3.connect('financas.db')
        self.db_cursor = self.db_conn.cursor()
        self.criar_tabela_orcamento()

        # Criação dos widgets da interface
        self.criar_widgets()
        self.carregar_orcamentos()

    def criar_tabela_orcamento(self):
        """
        Cria a tabela 'orcamento' no banco de dados se ela não existir.
        A tabela armazena o valor orçado para cada categoria.
        """
        try:
            self.db_cursor.execute('''
                CREATE TABLE IF NOT EXISTS orcamento (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conta_despesa TEXT NOT NULL UNIQUE,
                    valor_orcado REAL NOT NULL,
                    FOREIGN KEY (conta_despesa) REFERENCES categorias(nome)
                )
            ''')
            self.db_conn.commit()
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Não foi possível criar a tabela de orçamento: {e}", parent=self.root)

    def carregar_categorias_disponiveis(self):
        """Carrega as categorias da tabela 'categorias' para o Combobox."""
        try:
            self.db_cursor.execute("SELECT nome FROM categorias ORDER BY nome")
            return [row[0] for row in self.db_cursor.fetchall()]
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Leitura", f"Não foi possível carregar as categorias: {e}", parent=self.root)
            return []

    def criar_widgets(self):
        """Cria e posiciona os elementos gráficos na janela."""
        # --- Frame do Formulário ---
        frame_form = ttk.LabelFrame(self.root, text="Cadastrar Orçamento", padding=(10, 10))
        frame_form.pack(padx=10, pady=10, fill="x")

        # Categoria (Conta de Despesa)
        ttk.Label(frame_form, text="Categoria:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.combo_categorias = ttk.Combobox(frame_form, textvariable=self.conta_despesa, state="readonly", width=30)
        self.combo_categorias['values'] = self.carregar_categorias_disponiveis()
        self.combo_categorias.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Valor Orçado
        ttk.Label(frame_form, text="Valor Orçado (R$):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        entry_valor = ttk.Entry(frame_form, textvariable=self.valor_orcado, width=15)
        entry_valor.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # --- Frame dos Botões ---
        frame_botoes = ttk.Frame(self.root)
        frame_botoes.pack(padx=10, pady=5, fill="x")

        ttk.Button(frame_botoes, text="Salvar", command=self.salvar_orcamento).pack(side="left", padx=5)
        ttk.Button(frame_botoes, text="Excluir", command=self.excluir_orcamento).pack(side="left", padx=5)
        ttk.Button(frame_botoes, text="Limpar", command=self.limpar_campos).pack(side="left", padx=5)

        # --- Frame da Tabela (Treeview) ---
        frame_tabela = ttk.LabelFrame(self.root, text="Orçamentos Cadastrados", padding=(10, 10))
        frame_tabela.pack(padx=10, pady=10, fill="both", expand=True)

        self.tabela = ttk.Treeview(frame_tabela, columns=('id', 'categoria', 'valor'), show='headings')
        self.tabela.heading('id', text='ID')
        self.tabela.heading('categoria', text='Categoria')
        self.tabela.heading('valor', text='Valor Orçado (R$)')

        self.tabela.column('id', width=50, anchor="center")
        self.tabela.column('categoria', width=250)
        self.tabela.column('valor', width=150, anchor="e")
        
        # Adiciona a barra de rolagem
        scrollbar = ttk.Scrollbar(frame_tabela, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        self.tabela.pack(side="left", fill="both", expand=True)

        # Evento de clique para selecionar um item
        self.tabela.bind('<ButtonRelease-1>', self.selecionar_item)

    def carregar_orcamentos(self):
        """Carrega e exibe os dados da tabela 'orcamento' no Treeview."""
        # Limpa a tabela antes de carregar novos dados
        for item in self.tabela.get_children():
            self.tabela.delete(item)
        
        try:
            self.db_cursor.execute("SELECT id, conta_despesa, valor_orcado FROM orcamento ORDER BY conta_despesa")
            for row in self.db_cursor.fetchall():
                valor_formatado = f"R$ {row[2]:.2f}".replace('.', ',')
                self.tabela.insert('', 'end', values=(row[0], row[1], valor_formatado))
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Leitura", f"Não foi possível carregar os orçamentos: {e}", parent=self.root)

    def salvar_orcamento(self):
        """Salva um novo orçamento ou atualiza um existente."""
        categoria = self.conta_despesa.get()
        valor = self.valor_orcado.get()

        # Validação dos campos
        if not categoria:
            messagebox.showwarning("Campo Vazio", "Por favor, selecione uma categoria.", parent=self.root)
            return
        if valor <= 0:
            messagebox.showwarning("Valor Inválido", "O valor orçado deve ser maior que zero.", parent=self.root)
            return
        
        try:
            # Verifica se já existe um orçamento para esta categoria para decidir entre INSERT e UPDATE
            self.db_cursor.execute("SELECT id FROM orcamento WHERE conta_despesa = ?", (categoria,))
            registro_existente = self.db_cursor.fetchone()

            if registro_existente:
                # Atualiza o registro existente
                self.db_cursor.execute("UPDATE orcamento SET valor_orcado = ? WHERE conta_despesa = ?", (valor, categoria))
                messagebox.showinfo("Sucesso", "Orçamento atualizado com sucesso!", parent=self.root)
            else:
                # Insere um novo registro
                self.db_cursor.execute("INSERT INTO orcamento (conta_despesa, valor_orcado) VALUES (?, ?)", (categoria, valor))
                messagebox.showinfo("Sucesso", "Orçamento salvo com sucesso!", parent=self.root)
            
            self.db_conn.commit()
            self.limpar_campos()
            self.carregar_orcamentos()

        except sqlite3.Error as e:
            messagebox.showerror("Erro ao Salvar", f"Ocorreu um erro: {e}", parent=self.root)

    def excluir_orcamento(self):
        """Exclui um orçamento selecionado no Treeview."""
        item_selecionado = self.tabela.selection()
        if not item_selecionado:
            messagebox.showwarning("Nenhuma Seleção", "Por favor, selecione um orçamento na lista para excluir.", parent=self.root)
            return

        confirmar = messagebox.askyesno("Confirmar Exclusão", "Tem certeza que deseja excluir o orçamento selecionado?", parent=self.root)
        if not confirmar:
            return
            
        try:
            item_id = self.tabela.item(item_selecionado)['values'][0]
            self.db_cursor.execute("DELETE FROM orcamento WHERE id = ?", (item_id,))
            self.db_conn.commit()
            
            self.limpar_campos()
            self.carregar_orcamentos()
            messagebox.showinfo("Sucesso", "Orçamento excluído com sucesso!", parent=self.root)

        except sqlite3.Error as e:
            messagebox.showerror("Erro ao Excluir", f"Ocorreu um erro: {e}", parent=self.root)

    def selecionar_item(self, event):
        """Preenche o formulário quando um item do Treeview é clicado."""
        item_selecionado = self.tabela.selection()
        if not item_selecionado:
            return
        
        item = self.tabela.item(item_selecionado, 'values')
        
        self.id_orcamento.set(item[0])
        self.conta_despesa.set(item[1])
        
        # Converte o valor de "R$ 1.234,56" para um float 1234.56
        valor_str = item[2].replace('R$', '').strip().replace('.', '').replace(',', '.')
        self.valor_orcado.set(float(valor_str))

    def limpar_campos(self):
        """Limpa os campos de entrada do formulário."""
        self.id_orcamento.set("")
        self.combo_categorias.set("")
        self.valor_orcado.set(0.0)
        self.tabela.selection_remove(self.tabela.selection()) # Remove a seleção da tabela

# Função para ser chamada pelo programa principal
def iniciar_gerenciador_orcamento(parent):
    GerenciadorOrcamento(parent)