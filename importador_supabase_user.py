# Conteúdo corrigido para importador_supabase.py
import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime
import locale
import requests
import json
import os 

try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    print("Aviso: Locale 'pt_BR' não pôde ser definido.")

class SupabaseImporter(tk.Toplevel):
    # ALTERADO: Recebe user_id
    def __init__(self, parent_widget, app_logic, user_id):
        super().__init__(parent_widget)
        self.transient(parent_widget)
        self.grab_set()
        self.title("Importar Despesas do Supabase")
        self.geometry("1000x700")

        self.parent_app = app_logic
        self.user_id = user_id # Armazena o ID do usuário
        self.loaded_data = []
        self.config_file = "supabase_config.json"
        
        self.supabase_url = tk.StringVar()
        self.supabase_key = tk.StringVar()
        # ... (demais StringVars não mudam)
        
        self.load_config() 
        self.create_widgets()
        self.on_method_change() 

    # ... (load_config e save_config não mudam)

    def _perform_import(self, data_to_import):
        # ... (início da função não muda)
        imported_count = 0
        failed_import_count = 0
        errors = []
        ids_to_update_supabase_migrated_status = []
        
        local_conn = self.parent_app.conn
        local_cursor = self.parent_app.cursor

        for item_data in data_to_import:
            try:
                # ALTERADO: A query agora inclui a coluna 'user_id'
                local_cursor.execute("""
                    INSERT INTO despesas (descricao, valor, meio_pagamento, conta_despesa,
                                         num_parcelas, data_registro, data_pagamento, user_id)
                    VALUES (?, ?, ?, ?, ?, date('now'), ?, ?)
                """, (
                    item_data["descricao"],
                    item_data["valor"],
                    item_data["forma_pagamento"],
                    item_data["conta_despesa"],
                    item_data["num_parcelas"],
                    item_data["data_despesa_db_format"],
                    self.user_id # <-- ID do usuário logado é inserido
                ))
                local_conn.commit()
                imported_count += 1
                
                if item_data.get("id_supabase") is not None:
                    ids_to_update_supabase_migrated_status.append(item_data["id_supabase"])
            except Exception as e:
                failed_import_count += 1
                errors.append(f"Erro ao importar '{item_data['descricao']}': {e}")
                local_conn.rollback()

        # ... (resto da função não muda)
        if imported_count > 0:
            messagebox.showinfo("Importação Concluída", f"{imported_count} registros importados.", parent=self)
            if ids_to_update_supabase_migrated_status:
                self.update_supabase_migrated_status(ids_to_update_supabase_migrated_status)
            if hasattr(self.parent_app, 'carregar_despesas'):
                self.parent_app.carregar_despesas()
            self.loaded_data = []
            for i in self.tree.get_children(): self.tree.delete(i)

    # (As demais funções do importador não precisam de alteração, desde que a chamada inicial e
    # a inserção no banco de dados estejam corretas)

# ALTERADO: Função de inicialização recebe e repassa o user_id
def iniciar_importador_supabase(parent_widget, app_logic, user_id):
    SupabaseImporter(parent_widget, app_logic, user_id)