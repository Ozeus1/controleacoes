import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import os

class GerenciadorConfiguracoes:
    def __init__(self, root=None, standalone=False):
        """
        Inicializa o gerenciador de configurações.
        
        Args:
            root: Janela raiz do Tkinter (se não for fornecida, cria uma nova)
            standalone: Indica se é uma execução independente ou chamada de outro módulo
        """
        self.standalone = standalone
        
        if root is None:
            self.root = tk.Tk()
            self.root.title("Configurações do Sistema Financeiro")
            self.root.geometry("800x600")
            self.root.resizable(True, True)
        else:
            self.root = tk.Toplevel(root)
            self.root.title("Configurações do Sistema Financeiro")
            self.root.geometry("800x600")
            self.root.resizable(True, True)
            self.root.transient(root)
            self.root.grab_set()
        
        # Cores e estilo
        self.cor_primaria = "#4CAF50"  # Verde
        self.cor_secundaria = "#F0F4C3"  # Verde claro
        self.cor_fundo = "#F9F9F9"  # Quase branco
        self.cor_texto = "#333333"  # Cinza escuro
        
        # Configurar estilo
        self.configurar_estilo()
        
        # Conectar ao banco de dados
        self.conectar_banco_dados()
        
        # Criar a interface
        self.criar_interface()
        
        # Carregar dados iniciais
        self.carregar_meios_pagamento()
        self.carregar_categorias()
        
        if standalone:
            self.root.mainloop()
    
    def configurar_estilo(self):
        """Configura o estilo visual do aplicativo"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configurar estilo para botões
        style.configure('TButton', 
                        background=self.cor_primaria, 
                        foreground='white', 
                        font=('Arial', 10, 'bold'),
                        padding=5)
        
        # Configurar estilo para labels
        style.configure('TLabel', 
                        background=self.cor_fundo, 
                        foreground=self.cor_texto,
                        font=('Arial', 10))
        
        # Configurar estilo para entradas
        style.configure('TEntry', 
                        fieldbackground='white',
                        font=('Arial', 10))
        
        # Configurar estilo para frame
        style.configure('TFrame', background=self.cor_fundo)
        
        # Configurar estilo para treeview (tabela)
        style.configure('Treeview', 
                        background='white',
                        fieldbackground='white',
                        font=('Arial', 9))
        
        style.configure('Treeview.Heading', 
                        font=('Arial', 10, 'bold'),
                        background=self.cor_secundaria)
    
    def conectar_banco_dados(self):
        """Conecta ao banco de dados SQLite"""
        try:
            self.conn = sqlite3.connect('financas.db')
            self.cursor = self.conn.cursor()
            
            # Verificar se as tabelas necessárias existem
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS meios_pagamento (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL UNIQUE
                )
            ''')
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS categorias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL UNIQUE
                )
            ''')
            
            self.conn.commit()
            
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Não foi possível conectar ao banco de dados: {e}")
    
    def criar_interface(self):
        """Cria a interface gráfica do gerenciador de configurações"""
        # Criar notebook (abas)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Aba de Meios de Pagamento
        self.aba_meios_pagamento = ttk.Frame(notebook)
        notebook.add(self.aba_meios_pagamento, text="Meios de Pagamento")
        self.criar_aba_meios_pagamento()
        
        # Aba de Categorias
        self.aba_categorias = ttk.Frame(notebook)
        notebook.add(self.aba_categorias, text="Categorias")
        self.criar_aba_categorias()
        
        # Botão para fechar (apenas no modo standalone)
        if not self.standalone:
            btn_fechar = ttk.Button(self.root, text="Fechar", command=self.root.destroy)
            btn_fechar.pack(pady=10)
    
    def criar_aba_meios_pagamento(self):
        """Cria os elementos da aba de meios de pagamento"""
        # Frame principal dividido em duas partes
        frame_principal = ttk.Frame(self.aba_meios_pagamento)
        frame_principal.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Frame esquerdo (formulário)
        frame_form = ttk.Frame(frame_principal)
        frame_form.pack(side=tk.LEFT, fill=tk.BOTH, padx=10, pady=10)
        
        # Frame direito (tabela)
        frame_tabela = ttk.Frame(frame_principal)
        frame_tabela.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Elementos do formulário
        ttk.Label(frame_form, text="Gerenciar Meios de Pagamento", 
                 font=('Arial', 12, 'bold')).grid(row=0, column=0, columnspan=2, pady=10, sticky=tk.W)
        
        # ID (Oculto)
        self.id_meio_pagamento = tk.StringVar()
        ttk.Label(frame_form, text="ID:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(frame_form, textvariable=self.id_meio_pagamento, state='readonly', width=5).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Nome do meio de pagamento
        self.nome_meio_pagamento = tk.StringVar()
        ttk.Label(frame_form, text="Nome:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(frame_form, textvariable=self.nome_meio_pagamento, width=30).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Botões de ação
        frame_botoes = ttk.Frame(frame_form)
        frame_botoes.grid(row=3, column=0, columnspan=2, pady=10)
        
        ttk.Button(frame_botoes, text="Adicionar", 
                  command=self.adicionar_meio_pagamento).grid(row=0, column=0, padx=5)
        
        self.btn_atualizar_meio = ttk.Button(frame_botoes, text="Atualizar", 
                                           command=self.atualizar_meio_pagamento, state='disabled')
        self.btn_atualizar_meio.grid(row=0, column=1, padx=5)
        
        self.btn_excluir_meio = ttk.Button(frame_botoes, text="Excluir", 
                                         command=self.excluir_meio_pagamento, state='disabled')
        self.btn_excluir_meio.grid(row=0, column=2, padx=5)
        
        ttk.Button(frame_botoes, text="Limpar", 
                  command=self.limpar_campos_meio).grid(row=0, column=3, padx=5)
        
        # Tabela de meios de pagamento
        ttk.Label(frame_tabela, text="Meios de Pagamento Cadastrados", 
                 font=('Arial', 12, 'bold')).pack(pady=10, anchor=tk.W)
        
        # Frame para a tabela com scrollbar
        tree_frame = ttk.Frame(frame_tabela)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configurar tabela
        self.tabela_meios = ttk.Treeview(tree_frame, yscrollcommand=scrollbar.set)
        self.tabela_meios['columns'] = ('id', 'nome')
        
        # Formatação das colunas
        self.tabela_meios.column('#0', width=0, stretch=tk.NO)
        self.tabela_meios.column('id', anchor=tk.CENTER, width=50)
        self.tabela_meios.column('nome', anchor=tk.W, width=250)
        
        # Cabeçalhos
        self.tabela_meios.heading('#0', text='', anchor=tk.CENTER)
        self.tabela_meios.heading('id', text='ID', anchor=tk.CENTER)
        self.tabela_meios.heading('nome', text='Nome', anchor=tk.CENTER)
        
        # Posicionar tabela e conectar scrollbar
        self.tabela_meios.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tabela_meios.yview)
        
        # Vincular evento de seleção
        self.tabela_meios.bind("<ButtonRelease-1>", self.selecionar_meio_pagamento)
    
    def criar_aba_categorias(self):
        """Cria os elementos da aba de categorias"""
        # Frame principal dividido em duas partes
        frame_principal = ttk.Frame(self.aba_categorias)
        frame_principal.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Frame esquerdo (formulário)
        frame_form = ttk.Frame(frame_principal)
        frame_form.pack(side=tk.LEFT, fill=tk.BOTH, padx=10, pady=10)
        
        # Frame direito (tabela)
        frame_tabela = ttk.Frame(frame_principal)
        frame_tabela.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Elementos do formulário
        ttk.Label(frame_form, text="Gerenciar Categorias", 
                 font=('Arial', 12, 'bold')).grid(row=0, column=0, columnspan=2, pady=10, sticky=tk.W)
        
        # ID (Oculto)
        self.id_categoria = tk.StringVar()
        ttk.Label(frame_form, text="ID:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(frame_form, textvariable=self.id_categoria, state='readonly', width=5).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Nome da categoria
        self.nome_categoria = tk.StringVar()
        ttk.Label(frame_form, text="Nome:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(frame_form, textvariable=self.nome_categoria, width=30).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Botões de ação
        frame_botoes = ttk.Frame(frame_form)
        frame_botoes.grid(row=3, column=0, columnspan=2, pady=10)
        
        ttk.Button(frame_botoes, text="Adicionar", 
                  command=self.adicionar_categoria).grid(row=0, column=0, padx=5)
        
        self.btn_atualizar_cat = ttk.Button(frame_botoes, text="Atualizar", 
                                           command=self.atualizar_categoria, state='disabled')
        self.btn_atualizar_cat.grid(row=0, column=1, padx=5)
        
        self.btn_excluir_cat = ttk.Button(frame_botoes, text="Excluir", 
                                         command=self.excluir_categoria, state='disabled')
        self.btn_excluir_cat.grid(row=0, column=2, padx=5)
        
        ttk.Button(frame_botoes, text="Limpar", 
                  command=self.limpar_campos_categoria).grid(row=0, column=3, padx=5)
        
        # Tabela de categorias
        ttk.Label(frame_tabela, text="Categorias Cadastradas", 
                 font=('Arial', 12, 'bold')).pack(pady=10, anchor=tk.W)
        
        # Frame para a tabela com scrollbar
        tree_frame = ttk.Frame(frame_tabela)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configurar tabela
        self.tabela_categorias = ttk.Treeview(tree_frame, yscrollcommand=scrollbar.set)
        self.tabela_categorias['columns'] = ('id', 'nome')
        
        # Formatação das colunas
        self.tabela_categorias.column('#0', width=0, stretch=tk.NO)
        self.tabela_categorias.column('id', anchor=tk.CENTER, width=50)
        self.tabela_categorias.column('nome', anchor=tk.W, width=250)
        
        # Cabeçalhos
        self.tabela_categorias.heading('#0', text='', anchor=tk.CENTER)
        self.tabela_categorias.heading('id', text='ID', anchor=tk.CENTER)
        self.tabela_categorias.heading('nome', text='Nome', anchor=tk.CENTER)
        
        # Posicionar tabela e conectar scrollbar
        self.tabela_categorias.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tabela_categorias.yview)
        
        # Vincular evento de seleção
        self.tabela_categorias.bind("<ButtonRelease-1>", self.selecionar_categoria)
        
    # ======= MÉTODOS PARA MEIOS DE PAGAMENTO =======
    
    def carregar_meios_pagamento(self):
        """Carrega os meios de pagamento na tabela"""
        # Limpar tabela atual
        for item in self.tabela_meios.get_children():
            self.tabela_meios.delete(item)
            
        try:
            # Buscar todos os meios de pagamento
            self.cursor.execute("SELECT id, nome FROM meios_pagamento ORDER BY nome")
            meios = self.cursor.fetchall()
            
            # Inserir na tabela
            for meio in meios:
                self.tabela_meios.insert('', tk.END, values=meio)
                
        except sqlite3.Error as e:
            messagebox.showerror("Erro ao Carregar Dados", f"Ocorreu um erro: {e}")
    
    def adicionar_meio_pagamento(self):
        """Adiciona um novo meio de pagamento ao banco de dados"""
        nome = self.nome_meio_pagamento.get().strip()
        
        if not nome:
            messagebox.showwarning("Dados Incompletos", "Por favor, informe o nome do meio de pagamento.")
            return
        
        try:
            self.cursor.execute("INSERT INTO meios_pagamento (nome) VALUES (?)", (nome,))
            self.conn.commit()
            
            messagebox.showinfo("Sucesso", "Meio de pagamento adicionado com sucesso!")
            self.limpar_campos_meio()
            self.carregar_meios_pagamento()
            
        except sqlite3.IntegrityError:
            messagebox.showerror("Erro", "Este meio de pagamento já existe!")
            
        except sqlite3.Error as e:
            messagebox.showerror("Erro ao Salvar", f"Ocorreu um erro: {e}")
    
    def atualizar_meio_pagamento1(self):
        """Atualiza um meio de pagamento existente"""
        id_meio = self.id_meio_pagamento.get()
        nome = self.nome_meio_pagamento.get().strip()
        
        if not id_meio or not nome:
            messagebox.showwarning("Dados Incompletos", "Por favor, selecione um meio de pagamento.")
            return
        
        try:
            self.cursor.execute("UPDATE meios_pagamento SET nome = ? WHERE id = ?", (nome, id_meio))
            self.conn.commit()
            
            messagebox.showinfo("Sucesso", "Meio de pagamento atualizado com sucesso!")
            self.limpar_campos_meio()
            self.carregar_meios_pagamento()
            
        except sqlite3.IntegrityError:
            messagebox.showerror("Erro", "Este nome já está em uso por outro meio de pagamento!")
            
        except sqlite3.Error as e:
            messagebox.showerror("Erro ao Atualizar", f"Ocorreu um erro: {e}")
    
    
    # Em configuracao.py, substitua a função inteira por esta:

    def atualizar_meio_pagamento(self):
        """
        Atualiza um meio de pagamento existente, garantindo a consistência
        dos dados ao atualizar também os registros na tabela de despesas.
        """
        id_meio = self.id_meio_pagamento.get()
        novo_nome = self.nome_meio_pagamento.get().strip()

        if not id_meio or not novo_nome:
            messagebox.showwarning("Dados Incompletos", 
                                "Por favor, selecione um meio de pagamento e forneça um novo nome.", 
                                parent=self.root)
            return

        try:
            # 1. Buscar o nome antigo antes de qualquer alteração.
            self.cursor.execute("SELECT nome FROM meios_pagamento WHERE id = ?", (id_meio,))
            resultado = self.cursor.fetchone()
            if not resultado:
                messagebox.showerror("Erro", "Meio de pagamento não encontrado.", parent=self.root)
                return
            nome_antigo = resultado[0]

            # Se o nome não mudou, não há nada a fazer.
            if nome_antigo == novo_nome:
                messagebox.showinfo("Informação", "O nome não foi alterado.", parent=self.root)
                return

            # 2. Atualizar o nome na tabela principal 'meios_pagamento'.
            self.cursor.execute("UPDATE meios_pagamento SET nome = ? WHERE id = ?", (novo_nome, id_meio))

            # 3. (PASSO CRÍTICO) Atualizar todos os registros na tabela 'despesas' que usavam o nome antigo.
            self.cursor.execute("UPDATE despesas SET meio_pagamento = ? WHERE meio_pagamento = ?", (novo_nome, nome_antigo))
            
            # 4. Confirmar todas as alterações no banco de dados.
            self.conn.commit()
            
            messagebox.showinfo("Sucesso", 
                                f"Meio de pagamento '{nome_antigo}' foi atualizado para '{novo_nome}' com sucesso em todos os registros.",
                                parent=self.root)
            self.limpar_campos_meio()
            self.carregar_meios_pagamento()
            
        except sqlite3.IntegrityError:
            messagebox.showerror("Erro de Integridade", 
                                f"O nome '{novo_nome}' já está em uso por outro meio de pagamento!",
                                parent=self.root)
            self.conn.rollback() # Desfaz a alteração se houver erro
            
        except sqlite3.Error as e:
            messagebox.showerror("Erro ao Atualizar", f"Ocorreu um erro no banco de dados: {e}", parent=self.root)
            self.conn.rollback() # Desfaz a alteração se houver erro
        
    def excluir_meio_pagamento(self):
        """Exclui um meio de pagamento do banco de dados"""
        id_meio = self.id_meio_pagamento.get()
        
        if not id_meio:
            messagebox.showwarning("Seleção Necessária", "Por favor, selecione um meio de pagamento para excluir.")
            return
        
        
        
        
        
        # Verificar se o meio de pagamento está em uso
        try:
            self.cursor.execute("SELECT COUNT(*) FROM despesas WHERE meio_pagamento = (SELECT nome FROM meios_pagamento WHERE id = ?)", (id_meio,))
            count = self.cursor.fetchone()[0]
            
            if count > 0:
                messagebox.showwarning("Não é Possível Excluir", 
                                     f"Este meio de pagamento está sendo usado em {count} registros de despesas.")
                return
            
            # Confirmar exclusão
            confirmar = messagebox.askyesno("Confirmar Exclusão", 
                                          "Tem certeza que deseja excluir este meio de pagamento?")
            
            if confirmar:
                self.cursor.execute("DELETE FROM meios_pagamento WHERE id = ?", (id_meio,))
                self.conn.commit()
                
                messagebox.showinfo("Sucesso", "Meio de pagamento excluído com sucesso!")
                self.limpar_campos_meio()
                self.carregar_meios_pagamento()
                
        except sqlite3.Error as e:
            messagebox.showerror("Erro ao Excluir", f"Ocorreu um erro: {e}")
    
    def selecionar_meio_pagamento(self, evento):
        """Seleciona um meio de pagamento da tabela"""
        try:
            # Obter o item selecionado
            selecao = self.tabela_meios.selection()[0]
            valores = self.tabela_meios.item(selecao, 'values')
            
            # Preencher formulário
            self.id_meio_pagamento.set(valores[0])
            self.nome_meio_pagamento.set(valores[1])
            
            # Habilitar botões
            self.btn_atualizar_meio['state'] = 'normal'
            self.btn_excluir_meio['state'] = 'normal'
            
        except IndexError:
            pass  # Nenhum item selecionado
    
    def limpar_campos_meio(self):
        """Limpa os campos do formulário de meio de pagamento"""
        self.id_meio_pagamento.set('')
        self.nome_meio_pagamento.set('')
        self.btn_atualizar_meio['state'] = 'disabled'
        self.btn_excluir_meio['state'] = 'disabled'
        
    # ======= MÉTODOS PARA CATEGORIAS =======
    
    def carregar_categorias(self):
        """Carrega as categorias na tabela"""
        # Limpar tabela atual
        for item in self.tabela_categorias.get_children():
            self.tabela_categorias.delete(item)
            
        try:
            # Buscar todas as categorias
            self.cursor.execute("SELECT id, nome FROM categorias ORDER BY nome")
            categorias = self.cursor.fetchall()
            
            # Inserir na tabela
            for categoria in categorias:
                self.tabela_categorias.insert('', tk.END, values=categoria)
                
        except sqlite3.Error as e:
            messagebox.showerror("Erro ao Carregar Dados", f"Ocorreu um erro: {e}")
    
    def adicionar_categoria(self):
        """Adiciona uma nova categoria ao banco de dados"""
        nome = self.nome_categoria.get().strip()
        
        if not nome:
            messagebox.showwarning("Dados Incompletos", "Por favor, informe o nome da categoria.")
            return
        
        try:
            self.cursor.execute("INSERT INTO categorias (nome) VALUES (?)", (nome,))
            self.conn.commit()
            
            messagebox.showinfo("Sucesso", "Categoria adicionada com sucesso!")
            self.limpar_campos_categoria()
            self.carregar_categorias()
            
        except sqlite3.IntegrityError:
            messagebox.showerror("Erro", "Esta categoria já existe!")
            
        except sqlite3.Error as e:
            messagebox.showerror("Erro ao Salvar", f"Ocorreu um erro: {e}")
    
    def atualizar_categoria1(self):
        """Atualiza uma categoria existente"""
        id_categoria = self.id_categoria.get()
        nome = self.nome_categoria.get().strip()
        
        if not id_categoria or not nome:
            messagebox.showwarning("Dados Incompletos", "Por favor, selecione uma categoria.")
            return
        
        try:
            self.cursor.execute("UPDATE categorias SET nome = ? WHERE id = ?", (nome, id_categoria))
            self.conn.commit()
            
            messagebox.showinfo("Sucesso", "Categoria atualizada com sucesso!")
            self.limpar_campos_categoria()
            self.carregar_categorias()
            
        except sqlite3.IntegrityError:
            messagebox.showerror("Erro", "Este nome já está em uso por outra categoria!")
            
        except sqlite3.Error as e:
            messagebox.showerror("Erro ao Atualizar", f"Ocorreu um erro: {e}")
   ###############################
   
   
   # Em configuracao.py, substitua a função inteira por esta:

    def atualizar_categoria(self):
        """
        Atualiza uma categoria de despesa existente, garantindo a consistência
        dos dados ao atualizar também os registros na tabela de despesas.
        """
        id_categoria = self.id_categoria.get()
        novo_nome = self.nome_categoria.get().strip()

        if not id_categoria or not novo_nome:
            messagebox.showwarning("Dados Incompletos",
                                "Por favor, selecione uma categoria e forneça um novo nome.",
                                parent=self.root)
            return

        try:
            # 1. Buscar o nome antigo antes de qualquer alteração.
            self.cursor.execute("SELECT nome FROM categorias WHERE id = ?", (id_categoria,))
            resultado = self.cursor.fetchone()
            if not resultado:
                messagebox.showerror("Erro", "Categoria não encontrada.", parent=self.root)
                return
            nome_antigo = resultado[0]

            # Se o nome não mudou, não há nada a fazer.
            if nome_antigo == novo_nome:
                messagebox.showinfo("Informação", "O nome não foi alterado.", parent=self.root)
                return

            # 2. Atualizar o nome na tabela principal 'categorias'.
            self.cursor.execute("UPDATE categorias SET nome = ? WHERE id = ?", (novo_nome, id_categoria))

            # 3. (PASSO CRÍTICO) Atualizar todos os registros na tabela 'despesas' que usavam o nome antigo.
            self.cursor.execute("UPDATE despesas SET conta_despesa = ? WHERE conta_despesa = ?", (novo_nome, nome_antigo))
            
            # 4. Confirmar todas as alterações no banco de dados.
            self.conn.commit()
            
            messagebox.showinfo("Sucesso",
                                f"Categoria '{nome_antigo}' foi atualizada para '{novo_nome}' com sucesso em todos os registros.",
                                parent=self.root)
            self.limpar_campos_categoria()
            self.carregar_categorias()
            
        except sqlite3.IntegrityError:
            messagebox.showerror("Erro de Integridade",
                                f"O nome '{novo_nome}' já está em uso por outra categoria!",
                                parent=self.root)
            self.conn.rollback()  # Desfaz a alteração se houver erro
            
        except sqlite3.Error as e:
            messagebox.showerror("Erro ao Atualizar", f"Ocorreu um erro no banco de dados: {e}", parent=self.root)
            self.conn.rollback()  # Desfaz a alteração se houver erro
    
    
   
   ###################### 
    def excluir_categoria(self):
        """Exclui uma categoria do banco de dados"""
        id_categoria = self.id_categoria.get()
        
        if not id_categoria:
            messagebox.showwarning("Seleção Necessária", "Por favor, selecione uma categoria para excluir.")
            return
        
        # Verificar se a categoria está em uso
        try:
            self.cursor.execute("SELECT COUNT(*) FROM despesas WHERE conta_despesa = (SELECT nome FROM categorias WHERE id = ?)", (id_categoria,))
            count = self.cursor.fetchone()[0]
            
            if count > 0:
                messagebox.showwarning("Não é Possível Excluir", 
                                     f"Esta categoria está sendo usada em {count} registros de despesas.")
                return
            
            # Confirmar exclusão
            confirmar = messagebox.askyesno("Confirmar Exclusão", 
                                          "Tem certeza que deseja excluir esta categoria?")
            
            if confirmar:
                self.cursor.execute("DELETE FROM categorias WHERE id = ?", (id_categoria,))
                self.conn.commit()
                
                messagebox.showinfo("Sucesso", "Categoria excluída com sucesso!")
                self.limpar_campos_categoria()
                self.carregar_categorias()
                
        except sqlite3.Error as e:
            messagebox.showerror("Erro ao Excluir", f"Ocorreu um erro: {e}")
    
    def selecionar_categoria(self, evento):
        """Seleciona uma categoria da tabela"""
        try:
            # Obter o item selecionado
            selecao = self.tabela_categorias.selection()[0]
            valores = self.tabela_categorias.item(selecao, 'values')
            
            # Preencher formulário
            self.id_categoria.set(valores[0])
            self.nome_categoria.set(valores[1])
            
            # Habilitar botões
            self.btn_atualizar_cat['state'] = 'normal'
            self.btn_excluir_cat['state'] = 'normal'
            
        except IndexError:
            pass  # Nenhum item selecionado
    
    def limpar_campos_categoria(self):
        """Limpa os campos do formulário de categoria"""
        self.id_categoria.set('')
        self.nome_categoria.set('')
        self.btn_atualizar_cat['state'] = 'disabled'
        self.btn_excluir_cat['state'] = 'disabled'
    
    def __del__(self):
        """Destrutor da classe - fecha a conexão com o banco de dados"""
        if hasattr(self, 'conn'):
            self.conn.close()

# Função para executar o módulo como um programa independente
if __name__ == "__main__":
   app = GerenciadorConfiguracoes(standalone=True)

