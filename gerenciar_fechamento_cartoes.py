import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

class GerenciadorFechamentoCartoes:
    def __init__(self, parent):
        self.root = tk.Toplevel(parent)
        self.root.title("Gerenciar Fechamento de Faturas de Cartões")
        self.root.geometry("650x450")
        self.root.resizable(False, False)
        self.root.transient(parent)
        self.root.grab_set()

        # Variáveis
        self.id_fechamento = tk.StringVar() # Para armazenar o ID do item selecionado para edição/exclusão
        self.meio_pagamento_cartao = tk.StringVar()
        self.data_fechamento = tk.IntVar(value=1) # Dia do mês (1-31)

        # Conexão com o banco de dados
        self.db_conn = sqlite3.connect('financas.db')
        self.db_cursor = self.db_conn.cursor()
        self.criar_tabela_fechamento_cartoes()

        self.criar_widgets()
        self.carregar_fechamentos_cadastrados()

    def criar_tabela_fechamento_cartoes(self):
        """Cria a tabela 'fechamento_cartoes' se ela não existir."""
        try:
            self.db_cursor.execute('''
                CREATE TABLE IF NOT EXISTS fechamento_cartoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meio_pagamento TEXT NOT NULL UNIQUE,
                    data_fechamento INTEGER NOT NULL,
                    FOREIGN KEY (meio_pagamento) REFERENCES meios_pagamento(nome) 
                        ON DELETE CASCADE ON UPDATE CASCADE 
                )
            ''')
            # Adicionando ON DELETE CASCADE e ON UPDATE CASCADE para manter a integridade
            # se um meio de pagamento for alterado ou removido da tabela principal.
            self.db_conn.commit()
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Não foi possível criar a tabela de fechamento de cartões: {e}", parent=self.root)

    def carregar_meios_pagamento_tipo_cartao(self):
        """Carrega apenas meios de pagamento que contenham 'Cartão' no nome."""
        try:
            self.db_cursor.execute("SELECT nome FROM meios_pagamento ORDER BY nome")
            todos_meios = self.db_cursor.fetchall()
            # Filtra para incluir apenas os que contêm "cartão" (case-insensitive)
            meios_cartao = [meio[0] for meio in todos_meios if "cartão" in meio[0].lower()]
            return meios_cartao
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Leitura", f"Não foi possível carregar os meios de pagamento: {e}", parent=self.root)
            return []

    def criar_widgets(self):
        # --- Frame do Formulário ---
        frame_form = ttk.LabelFrame(self.root, text="Cadastrar Data de Fechamento", padding=(10, 10))
        frame_form.pack(padx=10, pady=10, fill="x")

        # Meio de Pagamento (Cartão)
        ttk.Label(frame_form, text="Cartão:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.combo_meios_cartao = ttk.Combobox(frame_form, textvariable=self.meio_pagamento_cartao, state="readonly", width=30)
        self.combo_meios_cartao['values'] = self.carregar_meios_pagamento_tipo_cartao()
        self.combo_meios_cartao.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Data de Fechamento (Dia do Mês)
        ttk.Label(frame_form, text="Dia do Fechamento:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.spin_data_fechamento = ttk.Spinbox(frame_form, from_=1, to=31, textvariable=self.data_fechamento, width=5)
        self.spin_data_fechamento.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # --- Frame dos Botões ---
        frame_botoes = ttk.Frame(self.root)
        frame_botoes.pack(padx=10, pady=5, fill="x")

        ttk.Button(frame_botoes, text="Salvar", command=self.salvar_fechamento).pack(side="left", padx=5)
        ttk.Button(frame_botoes, text="Excluir", command=self.excluir_fechamento).pack(side="left", padx=5)
        ttk.Button(frame_botoes, text="Limpar", command=self.limpar_campos).pack(side="left", padx=5)

        # --- Frame da Tabela (Treeview) ---
        frame_tabela = ttk.LabelFrame(self.root, text="Fechamentos Cadastrados", padding=(10, 10))
        frame_tabela.pack(padx=10, pady=10, fill="both", expand=True)

        self.tabela = ttk.Treeview(frame_tabela, columns=('id', 'cartao', 'dia_fechamento'), show='headings')
        self.tabela.heading('id', text='ID')
        self.tabela.heading('cartao', text='Meio de Pagamento (Cartão)')
        self.tabela.heading('dia_fechamento', text='Dia do Fechamento')

        self.tabela.column('id', width=50, anchor="center", stretch=tk.NO)
        self.tabela.column('cartao', width=300)
        self.tabela.column('dia_fechamento', width=150, anchor="center")
        
        scrollbar = ttk.Scrollbar(frame_tabela, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        self.tabela.pack(side="left", fill="both", expand=True)

        self.tabela.bind('<ButtonRelease-1>', self.selecionar_item_tabela)

    def carregar_fechamentos_cadastrados(self):
        for item in self.tabela.get_children():
            self.tabela.delete(item)
        
        try:
            self.db_cursor.execute("SELECT id, meio_pagamento, data_fechamento FROM fechamento_cartoes ORDER BY meio_pagamento")
            for row in self.db_cursor.fetchall():
                self.tabela.insert('', 'end', values=row)
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Leitura", f"Não foi possível carregar os fechamentos cadastrados: {e}", parent=self.root)

    def salvar_fechamento(self):
        cartao = self.meio_pagamento_cartao.get()
        dia_fechamento = self.data_fechamento.get()

        if not cartao:
            messagebox.showwarning("Campo Vazio", "Por favor, selecione um cartão.", parent=self.root)
            return
        if not (1 <= dia_fechamento <= 31):
            messagebox.showwarning("Valor Inválido", "O dia do fechamento deve ser entre 1 e 31.", parent=self.root)
            return
        
        try:
            # Verifica se já existe configuração para este cartão para decidir entre INSERT e UPDATE
            # Se self.id_fechamento.get() tiver um valor, é uma atualização de um item selecionado.
            # Se não, verificamos se o cartão já existe para novo cadastro.
            id_atual = self.id_fechamento.get()

            if id_atual: # Atualizando um item existente selecionado na tabela
                self.db_cursor.execute("UPDATE fechamento_cartoes SET meio_pagamento = ?, data_fechamento = ? WHERE id = ?",
                                       (cartao, dia_fechamento, id_atual))
                messagebox.showinfo("Sucesso", "Configuração de fechamento atualizada!", parent=self.root)
            else: # Tentando salvar um novo ou um que sobrescreva pelo nome do cartão
                self.db_cursor.execute("SELECT id FROM fechamento_cartoes WHERE meio_pagamento = ?", (cartao,))
                registro_existente = self.db_cursor.fetchone()
                if registro_existente:
                    # Atualiza o registro existente baseado no nome do cartão
                    self.db_cursor.execute("UPDATE fechamento_cartoes SET data_fechamento = ? WHERE meio_pagamento = ?", (dia_fechamento, cartao))
                    messagebox.showinfo("Sucesso", "Configuração de fechamento atualizada para o cartão!", parent=self.root)
                else:
                    # Insere um novo registro
                    self.db_cursor.execute("INSERT INTO fechamento_cartoes (meio_pagamento, data_fechamento) VALUES (?, ?)",
                                           (cartao, dia_fechamento))
                    messagebox.showinfo("Sucesso", "Configuração de fechamento salva!", parent=self.root)
            
            self.db_conn.commit()
        except sqlite3.IntegrityError: # Caso tente inserir um cartão que já existe (UNIQUE constraint)
             # Isso pode acontecer se o ID não estiver setado e o usuário tentar salvar um cartão já na lista
             # A lógica acima já tenta tratar isso com SELECT e UPDATE, mas como fallback:
            self.db_cursor.execute("UPDATE fechamento_cartoes SET data_fechamento = ? WHERE meio_pagamento = ?", (dia_fechamento, cartao))
            self.db_conn.commit()
            messagebox.showinfo("Sucesso", "Configuração de fechamento atualizada para o cartão existente!", parent=self.root)

        except sqlite3.Error as e:
            messagebox.showerror("Erro ao Salvar", f"Ocorreu um erro: {e}", parent=self.root)
        finally:
            self.limpar_campos()
            self.carregar_fechamentos_cadastrados()


    def excluir_fechamento(self):
        id_selecionado = self.id_fechamento.get()
        if not id_selecionado: # Verifica se um ID foi carregado no campo (após seleção na tabela)
            messagebox.showwarning("Nenhuma Seleção", "Por favor, selecione um item na lista para excluir.", parent=self.root)
            return

        confirmar = messagebox.askyesno("Confirmar Exclusão", "Tem certeza que deseja excluir esta configuração de fechamento?", parent=self.root)
        if not confirmar:
            return
            
        try:
            self.db_cursor.execute("DELETE FROM fechamento_cartoes WHERE id = ?", (id_selecionado,))
            self.db_conn.commit()
            
            messagebox.showinfo("Sucesso", "Configuração de fechamento excluída!", parent=self.root)
        except sqlite3.Error as e:
            messagebox.showerror("Erro ao Excluir", f"Ocorreu um erro: {e}", parent=self.root)
        finally:
            self.limpar_campos()
            self.carregar_fechamentos_cadastrados()

    def selecionar_item_tabela(self, event):
        item_selecionado = self.tabela.selection()
        if not item_selecionado:
            return
        
        item_values = self.tabela.item(item_selecionado, 'values')
        
        self.id_fechamento.set(item_values[0])
        self.meio_pagamento_cartao.set(item_values[1])
        self.data_fechamento.set(int(item_values[2]))

    def limpar_campos(self):
        self.id_fechamento.set("")
        self.combo_meios_cartao.set("") # Limpa a seleção do combobox
        self.data_fechamento.set(1) # Reseta para o valor padrão
        if self.tabela.selection(): # Remove a seleção visual da tabela
            self.tabela.selection_remove(self.tabela.selection()[0])


    def __del__(self):
        if self.db_conn:
            self.db_conn.close()

# Função para ser chamada pelo programa principal
def iniciar_gerenciador_fechamento_cartoes(parent):
    GerenciadorFechamentoCartoes(parent)