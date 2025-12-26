# Conteúdo corrigido para MENUBD.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import shutil
import csv
import os

class GerenciadorConfiguracoes2:
    def __init__(self, root, standalone=False, user_id=None): # Standalone e user_id para compatibilidade
        self.standalone = standalone
        self.user_id = user_id # Armazena o user_id, embora não seja usado para filtrar (listas globais)
        self.db_path = 'financas.db'

        if root is None:
            self.root = tk.Tk()
        else:
            self.root = tk.Toplevel(root)
            self.root.transient(root)
            self.root.grab_set()

        self.root.title("Gerenciador de Itens Globais e Backup")
        self.root.geometry("800x600")

        self.conectar_banco_dados()
        self.criar_interface()
        self.carregar_meios_pagamento()
        self.carregar_categorias()

    def conectar_banco_dados(self):
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            messagebox.showerror("Erro de BD", f"Não foi possível conectar: {e}")

    def criar_interface(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.aba_meios = ttk.Frame(notebook)
        notebook.add(self.aba_meios, text="Meios de Pagamento")
        self.aba_cat = ttk.Frame(notebook)
        notebook.add(self.aba_cat, text="Categorias")

        self.criar_aba_meios_pagamento()
        self.criar_aba_categorias()

        ops = ttk.LabelFrame(self.root, text="Operações de Banco de Dados (Admin)")
        ops.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(ops, text="Backup do Banco de Dados", command=self.salvar_banco_dados).pack(side=tk.LEFT, padx=5)
        
    def criar_aba_meios_pagamento(self):
        # ... (código da interface não muda)
        frame = ttk.Frame(self.aba_meios)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        form = ttk.Frame(frame); form.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Label(form, text="Gerenciar Meios de Pagamento", font=('Arial',12,'bold')).grid(row=0, column=0, columnspan=2, pady=5)
        self.id_meio = tk.StringVar(); self.nome_meio = tk.StringVar()
        ttk.Label(form, text="ID:").grid(row=1, column=0, sticky=tk.W); ttk.Entry(form, textvariable=self.id_meio, state='readonly', width=5).grid(row=1, column=1, pady=5)
        ttk.Label(form, text="Nome:").grid(row=2, column=0, sticky=tk.W); ttk.Entry(form, textvariable=self.nome_meio, width=25).grid(row=2, column=1)
        botoes = ttk.Frame(form); botoes.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(botoes, text="Adicionar", command=self.adicionar_meio_pagamento).grid(row=0, column=0, padx=5)
        self.btn_up_meio = ttk.Button(botoes, text="Atualizar", command=self.atualizar_meio_pagamento, state='disabled'); self.btn_up_meio.grid(row=0, column=1, padx=5)
        self.btn_del_meio = ttk.Button(botoes, text="Excluir", command=self.excluir_meio_pagamento, state='disabled'); self.btn_del_meio.grid(row=0, column=2, padx=5)
        ttk.Button(botoes, text="Limpar", command=self.limpar_campos_meio).grid(row=0, column=3, padx=5)
        tabela = ttk.Frame(frame); tabela.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        tv_frame = ttk.Frame(tabela); tv_frame.pack(fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(tv_frame); sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_meios = ttk.Treeview(tv_frame, columns=('id','nome'), show='headings', yscrollcommand=sb.set); sb.config(command=self.tree_meios.yview)
        self.tree_meios.heading('id', text='ID'); self.tree_meios.column('id', width=50, anchor=tk.CENTER)
        self.tree_meios.heading('nome', text='Nome'); self.tree_meios.column('nome', width=200)
        self.tree_meios.pack(fill=tk.BOTH, expand=True)
        self.tree_meios.bind("<ButtonRelease-1>", self.selecionar_meio_pagamento)

    def excluir_meio_pagamento(self):
        id_ = self.id_meio.get()
        nome_meio = self.nome_meio.get() # Usar o nome para a verificação
        if not id_:
            messagebox.showwarning("Atenção","Selecione um meio."); return
        
        # ALTERADO: Verifica se o NOME do meio de pagamento está em uso
        self.cursor.execute("SELECT COUNT(*) FROM despesas WHERE meio_pagamento=?", (nome_meio,))
        if self.cursor.fetchone()[0] > 0:
            messagebox.showwarning("Impossível Excluir",f"O meio de pagamento '{nome_meio}' está em uso e não pode ser excluído."); return
            
        if messagebox.askyesno("Confirma","Excluir este meio?"):
            self.cursor.execute("DELETE FROM meios_pagamento WHERE id=?", (id_,))
            self.conn.commit(); self.carregar_meios_pagamento(); self.limpar_campos_meio()

    def criar_aba_categorias(self):
        # ... (código da interface não muda)
        frame = ttk.Frame(self.aba_cat); frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        form = ttk.Frame(frame); form.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Label(form, text="Gerenciar Categorias", font=('Arial',12,'bold')).grid(row=0,column=0,columnspan=2,pady=5)
        self.id_cat = tk.StringVar(); self.nome_cat = tk.StringVar()
        ttk.Label(form, text="ID:").grid(row=1,column=0,sticky=tk.W); ttk.Entry(form, textvariable=self.id_cat, state='readonly', width=5).grid(row=1,column=1,pady=5)
        ttk.Label(form, text="Nome:").grid(row=2,column=0,sticky=tk.W); ttk.Entry(form, textvariable=self.nome_cat, width=25).grid(row=2,column=1)
        bots = ttk.Frame(form); bots.grid(row=3,column=0,columnspan=2,pady=10)
        ttk.Button(bots, text="Adicionar", command=self.adicionar_categoria).grid(row=0,column=0,padx=5)
        self.btn_up_cat=ttk.Button(bots,text="Atualizar",command=self.atualizar_categoria,state='disabled'); self.btn_up_cat.grid(row=0,column=1,padx=5)
        self.btn_del_cat=ttk.Button(bots,text="Excluir",command=self.excluir_categoria,state='disabled'); self.btn_del_cat.grid(row=0,column=2,padx=5)
        ttk.Button(bots,text="Limpar",command=self.limpar_campos_categoria).grid(row=0,column=3,padx=5)
        tabela=ttk.Frame(frame); tabela.pack(side=tk.RIGHT,fill=tk.BOTH,expand=True)
        tvf=ttk.Frame(tabela); tvf.pack(fill=tk.BOTH,expand=True)
        sc=ttk.Scrollbar(tvf); sc.pack(side=tk.RIGHT,fill=tk.Y)
        self.tree_cat=ttk.Treeview(tvf,columns=('id','nome'),show='headings',yscrollcommand=sc.set); sc.config(command=self.tree_cat.yview)
        self.tree_cat.heading('id',text='ID'); self.tree_cat.column('id',width=50,anchor=tk.CENTER)
        self.tree_cat.heading('nome',text='Nome'); self.tree_cat.column('nome',width=200)
        self.tree_cat.pack(fill=tk.BOTH,expand=True)
        self.tree_cat.bind("<ButtonRelease-1>",self.selecionar_categoria)

    def excluir_categoria(self):
        id_ = self.id_cat.get()
        nome_cat = self.nome_cat.get() # Usar o nome para a verificação
        if not id_:
            messagebox.showwarning("Atenção","Selecione categoria."); return
            
        # ALTERADO: Verifica se o NOME da categoria está em uso
        self.cursor.execute("SELECT COUNT(*) FROM despesas WHERE conta_despesa=?",(nome_cat,))
        if self.cursor.fetchone()[0]>0:
            messagebox.showwarning("Impossível Excluir",f"A categoria '{nome_cat}' está em uso e não pode ser excluída."); return

        if messagebox.askyesno("Confirma","Excluir esta categoria?"):
            self.cursor.execute("DELETE FROM categorias WHERE id=?",(id_,))
            self.conn.commit();self.carregar_categorias();self.limpar_campos_categoria()

    # (As demais funções: carregar, adicionar, atualizar, limpar, etc. não precisam de alteração
    # pois operam em listas globais. O código completo está abaixo por consistência.)

    def carregar_meios_pagamento(self):
        for item in self.tree_meios.get_children(): self.tree_meios.delete(item)
        self.cursor.execute("SELECT id, nome FROM meios_pagamento ORDER BY nome")
        for row in self.cursor.fetchall(): self.tree_meios.insert('', tk.END, values=row)

    def adicionar_meio_pagamento(self):
        nome = self.nome_meio.get().strip()
        if not nome: messagebox.showwarning("Atenção","Informe o nome do meio."); return
        try:
            self.cursor.execute("INSERT INTO meios_pagamento(nome) VALUES(?)", (nome,)); self.conn.commit()
            self.carregar_meios_pagamento(); self.limpar_campos_meio(); messagebox.showinfo("Sucesso","Meio adicionado.")
        except sqlite3.IntegrityError: messagebox.showerror("Erro","Este meio já existe.")

    def selecionar_meio_pagamento(self, event):
        sel = self.tree_meios.selection()
        if sel:
            id_, nome = self.tree_meios.item(sel[0],'values')
            self.id_meio.set(id_); self.nome_meio.set(nome)
            self.btn_up_meio['state']='normal'; self.btn_del_meio['state']='normal'

    def atualizar_meio_pagamento(self):
        id_ = self.id_meio.get(); nome = self.nome_meio.get().strip()
        if not id_ or not nome: messagebox.showwarning("Atenção","Selecione e informe o nome."); return
        try:
            self.cursor.execute("UPDATE meios_pagamento SET nome=? WHERE id=?", (nome,id_))
            self.conn.commit(); self.carregar_meios_pagamento(); self.limpar_campos_meio(); messagebox.showinfo("Sucesso","Meio atualizado.")
        except sqlite3.IntegrityError: messagebox.showerror("Erro","Nome já em uso.")
    
    def limpar_campos_meio(self):
        self.id_meio.set(''); self.nome_meio.set('')
        self.btn_up_meio['state']='disabled'; self.btn_del_meio['state']='disabled'

    def carregar_categorias(self):
        for i in self.tree_cat.get_children():self.tree_cat.delete(i)
        self.cursor.execute("SELECT id,nome FROM categorias ORDER BY nome")
        for r in self.cursor.fetchall():self.tree_cat.insert('',tk.END,values=r)

    def adicionar_categoria(self):
        nome=self.nome_cat.get().strip()
        if not nome:messagebox.showwarning("Atenção","Informe o nome da categoria.");return
        try:
            self.cursor.execute("INSERT INTO categorias(nome) VALUES(?)",(nome,)); self.conn.commit()
            self.carregar_categorias();self.limpar_campos_categoria(); messagebox.showinfo("Sucesso","Categoria adicionada.")
        except sqlite3.IntegrityError: messagebox.showerror("Erro","Esta categoria já existe.")

    def selecionar_categoria(self,event):
        sel=self.tree_cat.selection();
        if sel:
            id_,nm=self.tree_cat.item(sel[0],'values');self.id_cat.set(id_);self.nome_cat.set(nm)
            self.btn_up_cat['state']='normal';self.btn_del_cat['state']='normal'

    def atualizar_categoria(self):
        id_=self.id_cat.get();nm=self.nome_cat.get().strip()
        if not id_ or not nm:messagebox.showwarning("Atenção","Selecione e informe o nome.");return
        try:
            self.cursor.execute("UPDATE categorias SET nome=? WHERE id=?",(nm,id_)); self.conn.commit()
            self.carregar_categorias();self.limpar_campos_categoria(); messagebox.showinfo("Sucesso","Categoria atualizada.")
        except sqlite3.IntegrityError: messagebox.showerror("Erro","Nome já em uso.")

    def limpar_campos_categoria(self):
        self.id_cat.set('');self.nome_cat.set('')
        self.btn_up_cat['state']='disabled';self.btn_del_cat['state']='disabled'

    def salvar_banco_dados(self):
        destino=filedialog.asksaveasfilename(defaultextension=".db",filetypes=[("SQLite DB","*.db")])
        if destino:
            try:
                self.conn.close() # Fecha a conexão para permitir a cópia
                shutil.copy(self.db_path,destino)
                messagebox.showinfo("Sucesso",f"Backup do banco de dados salvo em:\n{destino}")
                self.conectar_banco_dados() # Reabre a conexão
            except Exception as e:
                messagebox.showerror("Erro",f"Não foi possível salvar: {e}")
                self.conectar_banco_dados() # Tenta reabrir a conexão mesmo em caso de erro

# Função de inicialização
def iniciar_gerenciador_bd(parent, user_id):
    GerenciadorConfiguracoes2(parent, standalone=False, user_id=user_id)