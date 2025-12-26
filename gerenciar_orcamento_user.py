import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

class GerenciadorOrcamento:
    """
    Interface gráfica para gerenciar a tabela de orçamentos,
    associando um valor orçado a uma categoria, de forma individual para cada usuário.
    """
    # ALTERADO: __init__ agora aceita user_id
    def __init__(self, parent, user_id):
        self.root = tk.Toplevel(parent)
        self.root.title("Gerenciar Orçamento por Categoria")
        self.root.geometry("600x450")
        self.root.resizable(False, False)
        self.root.transient(parent)
        self.root.grab_set()

        # ALTERADO: Armazena o ID do usuário logado
        self.user_id = user_id

        # Variáveis
        self.id_orcamento = tk.StringVar()
        self.conta_despesa = tk.StringVar()
        self.valor_orcado = tk.DoubleVar()

        self.db_conn = sqlite3.connect('financas.db')
        self.db_cursor = self.db_conn.cursor()
        self.criar_ou_migrar_tabela_orcamento()

        self.criar_widgets()
        self.carregar_orcamentos()

    def criar_ou_migrar_tabela_orcamento(self):
        """
        Cria a tabela 'orcamento' com suporte a múltiplos usuários ou
        migra a tabela existente para o novo formato.
        """
        try:
            # Verifica se a coluna user_id já existe
            self.db_cursor.execute("PRAGMA table_info(orcamento)")
            columns = [col[1] for col in self.db_cursor.fetchall()]
            
            if 'user_id' not in columns:
                # Se a coluna não existe, a tabela está no formato antigo.
                # Inicia o processo de migração.
                messagebox.showinfo("Atualização do Banco de Dados", 
                                    "Detectamos uma versão antiga da tabela de orçamentos. "
                                    "Ela será atualizada agora. Os orçamentos existentes serão atribuídos ao usuário admin.",
                                    parent=self.root)
                
                # Renomeia a tabela antiga
                self.db_cursor.execute("ALTER TABLE orcamento RENAME TO orcamento_old")
                
                # Cria a nova tabela com a estrutura correta
                self.db_cursor.execute('''
                    CREATE TABLE orcamento (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        conta_despesa TEXT NOT NULL,
                        valor_orcado REAL NOT NULL,
                        UNIQUE(user_id, conta_despesa),
                        FOREIGN KEY (conta_despesa) REFERENCES categorias(nome),
                        FOREIGN KEY (user_id) REFERENCES usuarios(id)
                    )
                ''')

                # Copia os dados da tabela antiga para a nova, atribuindo ao user_id 1 (admin)
                self.db_cursor.execute("""
                    INSERT INTO orcamento (id, user_id, conta_despesa, valor_orcado)
                    SELECT id, 1, conta_despesa, valor_orcado FROM orcamento_old
                """)
                
                # Remove a tabela antiga
                self.db_cursor.execute("DROP TABLE orcamento_old")
            else:
                # Se a coluna já existe, apenas garante que a tabela está criada
                self.db_cursor.execute('''
                    CREATE TABLE IF NOT EXISTS orcamento (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        conta_despesa TEXT NOT NULL,
                        valor_orcado REAL NOT NULL,
                        UNIQUE(user_id, conta_despesa),
                        FOREIGN KEY (conta_despesa) REFERENCES categorias(nome),
                        FOREIGN KEY (user_id) REFERENCES usuarios(id)
                    )
                ''')

            self.db_conn.commit()
        except sqlite3.Error as e:
            # Se a tabela 'orcamento' nem sequer existir, cria ela do zero.
            if "no such table: orcamento" in str(e):
                 self.db_cursor.execute('''
                    CREATE TABLE orcamento (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        conta_despesa TEXT NOT NULL,
                        valor_orcado REAL NOT NULL,
                        UNIQUE(user_id, conta_despesa),
                        FOREIGN KEY (conta_despesa) REFERENCES categorias(nome),
                        FOREIGN KEY (user_id) REFERENCES usuarios(id)
                    )
                ''')
                 self.db_conn.commit()
            else:
                messagebox.showerror("Erro de Banco de Dados", f"Não foi possível criar/migrar a tabela de orçamento: {e}", parent=self.root)

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
        frame_form = ttk.LabelFrame(self.root, text="Cadastrar Orçamento", padding=(10, 10))
        frame_form.pack(padx=10, pady=10, fill="x")

        ttk.Label(frame_form, text="Categoria:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.combo_categorias = ttk.Combobox(frame_form, textvariable=self.conta_despesa, state="readonly", width=30)
        self.combo_categorias['values'] = self.carregar_categorias_disponiveis()
        self.combo_categorias.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(frame_form, text="Valor Orçado (R$):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(frame_form, textvariable=self.valor_orcado, width=15).grid(row=1, column=1, padx=5, pady=5, sticky="w")

        frame_botoes = ttk.Frame(self.root)
        frame_botoes.pack(padx=10, pady=5, fill="x")

        ttk.Button(frame_botoes, text="Salvar / Atualizar", command=self.salvar_orcamento).pack(side="left", padx=5)
        ttk.Button(frame_botoes, text="Excluir", command=self.excluir_orcamento).pack(side="left", padx=5)
        ttk.Button(frame_botoes, text="Limpar", command=self.limpar_campos).pack(side="left", padx=5)

        frame_tabela = ttk.LabelFrame(self.root, text="Orçamentos Cadastrados por Você", padding=(10, 10))
        frame_tabela.pack(padx=10, pady=10, fill="both", expand=True)

        self.tabela = ttk.Treeview(frame_tabela, columns=('id', 'categoria', 'valor'), show='headings')
        self.tabela.heading('id', text='ID')
        self.tabela.heading('categoria', text='Categoria')
        self.tabela.heading('valor', text='Valor Orçado (R$)')
        self.tabela.column('id', width=50, anchor="center")
        self.tabela.column('categoria', width=250)
        self.tabela.column('valor', width=150, anchor="e")
        
        scrollbar = ttk.Scrollbar(frame_tabela, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tabela.pack(side="left", fill="both", expand=True)

        self.tabela.bind('<ButtonRelease-1>', self.selecionar_item)

    def carregar_orcamentos(self):
        """Carrega e exibe os orçamentos do usuário logado."""
        for item in self.tabela.get_children():
            self.tabela.delete(item)
        
        try:
            # ALTERADO: Filtra orçamentos pelo user_id
            self.db_cursor.execute("SELECT id, conta_despesa, valor_orcado FROM orcamento WHERE user_id = ? ORDER BY conta_despesa", (self.user_id,))
            for row in self.db_cursor.fetchall():
                valor_formatado = f"R$ {row[2]:.2f}".replace('.', ',')
                self.tabela.insert('', 'end', values=(row[0], row[1], valor_formatado))
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Leitura", f"Não foi possível carregar os orçamentos: {e}", parent=self.root)

    def salvar_orcamento(self):
        """Salva um novo orçamento ou atualiza um existente para o usuário logado."""
        categoria = self.conta_despesa.get()
        valor = self.valor_orcado.get()

        if not categoria:
            messagebox.showwarning("Campo Vazio", "Por favor, selecione uma categoria.", parent=self.root)
            return
        if valor <= 0:
            messagebox.showwarning("Valor Inválido", "O valor orçado deve ser maior que zero.", parent=self.root)
            return
        
        try:
            # ALTERADO: Verifica se já existe um orçamento para esta categoria E ESTE USUÁRIO
            self.db_cursor.execute("SELECT id FROM orcamento WHERE conta_despesa = ? AND user_id = ?", (categoria, self.user_id))
            registro_existente = self.db_cursor.fetchone()

            if registro_existente:
                # ALTERADO: Atualiza o registro existente para este usuário
                self.db_cursor.execute("UPDATE orcamento SET valor_orcado = ? WHERE conta_despesa = ? AND user_id = ?", (valor, categoria, self.user_id))
                messagebox.showinfo("Sucesso", "Orçamento atualizado com sucesso!", parent=self.root)
            else:
                # ALTERADO: Insere um novo registro com o user_id
                self.db_cursor.execute("INSERT INTO orcamento (conta_despesa, valor_orcado, user_id) VALUES (?, ?, ?)", (categoria, valor, self.user_id))
                messagebox.showinfo("Sucesso", "Orçamento salvo com sucesso!", parent=self.root)
            
            self.db_conn.commit()
            self.limpar_campos()
            self.carregar_orcamentos()

        except sqlite3.IntegrityError:
            # Este erro agora só deve acontecer se o usuário tentar adicionar a mesma categoria duas vezes.
            messagebox.showerror("Erro de Duplicidade", f"Você já definiu um orçamento para a categoria '{categoria}'.", parent=self.root)
        except sqlite3.Error as e:
            messagebox.showerror("Erro ao Salvar", f"Ocorreu um erro: {e}", parent=self.root)

    def excluir_orcamento(self):
        """Exclui um orçamento selecionado do usuário logado."""
        item_selecionado = self.tabela.selection()
        if not item_selecionado:
            messagebox.showwarning("Nenhuma Seleção", "Por favor, selecione um orçamento na lista para excluir.", parent=self.root)
            return

        confirmar = messagebox.askyesno("Confirmar Exclusão", "Tem certeza que deseja excluir o orçamento selecionado?", parent=self.root)
        if not confirmar:
            return
            
        try:
            item_id = self.tabela.item(item_selecionado)['values'][0]
            # ALTERADO: A exclusão agora também é segura, mas o principal é que a lista já é filtrada.
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
        
        valor_str = item[2].replace('R$', '').strip().replace('.', '').replace(',', '.')
        self.valor_orcado.set(float(valor_str))

    def limpar_campos(self):
        """Limpa os campos de entrada do formulário."""
        self.id_orcamento.set("")
        self.combo_categorias.set("")
        self.valor_orcado.set(0.0)
        # Garante que a seleção visual seja removida da tabela
        if self.tabela.selection():
            self.tabela.selection_remove(self.tabela.selection()[0])

# ALTERADO: A função de inicialização agora aceita e repassa o user_id
def iniciar_gerenciador_orcamento(parent, user_id):
    GerenciadorOrcamento(parent, user_id)