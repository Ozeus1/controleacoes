"""
Função para importar dados do banco Flask (multi-usuário) para o sistema_financeiro_v14.py (single-user)

Importa apenas os dados do usuário 'admin' do banco Flask (instance/financas.db)
para o banco local do v14 (financas.db), sem alterar a estrutura do banco v14.
"""

def importar_dados_flask(self):
    """
    Importa despesas do banco Flask (multi-usuário) para o banco v14 (single-user).
    Importa apenas dados do usuário admin (user_id = 1).
    """
    import os
    from tkinter import messagebox
    
    # Caminho do banco Flask
    flask_db_path = os.path.join(os.path.dirname(__file__), 'instance', 'financas.db')
    
    # Verificar se o banco Flask existe
    if not os.path.exists(flask_db_path):
        messagebox.showerror(
            "Erro", 
            f"Banco de dados Flask não encontrado em:\n{flask_db_path}\n\n"
            "Certifique-se de que o aplicativo Flask foi executado pelo menos uma vez."
        )
        return
    
    try:
        # Conectar ao banco Flask
        import sqlite3
        flask_conn = sqlite3.connect(flask_db_path)
        flask_cursor = flask_conn.cursor()
        
        # Verificar se a tabela despesas existe e tem a coluna user_id
        flask_cursor.execute("""
            SELECT COUNT(*) FROM sqlite_master 
            WHERE type='table' AND name='despesas'
        """)
        if flask_cursor.fetchone()[0] == 0:
            messagebox.showerror("Erro", "Tabela 'despesas' não encontrada no banco Flask.")
            flask_conn.close()
            return
        
        # Buscar ID do usuário admin
        flask_cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        admin_user = flask_cursor.fetchone()
        
        if not admin_user:
            messagebox.showerror(
                "Erro", 
                "Usuário 'admin' não encontrado no banco Flask.\n"
                "Execute o app Flask primeiro para criar o usuário padrão."
            )
            flask_conn.close()
            return
        
        admin_id = admin_user[0]
        
        # Buscar despesas do admin
        flask_cursor.execute("""
            SELECT descricao, meio_pagamento, conta_despesa, valor, 
                   num_parcelas, data_registro, data_pagamento
            FROM despesas
            WHERE user_id = ?
            ORDER BY data_registro
        """, (admin_id,))
        
        despesas_flask = flask_cursor.fetchall()
        
        if not despesas_flask:
            messagebox.showinfo(
                "Informação", 
                "Nenhuma despesa encontrada para o usuário admin no banco Flask."
            )
            flask_conn.close()
            return
        
        # Confirmar importação
        total_despesas = len(despesas_flask)
        resposta = messagebox.askyesno(
            "Confirmar Importação",
            f"Foram encontradas {total_despesas} despesas do usuário admin.\n\n"
            "Deseja importar esses dados para o banco local?\n\n"
            "ATENÇÃO: Despesas duplicadas podem ser criadas se você "
            "já importou esses dados anteriormente."
        )
        
        if not resposta:
            flask_conn.close()
            return
        
        # Importar despesas
        importadas = 0
        erros = 0
        
        for despesa in despesas_flask:
            try:
                # Inserir no banco v14 (sem user_id)
                self.cursor.execute("""
                    INSERT INTO despesas 
                    (descricao, meio_pagamento, conta_despesa, valor, 
                     num_parcelas, data_registro, data_pagamento)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, despesa)
                importadas += 1
            except sqlite3.Error as e:
                erros += 1
                print(f"Erro ao importar despesa: {e}")
        
        # Commit das alterações
        self.conn.commit()
        flask_conn.close()
        
        # Atualizar interface
        self.carregar_despesas()
        
        # Mensagem de sucesso
        mensagem = f"Importação concluída!\n\n"
        mensagem += f"✓ {importadas} despesas importadas com sucesso"
        if erros > 0:
            mensagem += f"\n✗ {erros} erros durante a importação"
        
        messagebox.showinfo("Sucesso", mensagem)
        
    except sqlite3.Error as e:
        messagebox.showerror(
            "Erro de Banco de Dados",
            f"Erro ao acessar o banco Flask:\n{e}"
        )
    except Exception as e:
        messagebox.showerror(
            "Erro",
            f"Erro inesperado durante a importação:\n{e}"
        )
