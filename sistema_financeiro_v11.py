#versão com controle de acesso. ainda não finlizado

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
from datetime import datetime, date
import calendar
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import FuncFormatter
import os
import locale
from tkcalendar import DateEntry
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter
from tkinter import filedialog
import hashlib # <--- ADICIONADO

# Tenta importar módulos locais, mas não quebra se não existirem
try:
    import configuracao
    import MENUBD_user
    import relclaude1_user
    import relatorios1_user
    import gerenciar_orcamento_user
    import relatorio_orcado_vs_gasto
    import gerenciar_fechamento_cartoes
    import relatorio_previsao_faturas_user
    import importador_excel_user
    import relatorio_balanco_user
    import relatorio_balanco_fluxo_caixa_user
    import importador_supabase_user
except ImportError:
    print("Aviso: Alguns módulos de extensão não foram encontrados. A funcionalidade completa pode estar limitada.")
    class PlaceholderModule:
        def __getattr__(self, name):
            def placeholder_func(*args, **kwargs):
                messagebox.showerror("Módulo Faltando", f"O módulo para esta função não foi encontrado.")
            return placeholder_func
    configuracao = MENUBD = relclaude1 = relatorios1 = gerenciar_orcamento = \
    relatorio_orcado_vs_gasto = gerenciar_fechamento_cartoes = \
    relatorio_previsao_faturas = importador_excel = relatorio_balanco = \
    relatorio_balanco_fluxo_caixa = importador_supabase = PlaceholderModule()

# Configurar a localização para formato de moeda brasileiro
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        print("Aviso: Locale 'pt_BR' não encontrado. A formatação de moeda pode não funcionar corretamente.")

# --- INÍCIO: NOVAS FUNÇÕES E CLASSES PARA GERENCIAMENTO DE USUÁRIOS ---

# --- FUNÇÕES DE SEGURANÇA ---
def hash_password(password):
    """Gera um hash SHA256 para a senha."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_password_hash, provided_password):
    """Verifica se a senha fornecida corresponde ao hash armazenado."""
    return stored_password_hash == hash_password(provided_password)

# --- FUNÇÃO DE SETUP DO BANCO DE DADOS DE USUÁRIOS ---
def setup_database_users():
    """Cria tabelas de usuário e migra dados existentes na primeira execução."""
    conn_despesas = sqlite3.connect('financas.db')
    cursor_despesas = conn_despesas.cursor()
    
    conn_receitas = sqlite3.connect('financas_receitas.db')
    cursor_receitas = conn_receitas.cursor()

    # ETAPA 1: Criar tabela de usuários se não existir
    cursor_despesas.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            expiration_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ETAPA 2: Verificar se a tabela de usuários está vazia para criar o admin padrão
    cursor_despesas.execute("SELECT COUNT(id) FROM usuarios")
    if cursor_despesas.fetchone()[0] == 0:
        hashed_pw = hash_password('admin')
        cursor_despesas.execute(
            "INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)",
            ('admin', hashed_pw, 'admin')
        )
        print("Usuário 'admin' padrão criado com a senha 'admin'.")

    # ETAPA 3: Migrar tabela de despesas (adicionar user_id)
    cursor_despesas.execute("PRAGMA table_info(despesas)")
    columns_despesas = [info[1] for info in cursor_despesas.fetchall()]
    if 'user_id' not in columns_despesas:
        cursor_despesas.execute("ALTER TABLE despesas ADD COLUMN user_id INTEGER REFERENCES usuarios(id)")
        # Atribui todos os registros existentes ao primeiro usuário (admin)
        cursor_despesas.execute("UPDATE despesas SET user_id = 1 WHERE user_id IS NULL")
        print("Tabela 'despesas' migrada com sucesso.")

    # ETAPA 4: Migrar tabela de receitas (adicionar user_id)
    cursor_receitas.execute("PRAGMA table_info(receitas)")
    columns_receitas = [info[1] for info in cursor_receitas.fetchall()]
    if 'user_id' not in columns_receitas:
        cursor_receitas.execute("ALTER TABLE receitas ADD COLUMN user_id INTEGER REFERENCES usuarios(id)")
        cursor_receitas.execute("UPDATE receitas SET user_id = 1 WHERE user_id IS NULL")
        print("Tabela 'receitas' migrada com sucesso.")

    conn_despesas.commit()
    conn_despesas.close()
    conn_receitas.commit()
    conn_receitas.close()

# --- CLASSE DA JANELA DE LOGIN ---
class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Login - Sistema Financeiro")
        self.geometry("350x200")
        self.resizable(False, False)
        
        self.conn = sqlite3.connect('financas.db')
        self.cursor = self.conn.cursor()

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()

        frame = ttk.Frame(self, padding="20")
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Usuário:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=self.username_var, width=30).grid(row=0, column=1, pady=5)

        ttk.Label(frame, text="Senha:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=self.password_var, show="*", width=30).grid(row=1, column=1, pady=5)
        
        ttk.Button(frame, text="Login", command=self.attempt_login).grid(row=2, column=0, columnspan=2, pady=20)
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.bind('<Return>', self.attempt_login)

    def on_closing(self):
        self.conn.close()
        self.destroy()

    def attempt_login(self, event=None):
        username = self.username_var.get()
        password = self.password_var.get()

        if not username or not password:
            messagebox.showerror("Erro", "Usuário e senha são obrigatórios.")
            return

        self.cursor.execute("SELECT id, password, role, expiration_date FROM usuarios WHERE username = ?", (username,))
        user_data = self.cursor.fetchone()

        if user_data:
            user_id, hashed_pw, role, expiration_date = user_data
            
            # Verificar senha
            if not verify_password(hashed_pw, password):
                messagebox.showerror("Erro de Login", "Usuário ou senha inválidos.")
                return
            
            # Verificar data de expiração para usuários comuns
            if role == 'user' and expiration_date:
                if datetime.strptime(expiration_date, '%Y-%m-%d').date() < date.today():
                    messagebox.showerror("Acesso Expirado", "Sua conta de usuário expirou. Contate o administrador.")
                    return
            
            # Login bem-sucedido
            self.conn.close()
            self.destroy()
            
            # Abre a aplicação principal
            root = tk.Tk()
            user_info = {'id': user_id, 'username': username, 'role': role}
            app = SistemaFinanceiro(root, user_info)
            root.mainloop()

        else:
            messagebox.showerror("Erro de Login", "Usuário ou senha inválidos.")

# --- CLASSE DE GERENCIAMENTO DE USUÁRIOS (SOMENTE ADMIN) ---
class UserManagementWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title("Gerenciamento de Usuários")
        self.geometry("800x500")

        self.conn = sqlite3.connect('financas.db')
        self.cursor = self.conn.cursor()

        # Frame principal
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Frame do formulário
        form_frame = ttk.LabelFrame(main_frame, text="Adicionar / Editar Usuário")
        form_frame.pack(fill=tk.X, pady=10)

        self.user_id = tk.StringVar()
        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.expiration_date = tk.StringVar()

        ttk.Label(form_frame, text="Usuário:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(form_frame, textvariable=self.username).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(form_frame, text="Senha:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        ttk.Entry(form_frame, textvariable=self.password).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(form_frame, text="Expira em (dd/mm/aaaa):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.date_entry = DateEntry(form_frame, width=12, date_pattern='dd/mm/yyyy', locale='pt_BR')
        self.date_entry.grid(row=1, column=1, padx=5, pady=5)
        self.date_entry.set_date(None) # Inicia sem data

        # Botões do formulário
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=2, column=0, columnspan=4, pady=10)
        ttk.Button(btn_frame, text="Adicionar", command=self.add_user).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Atualizar", command=self.update_user).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Limpar Campos", command=self.clear_fields).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Remover Data Exp.", command=self.remove_expiration).pack(side=tk.LEFT, padx=5)

        # Frame da lista de usuários
        list_frame = ttk.LabelFrame(main_frame, text="Usuários Cadastrados")
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(list_frame, columns=('id', 'username', 'role', 'expiration'), show='headings')
        self.tree.heading('id', text='ID')
        self.tree.heading('username', text='Usuário')
        self.tree.heading('role', text='Nível')
        self.tree.heading('expiration', text='Validade')
        self.tree.column('id', width=50, anchor='center')
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.bind('<<TreeviewSelect>>', self.select_user)
        
        # Botão de exclusão
        ttk.Button(main_frame, text="Excluir Usuário Selecionado", command=self.delete_user).pack(pady=10)
        
        self.load_users()

    def load_users(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.cursor.execute("SELECT id, username, role, expiration_date FROM usuarios ORDER BY username")
        for row in self.cursor.fetchall():
            exp_date = row[3]
            if exp_date:
                exp_date = datetime.strptime(exp_date, '%Y-%m-%d').strftime('%d/%m/%Y')
            else:
                exp_date = "Sem validade"
            self.tree.insert('', 'end', values=(row[0], row[1], row[2], exp_date))

    def clear_fields(self):
        self.user_id.set('')
        self.username.set('')
        self.password.set('')
        self.date_entry.set_date(None)
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection()[0])

    def select_user(self, event):
        selected_item = self.tree.focus()
        if not selected_item: return
        
        values = self.tree.item(selected_item, 'values')
        self.user_id.set(values[0])
        self.username.set(values[1])
        self.password.set('') # Limpa a senha por segurança
        
        exp_date_str = values[3]
        if exp_date_str != "Sem validade":
            self.date_entry.set_date(datetime.strptime(exp_date_str, '%d/%m/%Y'))
        else:
            self.date_entry.set_date(None)
            
    def add_user(self):
        username = self.username.get().strip()
        password = self.password.get().strip()
        exp_date = self.date_entry.get_date()
        
        if not username or not password:
            messagebox.showerror("Erro", "Usuário e senha são obrigatórios.", parent=self)
            return

        try:
            sql_date = exp_date.strftime('%Y-%m-%d') if exp_date else None
            hashed_pw = hash_password(password)
            self.cursor.execute(
                "INSERT INTO usuarios (username, password, role, expiration_date) VALUES (?, ?, 'user', ?)",
                (username, hashed_pw, sql_date)
            )
            self.conn.commit()
            messagebox.showinfo("Sucesso", "Usuário adicionado com sucesso!", parent=self)
            self.load_users()
            self.clear_fields()
        except sqlite3.IntegrityError:
            messagebox.showerror("Erro", "Este nome de usuário já existe.", parent=self)
        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro: {e}", parent=self)

    def update_user(self):
        user_id = self.user_id.get()
        if not user_id:
            messagebox.showerror("Erro", "Selecione um usuário para atualizar.", parent=self)
            return

        username = self.username.get().strip()
        password = self.password.get().strip()
        exp_date = self.date_entry.get_date()

        if not username:
            messagebox.showerror("Erro", "O nome de usuário não pode ser vazio.", parent=self)
            return
        
        try:
            sql_date = exp_date.strftime('%Y-%m-%d') if exp_date else None
            
            if password: # Atualiza a senha apenas se uma nova for fornecida
                hashed_pw = hash_password(password)
                self.cursor.execute(
                    "UPDATE usuarios SET username = ?, password = ?, expiration_date = ? WHERE id = ?",
                    (username, hashed_pw, sql_date, user_id)
                )
            else: # Mantém a senha antiga
                self.cursor.execute(
                    "UPDATE usuarios SET username = ?, expiration_date = ? WHERE id = ?",
                    (username, sql_date, user_id)
                )
            
            self.conn.commit()
            messagebox.showinfo("Sucesso", "Usuário atualizado com sucesso!", parent=self)
            self.load_users()
            self.clear_fields()
        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro: {e}", parent=self)
            
    def delete_user(self):
        user_id = self.user_id.get()
        if not user_id:
            messagebox.showerror("Erro", "Selecione um usuário para excluir.", parent=self)
            return
            
        if user_id == '1':
            messagebox.showerror("Erro", "Não é possível excluir o administrador principal.", parent=self)
            return

        if messagebox.askyesno("Confirmar", "Tem certeza que deseja excluir este usuário? Todas as suas despesas e receitas serão transferidas para o administrador.", parent=self):
            try:
                # Reatribuir dados para o admin (id=1)
                conn_despesas = sqlite3.connect('financas.db')
                cursor_despesas = conn_despesas.cursor()
                cursor_despesas.execute("UPDATE despesas SET user_id = 1 WHERE user_id = ?", (user_id,))
                conn_despesas.commit()
                conn_despesas.close()

                conn_receitas = sqlite3.connect('financas_receitas.db')
                cursor_receitas = conn_receitas.cursor()
                cursor_receitas.execute("UPDATE receitas SET user_id = 1 WHERE user_id = ?", (user_id,))
                conn_receitas.commit()
                conn_receitas.close()

                # Excluir usuário
                self.cursor.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
                self.conn.commit()
                
                messagebox.showinfo("Sucesso", "Usuário excluído e dados transferidos.", parent=self)
                self.load_users()
                self.clear_fields()
            except Exception as e:
                messagebox.showerror("Erro", f"Ocorreu um erro: {e}", parent=self)
                
    def remove_expiration(self):
        """Define a data de expiração como NULA no formulário."""
        self.date_entry.set_date(None)
        messagebox.showinfo("Informação", "Data de expiração removida do formulário. Clique em 'Atualizar' para salvar.", parent=self)

# --- FIM: NOVAS FUNÇÕES E CLASSES ---


# --- CLASSE PARA GERENCIAR CATEGORIAS DE RECEITA ---
class GerenciadorCategoriasReceita(tk.Toplevel):
    """Janela para gerenciar (adicionar, editar, excluir) categorias de receita."""
    def __init__(self, parent_widget, app_logic):
        super().__init__(parent_widget)
        self.transient(parent_widget)
        self.grab_set()
        self.title("Gerenciar Categorias de Receita")
        self.geometry("450x400")

        self.app_logic = app_logic
        self.conn_receitas = self.app_logic.conn_receitas
        self.cursor_receitas = self.app_logic.cursor_receitas
        self.user_id = self.app_logic.user_id # <--- ADICIONADO

        self.id_categoria_var = tk.StringVar()
        self.nome_categoria_var = tk.StringVar()

        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        frame_lista = ttk.LabelFrame(main_frame, text="Categorias Existentes")
        frame_lista.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.lista_categorias = tk.Listbox(frame_lista, height=10)
        self.lista_categorias.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.lista_categorias.bind("<<ListboxSelect>>", self.selecionar_categoria)

        scrollbar = ttk.Scrollbar(frame_lista, orient="vertical", command=self.lista_categorias.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.lista_categorias.config(yscrollcommand=scrollbar.set)
        
        frame_form = ttk.LabelFrame(main_frame, text="Adicionar / Editar Categoria")
        frame_form.pack(fill=tk.X, pady=10)

        ttk.Label(frame_form, text="ID:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(frame_form, textvariable=self.id_categoria_var, state='readonly', width=10).grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        ttk.Label(frame_form, text="Nome:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        entry_categoria = ttk.Entry(frame_form, textvariable=self.nome_categoria_var, width=40)
        entry_categoria.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        frame_form.columnconfigure(1, weight=1)

        frame_botoes = ttk.Frame(main_frame)
        frame_botoes.pack(fill=tk.X, pady=5)
        
        btn_adicionar = ttk.Button(frame_botoes, text="Adicionar Novo", command=self.adicionar_categoria)
        btn_adicionar.pack(side=tk.LEFT, padx=5)

        self.btn_atualizar = ttk.Button(frame_botoes, text="Salvar Edição", command=self.atualizar_categoria, state="disabled")
        self.btn_atualizar.pack(side=tk.LEFT, padx=5)

        self.btn_excluir = ttk.Button(frame_botoes, text="Excluir Selecionado", command=self.excluir_categoria, state="disabled")
        self.btn_excluir.pack(side=tk.LEFT, padx=5)
        
        btn_limpar = ttk.Button(frame_botoes, text="Limpar Formulário", command=self.limpar_campos)
        btn_limpar.pack(side=tk.LEFT, padx=5)
        
        self.carregar_categorias()

    def carregar_categorias(self):
        """Carrega a lista e seleciona o primeiro item para edição."""
        self.limpar_campos()
        self.lista_categorias.delete(0, tk.END)
        
        self.cursor_receitas.execute("SELECT nome FROM categorias_receita ORDER BY nome")
        categorias = self.cursor_receitas.fetchall()
        for categoria in categorias:
            self.lista_categorias.insert(tk.END, categoria[0])
            
        if self.lista_categorias.size() > 0:
            self.lista_categorias.selection_set(0)
            self.selecionar_categoria() 

    def limpar_campos(self):
        self.id_categoria_var.set("")
        self.nome_categoria_var.set("")
        if self.lista_categorias.curselection():
            self.lista_categorias.selection_clear(0, tk.END)
        self.btn_atualizar.config(state="disabled")
        self.btn_excluir.config(state="disabled")

    def selecionar_categoria(self, event=None):
        selecionado_indices = self.lista_categorias.curselection()
        if not selecionado_indices:
            self.id_categoria_var.set("")
            self.nome_categoria_var.set("")
            self.btn_atualizar.config(state="disabled")
            self.btn_excluir.config(state="disabled")
            return
        
        nome_selecionado = self.lista_categorias.get(selecionado_indices[0])
        self.cursor_receitas.execute("SELECT id FROM categorias_receita WHERE nome = ?", (nome_selecionado,))
        resultado = self.cursor_receitas.fetchone()
        
        if resultado:
            self.id_categoria_var.set(resultado[0])
            self.nome_categoria_var.set(nome_selecionado)
            self.btn_atualizar.config(state="normal")
            self.btn_excluir.config(state="normal")

    def adicionar_categoria(self):
        nome = self.nome_categoria_var.get().strip()
        if not nome:
            messagebox.showerror("Erro", "O nome da categoria não pode estar vazio.", parent=self)
            return
        self.id_categoria_var.set("")
        try:
            self.cursor_receitas.execute("INSERT INTO categorias_receita (nome) VALUES (?)", (nome,))
            self.conn_receitas.commit()
            self.carregar_categorias()
        except sqlite3.IntegrityError:
            messagebox.showerror("Erro", f"A categoria '{nome}' já existe.", parent=self)
        except Exception as e:
            messagebox.showerror("Erro no Banco de Dados", f"Erro ao adicionar categoria: {e}", parent=self)

    def atualizar_categoria(self):
        id_cat = self.id_categoria_var.get()
        novo_nome = self.nome_categoria_var.get().strip()

        if not id_cat or not novo_nome:
            messagebox.showwarning("Dados Incompletos", "Selecione uma categoria da lista para editar.", parent=self)
            return
        
        try:
            self.cursor_receitas.execute("SELECT nome FROM categorias_receita WHERE id = ?", (id_cat,))
            resultado = self.cursor_receitas.fetchone()
            if not resultado:
                messagebox.showerror("Erro", "Categoria de receita não encontrada.", parent=self)
                return
            nome_antigo = resultado[0]

            if nome_antigo == novo_nome:
                messagebox.showinfo("Informação", "O nome não foi alterado.", parent=self)
                return

            self.cursor_receitas.execute("UPDATE categorias_receita SET nome = ? WHERE id = ?", (novo_nome, id_cat))
            # Atualiza o nome da categoria em todos os registros de receita de TODOS os usuários
            self.cursor_receitas.execute("UPDATE receitas SET conta_receita = ? WHERE conta_receita = ?", (novo_nome, nome_antigo))
            
            self.conn_receitas.commit()
            
            messagebox.showinfo("Sucesso", f"Categoria '{nome_antigo}' foi atualizada para '{novo_nome}' com sucesso.", parent=self)
            self.carregar_categorias()
            items = self.lista_categorias.get(0, tk.END)
            if novo_nome in items:
                idx = items.index(novo_nome)
                self.lista_categorias.selection_set(idx)
                self.selecionar_categoria()

        except sqlite3.IntegrityError:
            messagebox.showerror("Erro de Integridade", f"O nome '{novo_nome}' já está em uso.", parent=self)
            self.conn_receitas.rollback()
        except Exception as e:
            messagebox.showerror("Erro ao Atualizar", f"Erro no banco de dados: {e}", parent=self)
            self.conn_receitas.rollback()

    def excluir_categoria(self):
        id_cat = self.id_categoria_var.get()
        nome_cat = self.nome_categoria_var.get()

        if not id_cat:
            messagebox.showerror("Erro", "Selecione uma categoria da lista para excluir.", parent=self)
            return
        # Verifica se a categoria está em uso por QUALQUER usuário
        self.cursor_receitas.execute("SELECT COUNT(*) FROM receitas WHERE conta_receita = ?", (nome_cat,))
        count = self.cursor_receitas.fetchone()[0]

        if count > 0:
            messagebox.showwarning("Impossível Excluir", 
                                 f"A categoria '{nome_cat}' está sendo usada em {count} registros de receita e não pode ser excluída.",
                                 parent=self)
            return

        if messagebox.askyesno("Confirmar Exclusão", f"Tem certeza que deseja excluir a categoria '{nome_cat}'?", parent=self):
            try:
                self.cursor_receitas.execute("DELETE FROM categorias_receita WHERE id = ?", (id_cat,))
                self.conn_receitas.commit()
                self.carregar_categorias()
            except Exception as e:
                messagebox.showerror("Erro no Banco de Dados", f"Erro ao excluir categoria: {e}", parent=self)

###################################################
  
# --- CLASSE PARA GERENCIAR RECEITAS ---
class GerenciadorReceitas(tk.Toplevel):
    def __init__(self, parent_widget, app_logic):
        super().__init__(parent_widget)
        self.transient(parent_widget)
        self.grab_set()
        self.title("Gerenciador de Receitas")
        self.geometry("950x600")

        self.parent_app = app_logic
        self.conn_receitas = self.parent_app.conn_receitas
        self.cursor_receitas = self.parent_app.cursor_receitas
        self.user_id = self.parent_app.user_id # <--- ADICIONADO

        self.id_receita = tk.StringVar()
        self.descricao = tk.StringVar()
        self.meio_recebimento = tk.StringVar()
        self.conta_receita = tk.StringVar()
        self.valor = tk.DoubleVar()
        
        self.criar_widgets()
        self.carregar_receitas()

    def carregar_combos(self):
        self.cursor_receitas.execute("SELECT nome FROM categorias_receita ORDER BY nome")
        self.combo_conta_receita['values'] = [row[0] for row in self.cursor_receitas.fetchall()]
        
        self.cursor_receitas.execute("SELECT nome FROM meios_recebimento ORDER BY nome")
        self.combo_meio_recebimento['values'] = [row[0] for row in self.cursor_receitas.fetchall()]

    def criar_widgets(self):
        # ... (código da interface sem alterações) ...
        frame_principal = ttk.Frame(self, padding="10")
        frame_principal.pack(fill=tk.BOTH, expand=True)

        frame_form = ttk.LabelFrame(frame_principal, text="Lançamento de Receita")
        frame_form.pack(fill=tk.X, pady=10)
        frame_form.columnconfigure(1, weight=1)

        ttk.Label(frame_form, text="Descrição:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(frame_form, textvariable=self.descricao, width=40).grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(frame_form, text="Valor (R$):").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        ttk.Entry(frame_form, textvariable=self.valor, width=15).grid(row=0, column=3, padx=5, pady=5, sticky="w")

        ttk.Label(frame_form, text="Categoria:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.combo_conta_receita = ttk.Combobox(frame_form, textvariable=self.conta_receita, state='readonly')
        self.combo_conta_receita.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(frame_form, text="Meio Recebimento:").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.combo_meio_recebimento = ttk.Combobox(frame_form, textvariable=self.meio_recebimento, width=20, state='readonly')
        self.combo_meio_recebimento.grid(row=1, column=3, padx=5, pady=5, sticky="w")
        
        ttk.Label(frame_form, text="Data Recebimento:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.data_entry = DateEntry(frame_form, width=12, date_pattern='dd/mm/yyyy', locale='pt_BR')
        self.data_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        self.data_entry.set_date(datetime.now())

        self.carregar_combos()

        frame_botoes = ttk.Frame(frame_form)
        frame_botoes.grid(row=3, column=0, columnspan=4, pady=10)
        ttk.Button(frame_botoes, text="Salvar", command=self.salvar_receita).pack(side=tk.LEFT, padx=5)
        self.btn_atualizar = ttk.Button(frame_botoes, text="Atualizar", command=self.atualizar_receita, state="disabled")
        self.btn_atualizar.pack(side=tk.LEFT, padx=5)
        self.btn_excluir = ttk.Button(frame_botoes, text="Excluir", command=self.excluir_receita, state="disabled")
        self.btn_excluir.pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botoes, text="Limpar", command=self.limpar_campos).pack(side=tk.LEFT, padx=5)

        frame_tabela = ttk.LabelFrame(frame_principal, text="Receitas Lançadas")
        frame_tabela.pack(fill=tk.BOTH, expand=True, pady=10)
        
        scrollbar = ttk.Scrollbar(frame_tabela)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tabela = ttk.Treeview(frame_tabela, yscrollcommand=scrollbar.set, selectmode="browse")
        self.tabela['columns'] = ('id', 'data', 'descricao', 'categoria', 'meio', 'valor')
        
        self.tabela.column("#0", width=0, stretch=tk.NO)
        self.tabela.column("id", anchor=tk.CENTER, width=40)
        self.tabela.column("data", anchor=tk.CENTER, width=100)
        self.tabela.column("descricao", anchor=tk.W, width=300)
        self.tabela.column("categoria", anchor=tk.W, width=150)
        self.tabela.column("meio", anchor=tk.W, width=150)
        self.tabela.column("valor", anchor=tk.E, width=120)

        self.tabela.heading("id", text="ID")
        self.tabela.heading("data", text="Data")
        self.tabela.heading("descricao", text="Descrição")
        self.tabela.heading("categoria", text="Categoria")
        self.tabela.heading("meio", text="Meio")
        self.tabela.heading("valor", text="Valor")
        
        self.tabela.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tabela.yview)
        self.tabela.bind("<ButtonRelease-1>", self.selecionar_item)

    def carregar_receitas(self):
        for i in self.tabela.get_children():
            self.tabela.delete(i)
        # ALTERADO: Filtra por user_id
        self.cursor_receitas.execute("""
            SELECT id, strftime('%d/%m/%Y', data_recebimento), descricao, conta_receita, meio_recebimento, valor
            FROM receitas WHERE user_id = ? ORDER BY data_recebimento DESC
        """, (self.user_id,))
        for row in self.cursor_receitas.fetchall():
            valor_formatado = locale.currency(row[5], grouping=True, symbol=True)
            self.tabela.insert("", tk.END, values=(row[0], row[1], row[2], row[3], row[4], valor_formatado))

    def limpar_campos(self):
        # ... (código sem alterações) ...
        self.id_receita.set("")
        self.descricao.set("")
        self.conta_receita.set("")
        self.meio_recebimento.set("")
        self.valor.set(0.0)
        self.data_entry.set_date(datetime.now())
        self.btn_atualizar.config(state="disabled")
        self.btn_excluir.config(state="disabled")
        if self.tabela.selection():
            self.tabela.selection_remove(self.tabela.selection())


    def salvar_receita(self):
        if not self.descricao.get() or self.valor.get() <= 0 or not self.conta_receita.get():
            messagebox.showerror("Erro de Validação", "Preencha todos os campos obrigatórios (Descrição, Valor > 0, Categoria).", parent=self)
            return

        try:
            data_recebimento = self.data_entry.get_date().strftime('%Y-%m-%d')
            # ALTERADO: Inclui user_id no INSERT
            self.cursor_receitas.execute("""
                INSERT INTO receitas (descricao, conta_receita, meio_recebimento, valor, data_recebimento, data_registro, num_parcelas, user_id)
                VALUES (?, ?, ?, ?, ?, date('now'), 1, ?)
            """, (self.descricao.get(), self.conta_receita.get(), self.meio_recebimento.get(), self.valor.get(), data_recebimento, self.user_id))
            self.conn_receitas.commit()
            messagebox.showinfo("Sucesso", "Receita salva com sucesso!", parent=self)
            self.limpar_campos()
            self.carregar_receitas()
        except Exception as e:
            messagebox.showerror("Erro no Banco de Dados", f"Erro ao salvar receita: {e}", parent=self)

    def selecionar_item(self, event):
        # ... (código sem alterações) ...
        selected_item = self.tabela.focus()
        if not selected_item: return
        
        values = self.tabela.item(selected_item, 'values')
        self.id_receita.set(values[0])
        
        data_obj = datetime.strptime(values[1], '%d/%m/%Y')
        self.data_entry.set_date(data_obj)
        
        self.descricao.set(values[2])
        self.conta_receita.set(values[3])
        self.meio_recebimento.set(values[4])
        
        try:
            valor_str = values[5].replace('R$', '').replace('.', '').replace(',', '.').strip()
            self.valor.set(float(valor_str))
        except (ValueError, IndexError):
             self.valor.set(0.0)

        self.btn_atualizar.config(state="normal")
        self.btn_excluir.config(state="normal")

    def atualizar_receita(self):
        receita_id = self.id_receita.get()
        if not receita_id: return
        
        if not self.descricao.get() or self.valor.get() <= 0 or not self.conta_receita.get():
            messagebox.showerror("Erro de Validação", "Preencha todos os campos obrigatórios.", parent=self)
            return
            
        try:
            data_recebimento = self.data_entry.get_date().strftime('%Y-%m-%d')
            # ALTERADO: Adiciona user_id ao WHERE para segurança
            self.cursor_receitas.execute("""
                UPDATE receitas SET descricao=?, conta_receita=?, meio_recebimento=?, valor=?, data_recebimento=?
                WHERE id=? AND user_id = ?
            """, (self.descricao.get(), self.conta_receita.get(), self.meio_recebimento.get(), self.valor.get(), data_recebimento, receita_id, self.user_id))
            self.conn_receitas.commit()
            messagebox.showinfo("Sucesso", "Receita atualizada com sucesso!", parent=self)
            self.limpar_campos()
            self.carregar_receitas()
        except Exception as e:
            messagebox.showerror("Erro no Banco de Dados", f"Erro ao atualizar receita: {e}", parent=self)

    def excluir_receita(self):
        receita_id = self.id_receita.get()
        if not receita_id: return

        if messagebox.askyesno("Confirmar", "Tem certeza que deseja excluir esta receita?", parent=self):
            try:
                # ALTERADO: Adiciona user_id ao WHERE para segurança
                self.cursor_receitas.execute("DELETE FROM receitas WHERE id=? AND user_id = ?", (receita_id, self.user_id))
                self.conn_receitas.commit()
                messagebox.showinfo("Sucesso", "Receita excluída com sucesso!", parent=self)
                self.limpar_campos()
                self.carregar_receitas()
            except Exception as e:
                messagebox.showerror("Erro no Banco de Dados", f"Erro ao excluir receita: {e}", parent=self)

# --- CLASSE PRINCIPAL DA APLICAÇÃO ---
    # ALTERADO: __init__ agora aceita user_info
    def __init__(self, root, user_info):
        self.root = root
        self.user_id = user_info['id']
        self.user_role = user_info['role']
        self.username = user_info['username']

        self.root.title(f"Sistema de Gerenciamento Financeiro - Usuário: {self.username} ({self.user_role})")
        self.root.geometry("1270x750")
        self.root.resizable(True, True)
        
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)

        # ... (Menus existentes) ...
        arquivo_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Arquivo", menu=arquivo_menu)
        arquivo_menu.add_command(label="Relatório Entre Datas", command=self.gerar_relatorio_entre_datas)
        arquivo_menu.add_command(label="Relatório Mensal por Período", command=self.gerar_relatorio_mensal_periodo)
        arquivo_menu.add_command(label="Importar de Planilha Excel...", command=self.abrir_importador_excel)
        arquivo_menu.add_command(label="Importar do Supabase...", command=self.abrir_importador_supabase) # <--- ADICIONE ESTA LINHA
          
        arquivo_menu.add_separator() 
        arquivo_menu.add_command(label="Sair", command=self.on_closing)

        relatorios_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Relatórios de Despesas", menu=relatorios_menu)
        relatorios_menu.add_command(label="Top 10 Contas (Gráfico Dinâmico)", command=self.mostrar_grafico_principais_contas)
        relatorios_menu.add_command(label="Por Categoria (Evolução)", command=self.gerar_relatorio_categoria)
        relatorios_menu.add_command(label="Por Meio de Pagamento (Evolução)", command=self.gerar_relatorio_meio_pagamento)
        relatorios_menu.add_separator()
        relatorios_menu.add_command(label="Relatórios Avançados com Gráficos", command=self.abrir_relatorios_avancados)
        relatorios_menu.add_command(label="Relatórios Simples (Listagem)", command=self.abrir_relatorios_simples)
        relatorios_menu.add_command(label="Mensal: Orçado vs. Gasto", command=self.abrir_relatorio_orcado_vs_gasto)
        relatorios_menu.add_command(label="Previsão de Faturas de Cartão", command=self.abrir_relatorio_previsao_faturas_cartao)

        config_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Configuração", menu=config_menu)
        config_menu.add_command(label="Gerenciar Categorias e Pagamentos", command=self.abrir_gerenciador)
        config_menu.add_command(label="Gerenciar Banco de Dados", command=self.abrir_gerenciador2)
        config_menu.add_command(label="Atualizar Interface", command=self.atualizar_dados_interface)
        config_menu.add_command(label="Gerenciar Orçamento", command=self.abrir_gerenciador_orcamento) 
        config_menu.add_command(label="Configurar Fechamento de Cartões", command=self.abrir_gerenciador_fechamento_cartoes)

        receitas_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Receitas", menu=receitas_menu)
        receitas_menu.add_command(label="Lançar/Gerenciar Receitas", command=self.abrir_gerenciador_receitas)
        receitas_menu.add_command(label="Gerenciar Categorias de Receita", command=self.abrir_gerenciador_categorias_receita)
        receitas_menu.add_separator()
        receitas_menu.add_command(label="Relatório Mensal de Receitas", command=self.gerar_relatorio_receita_mensal)
        receitas_menu.add_command(label="Relatório de Receitas por Categoria", command=self.gerar_relatorio_receita_categoria)
        receitas_menu.add_command(label="Relatório de Receitas Entre Datas", command=self.gerar_relatorio_receita_entre_datas)

        consolidado_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Relatórios Consolidados", menu=consolidado_menu)
        consolidado_menu.add_command(label="Balanço Mensal (Receita x Despesa)", command=self.abrir_relatorio_balanco)
        consolidado_menu.add_command(label="Balanço Mensal (Fluxo de Caixa)", command=self.abrir_relatorio_balancofc)
        
        # --- NOVO MENU DE ADMINISTRAÇÃO ---
        if self.user_role == 'admin':
            admin_menu = tk.Menu(self.menu_bar, tearoff=0)
            self.menu_bar.add_cascade(label="Administração", menu=admin_menu)
            admin_menu.add_command(label="Gerenciar Usuários", command=self.abrir_gerenciador_usuarios)

        ajuda_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Ajuda", menu=ajuda_menu)
        ajuda_menu.add_command(label="Ajuda", command=self.mostrar_ajuda)
        ajuda_menu.add_command(label="Sobre...", command=self.mostrar_sobre)
        


        self.cor_primaria = "#4CAF50"
        self.cor_secundaria = "#F0F4C3"
        self.cor_fundo = "#F9F9F9"
        self.cor_texto = "#333333"
        
        self.configurar_estilo()
        
        # Conexões agora são abertas aqui
        self.conn = sqlite3.connect('financas.db')
        self.cursor = self.conn.cursor()
        self.conn_receitas = sqlite3.connect('financas_receitas.db')
        self.cursor_receitas = self.conn_receitas.cursor()

        self.criar_banco_dados()
        self.criar_banco_dados_receitas()
        
        self.id_despesa = tk.StringVar()
        self.descricao = tk.StringVar()
        self.meio_pagamento = tk.StringVar()
        self.conta_despesa = tk.StringVar()
        self.valor = tk.DoubleVar()
        self.num_parcelas = tk.IntVar()
        
        self.mapa_meses_grafico = {}
        self.total_mes_selecionado_var = tk.StringVar()
        
        self.criar_widgets()
        self.carregar_despesas()

    # --- NOVA FUNÇÃO PARA ABRIR GERENCIADOR DE USUÁRIOS ---
    def abrir_gerenciador_usuarios(self):
        UserManagementWindow(self.root)

# Adicione este método completo dentro da classe SistemaFinanceiro

    def logout(self):
        """Fecha a janela atual e reinicia o processo de login."""
        # Fecha as conexões com o banco de dados de forma segura
        self.conn.close()
        self.conn_receitas.close()
        # Destrói a janela principal atual
        self.root.destroy()
        # Chama a função principal novamente para exibir a tela de login
        main()

    def on_closing(self):
        if messagebox.askokcancel("Sair", "Deseja sair do sistema?"):
            self.conn.close()
            self.conn_receitas.close()
            self.root.destroy()
            
    # ... (demais funções do sistema) ...
    # AS SEGUINTES FUNÇÕES FORAM ALTERADAS PARA INCLUIR `user_id` NAS QUERIES:
    # - mostrar_grafico_principais_contas
    # - mostrar_relatorio_entre_datas
    # - mostrar_relatorio_mensal_periodo
    # - carregar_despesas
    # - salvar_despesa
    # - atualizar_despesa
    # - excluir_despesa
    # - pesquisar_despesa
    # - on_bar_pick / mostrar_detalhes_categoria_mes
    # - atualizar_grafico
    # - mostrar_relatorio_mensal
    # - mostrar_relatorio_meio_pagamento
    # - mostrar_relatorio_categoria
    # - Todas as de exportação de despesas
    # - Todas as de relatórios de receitas
    # (Abaixo estão exemplos das alterações, o código completo contém todas elas)

    def carregar_despesas(self):
        """Carrega as despesas do usuário logado para a tabela"""
        for item in self.tabela.get_children():
            self.tabela.delete(item)
            
        try:
            # ALTERADO: Adicionado WHERE user_id = ?
            self.cursor.execute("""
                SELECT id, descricao, meio_pagamento, conta_despesa, valor, 
                       num_parcelas, strftime('%d/%m/%Y', data_pagamento) as data_formatada
                FROM despesas WHERE user_id = ?
                ORDER BY data_pagamento DESC
            """, (self.user_id,))
            
            for row in self.cursor.fetchall():
                valor_formatado = f"R$ {row[4]:.2f}".replace('.', ',')
                self.tabela.insert('', tk.END, values=(
                    row[0], row[1], row[2], row[3], 
                    valor_formatado, row[5], row[6]
                ))

            self._repovoar_combo_meses_grafico()
            self.atualizar_grafico()
                
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Erro ao carregar despesas: {e}")

    def salvar_despesa(self):
        """Salva uma nova despesa no banco de dados para o usuário logado"""
        if not self.validar_campos():
            return
            
        try:
            data_pagamento = self.data_entry.get_date().strftime('%Y-%m-%d')
            
            # ALTERADO: Adicionado user_id no INSERT
            self.cursor.execute("""
                INSERT INTO despesas (descricao, meio_pagamento, conta_despesa, valor,
                                     num_parcelas, data_registro, data_pagamento, user_id)
                VALUES (?, ?, ?, ?, ?, date('now'), ?, ?)
            """, (
                self.descricao.get().strip(), self.meio_pagamento.get().strip(),
                self.conta_despesa.get().strip(), self.valor.get(),
                self.num_parcelas.get(), data_pagamento, self.user_id
            ))
            
            self.conn.commit()
            messagebox.showinfo("Sucesso", "Despesa registrada com sucesso!")
            self.limpar_campos()
            self.carregar_despesas()
            
        except sqlite3.Error as e:
            messagebox.showerror("Erro ao Salvar", f"Ocorreu um erro: {e}")

    def atualizar_despesa(self):
        """Atualiza uma despesa existente, verificando a posse do usuário"""
        if not self.validar_campos() or not self.id_despesa.get():
            return
            
        if not messagebox.askyesno("Confirmar", "Tem certeza que deseja atualizar este registro?"):
            return
        
        try:
            data_pagamento = self.data_entry.get_date().strftime('%Y-%m-%d')
            
            # ALTERADO: Adicionado WHERE user_id = ? para segurança
            self.cursor.execute("""
                UPDATE despesas SET 
                    descricao = ?, meio_pagamento = ?, conta_despesa = ?,
                    valor = ?, num_parcelas = ?, data_pagamento = ?
                WHERE id = ? AND user_id = ?
            """, (
                self.descricao.get().strip(), self.meio_pagamento.get().strip(),
                self.conta_despesa.get().strip(), self.valor.get(),
                self.num_parcelas.get(), data_pagamento, self.id_despesa.get(), self.user_id
            ))
            
            self.conn.commit()
            messagebox.showinfo("Sucesso", "Registro atualizado com sucesso!")
            self.limpar_campos()
            self.carregar_despesas()
            
        except sqlite3.Error as e:
            messagebox.showerror("Erro ao Atualizar", f"Ocorreu um erro: {e}")

    def excluir_despesa(self):
        """Exclui uma despesa, verificando a posse do usuário"""
        if not self.id_despesa.get():
            return
            
        if not messagebox.askyesno("Confirmar", "Tem certeza que deseja excluir este registro?"):
            return
                
        try:
            # ALTERADO: Adicionado WHERE user_id = ? para segurança
            self.cursor.execute("DELETE FROM despesas WHERE id = ? AND user_id = ?", (self.id_despesa.get(), self.user_id))
            self.conn.commit()
            
            messagebox.showinfo("Sucesso", "Registro excluído com sucesso!")
            self.limpar_campos()
            self.carregar_despesas()
            
        except sqlite3.Error as e:
            messagebox.showerror("Erro ao Excluir", f"Ocorreu um erro: {e}")

    def pesquisar_despesa(self):
        """Pesquisa despesas do usuário logado"""
        termo = self.pesquisa_termo.get().strip()
        if not termo: return
            
        for item in self.tabela.get_children():
            self.tabela.delete(item)
            
        try:
            # ALTERADO: Adicionado WHERE user_id = ?
            self.cursor.execute("""
                SELECT id, descricao, meio_pagamento, conta_despesa, valor, 
                       num_parcelas, strftime('%d/%m/%Y', data_pagamento) as data_formatada
                FROM despesas
                WHERE user_id = ? AND (descricao LIKE ? OR conta_despesa LIKE ? OR meio_pagamento LIKE ?)
                ORDER BY data_pagamento DESC
            """, (self.user_id, f'%{termo}%', f'%{termo}%', f'%{termo}%'))
            
            # ... (Restante da função sem alteração na lógica de exibição) ...
            resultados = self.cursor.fetchall()
            
            # Inserir dados na tabela
            for row in resultados:
                # Formatar valor como R$
                valor_formatado = f"R$ {row[4]:.2f}".replace('.', ',')
                
                self.tabela.insert('', tk.END, values=(
                    row[0], row[1], row[2], row[3], 
                    valor_formatado, row[5], row[6]
                ))
                
            if not resultados:
                messagebox.showinfo("Pesquisa", "Nenhum resultado encontrado para o termo informado.")
                
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Pesquisa", f"Erro ao pesquisar despesas: {e}")


    def mostrar_relatorio_mensal(self, mes, ano):
        """Exibe o relatório mensal do usuário logado"""
        try:
            # ...
            primeiro_dia = f"{ano}-{mes:02d}-01"
            ultimo_dia = f"{ano}-{mes:02d}-{calendar.monthrange(ano, mes)[1]}"
            
            # ALTERADO: Adicionado WHERE user_id = ?
            self.cursor.execute("""
                SELECT conta_despesa, SUM(valor) as total_valor, COUNT(*) as total_registros
                FROM despesas
                WHERE data_pagamento BETWEEN ? AND ? AND user_id = ?
                GROUP BY conta_despesa ORDER BY total_valor DESC
            """, (primeiro_dia, ultimo_dia, self.user_id))
            # ... (Restante da função de exibição do relatório)
            
            resultados = self.cursor.fetchall()
            
            if not resultados:
                messagebox.showinfo("Relatório", f"Nenhuma despesa encontrada para {calendar.month_name[mes]} de {ano}.")
                return
                
            # Calcular total geral
            total_geral = sum(row[1] for row in resultados)
            
            # Criar nova janela para o relatório
            janela_relatorio = tk.Toplevel(self.root)
            janela_relatorio.title(f"Relatório de {calendar.month_name[mes]} de {ano}")
            janela_relatorio.geometry("900x700") # Aumentado um pouco para melhor visualização da legenda
            
            # Frame principal
            frame_principal = ttk.Frame(janela_relatorio, padding="10")
            frame_principal.pack(fill=tk.BOTH, expand=True)
            
            # Título
            titulo_texto = f"Relatório de Despesas - {calendar.month_name[mes]} de {ano}"
            titulo_label = ttk.Label(frame_principal, text=titulo_texto, font=('Arial', 16, 'bold'))
            titulo_label.pack(pady=10)
            
            # Total geral
            total_texto = f"Total de Despesas: {locale.currency(total_geral, grouping=True)}"
            total_label_widget = ttk.Label(frame_principal, text=total_texto, font=('Arial', 12))
            total_label_widget.pack(pady=5)
            
            # Frame com abas
            notebook = ttk.Notebook(frame_principal)
            notebook.pack(fill=tk.BOTH, expand=True, pady=10)
            
            # Aba de tabela
            tab_tabela = ttk.Frame(notebook)
            notebook.add(tab_tabela, text="Tabela")
            
            # Aba de gráfico
            tab_grafico = ttk.Frame(notebook)
            notebook.add(tab_grafico, text="Gráfico")
            
            # --- Início: Funções aninhadas para interatividade do gráfico de pizza ---
            def mostrar_detalhes_transacao_pizza(categoria_clicada, p_ano, p_mes):
                try:
                    detalhes_window = tk.Toplevel(janela_relatorio)
                    mes_nome = calendar.month_name[p_mes]
                    detalhes_window.title(f"Detalhes: {categoria_clicada} ({mes_nome}/{p_ano})")
                    detalhes_window.geometry("600x400")
                    detalhes_window.transient(janela_relatorio) # Mantém sobre a janela principal
                    detalhes_window.grab_set() # Foca nesta janela

                    tree_frame = ttk.Frame(detalhes_window, padding="10")
                    tree_frame.pack(fill=tk.BOTH, expand=True)

                    mes_ano_sql = f"{p_ano}-{p_mes:02d}"
                    self.cursor.execute("""
                        SELECT strftime('%d/%m/%Y', data_pagamento), descricao, valor
                        FROM despesas
                        WHERE conta_despesa = ? AND strftime('%Y-%m', data_pagamento) = ? AND user_id = ?
                        ORDER BY data_pagamento ASC
                    """, (categoria_clicada, mes_ano_sql, self.user_id))
                    transacoes = self.cursor.fetchall()

                    cols = ('data', 'descricao', 'valor')
                    tree = ttk.Treeview(tree_frame, columns=cols, show='headings')
                    tree.heading('data', text='Data')
                    tree.heading('descricao', text='Descrição')
                    tree.heading('valor', text='Valor')
                    tree.column('data', width=100, anchor=tk.CENTER)
                    tree.column('descricao', width=350, anchor=tk.W)
                    tree.column('valor', width=120, anchor=tk.E)
                    
                    scrollbar_detalhes = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
                    tree.configure(yscrollcommand=scrollbar_detalhes.set)
                    scrollbar_detalhes.pack(side=tk.RIGHT, fill=tk.Y)
                    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

                    soma_categoria = 0
                    if transacoes:
                        for data_t, desc_t, valor_t in transacoes:
                            tree.insert("", "end", values=(data_t, desc_t, locale.currency(valor_t, grouping=True)))
                            soma_categoria += valor_t
                    else:
                        tree.insert("", "end", values=("", "Nenhuma transação encontrada.", ""))

                    ttk.Label(detalhes_window, text=f"Total para {categoria_clicada}: {locale.currency(soma_categoria, grouping=True)}", font=('Arial', 10, 'bold')).pack(pady=5)
                
                except Exception as e_detail:
                    messagebox.showerror("Erro Detalhes", f"Não foi possível mostrar os detalhes: {e_detail}", parent=janela_relatorio)

            def on_slice_pick(event):
                gid = event.artist.get_gid()
                if gid:
                    categoria_selecionada, ano_selecionado, mes_selecionado = gid
                    mostrar_detalhes_transacao_pizza(categoria_selecionada, ano_selecionado, mes_selecionado)
            # --- Fim: Funções aninhadas ---

            # Criar tabela na primeira aba
            tree_frame_tabela = ttk.Frame(tab_tabela)
            tree_frame_tabela.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            scrollbar_tabela = ttk.Scrollbar(tree_frame_tabela)
            scrollbar_tabela.pack(side=tk.RIGHT, fill=tk.Y)
            
            colunas_tabela = ('categoria', 'total', 'registros', 'percentual')
            tabela_widget = ttk.Treeview(tree_frame_tabela, columns=colunas_tabela, show='headings', yscrollcommand=scrollbar_tabela.set)
            
            tabela_widget.heading('categoria', text='Categoria')
            tabela_widget.heading('total', text='Total (R$)')
            tabela_widget.heading('registros', text='Qtd. Registros')
            tabela_widget.heading('percentual', text='% do Total')
            
            tabela_widget.column('categoria', width=250, anchor=tk.W) # Aumentado para nomes de categoria
            tabela_widget.column('total', width=120, anchor=tk.E)
            tabela_widget.column('registros', width=100, anchor=tk.CENTER)
            tabela_widget.column('percentual', width=100, anchor=tk.CENTER)
            
            for row in resultados:
                categoria, total, registros = row
                percentual = (total / total_geral) * 100 if total_geral else 0
                tabela_widget.insert('', tk.END, values=(
                    categoria,
                    locale.currency(total, grouping=True),
                    registros,
                    f"{percentual:.1f}%"
                ))
                
            tabela_widget.pack(fill=tk.BOTH, expand=True)
            scrollbar_tabela.config(command=tabela_widget.yview)
            
            # Criar gráfico de pizza na segunda aba
            figura_pizza = Figure(figsize=(8, 6), dpi=100) # Ajustado tamanho
            ax_pizza = figura_pizza.add_subplot(111)
            
            categorias_grafico = [row[0] for row in resultados]
            valores_grafico = [row[1] for row in resultados]

            # Gerar cores distintas para o gráfico de pizza
            num_categorias = len(categorias_grafico)
            # Usar um colormap que tenha cores variadas. 'tab20' é uma boa opção.
            if num_categorias > 0 :
                cores = plt.cm.get_cmap('tab20', num_categorias).colors 
            else:
                cores = []

            wedges, texts, autotexts = ax_pizza.pie(
                valores_grafico, 
                autopct='%1.1f%%',
                startangle=140, # Ângulo inicial para melhor visualização das porcentagens
                colors=cores,
                pctdistance=0.85 # Distância das porcentagens do centro
            )

            # Tornar cada fatia clicável e definir seu GID (Group ID)
            for i, wedge in enumerate(wedges):
                wedge.set_picker(True)
                wedge.set_gid((categorias_grafico[i], ano, mes)) # Passa (categoria, ano_int, mes_int)

            # Estilo do gráfico de pizza
            ax_pizza.set_title(f'Distribuição de Despesas - {calendar.month_name[mes]} de {ano}', pad=20)
            ax_pizza.axis('equal')  # Garante que o gráfico seja circular
            
            # Adicionar legenda à direita
            # Ajustar bbox_to_anchor para garantir que a legenda caiba e não sobreponha o gráfico
            ax_pizza.legend(wedges, categorias_grafico, title="Categorias", 
                            loc="center left", bbox_to_anchor=(1, 0.5), fontsize='small')
            
            figura_pizza.tight_layout(rect=[0, 0, 0.85, 1]) # Ajustar layout para dar espaço à legenda

            canvas_pizza = FigureCanvasTkAgg(figura_pizza, tab_grafico)
            canvas_pizza_widget = canvas_pizza.get_tk_widget()
            canvas_pizza_widget.pack(fill=tk.BOTH, expand=True)
            canvas_pizza.mpl_connect('pick_event', on_slice_pick) # Conectar evento de clique
            
            # Botão para exportar
            ttk.Button(frame_principal, text="Exportar para Excel", 
                    command=lambda: self.exportar_relatorio_excel(mes, ano)).pack(pady=10)
                
        except Exception as e:
            messagebox.showerror("Erro ao Exibir Relatório", f"Ocorreu um erro: {e}")
            import traceback
            traceback.print_exc()

    # ... (O restante das funções de relatório e exportação também foram adaptadas da mesma forma)
    # --- As funções abaixo são apenas exemplos representativos das modificações ---
    
    def criar_banco_dados(self):
        """Cria o banco de dados e as tabelas e insere os dados padrão APENAS se as tabelas estiverem vazias."""
        try:
            # A conexão já é self.conn, estabelecida no __init__
            
            # --- ETAPA 1: Criar as tabelas (o IF NOT EXISTS garante que não haverá erro se já existirem) ---
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS despesas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    descricao TEXT NOT NULL,
                    meio_pagamento TEXT NOT NULL,
                    conta_despesa TEXT NOT NULL,
                    valor REAL NOT NULL,
                    num_parcelas INTEGER DEFAULT 1,
                    data_registro DATE NOT NULL,
                    data_pagamento DATE NOT NULL,
                    user_id INTEGER,
                    FOREIGN KEY(user_id) REFERENCES usuarios(id)
                )
            ''')
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS categorias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL UNIQUE
                )
            ''')
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS meios_pagamento (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL UNIQUE
                )
            ''')
            
            # --- ETAPA 2: Verificar se as tabelas de configuração estão vazias antes de inserir ---
            # Verificar e popular 'meios_pagamento'
            self.cursor.execute("SELECT COUNT(id) FROM meios_pagamento")
            if self.cursor.fetchone()[0] == 0:
                meios_padrao = [('Dinheiro',), ('Cartão Unlimited',), ('Cartão C6',), ('Cartão Nubank',), ('Cartão BB',),
                                ('Transferência',), ('PIX',), ('Boleto',)]
                self.cursor.executemany("INSERT INTO meios_pagamento (nome) VALUES (?)", meios_padrao)

            # Verificar e popular 'categorias'
            self.cursor.execute("SELECT COUNT(id) FROM categorias")
            if self.cursor.fetchone()[0] == 0:
                categorias_padrao = [('Tel. e Internet',), ('Gás',), ('Mercado',), ('Alimentação',), ('Moradia',), ('Transporte',), ('Educação',),
                                     ('Saúde',), ('Lazer',), ('Vestuário',), ('Funcionários',), ('Outros',)]
                self.cursor.executemany("INSERT INTO categorias (nome) VALUES (?)", categorias_padrao)

            self.conn.commit()
            
        except sqlite3.Error as e:
            messagebox.showerror("Erro no Banco de Dados", f"Ocorreu um erro na inicialização do BD: {e}")

    def criar_banco_dados_receitas(self):
        """Cria o banco de dados de receitas e insere os dados padrão APENAS se as tabelas estiverem vazias."""
        try:
            # A conexão já é self.conn_receitas, estabelecida no __init__

            self.cursor_receitas.execute('''
                CREATE TABLE IF NOT EXISTS receitas (
                    id INTEGER PRIMARY KEY, descricao TEXT NOT NULL, meio_recebimento TEXT,
                    conta_receita TEXT NOT NULL, valor REAL NOT NULL, num_parcelas INTEGER DEFAULT 1,
                    data_registro DATE NOT NULL, data_recebimento DATE NOT NULL,
                    user_id INTEGER,
                    FOREIGN KEY(user_id) REFERENCES usuarios(id)
                )
            ''')
            
            self.cursor_receitas.execute('CREATE TABLE IF NOT EXISTS categorias_receita (id INTEGER PRIMARY KEY, nome TEXT NOT NULL UNIQUE)')
            self.cursor_receitas.execute('CREATE TABLE IF NOT EXISTS meios_recebimento (id INTEGER PRIMARY KEY, nome TEXT NOT NULL UNIQUE)')

            self.cursor_receitas.execute("SELECT COUNT(id) FROM categorias_receita")
            if self.cursor_receitas.fetchone()[0] == 0:
                cat_receita_padrao = [('Salário',), ('Vendas',), ('Rendimentos',), ('Freelance',), ('Outras Receitas',)]
                self.cursor_receitas.executemany("INSERT INTO categorias_receita (nome) VALUES (?)", cat_receita_padrao)

            self.cursor_receitas.execute("SELECT COUNT(id) FROM meios_recebimento")
            if self.cursor_receitas.fetchone()[0] == 0:
                meios_receita_padrao = [('Transferência Bancária',), ('PIX',), ('Dinheiro',), ('Cheque',)]
                self.cursor_receitas.executemany("INSERT INTO meios_recebimento (nome) VALUES (?)", meios_receita_padrao)

            self.conn_receitas.commit()
        except sqlite3.Error as e:
            messagebox.showerror("Erro no BD de Receitas", f"Ocorreu um erro na inicialização do BD de Receitas: {e}")

    # ... [O restante do código, com todas as queries de despesa e receita sendo filtradas por self.user_id,
    #      é omitido por brevidade, mas está incluído na lógica completa. A implementação segue o padrão
    #      mostrado nos exemplos acima.]
# ... (restante do código original com as devidas alterações de user_id em todas as queries) ...
# A implementação completa envolveria modificar dezenas de queries. Os exemplos acima demonstram o padrão
# que foi aplicado a todas as interações com o banco de dados.

# ==============================================================================
# COLE ESTA CLASSE COMPLETA NO LUGAR DA CLASSE 'SistemaFinanceiro' EXISTENTE
# ==============================================================================
class SistemaFinanceiro:
    def __init__(self, root, user_info):
        self.root = root
        self.user_id = user_info['id']
        self.user_role = user_info['role']
        self.username = user_info['username']

        self.root.title(f"Sistema de Gerenciamento Financeiro - Usuário: {self.username} ({self.user_role})")
        self.root.geometry("1270x750")
        self.root.resizable(True, True)
        
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)

        # ==============================================================================
# SUBSTITUA ESTE BLOCO DENTRO DE def __init__
# ==============================================================================

        # --- MENUS ---
        arquivo_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Arquivo", menu=arquivo_menu)
        # CORRIGIDO: Adicionando lambda para passar user_id onde necessário
        arquivo_menu.add_command(label="Importar de Planilha Excel...", command=lambda: self.abrir_importador_excel(self.user_id))
        arquivo_menu.add_command(label="Importar do Supabase...", command=self.abrir_importador_supabase)
        arquivo_menu.add_separator()
        arquivo_menu.add_command(label="Deslogar / Trocar Usuário", command=self.logout)
        arquivo_menu.add_separator()
        arquivo_menu.add_command(label="Sair", command=self.on_closing)

        relatorios_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Relatórios de Despesas", menu=relatorios_menu)
        relatorios_menu.add_command(label="Top 10 Contas (Gráfico Dinâmico)", command=self.mostrar_grafico_principais_contas)
        relatorios_menu.add_command(label="Por Categoria (Evolução)", command=self.gerar_relatorio_categoria)
        relatorios_menu.add_command(label="Por Meio de Pagamento (Evolução)", command=self.gerar_relatorio_meio_pagamento)
        relatorios_menu.add_separator()
        relatorios_menu.add_command(label="Relatório Entre Datas", command=self.gerar_relatorio_entre_datas)
        relatorios_menu.add_command(label="Relatório Mensal por Período", command=self.gerar_relatorio_mensal_periodo)
        # CORRIGIDO: Adicionando lambda para passar user_id
        relatorios_menu.add_command(label="Relatórios Avançados com Gráficos", command=lambda: self.abrir_relatorios_avancados(self.user_id))
        relatorios_menu.add_command(label="Relatórios Simples (Listagem)", command=lambda: self.abrir_relatorios_simples(self.user_id))
        relatorios_menu.add_command(label="Relatório de Orçado vs. Gasto", command=lambda: self.abrir_relatorio_orcado_vs_gasto(self.user_id))
        relatorios_menu.add_command(label="Relatório de Faturas de Cartão", command=lambda: self.abrir_relatorio_previsao_faturas_cartao(self.user_id))

        config_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Configuração", menu=config_menu)
        # CORRIGIDO: Adicionando lambda para passar user_id
        config_menu.add_command(label="Gerenciar Categorias e Pagamentos", command=lambda: self.abrir_gerenciador(self.user_id))
        config_menu.add_command(label="Gerenciar Banco de Dados", command=lambda: self.abrir_gerenciador2(self.user_id))
        config_menu.add_command(label="Atualizar Interface", command=self.atualizar_dados_interface)
        config_menu.add_command(label="Gerenciar Orçamento", command=lambda: self.abrir_gerenciador_orcamento(self.user_id)) 
        config_menu.add_command(label="Configurar Fechamento de Cartões", command=self.abrir_gerenciador_fechamento_cartoes)

        receitas_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Receitas", menu=receitas_menu)
        receitas_menu.add_command(label="Lançar/Gerenciar Receitas", command=self.abrir_gerenciador_receitas)
        receitas_menu.add_command(label="Gerenciar Categorias de Receita", command=self.abrir_gerenciador_categorias_receita)
        receitas_menu.add_separator()
        receitas_menu.add_command(label="Relatório Mensal de Receitas", command=self.gerar_relatorio_receita_mensal)
        receitas_menu.add_command(label="Relatório de Receitas por Categoria", command=self.gerar_relatorio_receita_categoria)
        receitas_menu.add_command(label="Relatório de Receitas Entre Datas", command=self.gerar_relatorio_receita_entre_datas)

        consolidado_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Relatórios Consolidados", menu=consolidado_menu)
        # CORRIGIDO: Adicionando lambda para passar user_id
        consolidado_menu.add_command(label="Balanço Mensal (Receita x Despesa)", command=lambda: self.abrir_relatorio_balanco(self.user_id))
        consolidado_menu.add_command(label="Balanço Mensal (Fluxo de Caixa)", command=lambda: self.abrir_relatorio_balancofc(self.user_id))

        if self.user_role == 'admin':
            admin_menu = tk.Menu(self.menu_bar, tearoff=0)
            self.menu_bar.add_cascade(label="Administração", menu=admin_menu)
            admin_menu.add_command(label="Gerenciar Usuários", command=self.abrir_gerenciador_usuarios)

        ajuda_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Ajuda", menu=ajuda_menu)
        ajuda_menu.add_command(label="Ajuda", command=self.mostrar_ajuda)
        ajuda_menu.add_command(label="Sobre...", command=self.mostrar_sobre)

        # ==============================================================================
        # FIM DO BLOCO PARA SUBSTITUIÇÃO
        # ==============================================================================
        # --- ESTILO E BANCO DE DADOS ---
        self.cor_primaria = "#4CAF50"
        self.cor_secundaria = "#F0F4C3"
        self.cor_fundo = "#F9F9F9"
        self.cor_texto = "#333333"
        
        self.configurar_estilo()
        
        self.conn = sqlite3.connect('financas.db')
        self.cursor = self.conn.cursor()
        self.conn_receitas = sqlite3.connect('financas_receitas.db')
        self.cursor_receitas = self.conn_receitas.cursor()
        
        # --- VARIÁVEIS DE CONTROLE TKINTER ---
        self.id_despesa = tk.StringVar()
        self.descricao = tk.StringVar()
        self.meio_pagamento = tk.StringVar()
        self.conta_despesa = tk.StringVar()
        self.valor = tk.DoubleVar()
        self.num_parcelas = tk.IntVar()
        self.pesquisa_termo = tk.StringVar()
        self.mapa_meses_grafico = {}
        self.total_mes_selecionado_var = tk.StringVar()
        
        self.criar_widgets()
        self.carregar_despesas()

    def abrir_gerenciador_usuarios(self):
        UserManagementWindow(self.root)

    def logout(self):
        """Fecha a janela atual e reinicia o processo de login."""
        # Fecha as conexões com o banco de dados de forma segura
        self.conn.close()
        self.conn_receitas.close()
        # Destrói a janela principal atual
        self.root.destroy()
        # Chama a função principal novamente para exibir a tela de login
        main()

    def on_closing(self):
        if messagebox.askokcancel("Sair", "Deseja sair do sistema?"):
            self.conn.close()
            self.conn_receitas.close()
            self.root.destroy()
            
    def abrir_importador_supabase(self):
        importador_supabase_user.iniciar_importador_supabase(self.root, self)
        self.carregar_despesas()
        
    # ===== FUNÇÕES DE RECEITAS =====
    def abrir_gerenciador_receitas(self):
        GerenciadorReceitas(self.root, self)
    
    def abrir_relatorio_balanco(self, user_id):
        """Abre a janela do relatório de balanço Receita x Despesa."""
        relatorio_balanco_user.iniciar_relatorio_balanco(self.root, user_id)

    def abrir_relatorio_balancofc(self, user_id):
        """Abre a janela do relatório de balanço Receita x Despesa."""
        relatorio_balanco_fluxo_caixa_user.iniciar_relatorio_balanco(self.root, user_id)

    def abrir_gerenciador_categorias_receita(self):
        GerenciadorCategoriasReceita(self.root, self)

    def _criar_dialogo_datas(self, titulo, callback_gerar):
        dialog = tk.Toplevel(self.root)
        dialog.title(titulo)
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Data Inicial:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        data_inicial_entry = DateEntry(frame, width=12, date_pattern='dd/mm/yyyy', locale='pt_BR')
        data_inicial_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        ttk.Label(frame, text="Data Final:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        data_final_entry = DateEntry(frame, width=12, date_pattern='dd/mm/yyyy', locale='pt_BR')
        data_final_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        data_final_entry.set_date(datetime.now())

        def gerar():
            data_inicial = data_inicial_entry.get_date()
            data_final = data_final_entry.get_date()
            if data_inicial > data_final:
                messagebox.showerror("Erro", "A data inicial não pode ser posterior à data final.", parent=dialog)
                return
            dialog.destroy()
            callback_gerar(data_inicial.strftime("%Y-%m-%d"), data_final.strftime("%Y-%m-%d"))

        ttk.Button(frame, text="Gerar Relatório", command=gerar).grid(row=2, column=0, columnspan=2, pady=20)

    def gerar_relatorio_receita_entre_datas(self):
        self._criar_dialogo_datas("Relatório de Receitas por Período", 
                                  lambda d1, d2: self.mostrar_relatorio_receita(d1, d2, tipo='periodo'))
                                  
    def gerar_relatorio_receita_mensal(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Relatório Mensal de Receitas")
        dialog.geometry("300x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Mês:").grid(row=0, column=0, padx=5, pady=5)
        mes_combo = ttk.Combobox(frame, values=[calendar.month_name[i] for i in range(1, 13)], state="readonly", width=15)
        mes_combo.current(datetime.now().month - 1)
        mes_combo.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(frame, text="Ano:").grid(row=1, column=0, padx=5, pady=5)
        ano_var = tk.IntVar(value=datetime.now().year)
        ttk.Spinbox(frame, from_=2000, to=2100, textvariable=ano_var, width=10).grid(row=1, column=1, padx=5, pady=5)

        def gerar():
            mes = mes_combo.current() + 1
            ano = ano_var.get()
            dialog.destroy()
            self.mostrar_relatorio_receita(mes, ano, tipo='mensal')

        ttk.Button(frame, text="Gerar Relatório", command=gerar).grid(row=2, column=0, columnspan=2, pady=20)

    def gerar_relatorio_receita_categoria(self):
        self.cursor_receitas.execute("SELECT nome FROM categorias_receita ORDER BY nome")
        categorias = [row[0] for row in self.cursor_receitas.fetchall()]
        if not categorias:
            messagebox.showinfo("Informação", "Nenhuma categoria de receita cadastrada.", parent=self.root)
            return
            
        dialog = tk.Toplevel(self.root)
        dialog.title("Relatório por Categoria de Receita")
        dialog.geometry("350x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Selecione a Categoria:").pack(pady=5)
        cat_combo = ttk.Combobox(frame, values=categorias, state="readonly")
        cat_combo.pack(pady=5, fill=tk.X, expand=True)
        cat_combo.set(categorias[0])

        def gerar():
            categoria = cat_combo.get()
            dialog.destroy()
            self.mostrar_relatorio_receita(categoria, tipo='categoria')

        ttk.Button(frame, text="Gerar Relatório", command=gerar).pack(pady=10)

    def mostrar_relatorio_receita(self, *args, tipo):
        janela_relatorio = tk.Toplevel(self.root)
        janela_relatorio.geometry("900x600")
        frame_principal = ttk.Frame(janela_relatorio, padding="10")
        frame_principal.pack(fill=tk.BOTH, expand=True)

        query, params, titulo_relatorio = "", (), "Relatório de Receitas"
        col_headers, chart_type = ("Item", "Total (R$)"), "pie"

        if tipo == 'mensal':
            mes, ano = args
            titulo_relatorio = f"Receitas de {calendar.month_name[mes]}/{ano}"
            query = "SELECT conta_receita, SUM(valor) FROM receitas WHERE strftime('%Y-%m', data_recebimento) = ? AND user_id = ? GROUP BY conta_receita ORDER BY SUM(valor) DESC"
            params = (f"{ano}-{mes:02d}", self.user_id)
        elif tipo == 'categoria':
            categoria = args[0]
            titulo_relatorio = f"Evolução da Receita: {categoria}"
            query = "SELECT strftime('%m/%Y', data_recebimento) as mes, SUM(valor) FROM receitas WHERE conta_receita = ? AND user_id = ? GROUP BY strftime('%Y-%m', data_recebimento) ORDER BY strftime('%Y-%m', data_recebimento) ASC"
            params = (categoria, self.user_id)
            col_headers, chart_type = ("Mês/Ano", "Total (R$)"), "line"
        elif tipo == 'periodo':
            d1, d2 = args
            d1_fmt = datetime.strptime(d1, "%Y-%m-%d").strftime("%d/%m/%Y")
            d2_fmt = datetime.strptime(d2, "%Y-%m-%d").strftime("%d/%m/%Y")
            titulo_relatorio = f"Receitas de {d1_fmt} a {d2_fmt}"
            query = "SELECT conta_receita, SUM(valor) FROM receitas WHERE data_recebimento BETWEEN ? AND ? AND user_id = ? GROUP BY conta_receita ORDER BY SUM(valor) DESC"
            params = (d1, d2, self.user_id)
        
        janela_relatorio.title(titulo_relatorio)
        ttk.Label(frame_principal, text=titulo_relatorio, font=('Arial', 16, 'bold')).pack(pady=10)
        
        self.cursor_receitas.execute(query, params)
        resultados = self.cursor_receitas.fetchall()

        if not resultados:
            messagebox.showinfo("Sem Dados", "Nenhum dado encontrado.", parent=janela_relatorio)
            janela_relatorio.destroy()
            return
            
        notebook = ttk.Notebook(frame_principal)
        notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        tab_tabela = ttk.Frame(notebook)
        tab_grafico = ttk.Frame(notebook)
        notebook.add(tab_tabela, text="Tabela")
        notebook.add(tab_grafico, text="Gráfico")

        tree = ttk.Treeview(tab_tabela, columns=('col1', 'col2'), show='headings')
        tree.heading('col1', text=col_headers[0])
        tree.heading('col2', text=col_headers[1])
        tree.column('col2', anchor=tk.E)
        total_geral = 0
        for item, valor in resultados:
            tree.insert("", "end", values=(item, locale.currency(valor, grouping=True)))
            total_geral += valor
        tree.pack(fill=tk.BOTH, expand=True)
        ttk.Label(tab_tabela, text=f"Total: {locale.currency(total_geral, grouping=True)}", font=("Arial", 12, "bold")).pack(pady=5, anchor="e")

        fig = plt.Figure(figsize=(7, 5), dpi=100)
        ax = fig.add_subplot(111)
        labels = [row[0] for row in resultados]
        sizes = [row[1] for row in resultados]
        
        if chart_type == 'pie':
            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, pctdistance=0.85)
            ax.axis('equal')
        elif chart_type == 'line':
            ax.plot(labels, sizes, marker='o', linestyle='-', color=self.cor_primaria)
            ax.set_ylabel("Valor (R$)")
            ax.grid(True, linestyle='--', alpha=0.7)
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')

        canvas = FigureCanvasTkAgg(fig, master=tab_grafico)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        fig.tight_layout()

    # ===== FUNÇÕES DE DESPESA E OUTRAS =====
    
    def atualizar_dados_interface(self):
        try:
            self.carregar_despesas()
            messagebox.showinfo("Atualização Concluída", "Os dados da interface foram atualizados com sucesso!", parent=self.root)
        except Exception as e:
            messagebox.showerror("Erro na Atualização", f"Ocorreu um erro ao tentar atualizar os dados da interface:\n{e}", parent=self.root)
    
    
    def abrir_relatorio_previsao_faturas_cartao(self, user_id):
        """Abre a janela de relatório de Previsão de Faturas de Cartão."""
        relatorio_previsao_faturas_user.iniciar_relatorio_previsao_faturas(self.root, user_id)
   
    def abrir_importador_excel(self, user_id):
        """Abre a janela para importar despesas de uma planilha Excel."""
        importador_excel_user.iniciar_importador_excel(self.root, user_id)
        self.carregar_despesas()
        
    def abrir_gerenciador_fechamento_cartoes(self):
        """Abre a janela para gerenciar as datas de fechamento de faturas de cartões."""
        # Este módulo parece ser global e não depende do usuário, então mantemos como está.
        gerenciar_fechamento_cartoes.iniciar_gerenciador_fechamento_cartoes(self.root)
    
    def abrir_relatorio_orcado_vs_gasto(self, user_id):
        """Abre a janela de relatório Orçado vs. Gasto."""
        relatorio_orcado_vs_gasto.iniciar_relatorio_orcado_vs_gasto(self.root, user_id)
        
    def abrir_gerenciador_orcamento(self, user_id):
        """Abre a janela para gerenciar o orçamento por categoria."""
        gerenciar_orcamento_user.iniciar_gerenciador_orcamento(self.root, user_id)
    
    def abrir_relatorios_simples(self, user_id):
        """Chama a janela de relatórios simples do módulo relatorios1.py."""
        relatorios1_user.iniciar_relatorios(self.root, user_id)
        
    def abrir_relatorios_avancados(self, user_id):
        """Chama a janela de relatórios avançados do módulo relclaude1."""
        relclaude1_user.iniciar_relatorios_avancados(self.root, user_id)
    
    def mostrar_sobre(self):
        messagebox.showinfo(
            "Sobre o Sistema de Gestão Financeira",
            "Sistema de Gerenciamento Financeiro\n\nVersão: 4.0\nCom gestão de usuários."
        )

    def mostrar_ajuda(self):
        messagebox.showinfo(
            "Ajuda",
            "Para cadastrar uma nova despesa, preencha os campos e clique em 'Salvar'.\n\n"
            "Para editar ou excluir, clique em um registro na tabela para carregar seus dados.\n\n"
            "Use os menus para acessar relatórios e configurações. Seus dados são privados."
        )    
     
    def mostrar_grafico_principais_contas(self):
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.ticker import FuncFormatter
            import matplotlib.pyplot as plt
            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment
            from openpyxl.utils import get_column_letter
            
            data_atual = datetime.now()
            mes_atual_ym = data_atual.strftime("%Y-%m")
            mes_atual_formatado = data_atual.strftime("%m/%Y")

            janela_grafico = tk.Toplevel(self.root)
            janela_grafico.title(f"Top 10 Contas - {mes_atual_formatado}")
            janela_grafico.geometry("900x800")
            
            frame_principal = ttk.Frame(janela_grafico, padding="10")
            frame_principal.pack(fill=tk.BOTH, expand=True)

            def mostrar_detalhes_transacao(categoria, mes_ym_selecionado):
                try:
                    detalhes_window = tk.Toplevel(janela_grafico)
                    mes_formatado_titulo = datetime.strptime(mes_ym_selecionado, "%Y-%m").strftime("%m/%Y")
                    detalhes_window.title(f"Detalhes para '{categoria}' em {mes_formatado_titulo}")
                    detalhes_window.geometry("600x400")
                    detalhes_window.transient(janela_grafico)
                    detalhes_window.grab_set()

                    tree_frame = ttk.Frame(detalhes_window, padding="10")
                    tree_frame.pack(fill=tk.BOTH, expand=True)

                    self.cursor.execute("""
                        SELECT strftime('%d/%m/%Y', data_pagamento), descricao, valor
                        FROM despesas
                        WHERE conta_despesa = ? AND strftime('%Y-%m', data_pagamento) = ? AND user_id = ?
                        ORDER BY data_pagamento
                    """, (categoria, mes_ym_selecionado, self.user_id))
                    transacoes = self.cursor.fetchall()

                    cols = ('data', 'descricao', 'valor')
                    tree = ttk.Treeview(tree_frame, columns=cols, show='headings')
                    tree.heading('data', text='Data')
                    tree.heading('descricao', text='Descrição')
                    tree.heading('valor', text='Valor (R$)')
                    tree.column('data', width=100, anchor=tk.CENTER)
                    tree.column('descricao', width=350)
                    tree.column('valor', width=120, anchor=tk.E)
                    
                    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
                    tree.configure(yscrollcommand=scrollbar.set)
                    scrollbar.pack(side='right', fill='y')
                    tree.pack(side='left', fill='both', expand=True)

                    total_categoria = 0
                    for data, desc, valor in transacoes:
                        valor_formatado = locale.currency(valor, grouping=True)
                        tree.insert("", "end", values=(data, desc, valor_formatado))
                        total_categoria += valor
                    
                    total_formatado = locale.currency(total_categoria, grouping=True)
                    ttk.Label(detalhes_window, text=f"Total: {total_formatado}", font=('Arial', 12, 'bold')).pack(pady=5)

                except Exception as e:
                    messagebox.showerror("Erro", f"Erro ao buscar detalhes: {e}", parent=janela_grafico)

            def on_pick(event):
                gid = event.artist.get_gid()
                if gid:
                    categoria, mes_selecionado = gid
                    mostrar_detalhes_transacao(categoria, mes_selecionado)

            frame_selecao = ttk.Frame(frame_principal)
            frame_selecao.pack(fill=tk.X, pady=10)
            
            def obter_meses_disponiveis():
                self.cursor.execute("""
                    SELECT DISTINCT strftime('%Y-%m', data_pagamento) as ano_mes,
                                    strftime('%m/%Y', data_pagamento) as mes_formatado
                    FROM despesas WHERE user_id = ? ORDER BY ano_mes DESC LIMIT 24
                """, (self.user_id,))
                return self.cursor.fetchall()
            
            meses_disponiveis = obter_meses_disponiveis()
            if not meses_disponiveis:
                meses_disponiveis = [(mes_atual_ym,  mes_atual_formatado)]
            
            mapa_meses = {mes_fmt: mes_ym for mes_ym, mes_fmt in meses_disponiveis}
            valores_meses_formatados = [mes_fmt for _, mes_fmt in meses_disponiveis]
            
            ttk.Label(frame_selecao, text="Selecione o mês:").pack(side=tk.LEFT, padx=5)
            mes_combo = ttk.Combobox(frame_selecao, state="readonly", width=10)
            mes_combo['values'] = valores_meses_formatados
            mes_combo.pack(side=tk.LEFT, padx=5)

            if mes_atual_formatado in valores_meses_formatados:
                mes_combo.set(mes_atual_formatado)
            elif valores_meses_formatados:
                mes_combo.current(0)

            frame_grafico = ttk.Frame(frame_principal)
            frame_grafico.pack(fill=tk.BOTH, expand=True, pady=10)
            
            figura = Figure(figsize=(9, 6), dpi=100)
            ax = figura.add_subplot(111)
            
            canvas = FigureCanvasTkAgg(figura, frame_grafico)
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            canvas.mpl_connect('pick_event', on_pick)

            frame_info = ttk.Frame(frame_principal)
            frame_info.pack(fill=tk.X, pady=10)
            label_total = ttk.Label(frame_info, text="", font=('Arial', 12))
            label_total.pack(side=tk.LEFT, padx=10)
            label_percentual = ttk.Label(frame_info, text="", font=('Arial', 12))
            label_percentual.pack(side=tk.RIGHT, padx=10)
       
            def atualizar_grafico(mes_selecionado):
                try:
                    mes_exibicao = next((m_fmt for m_fmt, m_val in mapa_meses.items() if m_val == mes_selecionado), mes_atual_formatado)
                    
                    ax.clear()
                    
                    self.cursor.execute("""
                        SELECT conta_despesa, SUM(valor) as total_valor
                        FROM despesas WHERE strftime('%Y-%m', data_pagamento) = ? AND user_id = ?
                        GROUP BY conta_despesa ORDER BY total_valor DESC LIMIT 10
                    """, (mes_selecionado, self.user_id))
                    resultados = self.cursor.fetchall()

                    if not resultados:
                        ax.text(0.5, 0.5, f"Nenhuma despesa encontrada para {mes_exibicao}", ha='center', va='center', fontsize=14)
                        janela_grafico.title(f"Top 10 Contas - {mes_exibicao}")
                        ax.set_title(f'Top 10 Contas de Despesa - {mes_exibicao}')
                        canvas.draw()
                        label_total.config(text="Total Top 10: R$ 0,00")
                        label_percentual.config(text="Representa 0.0% do total do mês")
                        return

                    self.cursor.execute("SELECT SUM(valor) FROM despesas WHERE strftime('%Y-%m', data_pagamento) = ? AND user_id = ?", (mes_selecionado, self.user_id))
                    total_mes = self.cursor.fetchone()[0] or 0
                    
                    contas = [row[0] for row in resultados]
                    valores = [row[1] for row in resultados]
                    
                    total_top10 = sum(valores)
                    percentual_top10 = (total_top10 / total_mes * 100) if total_mes > 0 else 0
                    
                    cores = plt.cm.get_cmap('tab10', 10).colors

                    barras = ax.barh(contas[::-1], valores[::-1], color=cores, picker=True)

                    for i, barra in enumerate(barras):
                        categoria = contas[::-1][i]
                        barra.set_gid((categoria, mes_selecionado))

                    for barra in barras:
                        largura = barra.get_width()
                        ax.text(largura * 1.01, barra.get_y() + barra.get_height()/2, 
                                locale.currency(largura, grouping=True),
                                va='center', ha='left', fontsize=9)
                    
                    ax.set_title(f'Top 10 Contas de Despesa - {mes_exibicao}')
                    ax.set_xlabel('Valor Total (R$)')
                    ax.set_ylabel('Conta de Despesa')
                    ax.grid(True, linestyle='--', alpha=0.7, axis='x')
                    ax.set_xlim(right=max(valores) * 1.18)

                    def formatar_reais(x, pos):
                        return locale.currency(x, symbol=False, grouping=True)
                    ax.xaxis.set_major_formatter(FuncFormatter(formatar_reais))
                    
                    figura.tight_layout()
                    canvas.draw()
                    
                    label_total.config(text=f"Total Top 10: {locale.currency(total_top10, grouping=True)}")
                    label_percentual.config(text=f"Representa {percentual_top10:.1f}% do total do mês")
                
                except Exception as e:
                    messagebox.showerror("Erro", f"Erro ao atualizar gráfico: {e}")
           
            def on_mes_change(event):
                mes_selecionado_fmt = mes_combo.get()
                mes_valor_ym = mapa_meses.get(mes_selecionado_fmt)
                if not mes_valor_ym: return
                atualizar_grafico(mes_valor_ym)
                janela_grafico.title(f"Top 10 Contas - {mes_selecionado_fmt}")
            
            mes_combo.bind("<<ComboboxSelected>>", on_mes_change)
            
            mes_inicial_formatado = mes_combo.get()
            if mes_inicial_formatado:
                mes_inicial_ym = mapa_meses.get(mes_inicial_formatado)
                if mes_inicial_ym:
                    janela_grafico.title(f"Top 10 Contas - {mes_inicial_formatado}")
                    atualizar_grafico(mes_inicial_ym)
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exibir gráfico: {e}")
    
    def configurar_estilo(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', background=self.cor_primaria, foreground='white', font=('Arial', 10, 'bold'), padding=5)
        style.configure('TLabel', background=self.cor_fundo, foreground=self.cor_texto, font=('Arial', 10))
        style.configure('TEntry', fieldbackground='white', font=('Arial', 10))
        style.configure('TFrame', background=self.cor_fundo)
        style.configure('Treeview', background='white', fieldbackground='white', font=('Arial', 9))
        style.configure('Treeview.Heading', font=('Arial', 10, 'bold'), background=self.cor_secundaria)
    
    def carregar_categorias(self):
        self.cursor.execute("SELECT nome FROM categorias ORDER BY nome")
        return [categoria[0] for categoria in self.cursor.fetchall()]
    
    def carregar_meios_pagamento(self):
        self.cursor.execute("SELECT nome FROM meios_pagamento ORDER BY nome")
        return [meio[0] for meio in self.cursor.fetchall()]
    
    def criar_widgets(self):
        self.frame_principal = ttk.Frame(self.root)
        self.frame_principal.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.frame_form = ttk.Frame(self.frame_principal, style='TFrame')
        self.frame_form.pack(side=tk.LEFT, fill=tk.BOTH, padx=10, pady=10)
        
        self.frame_tabela = ttk.Frame(self.frame_principal, style='TFrame')
        self.frame_tabela.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(self.frame_form, text="Controle Financeiro", font=('Arial', 16, 'bold'), style='TLabel').grid(row=0, column=0, columnspan=2, pady=10)
        
        ttk.Label(self.frame_form, text="ID:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(self.frame_form, textvariable=self.id_despesa, state='readonly', width=5).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(self.frame_form, text="Descrição:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(self.frame_form, textvariable=self.descricao, width=30).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(self.frame_form, text="Meio de Pagamento:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.combo_meio_pagamento = ttk.Combobox(self.frame_form, textvariable=self.meio_pagamento, width=20, state='readonly')
        self.combo_meio_pagamento['values'] = self.carregar_meios_pagamento()
        self.combo_meio_pagamento.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(self.frame_form, text="Categoria:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.combo_conta_despesa = ttk.Combobox(self.frame_form, textvariable=self.conta_despesa, width=20, state='readonly')
        self.combo_conta_despesa['values'] = self.carregar_categorias()
        self.combo_conta_despesa.grid(row=4, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(self.frame_form, text="Valor (R$):").grid(row=5, column=0, sticky=tk.W, pady=5)
        ttk.Entry(self.frame_form, textvariable=self.valor, width=15).grid(row=5, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(self.frame_form, text="Parcelas:").grid(row=6, column=0, sticky=tk.W, pady=5)
        ttk.Spinbox(self.frame_form, from_=1, to=48, textvariable=self.num_parcelas, width=5).grid(row=6, column=1, sticky=tk.W, pady=5)
        self.num_parcelas.set(1)
        
        ttk.Label(self.frame_form, text="Data Pagamento:").grid(row=7, column=0, sticky=tk.W, pady=5)
        self.data_entry = DateEntry(self.frame_form, width=12, background=self.cor_primaria, foreground='white', borderwidth=2, date_pattern='dd/mm/yyyy', locale='pt_BR')
        self.data_entry.grid(row=7, column=1, sticky=tk.W, pady=5)
        self.data_entry.set_date(datetime.now())
        
        botoes_frame = ttk.Frame(self.frame_form)
        botoes_frame.grid(row=8, column=0, columnspan=2, pady=15)
        
        self.btn_salvar = ttk.Button(botoes_frame, text="Salvar", command=self.salvar_despesa)
        self.btn_salvar.grid(row=0, column=0, padx=5)
        
        self.btn_atualizar = ttk.Button(botoes_frame, text="Atualizar", command=self.atualizar_despesa, state='disabled')
        self.btn_atualizar.grid(row=0, column=1, padx=5)
        
        self.btn_excluir = ttk.Button(botoes_frame, text="Excluir", command=self.excluir_despesa, state='disabled')
        self.btn_excluir.grid(row=0, column=2, padx=5)
        
        self.btn_limpar = ttk.Button(botoes_frame, text="Limpar", command=self.limpar_campos)
        self.btn_limpar.grid(row=0, column=3, padx=5)
                      
        frame_pesquisa = ttk.LabelFrame(self.frame_form, text="Pesquisar")
        frame_pesquisa.grid(row=9, column=0, columnspan=2, sticky=tk.W+tk.E, pady=10)
        
        ttk.Entry(frame_pesquisa, textvariable=self.pesquisa_termo, width=20).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(frame_pesquisa, text="Buscar", command=self.pesquisar_despesa).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(frame_pesquisa, text="Mostrar Todos", command=self.carregar_despesas).grid(row=0, column=2, padx=5, pady=5)
        
        self.tree_frame = ttk.LabelFrame(self.frame_tabela, text="Registros de Despesas")
        self.tree_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(self.tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tabela = ttk.Treeview(self.tree_frame, yscrollcommand=scrollbar.set)
        
        self.tabela['columns'] = ('id', 'descricao', 'meio_pagamento', 'conta_despesa', 'valor', 'parcelas', 'data')
        
        self.tabela.column('#0', width=0, stretch=tk.NO)
        self.tabela.column('id', anchor=tk.CENTER, width=50)
        self.tabela.column('descricao', anchor=tk.W, width=200)
        self.tabela.column('meio_pagamento', anchor=tk.W, width=120)
        self.tabela.column('conta_despesa', anchor=tk.W, width=120)
        self.tabela.column('valor', anchor=tk.E, width=100)
        self.tabela.column('parcelas', anchor=tk.CENTER, width=70)
        self.tabela.column('data', anchor=tk.CENTER, width=100)
        
        self.tabela.heading('#0', text='', anchor=tk.CENTER)
        self.tabela.heading('id', text='ID', anchor=tk.CENTER)
        self.tabela.heading('descricao', text='Descrição', anchor=tk.CENTER)
        self.tabela.heading('meio_pagamento', text='Meio Pagamento', anchor=tk.CENTER)
        self.tabela.heading('conta_despesa', text='Categoria', anchor=tk.CENTER)
        self.tabela.heading('valor', text='Valor (R$)', anchor=tk.CENTER)
        self.tabela.heading('parcelas', text='Parcelas', anchor=tk.CENTER)
        self.tabela.heading('data', text='Data', anchor=tk.CENTER)
        
        self.tabela.bind("<ButtonRelease-1>", self.selecionar_item)
        
        self.tabela.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.config(command=self.tabela.yview)
        
        self.frame_grafico = ttk.LabelFrame(self.frame_tabela, text="Resumo de Gastos")
        self.frame_grafico.pack(fill=tk.BOTH, expand=True, pady=10)

        frame_controles_grafico = ttk.Frame(self.frame_grafico)
        frame_controles_grafico.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(frame_controles_grafico, text="Mês:").pack(side=tk.LEFT, padx=(0, 5))
        self.combo_mes_grafico = ttk.Combobox(frame_controles_grafico, state="readonly", width=10)
        self.combo_mes_grafico.pack(side=tk.LEFT)
        self.combo_mes_grafico.bind("<<ComboboxSelected>>", self.atualizar_grafico)
        
        label_total_mes = ttk.Label(frame_controles_grafico, textvariable=self.total_mes_selecionado_var, font=('Arial', 9, 'bold'))
        label_total_mes.pack(side=tk.LEFT, padx=(15, 0))

        self.figura_grafico = plt.Figure(figsize=(5, 4), dpi=100)
        self.canvas_grafico = FigureCanvasTkAgg(self.figura_grafico, self.frame_grafico)
        self.canvas_grafico.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.atualizar_grafico()
    
    def abrir_gerenciador(self, user_id):
        """Abre a janela de configurações de Categorias e Pagamentos."""
        # Supondo que o módulo 'configuracao' também foi adaptado para receber o user_id
        config_window = configuracao.GerenciadorConfiguracoes(self.root, False, user_id)
        self.root.wait_window(config_window.root)
        self.combo_meio_pagamento['values'] = self.carregar_meios_pagamento()
        self.combo_conta_despesa['values'] = self.carregar_categorias()

    def abrir_gerenciador2(self, user_id):
        """Abre a janela de gerenciamento de Banco de Dados."""
        # Supondo que o módulo 'MENUBD' também foi adaptado para receber o user_id
        config_window = MENUBD_user.GerenciadorConfiguracoes2(self.root, False, user_id)
        self.root.wait_window(config_window.root)
        self.combo_meio_pagamento['values'] = self.carregar_meios_pagamento()
        self.combo_conta_despesa['values'] = self.carregar_categorias()  
    
    def gerar_relatorio_entre_datas(self):
        # Esta função agora está completa e chama a 'mostrar_relatorio_entre_datas'
        self._criar_dialogo_datas("Relatório de Despesas por Período",
                                  lambda d1, d2: self.mostrar_relatorio_entre_datas(d1, d2))

    def mostrar_relatorio_entre_datas(self, data_inicial, data_final):
        try:
            data_inicial_formatada = datetime.strptime(data_inicial, "%Y-%m-%d").strftime("%d/%m/%Y")
            data_final_formatada = datetime.strptime(data_final, "%Y-%m-%d").strftime("%d/%m/%Y")
            
            self.cursor.execute("""
                SELECT conta_despesa, SUM(valor) as total_valor, COUNT(*) as total_registros
                FROM despesas
                WHERE data_pagamento BETWEEN ? AND ? AND user_id = ?
                GROUP BY conta_despesa ORDER BY total_valor DESC
            """, (data_inicial, data_final, self.user_id))
            
            resultados = self.cursor.fetchall()
            
            if not resultados:
                messagebox.showinfo("Relatório", f"Nenhuma despesa encontrada no período de {data_inicial_formatada} a {data_final_formatada}.")
                return
                
            total_geral = sum(row[1] for row in resultados)
            
            janela_relatorio = tk.Toplevel(self.root)
            janela_relatorio.title(f"Relatório de {data_inicial_formatada} a {data_final_formatada}")
            janela_relatorio.geometry("900x600")
            
            frame_principal = ttk.Frame(janela_relatorio, padding="10")
            frame_principal.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(frame_principal, text=f"Relatório de Despesas - {data_inicial_formatada} a {data_final_formatada}", font=('Arial', 16, 'bold')).pack(pady=10)
            ttk.Label(frame_principal, text=f"Total de Despesas: {locale.currency(total_geral, grouping=True)}", font=('Arial', 12)).pack(pady=5)
            
            notebook = ttk.Notebook(frame_principal)
            notebook.pack(fill=tk.BOTH, expand=True, pady=10)
            
            tab_tabela = ttk.Frame(notebook)
            notebook.add(tab_tabela, text="Tabela")
            tab_grafico = ttk.Frame(notebook)
            notebook.add(tab_grafico, text="Gráfico")
            
            tree_frame = ttk.Frame(tab_tabela)
            tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            scrollbar = ttk.Scrollbar(tree_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            colunas = ('categoria', 'total', 'registros', 'percentual')
            tabela = ttk.Treeview(tree_frame, columns=colunas, show='headings', yscrollcommand=scrollbar.set)
            
            tabela.heading('categoria', text='Categoria')
            tabela.heading('total', text='Total (R$)')
            tabela.heading('registros', text='Qtd. Registros')
            tabela.heading('percentual', text='% do Total')
            
            tabela.column('categoria', width=150)
            tabela.column('total', width=100, anchor=tk.E)
            tabela.column('registros', width=100, anchor=tk.CENTER)
            tabela.column('percentual', width=100, anchor=tk.CENTER)
            
            for row in resultados:
                categoria, total, registros = row
                percentual = (total / total_geral) * 100
                tabela.insert('', tk.END, values=(categoria, locale.currency(total, grouping=True), registros, f"{percentual:.1f}%"))
                
            tabela.pack(fill=tk.BOTH, expand=True)
            scrollbar.config(command=tabela.yview)
            
            figura = plt.Figure(figsize=(7, 5), dpi=100)
            ax = figura.add_subplot(111)
            
            categorias = [row[0] for row in resultados]
            valores = [row[1] for row in resultados]
            
            wedges, texts, autotexts = ax.pie(valores, autopct='%1.1f%%', startangle=90)
            
            ax.set_title(f'Distribuição de Despesas - {data_inicial_formatada} a {data_final_formatada}')
            ax.axis('equal')
            
            ax.legend(wedges, categorias, title="Categorias", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
            figura.tight_layout()
            
            canvas = FigureCanvasTkAgg(figura, tab_grafico)
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exibir relatório: {e}")

    def gerar_relatorio_mensal_periodo(self):
        self._criar_dialogo_datas("Relatório de Despesas por Mês", 
                                  lambda d1, d2: self.mostrar_relatorio_mensal_periodo(d1, d2))

    def mostrar_relatorio_mensal_periodo(self, data_inicial, data_final):
        try:
            data_inicial_formatada = datetime.strptime(data_inicial, "%Y-%m-%d").strftime("%d/%m/%Y")
            data_final_formatada = datetime.strptime(data_final, "%Y-%m-%d").strftime("%d/%m/%Y")
            
            self.cursor.execute("""
                SELECT strftime('%Y-%m', data_pagamento) as ano_mes, strftime('%m/%Y', data_pagamento) as mes_ano_formatado,
                       SUM(valor) as total_valor, COUNT(*) as total_registros
                FROM despesas
                WHERE data_pagamento BETWEEN ? AND ? AND user_id = ?
                GROUP BY ano_mes ORDER BY ano_mes
            """, (data_inicial, data_final, self.user_id))
            
            resultados = self.cursor.fetchall()
            
            if not resultados:
                messagebox.showinfo("Relatório", f"Nenhuma despesa encontrada no período.")
                return
                
            total_geral = sum(row[2] for row in resultados)
            
            janela_relatorio = tk.Toplevel(self.root)
            janela_relatorio.title(f"Relatório Mensal - {data_inicial_formatada} a {data_final_formatada}")
            janela_relatorio.geometry("900x600")
            
            frame_principal = ttk.Frame(janela_relatorio, padding="10")
            frame_principal.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(frame_principal, text=f"Despesas Mensais - {data_inicial_formatada} a {data_final_formatada}", font=('Arial', 16, 'bold')).pack(pady=10)
            ttk.Label(frame_principal, text=f"Total de Despesas: {locale.currency(total_geral, grouping=True)}", font=('Arial', 12)).pack(pady=5)
            
            notebook = ttk.Notebook(frame_principal)
            notebook.pack(fill=tk.BOTH, expand=True, pady=10)
            
            tab_tabela = ttk.Frame(notebook)
            notebook.add(tab_tabela, text="Tabela")
            tab_grafico = ttk.Frame(notebook)
            notebook.add(tab_grafico, text="Gráfico de Barras")
            tab_grafico_linha = ttk.Frame(notebook)
            notebook.add(tab_grafico_linha, text="Evolução (Linha)")
            
            tree_frame = ttk.Frame(tab_tabela)
            tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            scrollbar = ttk.Scrollbar(tree_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            colunas = ('mes_ano', 'total', 'registros', 'percentual')
            tabela = ttk.Treeview(tree_frame, columns=colunas, show='headings', yscrollcommand=scrollbar.set)
            
            tabela.heading('mes_ano', text='Mês/Ano')
            tabela.heading('total', text='Total (R$)')
            tabela.heading('registros', text='Qtd. Registros')
            tabela.heading('percentual', text='% do Total')
            
            tabela.column('mes_ano', width=100, anchor=tk.CENTER)
            tabela.column('total', width=150, anchor=tk.E)
            tabela.column('registros', width=100, anchor=tk.CENTER)
            tabela.column('percentual', width=100, anchor=tk.CENTER)
            
            for row in resultados:
                ano_mes, mes_ano_formatado, total, registros = row
                percentual = (total / total_geral) * 100
                tabela.insert('', tk.END, values=(mes_ano_formatado, locale.currency(total, grouping=True), registros, f"{percentual:.1f}%"))
                
            tabela.pack(fill=tk.BOTH, expand=True)
            scrollbar.config(command=tabela.yview)
            
            meses = [row[1] for row in resultados]
            valores = [row[2] for row in resultados]

            figura_barra = plt.Figure(figsize=(7, 5), dpi=100)
            ax_barra = figura_barra.add_subplot(111)
            barras = ax_barra.bar(meses, valores, color=self.cor_primaria)
            ax_barra.set_title(f'Despesas Mensais - {data_inicial_formatada} a {data_final_formatada}')
            ax_barra.set_ylabel('Valor Total (R$)')
            plt.setp(ax_barra.get_xticklabels(), rotation=45, ha='right')
            figura_barra.tight_layout()
            canvas_barra = FigureCanvasTkAgg(figura_barra, tab_grafico)
            canvas_barra.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            figura_linha = plt.Figure(figsize=(7, 5), dpi=100)
            ax_linha = figura_linha.add_subplot(111)
            ax_linha.plot(meses, valores, marker='o', linestyle='-', color=self.cor_primaria)
            ax_linha.set_title(f'Evolução de Despesas Mensais')
            ax_linha.set_ylabel('Valor Total (R$)')
            ax_linha.grid(True, linestyle='--', alpha=0.7)
            plt.setp(ax_linha.get_xticklabels(), rotation=45, ha='right')
            figura_linha.tight_layout()
            canvas_linha = FigureCanvasTkAgg(figura_linha, tab_grafico_linha)
            canvas_linha.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exibir relatório: {e}")
    
    def _repovoar_combo_meses_grafico(self):
        try:
            selecao_previa = self.combo_mes_grafico.get()
            mes_atual_display = datetime.now().strftime('%m/%Y')
            mes_atual_query = datetime.now().strftime('%Y-%m')

            self.cursor.execute("""
                SELECT DISTINCT strftime('%Y-%m', data_pagamento) as mes_query,
                                strftime('%m/%Y', data_pagamento) as mes_display
                FROM despesas WHERE user_id = ? ORDER BY mes_query DESC
            """, (self.user_id,))
            meses_disponiveis = self.cursor.fetchall()
            
            self.mapa_meses_grafico = {display: query for query, display in meses_disponiveis}
            valores_combo = [display for _, display in meses_disponiveis]
            
            if mes_atual_display not in self.mapa_meses_grafico:
                valores_combo.insert(0, mes_atual_display)
                self.mapa_meses_grafico[mes_atual_display] = mes_atual_query
            
            self.combo_mes_grafico['values'] = valores_combo

            if selecao_previa in valores_combo:
                self.combo_mes_grafico.set(selecao_previa)
            else:
                self.combo_mes_grafico.set(mes_atual_display)
        except Exception as e:
            print(f"Erro ao repovoar combo de meses: {e}")

    def carregar_despesas(self):
        for item in self.tabela.get_children():
            self.tabela.delete(item)
        try:
            self.cursor.execute("""
                SELECT id, descricao, meio_pagamento, conta_despesa, valor, 
                       num_parcelas, strftime('%d/%m/%Y', data_pagamento) as data_formatada
                FROM despesas WHERE user_id = ? ORDER BY data_pagamento DESC
            """, (self.user_id,))
            
            for row in self.cursor.fetchall():
                valor_formatado = f"R$ {row[4]:.2f}".replace('.', ',')
                self.tabela.insert('', tk.END, values=(row[0], row[1], row[2], row[3], valor_formatado, row[5], row[6]))

            self._repovoar_combo_meses_grafico()
            self.atualizar_grafico()
        except sqlite3.Error as e:
            messagebox.showerror("Erro de BD", f"Erro ao carregar despesas: {e}")
    
    def limpar_campos(self):
        self.id_despesa.set('')
        self.descricao.set('')
        self.meio_pagamento.set('')
        self.conta_despesa.set('')
        self.valor.set(0.0)
        self.num_parcelas.set(1)
        self.data_entry.set_date(datetime.now())
        self.btn_atualizar['state'] = 'disabled'
        self.btn_excluir['state'] = 'disabled'
        self.btn_salvar['state'] = 'normal'
    
    def validar_campos(self):
        if not all([self.descricao.get().strip(), self.meio_pagamento.get().strip(), self.conta_despesa.get().strip()]):
            messagebox.showwarning("Campos Obrigatórios", "Descrição, Meio de Pagamento e Categoria são obrigatórios.")
            return False
        try:
            if float(self.valor.get()) <= 0:
                messagebox.showwarning("Valor Inválido", "O valor deve ser maior que zero.")
                return False
        except ValueError:
            messagebox.showwarning("Valor Inválido", "Formato de valor inválido.")
            return False
        return True
    
    def salvar_despesa(self):
        if not self.validar_campos(): return
        try:
            data_pagamento = self.data_entry.get_date().strftime('%Y-%m-%d')
            self.cursor.execute("""
                INSERT INTO despesas (descricao, meio_pagamento, conta_despesa, valor,
                                     num_parcelas, data_registro, data_pagamento, user_id)
                VALUES (?, ?, ?, ?, ?, date('now'), ?, ?)
            """, (
                self.descricao.get().strip(), self.meio_pagamento.get().strip(),
                self.conta_despesa.get().strip(), self.valor.get(),
                self.num_parcelas.get(), data_pagamento, self.user_id
            ))
            self.conn.commit()
            messagebox.showinfo("Sucesso", "Despesa registrada com sucesso!")
            self.limpar_campos()
            self.carregar_despesas()
        except sqlite3.Error as e:
            messagebox.showerror("Erro ao Salvar", f"Ocorreu um erro: {e}")
    
    def selecionar_item(self, event):
        try:
            selected_item = self.tabela.selection()[0]
            item = self.tabela.item(selected_item)
            values = item['values']
            if not values: return
            self.limpar_campos()
            self.id_despesa.set(values[0])
            self.descricao.set(values[1])
            self.meio_pagamento.set(values[2])
            self.conta_despesa.set(values[3])
            valor_str = values[4].replace('R$', '').replace(' ', '').replace(',', '.')
            self.valor.set(float(valor_str))
            self.num_parcelas.set(values[5])
            dia, mes, ano = map(int, values[6].split('/'))
            self.data_entry.set_date(datetime(ano, mes, dia))
            self.btn_atualizar['state'] = 'normal'
            self.btn_excluir['state'] = 'normal'
            self.btn_salvar['state'] = 'disabled'
        except IndexError:
            pass
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao selecionar item: {e}")
    
    def atualizar_despesa(self):
        if not self.validar_campos() or not self.id_despesa.get(): return
        if not messagebox.askyesno("Confirmar Atualização", "Tem certeza?"): return
        try:
            data_pagamento = self.data_entry.get_date().strftime('%Y-%m-%d')
            self.cursor.execute("""
                UPDATE despesas SET descricao = ?, meio_pagamento = ?, conta_despesa = ?,
                    valor = ?, num_parcelas = ?, data_pagamento = ?
                WHERE id = ? AND user_id = ?
            """, (
                self.descricao.get().strip(), self.meio_pagamento.get().strip(),
                self.conta_despesa.get().strip(), self.valor.get(),
                self.num_parcelas.get(), data_pagamento, self.id_despesa.get(), self.user_id
            ))
            self.conn.commit()
            messagebox.showinfo("Sucesso", "Registro atualizado!")
            self.limpar_campos()
            self.carregar_despesas()
        except sqlite3.Error as e:
            messagebox.showerror("Erro ao Atualizar", f"Ocorreu um erro: {e}")
    
    def excluir_despesa(self):
        if not self.id_despesa.get():
            messagebox.showwarning("Selecione um Registro", "Por favor, selecione um registro para excluir.")
            return
            
        if not messagebox.askyesno("Confirmar Exclusão", "Tem certeza? Esta ação não pode ser desfeita."): return
        try:
            self.cursor.execute("DELETE FROM despesas WHERE id = ? AND user_id = ?", (self.id_despesa.get(), self.user_id))
            self.conn.commit()
            
            messagebox.showinfo("Sucesso", "Registro excluído com sucesso!")
            
            self.limpar_campos()
            self.carregar_despesas()
            
        except sqlite3.Error as e:
            messagebox.showerror("Erro ao Excluir", f"Ocorreu um erro: {e}")
    
    def pesquisar_despesa(self):
        termo = self.pesquisa_termo.get().strip()
        
        if not termo:
            messagebox.showinfo("Pesquisa", "Por favor, digite um termo para pesquisar.")
            return
            
        for item in self.tabela.get_children():
            self.tabela.delete(item)
            
        try:
            self.cursor.execute("""
                SELECT id, descricao, meio_pagamento, conta_despesa, valor, 
                       num_parcelas, strftime('%d/%m/%Y', data_pagamento) as data_formatada
                FROM despesas
                WHERE user_id = ? AND (descricao LIKE ? OR conta_despesa LIKE ? OR meio_pagamento LIKE ?)
                ORDER BY data_pagamento DESC
            """, (self.user_id, f'%{termo}%', f'%{termo}%', f'%{termo}%'))
            
            resultados = self.cursor.fetchall()
            
            for row in resultados:
                valor_formatado = f"R$ {row[4]:.2f}".replace('.', ',')
                self.tabela.insert('', tk.END, values=(row[0], row[1], row[2], row[3], valor_formatado, row[5], row[6]))
                
            if not resultados:
                messagebox.showinfo("Pesquisa", "Nenhum resultado encontrado para o termo informado.")
                
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Pesquisa", f"Erro ao pesquisar despesas: {e}")

    def on_bar_pick(self, event):
        try:
            gid = event.artist.get_gid()
            if not gid: return
            categoria_selecionada, ano_mes = gid
            self.mostrar_detalhes_categoria_mes(categoria_selecionada, ano_mes)
        except Exception: pass

    def mostrar_detalhes_categoria_mes(self, categoria, ano_mes):
        try:
            mes_ano_formatado = datetime.strptime(ano_mes, "%Y-%m").strftime("%m/%Y")
            
            janela_detalhes = tk.Toplevel(self.root)
            janela_detalhes.title(f"Detalhes para '{categoria}' em {mes_ano_formatado}")
            janela_detalhes.geometry("600x400")
            janela_detalhes.transient(self.root)
            janela_detalhes.grab_set()

            frame_detalhes = ttk.Frame(janela_detalhes, padding="10")
            frame_detalhes.pack(fill=tk.BOTH, expand=True)

            self.cursor.execute("""
                SELECT strftime('%d/%m/%Y', data_pagamento), descricao, valor
                FROM despesas
                WHERE conta_despesa = ? AND strftime('%Y-%m', data_pagamento) = ? AND user_id = ?
                ORDER BY data_pagamento
            """, (categoria, ano_mes, self.user_id))
            
            transacoes = self.cursor.fetchall()

            if not transacoes:
                ttk.Label(frame_detalhes, text="Nenhuma transação encontrada.").pack()
                return

            colunas = ('data', 'descricao', 'valor')
            tabela_detalhes = ttk.Treeview(frame_detalhes, columns=colunas, show='headings')
            
            tabela_detalhes.heading('data', text='Data')
            tabela_detalhes.heading('descricao', text='Descrição')
            tabela_detalhes.heading('valor', text='Valor (R$)')

            tabela_detalhes.column('data', width=100, anchor=tk.CENTER)
            tabela_detalhes.column('descricao', width=300, anchor=tk.W)
            tabela_detalhes.column('valor', width=120, anchor=tk.E)

            total = 0
            for data, desc, valor in transacoes:
                valor_formatado = locale.currency(valor, grouping=True)
                tabela_detalhes.insert('', tk.END, values=(data, desc, valor_formatado))
                total += valor

            tabela_detalhes.pack(fill=tk.BOTH, expand=True)

            total_formatado = locale.currency(total, grouping=True)
            ttk.Label(frame_detalhes, text=f"Total: {total_formatado}", font=('Arial', 12, 'bold')).pack(pady=10)

        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível carregar os detalhes: {e}")

    def atualizar_grafico(self, event=None):
        try:
            self.figura_grafico.clear()
            ax = self.figura_grafico.add_subplot(111)

            mes_exibicao = self.combo_mes_grafico.get()
            if not mes_exibicao:
                mes_exibicao = datetime.now().strftime('%m/%Y')
            
            mes_para_query = self.mapa_meses_grafico.get(mes_exibicao, datetime.now().strftime('%Y-%m'))
            self.frame_grafico.config(text=f"Resumo de Gastos ({mes_exibicao})")

            self.cursor.execute("SELECT SUM(valor) FROM despesas WHERE strftime('%Y-%m', data_pagamento) = ? AND user_id = ?", (mes_para_query, self.user_id))
            total_mes = self.cursor.fetchone()[0] or 0.0
            self.total_mes_selecionado_var.set(f"Total do Mês: {locale.currency(total_mes, grouping=True)}")

            self.cursor.execute("""
                SELECT conta_despesa, SUM(valor) as total
                FROM despesas WHERE strftime('%Y-%m', data_pagamento) = ? AND user_id = ?
                GROUP BY conta_despesa ORDER BY total DESC LIMIT 10
            """, (mes_para_query, self.user_id))
            
            resultados = self.cursor.fetchall()
            
            if resultados:
                categorias = [row[0] for row in resultados]
                valores = [row[1] for row in resultados]
                
                cores_grafico = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
                
                barras = ax.bar(categorias, valores, color=cores_grafico[:len(categorias)], picker=True)

                for i, barra in enumerate(barras):
                    barra.set_gid((categorias[i], mes_para_query))
                    altura = barra.get_height()
                    ax.text(barra.get_x() + barra.get_width() / 2., altura, locale.currency(altura, symbol=True, grouping=True), ha='center', va='bottom', rotation=0, fontsize=8)

                ax.set_title(f'Top 10 Categorias ({mes_exibicao})')
                ax.set_ylabel('Valor Total (R$)')
                ax.set_xlabel('Categoria')
                
                formatter = FuncFormatter(lambda y, _: locale.currency(y, symbol=True, grouping=True))
                ax.yaxis.set_major_formatter(formatter)

                plt.setp(ax.get_xticklabels(), rotation=45, ha='right', fontsize=8)
                ax.margins(y=0.15)
                
            else:
                ax.text(0.5, 0.5, f'Sem dados para o mês {mes_exibicao}', horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
                ax.set_title(f'Top 10 Categorias ({mes_exibicao})')
                ax.axis('off')

            self.canvas_grafico.mpl_connect('pick_event', self.on_bar_pick)
            self.figura_grafico.tight_layout()
            self.canvas_grafico.draw()
            
        except Exception as e:
            print(f"Erro ao atualizar gráfico: {e}")
    
    def gerar_relatorio_mensal(self):
        try:
            meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
            
            dialog = tk.Toplevel(self.root)
            dialog.title("Relatório Mensal")
            dialog.geometry("300x200")
            dialog.resizable(False, False)
            
            mes_var = tk.IntVar(value=datetime.now().month)
            ano_var = tk.IntVar(value=datetime.now().year)
            
            frame = ttk.Frame(dialog, padding="10")
            frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(frame, text="Mês:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
            mes_combo = ttk.Combobox(frame, values=meses, width=15, state='readonly')
            mes_combo.current(datetime.now().month - 1)
            mes_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
            
            ttk.Label(frame, text="Ano:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
            ano_spin = ttk.Spinbox(frame, from_=2000, to=2100, textvariable=ano_var, width=10)
            ano_spin.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
            
            def gerar():
                mes_indice = meses.index(mes_combo.get()) + 1
                ano = ano_var.get()
                self.mostrar_relatorio_mensal(mes_indice, ano)
                dialog.destroy()
            
            ttk.Button(frame, text="Gerar Relatório", command=gerar).grid(row=2, column=0, columnspan=2, pady=20)
            
            dialog.transient(self.root)
            dialog.wait_visibility()
            dialog.grab_set()
            dialog.focus_set()
            dialog.wait_window()
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao gerar relatório: {e}")
   
    def mostrar_relatorio_mensal(self, mes, ano):
        try:
            primeiro_dia = f"{ano}-{mes:02d}-01"
            ultimo_dia = f"{ano}-{mes:02d}-{calendar.monthrange(ano, mes)[1]}"
            
            self.cursor.execute("""
                SELECT conta_despesa, SUM(valor) as total_valor, COUNT(*) as total_registros
                FROM despesas
                WHERE data_pagamento BETWEEN ? AND ? AND user_id = ?
                GROUP BY conta_despesa ORDER BY total_valor DESC
            """, (primeiro_dia, ultimo_dia, self.user_id))
            
            resultados = self.cursor.fetchall()
            
            if not resultados:
                messagebox.showinfo("Relatório", f"Nenhuma despesa encontrada para {calendar.month_name[mes]} de {ano}.")
                return
                
            total_geral = sum(row[1] for row in resultados)
            
            janela_relatorio = tk.Toplevel(self.root)
            janela_relatorio.title(f"Relatório de {calendar.month_name[mes]} de {ano}")
            janela_relatorio.geometry("900x700")
            
            frame_principal = ttk.Frame(janela_relatorio, padding="10")
            frame_principal.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(frame_principal, text=f"Relatório de Despesas - {calendar.month_name[mes]} de {ano}", font=('Arial', 16, 'bold')).pack(pady=10)
            ttk.Label(frame_principal, text=f"Total de Despesas: {locale.currency(total_geral, grouping=True)}", font=('Arial', 12)).pack(pady=5)
            
            notebook = ttk.Notebook(frame_principal)
            notebook.pack(fill=tk.BOTH, expand=True, pady=10)
            
            tab_tabela = ttk.Frame(notebook)
            notebook.add(tab_tabela, text="Tabela")
            tab_grafico = ttk.Frame(notebook)
            notebook.add(tab_grafico, text="Gráfico")
            
            tree_frame = ttk.Frame(tab_tabela)
            tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            scrollbar = ttk.Scrollbar(tree_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            tabela = ttk.Treeview(tree_frame, columns=('categoria', 'total', 'registros', 'percentual'), show='headings', yscrollcommand=scrollbar.set)
            
            tabela.heading('categoria', text='Categoria')
            tabela.heading('total', text='Total (R$)')
            tabela.heading('registros', text='Qtd. Registros')
            tabela.heading('percentual', text='% do Total')
            
            tabela.column('categoria', width=250, anchor=tk.W)
            tabela.column('total', width=120, anchor=tk.E)
            tabela.column('registros', width=100, anchor=tk.CENTER)
            tabela.column('percentual', width=100, anchor=tk.CENTER)
            
            for row in resultados:
                categoria, total, registros = row
                percentual = (total / total_geral) * 100 if total_geral else 0
                tabela.insert('', tk.END, values=(categoria, locale.currency(total, grouping=True), registros, f"{percentual:.1f}%"))
                
            tabela.pack(fill=tk.BOTH, expand=True)
            scrollbar.config(command=tabela.yview)
            
            figura = plt.Figure(figsize=(8, 6), dpi=100)
            ax = figura.add_subplot(111)
            
            categorias = [row[0] for row in resultados]
            valores = [row[1] for row in resultados]

            wedges, _, _ = ax.pie(valores, autopct='%1.1f%%', startangle=140)
            
            ax.set_title(f'Distribuição de Despesas - {calendar.month_name[mes]} de {ano}', pad=20)
            ax.axis('equal')
            
            ax.legend(wedges, categorias, title="Categorias", loc="center left", bbox_to_anchor=(1, 0.5), fontsize='small')
            
            figura.tight_layout(rect=[0, 0, 0.85, 1])
            
            canvas = FigureCanvasTkAgg(figura, tab_grafico)
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
        except Exception as e:
            messagebox.showerror("Erro ao Exibir Relatório", f"Ocorreu um erro: {e}")
   

    # ==============================================================================
# SUBSTITUA AS 4 FUNÇÕES CORRESPONDENTES NA SUA CLASSE 'SistemaFinanceiro'
# ==============================================================================

    def gerar_relatorio_categoria(self):
        """Gera um relatório de despesas por categoria"""
        try:
            categorias = self.carregar_categorias()
            
            if not categorias:
                messagebox.showinfo("Relatório", "Não há categorias cadastradas.")
                return
                
            dialog = tk.Toplevel(self.root)
            dialog.title("Relatório por Categoria")
            dialog.geometry("350x150")
            dialog.resizable(False, False)
            dialog.transient(self.root)
            dialog.grab_set()

            frame = ttk.Frame(dialog, padding="10")
            frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(frame, text="Selecione a Categoria:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
            categoria_combo = ttk.Combobox(frame, values=categorias, width=25, state="readonly")
            categoria_combo.current(0)
            categoria_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
            
            def gerar():
                categoria = categoria_combo.get()
                dialog.destroy()
                self.mostrar_relatorio_categoria(categoria)
            
            ttk.Button(frame, text="Gerar Relatório", command=gerar).grid(row=2, column=0, columnspan=2, pady=20)
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao gerar relatório de categoria: {e}")
    
    def mostrar_relatorio_categoria(self, categoria):
        """Exibe o relatório por categoria selecionada"""
        try:
            self.cursor.execute("""
                SELECT 
                    strftime('%Y-%m', data_pagamento) as mes_ano,
                    strftime('%m/%Y', data_pagamento) as mes_ano_formatado,
                    SUM(valor) as total_valor
                FROM despesas
                WHERE conta_despesa = ? AND user_id = ?
                GROUP BY mes_ano
                ORDER BY mes_ano ASC
            """, (categoria, self.user_id))
            
            resultados = self.cursor.fetchall()
            
            if not resultados:
                messagebox.showinfo("Relatório", f"Nenhuma despesa encontrada para a categoria '{categoria}'.")
                return
                
            total_geral = sum(row[2] for row in resultados)
            
            janela_relatorio = tk.Toplevel(self.root)
            janela_relatorio.title(f"Relatório da Categoria: {categoria}")
            janela_relatorio.geometry("800x600")
            
            frame_principal = ttk.Frame(janela_relatorio, padding="10")
            frame_principal.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(frame_principal, text=f"Evolução de Despesas - Categoria: {categoria}", font=('Arial', 16, 'bold')).pack(pady=10)
            ttk.Label(frame_principal, text=f"Total de Despesas na Categoria: {locale.currency(total_geral, grouping=True)}", font=('Arial', 12)).pack(pady=5)
            
            notebook = ttk.Notebook(frame_principal)
            notebook.pack(fill=tk.BOTH, expand=True, pady=10)
            
            tab_tabela = ttk.Frame(notebook)
            notebook.add(tab_tabela, text="Tabela")
            tab_grafico = ttk.Frame(notebook)
            notebook.add(tab_grafico, text="Gráfico")
            
            tree_frame = ttk.Frame(tab_tabela)
            tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            scrollbar = ttk.Scrollbar(tree_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            tabela = ttk.Treeview(tree_frame, columns=('mes_ano', 'total'), show='headings', yscrollcommand=scrollbar.set)
            tabela.heading('mes_ano', text='Mês/Ano')
            tabela.heading('total', text='Total (R$)')
            tabela.column('mes_ano', width=150, anchor=tk.CENTER)
            tabela.column('total', width=150, anchor=tk.E)
            
            for row in resultados:
                tabela.insert('', tk.END, values=(row[1], locale.currency(row[2], grouping=True)))
            
            tabela.pack(fill=tk.BOTH, expand=True)
            scrollbar.config(command=tabela.yview)
            
            figura = plt.Figure(figsize=(7, 5), dpi=100)
            ax = figura.add_subplot(111)
            
            meses = [row[1] for row in resultados]
            valores = [row[2] for row in resultados]
            
            ax.plot(meses, valores, marker='o', linestyle='-', color=self.cor_primaria, linewidth=2)
            
            for i, valor in enumerate(valores):
                ax.annotate(f'{locale.currency(valor, symbol=False)}', (meses[i], valores[i]), textcoords="offset points", xytext=(0,10), ha='center', fontsize=8)
            
            ax.set_title(f'Evolução de Despesas - {categoria}')
            ax.set_xlabel('Mês/Ano')
            ax.set_ylabel('Valor Total (R$)')
            ax.grid(True, linestyle='--', alpha=0.7)
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
            figura.tight_layout()
            
            canvas = FigureCanvasTkAgg(figura, tab_grafico)
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exibir relatório de categoria: {e}")

    def gerar_relatorio_meio_pagamento(self):
        """Gera um relatório de despesas por meio de pagamento"""
        try:
            self.cursor.execute("SELECT DISTINCT meio_pagamento FROM despesas WHERE user_id = ? ORDER BY meio_pagamento", (self.user_id,))
            meios_pagamento = [row[0] for row in self.cursor.fetchall()]
            
            if not meios_pagamento:
                messagebox.showinfo("Relatório", "Não há meios de pagamento com despesas lançadas.")
                return
                
            dialog = tk.Toplevel(self.root)
            dialog.title("Relatório por Meio de Pagamento")
            dialog.geometry("350x150")
            dialog.resizable(False, False)
            dialog.transient(self.root)
            dialog.grab_set()

            frame = ttk.Frame(dialog, padding="10")
            frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(frame, text="Selecione o Meio:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
            meio_combo = ttk.Combobox(frame, values=meios_pagamento, width=25, state="readonly")
            meio_combo.current(0)
            meio_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
            
            def gerar():
                meio = meio_combo.get()
                dialog.destroy()
                self.mostrar_relatorio_meio_pagamento(meio)
            
            ttk.Button(frame, text="Gerar Relatório", command=gerar).grid(row=2, column=0, columnspan=2, pady=20)
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao gerar relatório de meio de pagamento: {e}")

    def mostrar_relatorio_meio_pagamento(self, meio_pagamento):
        """Exibe o relatório por meio de pagamento selecionado"""
        try:
            self.cursor.execute("""
                SELECT 
                    strftime('%Y-%m', data_pagamento) as mes_ano,
                    strftime('%m/%Y', data_pagamento) as mes_ano_formatado,
                    SUM(valor) as total_valor
                FROM despesas
                WHERE meio_pagamento = ? AND user_id = ?
                GROUP BY mes_ano
                ORDER BY mes_ano ASC
            """, (meio_pagamento, self.user_id))
            
            resultados = self.cursor.fetchall()
            
            if not resultados:
                messagebox.showinfo("Relatório", f"Nenhuma despesa encontrada para o meio de pagamento '{meio_pagamento}'.")
                return
                
            total_geral = sum(row[2] for row in resultados)

            janela_relatorio = tk.Toplevel(self.root)
            janela_relatorio.title(f"Relatório do Meio de Pagamento: {meio_pagamento}")
            janela_relatorio.geometry("800x600")
            
            frame_principal = ttk.Frame(janela_relatorio, padding="10")
            frame_principal.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(frame_principal, text=f"Evolução de Despesas - Meio: {meio_pagamento}", font=('Arial', 16, 'bold')).pack(pady=10)
            ttk.Label(frame_principal, text=f"Total de Despesas: {locale.currency(total_geral, grouping=True)}", font=('Arial', 12)).pack(pady=5)
            
            notebook = ttk.Notebook(frame_principal)
            notebook.pack(fill=tk.BOTH, expand=True, pady=10)
            
            tab_tabela = ttk.Frame(notebook)
            notebook.add(tab_tabela, text="Tabela")
            tab_grafico = ttk.Frame(notebook)
            notebook.add(tab_grafico, text="Gráfico")
            
            tree_frame = ttk.Frame(tab_tabela)
            tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            scrollbar = ttk.Scrollbar(tree_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            tabela = ttk.Treeview(tree_frame, columns=('mes_ano', 'total'), show='headings', yscrollcommand=scrollbar.set)
            tabela.heading('mes_ano', text='Mês/Ano')
            tabela.heading('total', text='Total (R$)')
            tabela.column('mes_ano', width=150, anchor=tk.CENTER)
            tabela.column('total', width=150, anchor=tk.E)
            
            for row in resultados:
                tabela.insert('', tk.END, values=(row[1], locale.currency(row[2], grouping=True)))
                
            tabela.pack(fill=tk.BOTH, expand=True)
            scrollbar.config(command=tabela.yview)
            
            figura = plt.Figure(figsize=(7, 5), dpi=100)
            ax = figura.add_subplot(111)
            
            meses = [row[1] for row in resultados]
            valores = [row[2] for row in resultados]
            
            ax.plot(meses, valores, marker='o', linestyle='-', color=self.cor_primaria, linewidth=2)
            
            for i, valor in enumerate(valores):
                ax.annotate(f'{locale.currency(valor, symbol=False)}', (meses[i], valores[i]), textcoords="offset points", xytext=(0,10), ha='center', fontsize=8)
            
            ax.set_title(f'Evolução de Despesas - {meio_pagamento}')
            ax.set_xlabel('Mês/Ano')
            ax.set_ylabel('Valor Total (R$)')
            ax.grid(True, linestyle='--', alpha=0.7)
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
            figura.tight_layout()
            
            canvas = FigureCanvasTkAgg(figura, tab_grafico)
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exibir relatório de meio de pagamento: {e}")


    def exportar_excel(self):
        try:
            self.cursor.execute("""
                SELECT id, descricao, meio_pagamento, conta_despesa, valor, num_parcelas,
                       strftime('%d/%m/%Y', data_pagamento), strftime('%d/%m/%Y', data_registro)
                FROM despesas WHERE user_id = ? ORDER BY data_pagamento DESC
            """, (self.user_id,))
            
            df = pd.DataFrame(self.cursor.fetchall(), columns=['ID', 'Descrição', 'Meio de Pagamento', 'Categoria', 'Valor (R$)', 'Parcelas', 'Data de Pagamento', 'Data de Registro'])
            
            file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
            if not file_path: return
                
            df.to_excel(file_path, index=False, sheet_name='Despesas')
            messagebox.showinfo("Exportação Concluída", f"Dados exportados para {file_path}")
        except Exception as e:
            messagebox.showerror("Erro na Exportação", f"Erro ao exportar dados: {e}")


# Função principal
def main():
    # Primeiro, garante que o banco de dados está pronto para o sistema de usuários
    setup_database_users()
    
    # Inicia a janela de login em vez da aplicação principal
    login_app = LoginWindow()
    login_app.mainloop()

if __name__ == "__main__":
    main()