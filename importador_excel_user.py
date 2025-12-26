import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import sqlite3
from datetime import datetime

class ImportadorExcel:
    """
    Classe para criar uma interface gráfica que permite a importação de despesas
    a partir de uma planilha Excel, associando-as ao usuário logado.
    """
    # ALTERADO: O construtor agora aceita o user_id
    def __init__(self, parent, user_id):
        self.parent = parent
        self.user_id = user_id  # Armazena o ID do usuário logado
        self.root = tk.Toplevel(parent)
        self.root.title("Importador de Despesas por Excel")
        self.root.geometry("700x500")
        self.root.resizable(False, False)
        
        self.root.transient(parent)
        self.root.grab_set()

        self.db_path = 'financas.db'
        self.arquivo_excel = None

        # --- Widgets da Interface ---
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        frame_selecao = ttk.LabelFrame(main_frame, text="1. Selecionar Arquivo", padding="10")
        frame_selecao.pack(fill=tk.X, pady=5)

        self.lbl_arquivo = ttk.Label(frame_selecao, text="Nenhum arquivo selecionado.", width=60)
        self.lbl_arquivo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        btn_selecionar = ttk.Button(frame_selecao, text="Procurar...", command=self.selecionar_arquivo)
        btn_selecionar.pack(side=tk.RIGHT, padx=5)

        frame_acao = ttk.LabelFrame(main_frame, text="2. Processar", padding="10")
        frame_acao.pack(fill=tk.X, pady=10)

        self.btn_importar = ttk.Button(frame_acao, text="Iniciar Importação", command=self.importar_dados, state="disabled")
        self.btn_importar.pack(pady=10)

        frame_resultados = ttk.LabelFrame(main_frame, text="Resultados da Importação", padding="10")
        frame_resultados.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.tree_resultados = ttk.Treeview(frame_resultados, columns=('Linha', 'Erro'), show='headings')
        self.tree_resultados.heading('Linha', text='Linha do Excel')
        self.tree_resultados.heading('Erro', text='Motivo da Falha')
        self.tree_resultados.column('Linha', width=100, anchor=tk.CENTER)
        self.tree_resultados.column('Erro', width=550)
        
        scrollbar = ttk.Scrollbar(frame_resultados, orient="vertical", command=self.tree_resultados.yview)
        self.tree_resultados.configure(yscrollcommand=scrollbar.set)
        
        self.tree_resultados.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def selecionar_arquivo(self):
        """Abre uma caixa de diálogo para o usuário selecionar um arquivo .xlsx."""
        caminho = filedialog.askopenfilename(
            title="Selecione a planilha Excel",
            filetypes=[("Arquivos Excel", "*.xlsx"), ("Todos os arquivos", "*.*")]
        )
        if caminho:
            self.arquivo_excel = caminho
            self.lbl_arquivo.config(text=caminho.split('/')[-1])
            self.btn_importar['state'] = 'normal'
            for i in self.tree_resultados.get_children():
                self.tree_resultados.delete(i)
        else:
            self.lbl_arquivo.config(text="Nenhum arquivo selecionado.")
            self.btn_importar['state'] = 'disabled'

    def obter_listas_validacao(self):
        """Busca as categorias e meios de pagamento válidos no banco de dados."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT nome FROM categorias")
            categorias_validas = {row[0] for row in cursor.fetchall()}
            
            cursor.execute("SELECT nome FROM meios_pagamento")
            meios_pagamento_validos = {row[0] for row in cursor.fetchall()}
            
            conn.close()
            return categorias_validas, meios_pagamento_validos
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Não foi possível ler as configurações: {e}", parent=self.root)
            return None, None

    def importar_dados(self):
        """Lê a planilha, valida e insere os dados no banco de dados para o usuário logado."""
        if not self.arquivo_excel:
            messagebox.showwarning("Atenção", "Selecione um arquivo Excel primeiro.", parent=self.root)
            return

        for i in self.tree_resultados.get_children():
            self.tree_resultados.delete(i)

        categorias_validas, meios_pagamento_validos = self.obter_listas_validacao()
        if categorias_validas is None:
            return

        try:
            df = pd.read_excel(self.arquivo_excel)
            colunas_necessarias = ['Descrição', 'Meio de Pagamento', 'Categoria', 'Valor', 'Parcelas', 'Data de Pagamento']
            
            if not all(col in df.columns for col in colunas_necessarias):
                messagebox.showerror("Erro de Coluna", f"A planilha deve conter as colunas: {', '.join(colunas_necessarias)}", parent=self.root)
                return

            registros_sucesso = 0
            registros_falha = 0
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for index, row in df.iterrows():
                linha_excel = index + 2
                
                descricao = row['Descrição']
                meio_pagamento = row['Meio de Pagamento']
                categoria = row['Categoria']
                valor = row['Valor']
                parcelas = row['Parcelas']
                data_pagamento_raw = row['Data de Pagamento']
                
                erros = []
                if pd.isna(descricao) or not str(descricao).strip():
                    erros.append("Coluna 'Descrição' não pode ser vazia.")
                if categoria not in categorias_validas:
                    erros.append(f"Categoria '{categoria}' não existe.")
                if meio_pagamento not in meios_pagamento_validos:
                    erros.append(f"Meio de Pagamento '{meio_pagamento}' não existe.")

                try:
                    data_pagamento = pd.to_datetime(data_pagamento_raw).strftime('%Y-%m-%d')
                except (ValueError, TypeError):
                    erros.append("Formato de data inválido na coluna 'Data de Pagamento'.")
                
                try:
                    float(valor)
                except (ValueError, TypeError):
                    erros.append("Coluna 'Valor' contém um valor não numérico.")


                if not erros:
                    try:
                        # ALTERADO: A query de inserção agora inclui a coluna 'user_id' e seu valor.
                        cursor.execute("""
                            INSERT INTO despesas (descricao, meio_pagamento, conta_despesa, valor, num_parcelas, data_registro, data_pagamento, user_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            str(descricao), 
                            str(meio_pagamento), 
                            str(categoria), 
                            float(valor), 
                            int(parcelas), 
                            datetime.now().strftime('%Y-%m-%d'), 
                            data_pagamento, 
                            self.user_id  # <-- Valor do usuário logado é inserido aqui
                        ))
                        registros_sucesso += 1
                    except (sqlite3.Error, ValueError) as e:
                        self.tree_resultados.insert("", "end", values=(linha_excel, f"Erro de inserção no banco: {e}"))
                        registros_falha += 1
                else:
                    self.tree_resultados.insert("", "end", values=(linha_excel, " | ".join(erros)))
                    registros_falha += 1

            conn.commit()
            conn.close()

            messagebox.showinfo(
                "Importação Concluída",
                f"Processo finalizado!\n\n"
                f"Registros importados com sucesso: {registros_sucesso}\n"
                f"Registros com falha: {registros_falha}",
                parent=self.root
            )

        except FileNotFoundError:
            messagebox.showerror("Erro", f"Arquivo não encontrado: {self.arquivo_excel}", parent=self.root)
        except Exception as e:
            messagebox.showerror("Erro Inesperado", f"Ocorreu um erro ao processar o arquivo: {e}", parent=self.root)
            if 'conn' in locals() and conn:
                conn.close()

# ALTERADO: A função de inicialização agora aceita e repassa o user_id.
def iniciar_importador_excel(parent, user_id):
    """Função para ser chamada pelo programa principal para iniciar a interface."""
    ImportadorExcel(parent, user_id)