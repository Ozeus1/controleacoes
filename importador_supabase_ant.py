# importador_supabase.py

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import psycopg2
from datetime import datetime
import locale

# Configurar a localização para formato de moeda brasileiro (necessário para formatação)
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
        self.geometry("900x600")

        self.parent_app = app_logic # Access to the main app's SQLite connection
        self.supabase_conn = None
        self.supabase_cursor = None
        self.loaded_data = [] # To store data fetched from Supabase

        # Supabase Connection Details (Replace with your actual details)
        # BEST PRACTICE: Store these securely, e.g., in environment variables or a separate config file
        self.DB_HOST = "gbrktfhxlfqdefuofdpk.supabase.co" # e.g., 'project-id.supabase.co'
        self.DB_NAME = "Financaspessoais" # e.g., 'postgres' or your custom database name
        self.DB_USER = "postgres" # e.g., 'postgres'
        self.DB_PASSWORD = "Senhasupabase!@#$1" # Your database password
        self.DB_PORT = "5432" # Default PostgreSQL port 
        
        self.create_widgets()
        self.connect_to_supabase()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Connection status and Load button
        conn_frame = ttk.LabelFrame(main_frame, text="Conexão Supabase")
        conn_frame.pack(fill=tk.X, pady=5)

        self.status_label = ttk.Label(conn_frame, text="Status: Desconectado")
        self.status_label.pack(side=tk.LEFT, padx=5)

        ttk.Button(conn_frame, text="Carregar Dados do Supabase", command=self.load_data_from_supabase).pack(side=tk.RIGHT, padx=5)

        # Data display Treeview
        tree_frame = ttk.LabelFrame(main_frame, text="Dados para Importar")
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.tree = ttk.Treeview(tree_frame, selectmode="none")
        self.tree['columns'] = ('select', 'descricao', 'meio', 'categoria', 'valor', 'parcelas', 'data_pagamento')
        
        self.tree.column("#0", width=0, stretch=tk.NO)
        self.tree.column("select", anchor=tk.CENTER, width=50)
        self.tree.column("descricao", anchor=tk.W, width=250)
        self.tree.column("meio", anchor=tk.W, width=120)
        self.tree.column("categoria", anchor=tk.W, width=120)
        self.tree.column("valor", anchor=tk.E, width=100)
        self.tree.column("parcelas", anchor=tk.CENTER, width=70)
        self.tree.column("data_pagamento", anchor=tk.CENTER, width=100)

        self.tree.heading("select", text="Sel.", command=self.toggle_all_selections)
        self.tree.heading("descricao", text="Descrição")
        self.tree.heading("meio", text="Meio Pgto.")
        self.tree.heading("categoria", text="Categoria")
        self.tree.heading("valor", text="Valor")
        self.tree.heading("parcelas", text="Parcelas")
        self.tree.heading("data_pagamento", text="Data Pgto.")

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.config(yscrollcommand=scrollbar.set)

        self.tree.bind("<ButtonRelease-1>", self.on_tree_click)

        # Import buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="Importar Selecionados", command=self.import_selected_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Importar Todos", command=self.import_all_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Fechar", command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def connect_to_supabase(self):
        try:
            self.supabase_conn = psycopg2.connect(
                host=self.DB_HOST,
                database=self.DB_NAME,
                user=self.DB_USER,
                password=self.DB_PASSWORD,
                port=self.DB_PORT
            )
            self.supabase_cursor = self.supabase_conn.cursor()
            self.status_label.config(text="Status: Conectado ao Supabase", foreground="green")
        except Exception as e:
            self.status_label.config(text=f"Status: Erro de Conexão - {e}", foreground="red")
            messagebox.showerror("Erro de Conexão Supabase", f"Não foi possível conectar ao Supabase: {e}\nVerifique suas credenciais e conexão.", parent=self)
            self.supabase_conn = None
            self.supabase_cursor = None

    def load_data_from_supabase(self):
        if not self.supabase_conn:
            messagebox.showwarning("Conexão Necessária", "Primeiro, conecte-se ao Supabase.", parent=self)
            return

        for i in self.tree.get_children():
            self.tree.delete(i)
        self.loaded_data = []

        try:
            # ASSUMPTION: Supabase table 'dados_financeiros' has these columns
            # Adjust column names below to match your actual Supabase table schema
            self.supabase_cursor.execute("""
                SELECT
                    description,       -- Mapped to descricao
                    payment_method,    -- Mapped to meio_pagamento
                    category,          -- Mapped to conta_despesa
                    amount,            -- Mapped to valor
                    installments,      -- Mapped to num_parcelas
                    payment_date       -- Mapped to data_pagamento (assuming DATE or TIMESTAMP)
                FROM dados_financeiros
                ORDER BY payment_date DESC
            """)
            
            rows = self.supabase_cursor.fetchall()

            if not rows:
                messagebox.showinfo("Sem Dados", "Nenhum dado encontrado na tabela 'dados_financeiros' do Supabase.", parent=self)
                return

            for i, row in enumerate(rows):
                # Map Supabase data to local 'despesas' table format
                descricao = row[0]
                meio_pagamento = row[1]
                conta_despesa = row[2]
                valor = float(row[3]) # Ensure it's float
                num_parcelas = int(row[4]) if row[4] is not None else 1 # Default to 1 if null
                
                # Format date to 'DD/MM/YYYY' for display, assume YYYY-MM-DD from Supabase
                data_pagamento_dt = row[5] # This should be a datetime object from psycopg2
                if isinstance(data_pagamento_dt, str):
                    try:
                        data_pagamento_dt = datetime.strptime(data_pagamento_dt, '%Y-%m-%d')
                    except ValueError:
                        data_pagamento_dt = datetime.now() # Fallback if format is unexpected
                
                data_pagamento_display = data_pagamento_dt.strftime('%d/%m/%Y')
                data_pagamento_db_format = data_pagamento_dt.strftime('%Y-%m-%d') # For SQLite insert

                # Store original Supabase values and formatted values for display/import
                item_data = {
                    "original_row": row,
                    "descricao": descricao,
                    "meio_pagamento": meio_pagamento,
                    "conta_despesa": conta_despesa,
                    "valor": valor,
                    "num_parcelas": num_parcelas,
                    "data_pagamento_display": data_pagamento_display,
                    "data_pagamento_db_format": data_pagamento_db_format,
                    "selected": False # Add a selection state
                }
                self.loaded_data.append(item_data)

                # Insert into Treeview for display
                self.tree.insert("", tk.END, iid=str(i), values=(
                    "[]", # Checkbox placeholder
                    descricao,
                    meio_pagamento,
                    conta_despesa,
                    locale.currency(valor, grouping=True),
                    num_parcelas,
                    data_pagamento_display
                ))
            messagebox.showinfo("Sucesso", f"{len(self.loaded_data)} registros carregados do Supabase.", parent=self)

        except Exception as e:
            messagebox.showerror("Erro ao Carregar Dados", f"Ocorreu um erro ao carregar dados: {e}", parent=self)
            import traceback
            traceback.print_exc()

    def on_tree_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return

        column_id = self.tree.identify_column(event.x)
        if column_id == "#1": # Column "select"
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
        imported_count = 0
        failed_count = 0
        errors = []

        local_conn = self.parent_app.conn
        local_cursor = self.parent_app.cursor

        for item_data in data_to_import:
            try:
                local_cursor.execute("""
                    INSERT INTO despesas (descricao, meio_pagamento, conta_despesa, valor,
                                         num_parcelas, data_registro, data_pagamento)
                    VALUES (?, ?, ?, ?, ?, date('now'), ?)
                """, (
                    item_data["descricao"],
                    item_data["meio_pagamento"],
                    item_data["conta_despesa"],
                    item_data["valor"],
                    item_data["num_parcelas"],
                    item_data["data_pagamento_db_format"]
                ))
                local_conn.commit()
                imported_count += 1
            except Exception as e:
                failed_count += 1
                errors.append(f"Erro ao importar '{item_data['descricao']}': {e}")
                local_conn.rollback() # Rollback on error for this item

        if imported_count > 0:
            messagebox.showinfo("Importação Concluída", 
                                f"Importação finalizada:\n{imported_count} registros importados com sucesso.\n{failed_count} falhas.", 
                                parent=self)
            self.parent_app.carregar_despesas() # Refresh main app's display
            self.loaded_data = [] # Clear loaded data after successful import
            for i in self.tree.get_children():
                self.tree.delete(i)
        elif failed_count > 0:
             messagebox.showerror("Importação com Erros", 
                                f"Importação finalizada com falhas:\n{failed_count} registros falharam.\nErros: {', '.join(errors[:5])}...", 
                                parent=self)
        else:
            messagebox.showinfo("Importação", "Nenhum registro foi importado.", parent=self)
        
        self.destroy() # Close the importer window after operation

    def destroy(self):
        if self.supabase_conn:
            try:
                self.supabase_cursor.close()
                self.supabase_conn.close()
                self.status_label.config(text="Status: Desconectado", foreground="black")
            except Exception as e:
                print(f"Erro ao fechar conexão Supabase: {e}")
        super().destroy()

# Function to be called from the main application
def iniciar_importador_supabase(parent_widget, app_logic):
    SupabaseImporter(parent_widget, app_logic)