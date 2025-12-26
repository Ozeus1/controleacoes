import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import shutil
import csv
import os

class GerenciadorConfiguracoes2:
    def __init__(self, root=None, standalone=False):
        """
        Inicializa o gerenciador de configurações.
        """
        self.standalone = standalone
        self.db_path = 'financas.db'

        # Janela principal
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
        self.cor_primaria = "#4CAF50"
        self.cor_secundaria = "#F0F4C3"
        self.cor_fundo = "#F9F9F9"
        self.cor_texto = "#333333"

        self.configurar_estilo()
        self.conectar_banco_dados()
        self.criar_interface()

        # Carregar dados
        self.carregar_meios_pagamento()
        self.carregar_categorias()

        if standalone:
            self.root.mainloop()

    def configurar_estilo(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', background=self.cor_primaria,
                        foreground='white', font=('Arial', 10, 'bold'), padding=5)
        style.configure('TLabel', background=self.cor_fundo,
                        foreground=self.cor_texto, font=('Arial', 10))
        style.configure('TEntry', fieldbackground='white', font=('Arial', 10))
        style.configure('TFrame', background=self.cor_fundo)
        style.configure('Treeview', background='white', fieldbackground='white', font=('Arial', 9))
        style.configure('Treeview.Heading', font=('Arial', 10, 'bold'), background=self.cor_secundaria)

    def conectar_banco_dados(self):
        try:
            if hasattr(self, 'conn'):
                self.conn.close()
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            # Criar tabelas
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS meios_pagamento (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL UNIQUE
                )''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS categorias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL UNIQUE
                )''')
            self.conn.commit()
        except sqlite3.Error as e:
            messagebox.showerror("Erro de BD", f"Não foi possível conectar ao BD: {e}")

    def criar_interface(self):
        # Notebook
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        # Abas
        self.aba_meios = ttk.Frame(notebook)
        notebook.add(self.aba_meios, text="Meios de Pagamento")
        self.aba_cat = ttk.Frame(notebook)
        notebook.add(self.aba_cat, text="Categorias")

        # Operações e abas
        self.criar_aba_meios_pagamento()
        self.criar_aba_categorias()

        # Painel inferior
        ops = ttk.Frame(self.root)
        ops.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(ops, text="Salvar BD", command=self.salvar_banco_dados).pack(side=tk.LEFT, padx=5)
        ttk.Button(ops, text="Importar BD", command=self.importar_banco_dados).pack(side=tk.LEFT, padx=5)
        ttk.Button(ops, text="Exportar CSV", command=self.exportar_csv).pack(side=tk.LEFT, padx=5)
        if not self.standalone:
            ttk.Button(self.root, text="Fechar", command=self.root.destroy).pack(pady=5)

    # ---- Aba Meios ----
    def criar_aba_meios_pagamento(self):
        frame = ttk.Frame(self.aba_meios)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        # Form
        form = ttk.Frame(frame)
        form.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Label(form, text="Gerenciar Meios de Pagamento", font=('Arial',12,'bold')).grid(row=0, column=0, columnspan=2, pady=5)
        self.id_meio = tk.StringVar()
        ttk.Label(form, text="ID:").grid(row=1, column=0, sticky=tk.W)
        ttk.Entry(form, textvariable=self.id_meio, state='readonly', width=5).grid(row=1, column=1, pady=5)
        self.nome_meio = tk.StringVar()
        ttk.Label(form, text="Nome:").grid(row=2, column=0, sticky=tk.W)
        ttk.Entry(form, textvariable=self.nome_meio, width=25).grid(row=2, column=1)
        # Botões
        botoes = ttk.Frame(form)
        botoes.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(botoes, text="Adicionar", command=self.adicionar_meio_pagamento).grid(row=0, column=0, padx=5)
        self.btn_up_meio = ttk.Button(botoes, text="Atualizar", command=self.atualizar_meio_pagamento, state='disabled')
        self.btn_up_meio.grid(row=0, column=1, padx=5)
        self.btn_del_meio = ttk.Button(botoes, text="Excluir", command=self.excluir_meio_pagamento, state='disabled')
        self.btn_del_meio.grid(row=0, column=2, padx=5)
        ttk.Button(botoes, text="Limpar", command=self.limpar_campos_meio).grid(row=0, column=3, padx=5)
        # Tabela
        tabela = ttk.Frame(frame)
        tabela.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        ttk.Label(tabela, text="Meios Cadastrados", font=('Arial',12,'bold')).pack(anchor=tk.W)
        tv_frame = ttk.Frame(tabela)
        tv_frame.pack(fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(tv_frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_meios = ttk.Treeview(tv_frame, columns=('id','nome'), show='headings', yscrollcommand=sb.set)
        self.tree_meios.heading('id', text='ID'); self.tree_meios.heading('nome', text='Nome')
        self.tree_meios.column('id', width=50, anchor=tk.CENTER); self.tree_meios.column('nome', width=200)
        self.tree_meios.pack(fill=tk.BOTH, expand=True); sb.config(command=self.tree_meios.yview)
        self.tree_meios.bind("<ButtonRelease-1>", self.selecionar_meio_pagamento)

    def carregar_meios_pagamento(self):
        for item in self.tree_meios.get_children(): self.tree_meios.delete(item)
        self.cursor.execute("SELECT id, nome FROM meios_pagamento ORDER BY nome")
        for row in self.cursor.fetchall(): self.tree_meios.insert('', tk.END, values=row)

    def adicionar_meio_pagamento(self):
        nome = self.nome_meio.get().strip()
        if not nome:
            messagebox.showwarning("Atenção","Informe o nome do meio.")
            return
        try:
            self.cursor.execute("INSERT INTO meios_pagamento(nome) VALUES(?)", (nome,))
            self.conn.commit()
            self.carregar_meios_pagamento(); self.limpar_campos_meio()
            messagebox.showinfo("Sucesso","Meio adicionado.")
        except sqlite3.IntegrityError:
            messagebox.showerror("Erro","Este meio já existe.")

    def selecionar_meio_pagamento(self, event):
        sel = self.tree_meios.selection()
        if sel:
            id_, nome = self.tree_meios.item(sel[0],'values')
            self.id_meio.set(id_); self.nome_meio.set(nome)
            self.btn_up_meio['state']='normal'; self.btn_del_meio['state']='normal'

    def atualizar_meio_pagamento(self):
        id_ = self.id_meio.get(); nome = self.nome_meio.get().strip()
        if not id_ or not nome:
            messagebox.showwarning("Atenção","Selecione e informe o nome."); return
        try:
            self.cursor.execute("UPDATE meios_pagamento SET nome=? WHERE id=?", (nome,id_))
            self.conn.commit(); self.carregar_meios_pagamento(); self.limpar_campos_meio()
            messagebox.showinfo("Sucesso","Meio atualizado.")
        except sqlite3.IntegrityError:
            messagebox.showerror("Erro","Nome já em uso.")

    def excluir_meio_pagamento(self):
        id_ = self.id_meio.get()
        if not id_:
            messagebox.showwarning("Atenção","Selecione um meio."); return
        self.cursor.execute("SELECT COUNT(*) FROM despesas WHERE meio_pagamento=?", (id_,))
        if self.cursor.fetchone()[0] > 0:
            messagebox.showwarning("Impossível","Meio em uso."); return
        if messagebox.askyesno("Confirma","Excluir este meio?"):
            self.cursor.execute("DELETE FROM meios_pagamento WHERE id=?", (id_,))
            self.conn.commit(); self.carregar_meios_pagamento(); self.limpar_campos_meio()

    def limpar_campos_meio(self):
        self.id_meio.set(''); self.nome_meio.set('')
        self.btn_up_meio['state']='disabled'; self.btn_del_meio['state']='disabled'

    # ---- Aba Categorias ----
    def criar_aba_categorias(self):
        frame = ttk.Frame(self.aba_cat)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        form = ttk.Frame(frame)
        form.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Label(form, text="Gerenciar Categorias", font=('Arial',12,'bold')).grid(row=0,column=0,columnspan=2,pady=5)
        self.id_cat = tk.StringVar()
        ttk.Label(form, text="ID:").grid(row=1,column=0,sticky=tk.W)
        ttk.Entry(form, textvariable=self.id_cat, state='readonly', width=5).grid(row=1,column=1,pady=5)
        self.nome_cat = tk.StringVar()
        ttk.Label(form, text="Nome:").grid(row=2,column=0,sticky=tk.W)
        ttk.Entry(form, textvariable=self.nome_cat, width=25).grid(row=2,column=1)
        bots = ttk.Frame(form); bots.grid(row=3,column=0,columnspan=2,pady=10)
        ttk.Button(bots, text="Adicionar", command=self.adicionar_categoria).grid(row=0,column=0,padx=5)
        self.btn_up_cat=ttk.Button(bots,text="Atualizar",command=self.atualizar_categoria,state='disabled')
        self.btn_up_cat.grid(row=0,column=1,padx=5)
        self.btn_del_cat=ttk.Button(bots,text="Excluir",command=self.excluir_categoria,state='disabled')
        self.btn_del_cat.grid(row=0,column=2,padx=5)
        ttk.Button(bots,text="Limpar",command=self.limpar_campos_categoria).grid(row=0,column=3,padx=5)
        tabela=ttk.Frame(frame); tabela.pack(side=tk.RIGHT,fill=tk.BOTH,expand=True)
        ttk.Label(tabela,text="Categorias Cadastradas",font=('Arial',12,'bold')).pack(anchor=tk.W)
        tvf=ttk.Frame(tabela); tvf.pack(fill=tk.BOTH,expand=True)
        sc=ttk.Scrollbar(tvf); sc.pack(side=tk.RIGHT,fill=tk.Y)
        self.tree_cat=ttk.Treeview(tvf,columns=('id','nome'),show='headings',yscrollcommand=sc.set)
        self.tree_cat.heading('id',text='ID');self.tree_cat.heading('nome',text='Nome')
        self.tree_cat.column('id',width=50,anchor=tk.CENTER);self.tree_cat.column('nome',width=200)
        self.tree_cat.pack(fill=tk.BOTH,expand=True);sc.config(command=self.tree_cat.yview)
        self.tree_cat.bind("<ButtonRelease-1>",self.selecionar_categoria)

    def carregar_categorias(self):
        for i in self.tree_cat.get_children():self.tree_cat.delete(i)
        self.cursor.execute("SELECT id,nome FROM categorias ORDER BY nome")
        for r in self.cursor.fetchall():self.tree_cat.insert('',tk.END,values=r)

    def adicionar_categoria(self):
        nome=self.nome_cat.get().strip()
        if not nome:messagebox.showwarning("Atenção","Informe o nome da categoria.");return
        try:
            self.cursor.execute("INSERT INTO categorias(nome) VALUES(?)",(nome,))
            self.conn.commit();self.carregar_categorias();self.limpar_campos_categoria()
            messagebox.showinfo("Sucesso","Categoria adicionada.")
        except sqlite3.IntegrityError:
            messagebox.showerror("Erro","Esta categoria já existe.")

    def selecionar_categoria(self,event):
        sel=self.tree_cat.selection();
        if sel:
            id_,nm=self.tree_cat.item(sel[0],'values');self.id_cat.set(id_);self.nome_cat.set(nm)
            self.btn_up_cat['state']='normal';self.btn_del_cat['state']='normal'

    def atualizar_categoria(self):
        id_=self.id_cat.get();nm=self.nome_cat.get().strip()
        if not id_ or not nm:messagebox.showwarning("Atenção","Selecione e informe o nome.");return
        try:
            self.cursor.execute("UPDATE categorias SET nome=? WHERE id=?",(nm,id_))
            self.conn.commit();self.carregar_categorias();self.limpar_campos_categoria()
            messagebox.showinfo("Sucesso","Categoria atualizada.")
        except sqlite3.IntegrityError:
            messagebox.showerror("Erro","Nome já em uso.")

    def excluir_categoria(self):
        id_=self.id_cat.get()
        if not id_:messagebox.showwarning("Atenção","Selecione categoria.");return
        self.cursor.execute("SELECT COUNT(*) FROM despesas WHERE conta_despesa=?",(id_,))
        if self.cursor.fetchone()[0]>0:messagebox.showwarning("Impossível","Categoria em uso.");return
        if messagebox.askyesno("Confirma","Excluir esta categoria?"):
            self.cursor.execute("DELETE FROM categorias WHERE id=?",(id_,))
            self.conn.commit();self.carregar_categorias();self.limpar_campos_categoria()

    def limpar_campos_categoria(self):
        self.id_cat.set('');self.nome_cat.set('')
        self.btn_up_cat['state']='disabled';self.btn_del_cat['state']='disabled'

    # ---- Operações de Banco ----
    def salvar_banco_dados(self):
        destino=filedialog.asksaveasfilename(defaultextension=".db",filetypes=[("SQLite DB","*.db")])
        if destino:
            try:shutil.copy(self.db_path,destino);messagebox.showinfo("Sucesso",f"BD salvo em:\n{destino}")
            except Exception as e:messagebox.showerror("Erro",f"Não foi possível salvar: {e}")

    def importar_banco_dados(self):
        src=filedialog.askopenfilename(filetypes=[("SQLite DB","*.db")])
        if src:
            try:
                self.db_path=src;self.conectar_banco_dados();self.carregar_meios_pagamento();self.carregar_categorias()
                messagebox.showinfo("Sucesso",f"BD importado de:\n{src}")
            except Exception as e:messagebox.showerror("Erro",f"Não foi possível importar: {e}")

    def exportar_csv(self):
        pasta=filedialog.askdirectory()
        if pasta:
            try:
                # meios
                self.cursor.execute("SELECT id,nome FROM meios_pagamento")
                with open(os.path.join(pasta,"meios_pagamento.csv"),"w",newline='',encoding='utf-8') as f:
                    w=csv.writer(f);w.writerow(["id","nome"]);w.writerows(self.cursor.fetchall())
                # categorias
                self.cursor.execute("SELECT id,nome FROM categorias")
                with open(os.path.join(pasta,"categorias.csv"),"w",newline='',encoding='utf-8') as f:
                    w=csv.writer(f);w.writerow(["id","nome"]);w.writerows(self.cursor.fetchall())
                messagebox.showinfo("Sucesso",f"CSVs salvos em:\n{pasta}")
            except Exception as e:messagebox.showerror("Erro",f"Não foi possível exportar: {e}")

    def __del__(self):
        if hasattr(self,'conn'):self.conn.close()

if __name__ == '__main__':
    app = GerenciadorConfiguracoes2(standalone=True)
