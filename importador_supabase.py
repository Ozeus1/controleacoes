# importador_supabase_final_com_controle_migrado.py

import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime
import locale
import requests
import json
import os 

# Configurar a localização para formato de moeda brasileiro
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        print("Aviso: Locale 'pt_BR' não encontrado. A formatação de moeda pode não funcionar corretamente.")

class SupabaseImporter(tk.Toplevel):
    def __init__(self, parent_widget, app_logic):
        super().__init__(parent_widget)
        self.transient(parent_widget)
        self.grab_set()
        self.title("Importar Despesas do Supabase")
        self.geometry("1000x700") # Aumentado um pouco para acomodar mais colunas

        self.parent_app = app_logic
        self.supabase_conn = None
        self.supabase_cursor = None
        self.loaded_data = []
        
        # Nome do arquivo de configuração
        self.config_file = "supabase_config.json"
        
        # Variáveis de configuração
        self.supabase_url = tk.StringVar()
        self.supabase_key = tk.StringVar()
        self.db_host = tk.StringVar()
        self.db_name = tk.StringVar()
        self.db_user = tk.StringVar()
        self.db_password = tk.StringVar()
        self.db_port = tk.StringVar(value="5432")
        self.table_name = tk.StringVar(value="transacoes_financeiras")
        self.method_var = tk.StringVar(value="rest_api")

        self.load_config() 
        
        self.create_widgets()
        self.on_method_change() 

    def load_config(self):
        """Carrega URL e API Key de um arquivo de configuração."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.supabase_url.set(config.get("supabase_url", ""))
                    self.supabase_key.set(config.get("supabase_key", ""))
                    self.db_host.set(config.get("db_host", ""))
                    self.db_name.set(config.get("db_name", "postgres"))
                    self.db_user.set(config.get("db_user", "postgres"))
                    self.db_password.set(config.get("db_password", "")) # Cuidado: salvar senha em texto plano NÃO é seguro!
                    self.db_port.set(config.get("db_port", "5432"))
                    self.table_name.set(config.get("table_name", "transacoes_financeiras"))
                    self.method_var.set(config.get("connection_method", "rest_api"))
            except Exception as e:
                messagebox.showwarning("Erro de Configuração", f"Não foi possível carregar as configurações: {e}", parent=self)
        
        # Valores padrão se o arquivo não existir ou for inválido, ou para preencher os StringVar
        if not self.supabase_url.get():
            self.supabase_url.set("https://1gbrktfhxlfqdefuofdpk.supabase.co")
        if not self.supabase_key.get():
            self.supabase_key.set("1eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdicmt0Zmh4bGZxZGVmdW9mZHBrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTA2MDQwODYsImV4cCI6MjA2NjE4MDA4Nn0.7K8r6i6xjQr__zTE1UY2cWc56O5qPllq9oTe4qdf_BY")
        if not self.db_host.get():
            self.db_host.set("gbrktfhxlfqdefuofdpk.supabase.co")
        if not self.db_name.get():
            self.db_name.set("postgres")
        if not self.db_user.get():
            self.db_user.set("postgres")
        if not self.db_port.get():
            self.db_port.set("5432")
        if not self.table_name.get():
            self.table_name.set("transacoes_financeiras")
        if not self.method_var.get():
            self.method_var.set("rest_api")

    def save_config(self):
        """Salva URL e API Key em um arquivo de configuração."""
        config = {
            "supabase_url": self.supabase_url.get(),
            "supabase_key": self.supabase_key.get(),
            "db_host": self.db_host.get(),
            "db_name": self.db_name.get(),
            "db_user": self.db_user.get(),
            "db_password": self.db_password.get(), # Salvar senha em texto plano NÃO é seguro!
            "db_port": self.db_port.get(),
            "table_name": self.table_name.get(),
            "connection_method": self.method_var.get(),
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
            messagebox.showinfo("Configuração Salva", "Configurações salvas com sucesso!", parent=self)
        except Exception as e:
            messagebox.showerror("Erro ao Salvar Config", f"Não foi possível salvar as configurações: {e}", parent=self)

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Configuração da conexão
        config_frame = ttk.LabelFrame(main_frame, text="Configuração da Conexão")
        config_frame.pack(fill=tk.X, pady=5)

        # Método de conexão
        method_frame = ttk.Frame(config_frame)
        method_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(method_frame, text="Método:").pack(side=tk.LEFT)
        method_combo = ttk.Combobox(method_frame, textvariable=self.method_var, 
                                  values=["rest_api", "postgresql"], width=15, state="readonly")
        method_combo.pack(side=tk.LEFT, padx=5)
        method_combo.bind('<<ComboboxSelected>>', self.on_method_change)

        # Frame para configurações REST API
        self.rest_frame = ttk.LabelFrame(config_frame, text="Configurações REST API")
        
        url_frame = ttk.Frame(self.rest_frame)
        url_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(url_frame, text="URL do Projeto:").pack(side=tk.LEFT)
        self.url_entry = ttk.Entry(url_frame, textvariable=self.supabase_url, width=50)
        self.url_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        key_frame = ttk.Frame(self.rest_frame)
        key_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(key_frame, text="API Key:").pack(side=tk.LEFT)
        self.key_entry = ttk.Entry(key_frame, textvariable=self.supabase_key, show="*", width=50)
        self.key_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Frame para configurações PostgreSQL
        self.pg_frame = ttk.LabelFrame(config_frame, text="Configurações PostgreSQL")
        
        pg_grid = ttk.Frame(self.pg_frame)
        pg_grid.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(pg_grid, text="Host:").grid(row=0, column=0, sticky="w", padx=2, pady=2)
        self.host_entry = ttk.Entry(pg_grid, textvariable=self.db_host, width=30)
        self.host_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        
        ttk.Label(pg_grid, text="Porta:").grid(row=0, column=2, sticky="w", padx=2, pady=2)
        self.port_entry = ttk.Entry(pg_grid, textvariable=self.db_port, width=10)
        self.port_entry.grid(row=0, column=3, padx=5, pady=2)
        
        ttk.Label(pg_grid, text="Database:").grid(row=1, column=0, sticky="w", padx=2, pady=2)
        self.db_entry = ttk.Entry(pg_grid, textvariable=self.db_name, width=20)
        self.db_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        
        ttk.Label(pg_grid, text="Usuário:").grid(row=2, column=0, sticky="w", padx=2, pady=2)
        self.user_entry = ttk.Entry(pg_grid, textvariable=self.db_user, width=20)
        self.user_entry.grid(row=2, column=1, padx=5, pady=2, sticky="ew")
        
        ttk.Label(pg_grid, text="Senha:").grid(row=2, column=2, sticky="w", padx=2, pady=2)
        self.pass_entry = ttk.Entry(pg_grid, textvariable=self.db_password, show="*", width=20)
        self.pass_entry.grid(row=2, column=3, padx=5, pady=2, sticky="ew")
        
        pg_grid.columnconfigure(1, weight=1)

        # Status e botões de ação
        action_frame = ttk.Frame(config_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.status_label = ttk.Label(action_frame, text="Status: Desconectado")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(action_frame, text="Testar Conexão", command=self.test_connection).pack(side=tk.RIGHT, padx=5)
        ttk.Button(action_frame, text="Carregar Dados", command=self.load_data_from_supabase).pack(side=tk.RIGHT, padx=5)
        ttk.Button(action_frame, text="Salvar Config", command=self.save_config).pack(side=tk.RIGHT, padx=5)


        # Configuração da tabela
        table_frame = ttk.Frame(config_frame)
        table_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(table_frame, text="Nome da Tabela:").pack(side=tk.LEFT)
        self.table_entry = ttk.Entry(table_frame, textvariable=self.table_name, width=30)
        self.table_entry.pack(side=tk.LEFT, padx=5)

        # Aviso sobre edição
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(info_frame, text="💡 Dica: Dê duplo-clique em qualquer campo para editá-lo antes de importar",
                 foreground="blue", font=("Arial", 9, "italic")).pack(anchor=tk.W)

        # Data display Treeview
        tree_frame = ttk.LabelFrame(main_frame, text="Dados para Importar")
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.tree = ttk.Treeview(tree_frame, selectmode="none")
        # Adicionada a coluna 'data_despesa' ao Treeview
        self.tree['columns'] = ('select', 'descricao', 'valor', 'forma_pagamento', 'conta_despesa', 'numero_parcelas', 'data_despesa', 'created_at')
        
        # Configuração das colunas
        self.tree.column("#0", width=0, stretch=tk.NO)
        self.tree.column("select", anchor=tk.CENTER, width=50)
        self.tree.column("descricao", anchor=tk.W, width=200)
        self.tree.column("valor", anchor=tk.E, width=90)
        self.tree.column("forma_pagamento", anchor=tk.W, width=120)
        self.tree.column("conta_despesa", anchor=tk.W, width=120)
        self.tree.column("numero_parcelas", anchor=tk.CENTER, width=70)
        self.tree.column("data_despesa", anchor=tk.CENTER, width=100) # Nova coluna para data_despesa
        self.tree.column("created_at", anchor=tk.CENTER, width=100)

        # Configuração dos cabeçalhos
        self.tree.heading("select", text="Sel.", command=self.toggle_all_selections)
        self.tree.heading("descricao", text="Descrição")
        self.tree.heading("valor", text="Valor")
        self.tree.heading("forma_pagamento", text="Meio Pgto.")
        self.tree.heading("conta_despesa", text="Categoria")
        self.tree.heading("numero_parcelas", text="Parcelas")
        self.tree.heading("data_despesa", text="Data Despesa") # Novo cabeçalho
        self.tree.heading("created_at", text="Data Criação")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.config(yscrollcommand=scrollbar.set)

        self.tree.bind("<ButtonRelease-1>", self.on_tree_click)
        self.tree.bind("<Double-Button-1>", self.on_tree_double_click)

        # Import buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="Importar Selecionados", command=self.import_selected_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Importar Todos", command=self.import_all_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Fechar", command=self.destroy).pack(side=tk.RIGHT, padx=5)


    def on_method_change(self, event=None):
        method = self.method_var.get()
        if method == "rest_api":
            self.rest_frame.pack(fill=tk.X, padx=5, pady=5)
            self.pg_frame.pack_forget()
        else:
            self.pg_frame.pack(fill=tk.X, padx=5, pady=5)
            self.rest_frame.pack_forget()

    def test_connection(self):
        """Testa a conexão com o Supabase"""
        method = self.method_var.get()
        
        if method == "rest_api":
            self.test_rest_api_connection()
        else:
            self.test_postgresql_connection()

    def test_rest_api_connection(self):
        """Testa conexão via REST API"""
        url = self.supabase_url.get().strip()
        key = self.supabase_key.get().strip()
        
        if not url or not key:
            messagebox.showwarning("Configuração Incompleta", 
                                 "Por favor, preencha a URL e a chave da API.", parent=self)
            return
        
        try:
            headers = {
                'apikey': key,
                'Authorization': f'Bearer {key}',
                'Content-Type': 'application/json'
            }
            
            test_url = f"{url}/rest/v1/"
            response = requests.get(test_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                self.status_label.config(text="Status: Conectado via REST API", foreground="green")
                messagebox.showinfo("Sucesso", "Conexão REST API estabelecida com sucesso!", parent=self)
            else:
                self.status_label.config(text=f"Status: Erro HTTP {response.status_code}", foreground="red")
                messagebox.showerror("Erro", f"Erro na conexão: HTTP {response.status_code} - {response.text}", parent=self)
                
        except requests.exceptions.Timeout:
            self.status_label.config(text="Status: Timeout", foreground="red")
            messagebox.showerror("Timeout", "Timeout na conexão. Verifique a URL e sua conexão de internet.", parent=self)
        except Exception as e:
            self.status_label.config(text=f"Status: Erro - {str(e)[:50]}", foreground="red")
            messagebox.showerror("Erro", f"Erro na conexão: {e}", parent=self)

    def test_postgresql_connection(self):
        """Testa conexão via PostgreSQL"""
        try:
            conn = psycopg2.connect(
                host=self.db_host.get().strip(),
                database=self.db_name.get().strip(),
                user=self.db_user.get().strip(),
                password=self.db_password.get().strip(),
                port=self.db_port.get().strip(),
                connect_timeout=10
            )
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            cursor.close()
            conn.close()
            
            self.status_label.config(text="Status: Conectado via PostgreSQL", foreground="green")
            messagebox.showinfo("Sucesso", "Conexão PostgreSQL estabelecida com sucesso!", parent=self)
            
        except Exception as e:
            self.status_label.config(text=f"Status: Erro PostgreSQL - {str(e)[:50]}", foreground="red")
            messagebox.showerror("Erro PostgreSQL", f"Erro na conexão: {e}", parent=self)

    def load_data_from_supabase(self):
        """Carrega dados do Supabase usando o método selecionado"""
        method = self.method_var.get()
        
        if method == "rest_api":
            self.load_data_via_rest_api()
        else:
            self.load_data_via_postgresql()

    def load_data_via_rest_api(self):
        """Carrega dados via REST API"""
        url = self.supabase_url.get().strip()
        key = self.supabase_key.get().strip()
        table_name = self.table_name.get().strip()

        if not url or not key or not table_name:
            messagebox.showwarning("Configuração Incompleta", 
                                 "Por favor, preencha todos os campos necessários.", parent=self)
            return

        # Limpar dados anteriores
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.loaded_data = []

        try:
            headers = {
                'apikey': key,
                'Authorization': f'Bearer {key}',
                'Content-Type': 'application/json'
            }
            
            # ATUALIZADO: Buscar 'data_despesa' e 'migrado'
            api_url = f"{url}/rest/v1/{table_name}?select=id,descricao,valor,forma_pagamento,conta_despesa,numero_parcelas,data_despesa,created_at,migrado&migrado=eq.false&order=created_at.desc"
            response = requests.get(api_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                messagebox.showerror("Erro", f"Erro ao buscar dados: HTTP {response.status_code}\n{response.text}", parent=self)
                return
            
            data = response.json()
            
            if not data:
                messagebox.showinfo("Sem Dados", f"Nenhum dado com 'migrado=FALSE' encontrado na tabela '{table_name}'.", parent=self)
                return

            self.process_loaded_data(data)
            
        except requests.exceptions.Timeout:
            messagebox.showerror("Timeout", "Timeout ao carregar dados. Tente novamente.", parent=self)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar dados via REST API: {e}", parent=self)

    def load_data_via_postgresql(self):
        """Carrega dados via conexão PostgreSQL direta"""
        table_name = self.table_name.get().strip()
        
        if not table_name:
            messagebox.showwarning("Configuração Incompleta", 
                                 "Por favor, informe o nome da tabela.", parent=self)
            return

        try:
            conn = psycopg2.connect(
                host=self.db_host.get().strip(),
                database=self.db_name.get().strip(),
                user=self.db_user.get().strip(),
                password=self.db_password.get().strip(),
                port=self.db_port.get().strip(),
                connect_timeout=10
            )
            cursor = conn.cursor()
            
            # Limpar dados anteriores
            for i in self.tree.get_children():
                self.tree.delete(i)
            self.loaded_data = []
            
            # ATUALIZADO: Buscar 'data_despesa' e 'migrado'
            cursor.execute(f"""
                SELECT
                    id,
                    descricao,
                    valor,
                    forma_pagamento,
                    conta_despesa,
                    numero_parcelas,
                    data_despesa, -- Adicionado data_despesa
                    created_at,
                    migrado
                FROM {table_name}
                WHERE migrado = FALSE
                ORDER BY created_at DESC
            """)
            
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            
            if not rows:
                messagebox.showinfo("Sem Dados", f"Nenhum dado com 'migrado=FALSE' encontrado na tabela '{table_name}'.", parent=self)
                return

            # Converter rows para formato de dicionário para reuso de process_loaded_data
            data = []
            # Mapeamento para garantir que os campos estejam corretos no dicionário
            column_names = ['id', 'descricao', 'valor', 'forma_pagamento', 'conta_despesa', 
                            'numero_parcelas', 'data_despesa', 'created_at', 'migrado'] # ATUALIZADO
            for row_tuple in rows:
                row_dict = dict(zip(column_names, row_tuple))
                data.append(row_dict)
            
            self.process_loaded_data(data)
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar dados via PostgreSQL: {e}", parent=self)

    def process_loaded_data(self, data):
        """Processa os dados carregados e popula a interface"""
        for i, row in enumerate(data):
            id_supabase = row.get('id')
            descricao = row.get('descricao', '')
            valor = float(row.get('valor', 0))
            forma_pagamento = row.get('forma_pagamento', '')
            conta_despesa = row.get('conta_despesa', '')
            num_parcelas = int(row.get('numero_parcelas', 1)) if row.get('numero_parcelas') is not None else 1
            
            # NOVO: Processar data_despesa para exibição e formato de DB
            data_despesa_raw = row.get('data_despesa')
            if data_despesa_raw:
                try:
                    # Tenta converter do formato 'YYYY-MM-DD' (ou similar)
                    data_despesa_dt = datetime.fromisoformat(data_despesa_raw.replace('Z', '+00:00') if isinstance(data_despesa_raw, str) else str(data_despesa_raw))
                except ValueError:
                    try: # Fallback para outros formatos de string se necessário
                        data_despesa_dt = datetime.strptime(data_despesa_raw[:10], '%Y-%m-%d') # Pega apenas a parte da data
                    except ValueError:
                        data_despesa_dt = datetime.now() # Fallback geral
            elif isinstance(data_despesa_raw, datetime): 
                data_despesa_dt = data_despesa_raw
            else:
                data_despesa_dt = datetime.now() 
            
            data_despesa_display = data_despesa_dt.strftime('%d/%m/%Y')
            data_despesa_db_format = data_despesa_dt.strftime('%Y-%m-%d') # Para o DB local SQLite

            created_at_raw = row.get('created_at')
            migrado_status = row.get('migrado', False)
            
            # A lógica para created_at permanece, mas não é a que será usada para data_pagamento
            if created_at_raw:
                try:
                    created_at_dt = datetime.fromisoformat(created_at_raw.replace('Z', '+00:00'))
                except ValueError:
                    try:
                        created_at_dt = datetime.strptime(created_at_raw[:19], '%Y-%m-%dT%H:%M:%S')
                    except ValueError:
                        created_at_dt = datetime.now()
            elif isinstance(created_at_raw, datetime):
                created_at_dt = created_at_raw
            else:
                created_at_dt = datetime.now()
            
            created_at_display = created_at_dt.strftime('%d/%m/%Y %H:%M') # Mostra a hora também para created_at
            
            # Armazenar dados, incluindo o ID do Supabase, status de migração e a data da despesa
            item_data = {
                "original_row": row,
                "id_supabase": id_supabase,
                "descricao": descricao,
                "valor": valor,
                "forma_pagamento": forma_pagamento,
                "conta_despesa": conta_despesa,
                "num_parcelas": num_parcelas,
                "data_despesa": data_despesa_display, # Campo editável (formato dd/mm/yyyy)
                "data_despesa_display": data_despesa_display, # Para exibição
                "data_despesa_db_format": data_despesa_db_format, # Para inserção no banco (formato yyyy-mm-dd)
                "created_at_display": created_at_display, # Apenas para exibição, não será importado como data_pagamento
                "migrado_status": migrado_status,
                "selected": False
            }
            self.loaded_data.append(item_data)

            # Inserir na interface (Treeview) - a ordem aqui é importante para exibição
            self.tree.insert("", tk.END, iid=str(i), values=(
                "[]",
                descricao,
                locale.currency(valor, grouping=True),
                forma_pagamento,
                conta_despesa,
                num_parcelas,
                data_despesa_display, # Adicionado à exibição
                created_at_display
            ))
        
        messagebox.showinfo("Sucesso", f"{len(self.loaded_data)} registros carregados do Supabase.", parent=self)

    def on_tree_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return

        column_id = self.tree.identify_column(event.x)
        if column_id == "#1":  # Column "select"
            index = int(item_id)
            if 0 <= index < len(self.loaded_data):
                self.loaded_data[index]["selected"] = not self.loaded_data[index]["selected"]
                self.update_checkbox_display(item_id, self.loaded_data[index]["selected"])

    def update_checkbox_display(self, item_id, is_selected):
        current_values = list(self.tree.item(item_id, 'values'))
        current_values[0] = "[X]" if is_selected else "[]"
        self.tree.item(item_id, values=current_values)

    def toggle_all_selections(self):
        all_selected = all(item["selected"] for item in self.loaded_data)
        for i, item_data in enumerate(self.loaded_data):
            self.loaded_data[i]["selected"] = not all_selected
            self.update_checkbox_display(str(i), self.loaded_data[i]["selected"])

    def on_tree_double_click(self, event):
        """Permite editar qualquer campo ao dar duplo clique"""
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return

        column_id = self.tree.identify_column(event.x)
        index = int(item_id)

        if 0 <= index < len(self.loaded_data):
            # Mapear coluna para campo editável
            column_map = {
                "#2": ("descricao", "Descrição", "descricao"),
                "#3": ("valor", "Valor", "valor"),
                "#4": ("forma_pagamento", "Meio Pagamento", "forma_pagamento"),
                "#5": ("conta_despesa", "Categoria", "conta_despesa"),
                "#6": ("numero_parcelas", "Número de Parcelas", "num_parcelas"),
                "#7": ("data_despesa", "Data Despesa", "data_despesa")
            }

            if column_id in column_map:
                field_key, field_label, data_key = column_map[column_id]
                self.edit_field(item_id, index, field_key, field_label, data_key, column_id)

    def edit_field(self, item_id, index, field_key, field_label, data_key, column_id):
        """Abre um diálogo genérico para editar qualquer campo"""
        # Obter valor atual
        current_value = self.loaded_data[index].get(data_key, "")
        if field_key == "data_despesa":
            # Para data, mostrar no formato dd/mm/yyyy se disponível
            current_value = self.loaded_data[index].get("data_despesa_display", current_value)

        # Criar janela de diálogo
        dialog = tk.Toplevel(self)
        dialog.title(f"Editar {field_label}")
        dialog.geometry("400x150")
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text=f"Novo valor para {field_label}:").pack(pady=10)

        field_var = tk.StringVar(value=str(current_value))
        field_entry = ttk.Entry(dialog, textvariable=field_var, width=50)
        field_entry.pack(pady=5)
        field_entry.focus()
        field_entry.select_range(0, tk.END)

        def salvar_campo():
            novo_valor = field_var.get().strip()
            if not novo_valor:
                messagebox.showwarning("Valor Vazio", "O campo não pode estar vazio.", parent=dialog)
                return

            try:
                # Validação específica por tipo de campo
                if field_key == "valor":
                    # Converter para float
                    novo_valor = float(novo_valor.replace(',', '.'))
                elif field_key == "numero_parcelas":
                    # Converter para int
                    novo_valor = int(novo_valor)
                elif field_key == "data_despesa":
                    # Validar formato de data e converter
                    from datetime import datetime
                    if '/' in novo_valor:
                        # Formato dd/mm/yyyy
                        data_obj = datetime.strptime(novo_valor, '%d/%m/%Y')
                        # Atualizar tanto o formato de exibição quanto o formato DB
                        self.loaded_data[index]["data_despesa_display"] = novo_valor
                        self.loaded_data[index]["data_despesa_db_format"] = data_obj.strftime('%Y-%m-%d')
                        self.loaded_data[index]["data_despesa"] = novo_valor
                    else:
                        # Formato yyyy-mm-dd
                        data_obj = datetime.strptime(novo_valor, '%Y-%m-%d')
                        self.loaded_data[index]["data_despesa_display"] = data_obj.strftime('%d/%m/%Y')
                        self.loaded_data[index]["data_despesa_db_format"] = novo_valor
                        self.loaded_data[index]["data_despesa"] = data_obj.strftime('%d/%m/%Y')

                # Atualizar nos dados carregados
                self.loaded_data[index][data_key] = novo_valor

                # Atualizar na interface
                current_values = list(self.tree.item(item_id, 'values'))
                column_index = int(column_id.replace('#', '')) - 1

                # Formatar valor para exibição
                if field_key == "valor":
                    display_value = f"{novo_valor:.2f}"
                elif field_key == "data_despesa":
                    display_value = self.loaded_data[index]["data_despesa_display"]
                else:
                    display_value = str(novo_valor)

                current_values[column_index] = display_value
                self.tree.item(item_id, values=current_values)

                dialog.destroy()

            except ValueError as e:
                messagebox.showerror("Erro de Validação",
                                    f"Valor inválido para {field_label}: {str(e)}",
                                    parent=dialog)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Salvar", command=salvar_campo).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

        # Permitir salvar com Enter
        field_entry.bind('<Return>', lambda e: salvar_campo())

    def import_selected_data(self):
        selected_items = [item for item in self.loaded_data if item["selected"]]
        if not selected_items:
            messagebox.showwarning("Nenhuma Seleção", "Nenhum item selecionado para importação.", parent=self)
            return

        if not messagebox.askyesno("Confirmar Importação", f"Deseja importar {len(selected_items)} registros selecionados para o banco de dados local?", parent=self):
            return

        self._perform_import(selected_items)

    def import_all_data(self):
        if not self.loaded_data:
            messagebox.showinfo("Sem Dados", "Nenhum dado carregado para importar.", parent=self)
            return

        if not messagebox.askyesno("Confirmar Importação", f"Deseja importar TODOS os {len(self.loaded_data)} registros exibidos para o banco de dados local?", parent=self):
            return
            
        self._perform_import(self.loaded_data)
        
    def _perform_import(self, data_to_import):
        """
        Realiza a importação dos dados selecionados.
        IMPORTANTE: Usa os valores de self.loaded_data, que contém os dados editados na interface,
        garantindo que valores modificados pelo usuário sejam importados corretamente.
        """
        imported_count = 0
        failed_import_count = 0
        eventos_caixa_count = 0
        errors = []
        ids_to_update_supabase_migrated_status = []
        ids_to_delete_from_supabase = []

        local_conn = self.parent_app.conn
        local_cursor = self.parent_app.cursor

        # Coletar IDs não selecionados para deletar
        for item_data in self.loaded_data:
            if not item_data["selected"] and item_data.get("id_supabase") is not None:
                ids_to_delete_from_supabase.append(item_data["id_supabase"])

        # Importar cada item selecionado (usando valores editados na interface)
        for item_data in data_to_import:
            try:
                categoria = item_data["conta_despesa"].strip().lower()

                # Verificar se é categoria "pagamento" - inserir em eventos_caixa_avulsos
                if categoria == "pagamento":
                    # Garantir que o valor seja negativo (saída de caixa)
                    valor_saida = -abs(item_data["valor"])
                    local_cursor.execute("""
                        INSERT INTO eventos_caixa_avulsos (data, descricao, valor)
                        VALUES (?, ?, ?)
                    """, (
                        item_data["data_despesa_db_format"],
                        item_data["descricao"],
                        valor_saida
                    ))
                    local_conn.commit()
                    eventos_caixa_count += 1
                else:
                    # Inserir como despesa normal
                    local_cursor.execute("""
                        INSERT INTO despesas (descricao, valor, meio_pagamento, conta_despesa,
                                             num_parcelas, data_registro, data_pagamento)
                        VALUES (?, ?, ?, ?, ?, date('now'), ?)
                    """, (
                        item_data["descricao"],
                        item_data["valor"],
                        item_data["forma_pagamento"],
                        item_data["conta_despesa"],
                        item_data["num_parcelas"],
                        item_data["data_despesa_db_format"]
                    ))
                    local_conn.commit()

                imported_count += 1

                # Se a importação local foi bem-sucedida, adicionar ID à lista para atualização no Supabase
                if item_data.get("id_supabase") is not None:
                    ids_to_update_supabase_migrated_status.append(item_data["id_supabase"])
            except Exception as e:
                failed_import_count += 1
                errors.append(f"Erro ao importar '{item_data['descricao']}': {e}")
                local_conn.rollback()

        if imported_count > 0:
            msg_detalhes = f"Importação finalizada:\n{imported_count} registros importados com sucesso.\n"
            if eventos_caixa_count > 0:
                msg_detalhes += f"{eventos_caixa_count} registros importados como Saída de Caixa Avulso.\n"
            if failed_import_count > 0:
                msg_detalhes += f"{failed_import_count} falhas."

            messagebox.showinfo("Importação Concluída", msg_detalhes, parent=self)

            # --- Lógica de Atualização do Status 'migrado' no Supabase ---
            if ids_to_update_supabase_migrated_status:
                self.update_supabase_migrated_status(ids_to_update_supabase_migrated_status)
            # --- Fim da Lógica de Atualização ---

            # --- Lógica de Exclusão de Registros Não Selecionados ---
            if ids_to_delete_from_supabase:
                self.delete_from_supabase(ids_to_delete_from_supabase)
            # --- Fim da Lógica de Exclusão ---

            if hasattr(self.parent_app, 'carregar_despesas'):
                self.parent_app.carregar_despesas()

            # Limpa os dados carregados da interface
            self.loaded_data = []
            for i in self.tree.get_children():
                self.tree.delete(i)
        elif failed_import_count > 0:
             messagebox.showerror("Importação com Erros",
                                f"Importação finalizada com falhas:\n{failed_import_count} registros falharam.\nErros: {', '.join(errors[:5])}...",
                                parent=self)
        else:
            messagebox.showinfo("Importação", "Nenhum registro foi importado.", parent=self)

    def update_supabase_migrated_status(self, ids_to_update):
        """Atualiza o campo 'migrado' para TRUE no Supabase para os IDs fornecidos."""
        method = self.method_var.get()
        table_name = self.table_name.get().strip()
        updated_count = 0
        
        if method == "rest_api":
            url = self.supabase_url.get().strip()
            key = self.supabase_key.get().strip()
            headers = {
                'apikey': key,
                'Authorization': f'Bearer {key}',
                'Content-Type': 'application/json',
                'Prefer': 'return=representation'
            }
            
            ids_str = ",".join(map(str, ids_to_update))
            update_url = f"{url}/rest/v1/{table_name}?id=in.({ids_str})"
            payload = {"migrado": True}

            try:
                response = requests.patch(update_url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    updated_records = response.json()
                    updated_count = len(updated_records)
                    messagebox.showinfo("Atualização Supabase", 
                                        f"{updated_count} registros atualizados para 'migrado=TRUE' no Supabase via REST API.", 
                                        parent=self)
                else:
                    messagebox.showerror("Erro ao Atualizar Supabase (REST)", 
                                        f"Erro HTTP {response.status_code} ao atualizar: {response.text}", 
                                        parent=self)
            except Exception as e:
                messagebox.showerror("Erro ao Atualizar Supabase (REST)", 
                                    f"Erro de conexão ao atualizar: {e}", parent=self)
        
        elif method == "postgresql":
            try:
                conn = psycopg2.connect(
                    host=self.db_host.get().strip(),
                    database=self.db_name.get().strip(),
                    user=self.db_user.get().strip(),
                    password=self.db_password.get().strip(),
                    port=self.db_port.get().strip(),
                    connect_timeout=10
                )
                cursor = conn.cursor()
                
                # Atualizar registros com base nos IDs
                placeholders = ','.join(['%s'] * len(ids_to_update))
                update_query = f"UPDATE {table_name} SET migrado = TRUE WHERE id IN ({placeholders})"
                
                cursor.execute(update_query, tuple(ids_to_update))
                conn.commit()
                updated_count = cursor.rowcount
                
                cursor.close()
                conn.close()
                
                messagebox.showinfo("Atualização Supabase", 
                                    f"{updated_count} registros atualizados para 'migrado=TRUE' no Supabase via PostgreSQL.", 
                                    parent=self)
                
            except Exception as e:
                messagebox.showerror("Erro ao Atualizar Supabase (PostgreSQL)", 
                                    f"Erro ao atualizar via PostgreSQL: {e}", parent=self)

        return updated_count

    def delete_from_supabase(self, ids_to_delete):
        """Deleta registros do Supabase com base nos IDs fornecidos."""
        if not ids_to_delete:
            return 0

        method = self.method_var.get()
        table_name = self.table_name.get().strip()
        deleted_count = 0

        if method == "rest_api":
            url = self.supabase_url.get().strip()
            key = self.supabase_key.get().strip()
            headers = {
                'apikey': key,
                'Authorization': f'Bearer {key}',
                'Content-Type': 'application/json',
                'Prefer': 'return=representation'
            }

            ids_str = ",".join(map(str, ids_to_delete))
            delete_url = f"{url}/rest/v1/{table_name}?id=in.({ids_str})"

            try:
                response = requests.delete(delete_url, headers=headers, timeout=30)
                if response.status_code == 200:
                    deleted_records = response.json()
                    deleted_count = len(deleted_records)
                    messagebox.showinfo("Exclusão Supabase",
                                        f"{deleted_count} registros excluídos do Supabase via REST API.",
                                        parent=self)
                else:
                    messagebox.showerror("Erro ao Excluir Supabase (REST)",
                                        f"Erro HTTP {response.status_code} ao excluir: {response.text}",
                                        parent=self)
            except Exception as e:
                messagebox.showerror("Erro ao Excluir Supabase (REST)",
                                    f"Erro de conexão ao excluir: {e}", parent=self)

        elif method == "postgresql":
            try:
                conn = psycopg2.connect(
                    host=self.db_host.get().strip(),
                    database=self.db_name.get().strip(),
                    user=self.db_user.get().strip(),
                    password=self.db_password.get().strip(),
                    port=self.db_port.get().strip(),
                    connect_timeout=10
                )
                cursor = conn.cursor()

                # Deletar registros com base nos IDs
                placeholders = ','.join(['%s'] * len(ids_to_delete))
                delete_query = f"DELETE FROM {table_name} WHERE id IN ({placeholders})"

                cursor.execute(delete_query, tuple(ids_to_delete))
                conn.commit()
                deleted_count = cursor.rowcount

                cursor.close()
                conn.close()

                messagebox.showinfo("Exclusão Supabase",
                                    f"{deleted_count} registros excluídos do Supabase via PostgreSQL.",
                                    parent=self)

            except Exception as e:
                messagebox.showerror("Erro ao Excluir Supabase (PostgreSQL)",
                                    f"Erro ao excluir via PostgreSQL: {e}", parent=self)

        return deleted_count


    def destroy(self):
        if self.supabase_conn:
            try:
                self.supabase_cursor.close()
                self.supabase_conn.close()
            except Exception as e:
                print(f"Erro ao fechar conexão Supabase: {e}")
        super().destroy()

# Função para ser chamada da aplicação principal
# Esta função deve estar FORA da classe SupabaseImporter
def iniciar_importador_supabase(parent_widget, app_logic):
    SupabaseImporter(parent_widget, app_logic)

# Exemplo de como esta classe seria integrada em uma aplicação principal (para fins de teste)
if __name__ == "__main__":
    class MockApp:
        def __init__(self):
            self.root = tk.Tk()
            self.root.withdraw() 
            self.conn = None
            self.cursor = None
            self.setup_local_db()

        def setup_local_db(self):
            import sqlite3
            self.conn = sqlite3.connect('financas.db')
            self.cursor = self.conn.cursor()
            # Certifique-se de que a tabela 'despesas' no seu DB local tem estas colunas.
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS despesas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    descricao TEXT NOT NULL,
                    valor REAL NOT NULL,
                    meio_pagamento TEXT,
                    conta_despesa TEXT,
                    num_parcelas INTEGER DEFAULT 1,
                    data_registro TEXT,
                    data_pagamento TEXT
                )
            ''')
            self.conn.commit()

        def carregar_despesas(self):
            print("Método carregar_despesas da aplicação principal chamado (simulado).")
            # Adicione aqui a lógica para recarregar despesas na interface principal

    mock_app = MockApp()
    iniciar_importador_supabase(mock_app.root, mock_app)
    mock_app.root.mainloop()
    if mock_app.conn:
        mock_app.conn.close()