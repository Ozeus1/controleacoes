"""
Gerenciador de Sincronização de Bancos de Dados
Interface gráfica para sincronizar dados entre Flask (multi-user) e Desktop (single-user)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import os
import shutil
from datetime import datetime
from pathlib import Path
import psycopg2
from dotenv import load_dotenv
import threading
import subprocess
from urllib.parse import urlparse
import sys

# Carregar variáveis de ambiente
# A carga inicial pode falhar no executável se o CWD não for o correto, 
# mas faremos a recarga na classe com o caminho correto.
load_dotenv()


class GerenciadorSyncBancos:
    def __init__(self, parent):
        self.root = tk.Toplevel(parent)
        self.root.title("Sincronização de Bancos de Dados - Flask ↔ Desktop")
        self.root.geometry("900x700")
        self.root.transient(parent)
        self.root.grab_set()
        
        # Configurar ícone
        try:
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            icon_path = os.path.join(base_path, 'finan.ico')
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"Erro ao carregar ícone: {e}")
        
        # Caminhos dos bancos (Compatível com PyInstaller)
        if getattr(sys, 'frozen', False):
            # Se for executável
            self.base_dir = os.path.dirname(sys.executable)
        else:
            # Se for script
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
            
        # Recarregar .env do diretório correto
        dotenv_path = os.path.join(self.base_dir, '.env')
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path, override=True)
            
        self.flask_db = os.path.join(self.base_dir, 'instance', 'financas.db')
        self.desktop_db = os.path.join(self.base_dir, 'financas.db')
        self.desktop_receitas_db = os.path.join(self.base_dir, 'financas_receitas.db')
        
        # ID do admin (padrão)
        self.admin_id = 1
        
        self.criar_widgets()
        self.verificar_bancos()
    
    def criar_widgets(self):
        """Cria a interface gráfica"""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        title_label = ttk.Label(
            main_frame,
            text="Gerenciador de Sincronização de Bancos",
            font=('Arial', 14, 'bold')
        )
        title_label.pack(pady=(0, 10))
        
        # Frame de status dos bancos
        self.criar_frame_status(main_frame)
        
        # Frame de operações
        self.criar_frame_operacoes(main_frame)
        
        # Frame de log
        self.criar_frame_log(main_frame)
        
        # Barra de progresso
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=5)
        
        # Botão fechar
        ttk.Button(
            main_frame,
            text="Fechar",
            command=self.root.destroy
        ).pack(pady=5)
    
    def criar_frame_status(self, parent):
        """Cria frame com status dos bancos"""
        frame = ttk.LabelFrame(parent, text="Status dos Bancos de Dados", padding="10")
        frame.pack(fill=tk.X, pady=5)
        
        # Flask DB
        flask_frame = ttk.Frame(frame)
        flask_frame.pack(fill=tk.X, pady=2)
        ttk.Label(flask_frame, text="Flask (Multi-User):", font=('Arial', 9, 'bold')).pack(side=tk.LEFT)
        self.lbl_flask_status = ttk.Label(flask_frame, text="Verificando...")
        self.lbl_flask_status.pack(side=tk.LEFT, padx=10)
        
        # Desktop DB (Despesas)
        desktop_frame = ttk.Frame(frame)
        desktop_frame.pack(fill=tk.X, pady=2)
        ttk.Label(desktop_frame, text="Desktop - Despesas:", font=('Arial', 9, 'bold')).pack(side=tk.LEFT)
        self.lbl_desktop_status = ttk.Label(desktop_frame, text="Verificando...")
        self.lbl_desktop_status.pack(side=tk.LEFT, padx=10)
        
        # Desktop DB (Receitas)
        receitas_frame = ttk.Frame(frame)
        receitas_frame.pack(fill=tk.X, pady=2)
        ttk.Label(receitas_frame, text="Desktop - Receitas:", font=('Arial', 9, 'bold')).pack(side=tk.LEFT)
        self.lbl_receitas_status = ttk.Label(receitas_frame, text="Verificando...")
        self.lbl_receitas_status.pack(side=tk.LEFT, padx=10)
    
    def criar_frame_operacoes(self, parent):
        """Cria frame com botões de operações"""
        frame = ttk.LabelFrame(parent, text="Operações", padding="10")
        frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Grid para organizar botões
        btn_width = 30
        
        # Linha 1: Backups
        ttk.Label(frame, text="BACKUPS:", font=('Arial', 10, 'bold')).grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5)
        )
        
        ttk.Button(
            frame,
            text="📦 Backup Flask DB",
            command=self.backup_flask,
            width=btn_width
        ).grid(row=1, column=0, padx=5, pady=2, sticky=tk.EW)
        
        ttk.Button(
            frame,
            text="📦 Backup Desktop DBs",
            command=self.backup_desktop,
            width=btn_width
        ).grid(row=1, column=1, padx=5, pady=2, sticky=tk.EW)
        
        # Separador
        ttk.Separator(frame, orient='horizontal').grid(
            row=2, column=0, columnspan=2, sticky=tk.EW, pady=10
        )
        
        # Linha 2: Sincronização
        ttk.Label(frame, text="SINCRONIZAÇÃO:", font=('Arial', 10, 'bold')).grid(
            row=3, column=0, columnspan=2, sticky=tk.W, pady=(0, 5)
        )
        
        ttk.Button(
            frame,
            text="⬇️ Flask → Desktop (Importar)",
            command=self.importar_flask_para_desktop,
            width=btn_width
        ).grid(row=4, column=0, padx=5, pady=2, sticky=tk.EW)
        
        ttk.Button(
            frame,
            text="⬆️ Desktop → Flask (Exportar)",
            command=self.exportar_desktop_para_flask,
            width=btn_width
        ).grid(row=4, column=1, padx=5, pady=2, sticky=tk.EW)
        
        # Separador
        ttk.Separator(frame, orient='horizontal').grid(
            row=5, column=0, columnspan=2, sticky=tk.EW, pady=10
        )
        
        # Linha 3: Restauração
        ttk.Label(frame, text="RESTAURAÇÃO:", font=('Arial', 10, 'bold')).grid(
            row=6, column=0, columnspan=2, sticky=tk.W, pady=(0, 5)
        )
        
        ttk.Button(
            frame,
            text="📂 Restaurar Flask DB",
            command=self.restaurar_flask,
            width=btn_width
        ).grid(row=7, column=0, padx=5, pady=2, sticky=tk.EW)
        
        ttk.Button(
            frame,
            text="📂 Restaurar Desktop DBs",
            command=self.restaurar_desktop,
            width=btn_width
        ).grid(row=7, column=1, padx=5, pady=2, sticky=tk.EW)
        
        # Configurar colunas para expandir igualmente
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
    
    def criar_frame_log(self, parent):
        """Cria frame com área de log"""
        frame = ttk.LabelFrame(parent, text="Log de Operações", padding="5")
        frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Text widget com scrollbar
        log_scroll = ttk.Scrollbar(frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(
            frame,
            height=10,
            wrap=tk.WORD,
            yscrollcommand=log_scroll.set,
            font=('Consolas', 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        log_scroll.config(command=self.log_text.yview)
        
        # Botão limpar log
        ttk.Button(frame, text="Limpar Log", command=self.limpar_log).pack(pady=2)
    
    def log(self, mensagem, tipo='info'):
        """Adiciona mensagem ao log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Define cores por tipo
        cores = {
            'info': 'black',
            'success': 'darkgreen',
            'warning': 'orange',
            'error': 'red'
        }
        
        # Insere no text widget
        self.log_text.insert(tk.END, f"[{timestamp}] {mensagem}\n")
        
        # Aplica cor
        line_start = f"{self.log_text.index(tk.END)}-2l"
        line_end = f"{self.log_text.index(tk.END)}-1l"
        tag_name = f"tag_{timestamp.replace(':', '')}"
        self.log_text.tag_add(tag_name, line_start, line_end)
        self.log_text.tag_config(tag_name, foreground=cores.get(tipo, 'black'))
        
        # Auto-scroll
        self.log_text.see(tk.END)
        self.root.update()
    
    def limpar_log(self):
        """Limpa o log"""
        self.log_text.delete('1.0', tk.END)

    def _perguntar_modo_sync(self, titulo, mensagem):
        """
        Pergunta ao usuário o modo de sincronização.
        Retorna: 'parcial', 'total' ou None (cancelar)
        """
        dialog = tk.Toplevel(self.root)
        dialog.title(titulo)
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Centralizar
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'{width}x{height}+{x}+{y}')
        
        ttk.Label(dialog, text=titulo, font=('Arial', 12, 'bold')).pack(pady=10)
        ttk.Label(dialog, text=mensagem, wraplength=350, justify=tk.CENTER).pack(pady=10)
        
        self._modo_escolhido = None
        
        def set_parcial():
            self._modo_escolhido = 'parcial'
            dialog.destroy()
            
        def set_total():
            if messagebox.askyesno("Confirmar Substituição", 
                                 "⚠️ ATENÇÃO: O modo TOTAL apagará TODOS os dados do destino antes de importar.\n\n"
                                 "Tem certeza que deseja continuar?", parent=dialog):
                self._modo_escolhido = 'total'
                dialog.destroy()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=20)
        
        ttk.Button(btn_frame, text="Parcial (Adicionar)", command=set_parcial, width=20).pack(pady=5)
        ttk.Button(btn_frame, text="Total (Substituir)", command=set_total, width=20).pack(pady=5)
        ttk.Button(btn_frame, text="Cancelar", command=dialog.destroy).pack(pady=5)
        
        self.root.wait_window(dialog)
        return self._modo_escolhido
    
    def verificar_bancos(self):
        """Inicia verificação dos bancos em background"""
        thread = threading.Thread(target=self._verificar_bancos_thread)
        thread.daemon = True
        thread.start()

    def _verificar_bancos_thread(self):
        """Verifica status dos bancos de dados (Executado em thread)"""
        self.root.after(0, lambda: self.log("Verificando bancos de dados..."))
        
        # Flask DB (PostgreSQL)
        db_url = os.environ.get('DATABASE_URL')
        if db_url:
            try:
                # Adiciona timeout de 5 segundos
                conn = psycopg2.connect(db_url, connect_timeout=5)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM despesas WHERE user_id = %s", (self.admin_id,))
                count = cursor.fetchone()[0]
                conn.close()
                
                def update_flask_success(c=count):
                    self.lbl_flask_status.config(
                        text=f"✓ Conectado (PostgreSQL) - {c} despesas",
                        foreground='darkgreen'
                    )
                    self.log(f"Flask DB (Postgres): {c} despesas encontradas", 'success')
                
                self.root.after(0, update_flask_success)
                
            except Exception as e:
                def update_flask_error(msg=str(e)):
                    self.lbl_flask_status.config(text=f"⚠️ Erro Conexão: {msg[:30]}...", foreground='red')
                    self.log(f"Erro ao conectar Flask DB (Postgres): {msg}", 'error')
                
                self.root.after(0, update_flask_error)
        else:
            def update_flask_missing():
                self.lbl_flask_status.config(text="✗ DATABASE_URL não definida", foreground='red')
                self.log("Variável DATABASE_URL não encontrada no .env", 'warning')
            
            self.root.after(0, update_flask_missing)
        
        # Desktop DB (Despesas)
        if os.path.exists(self.desktop_db):
            try:
                conn = sqlite3.connect(self.desktop_db)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM despesas")
                count = cursor.fetchone()[0]
                conn.close()
                
                def update_desktop_success(c=count):
                    self.lbl_desktop_status.config(
                        text=f"✓ OK ({c} despesas)",
                        foreground='darkgreen'
                    )
                    self.log(f"Desktop DB (Despesas): {c} registros", 'success')
                
                self.root.after(0, update_desktop_success)
                
            except Exception as e:
                def update_desktop_error(msg=str(e)):
                    self.lbl_desktop_status.config(text=f"⚠️ Erro: {msg}", foreground='red')
                    self.log(f"Erro ao verificar Desktop DB: {msg}", 'error')
                
                self.root.after(0, update_desktop_error)
        else:
            def update_desktop_missing():
                self.lbl_desktop_status.config(text="✗ Não encontrado", foreground='red')
                self.log("Desktop DB (Despesas) não encontrado", 'warning')
            
            self.root.after(0, update_desktop_missing)
        
        # Desktop DB (Receitas)
        if os.path.exists(self.desktop_receitas_db):
            try:
                conn = sqlite3.connect(self.desktop_receitas_db)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM receitas")
                count = cursor.fetchone()[0]
                conn.close()
                
                def update_receitas_success(c=count):
                    self.lbl_receitas_status.config(
                        text=f"✓ OK ({c} receitas)",
                        foreground='darkgreen'
                    )
                    self.log(f"Desktop DB (Receitas): {c} registros", 'success')
                
                self.root.after(0, update_receitas_success)
                
            except Exception as e:
                def update_receitas_error(msg=str(e)):
                    self.lbl_receitas_status.config(text=f"⚠️ Erro: {msg}", foreground='red')
                    self.log(f"Erro ao verificar Desktop Receitas DB: {msg}", 'error')
                
                self.root.after(0, update_receitas_error)
        else:
            def update_receitas_missing():
                self.lbl_receitas_status.config(text="✗ Não encontrado", foreground='red')
                self.log("Desktop DB (Receitas) não encontrado", 'warning')
            
            self.root.after(0, update_receitas_missing)

    def importar_flask_para_desktop(self):
        """Importa dados do Flask para Desktop (somente admin)"""
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            messagebox.showerror("Erro", "Configuração do banco Flask (PostgreSQL) não encontrada!")
            return
        
        if not os.path.exists(self.desktop_db):
            messagebox.showerror("Erro", "Banco Desktop não encontrado!")
            return
        
        try:
            # Conectar aos bancos
            flask_conn = psycopg2.connect(db_url)
            flask_cursor = flask_conn.cursor()
            
            desktop_conn = sqlite3.connect(self.desktop_db)
            desktop_cursor = desktop_conn.cursor()
            
            # Contar despesas do admin no Flask
            flask_cursor.execute(
                "SELECT COUNT(*) FROM despesas WHERE user_id = %s",
                (self.admin_id,)
            )
            total_flask = flask_cursor.fetchone()[0]
            
            if total_flask == 0:
                messagebox.showinfo(
                    "Informação",
                    "Nenhuma despesa do admin encontrada no Flask."
                )
                flask_conn.close()
                desktop_conn.close()
                return

            # Perguntar modo de sincronização
            modo = self._perguntar_modo_sync(
                "Modo de Importação",
                f"Existem {total_flask} despesas no Flask (Admin).\n"
                "Como deseja importar para o Desktop?"
            )
            
            if not modo:
                flask_conn.close()
                desktop_conn.close()
                return
            
            # Importar
            self.log(f"Iniciando importação ({modo.upper()}) de {total_flask} despesas...")
            self.progress.start()
            
            # Se for total, limpar banco destino
            if modo == 'total':
                try:
                    desktop_cursor.execute("DELETE FROM despesas")
                    self.log("Dados antigos do Desktop apagados (Modo Total)", 'warning')
                except Exception as e:
                    self.log(f"Erro ao limpar Desktop: {e}", 'error')
                    self.progress.stop()
                    return

            flask_cursor.execute("""
                SELECT 
                    d.descricao, 
                    mp.nome as meio_pagamento, 
                    cd.nome as conta_despesa, 
                    d.valor,
                    d.num_parcelas, 
                    d.data_registro, 
                    d.data_pagamento
                FROM despesas d
                JOIN meios_pagamento mp ON d.meio_pagamento_id = mp.id
                JOIN categorias_despesa cd ON d.categoria_id = cd.id
                WHERE d.user_id = %s
                ORDER BY d.data_registro
            """, (self.admin_id,))
            
            importadas = 0
            erros = 0
            
            for despesa in flask_cursor.fetchall():
                try:
                    desktop_cursor.execute("""
                        INSERT INTO despesas
                        (descricao, meio_pagamento, conta_despesa, valor,
                         num_parcelas, data_registro, data_pagamento)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, despesa)
                    importadas += 1
                except sqlite3.Error as e:
                    erros += 1
                    self.log(f"Erro ao importar registro: {e}", 'error')
            
            # Sincronizar Orçamentos
            self._importar_orcamentos(flask_cursor, desktop_cursor, modo)
            
            desktop_conn.commit()
            flask_conn.close()
            desktop_conn.close()
            
            self.progress.stop()
            
            self.log(f"✓ Importação concluída: {importadas} OK, {erros} erros", 'success')
            self.verificar_bancos()
            
            mensagem = f"Importação ({modo.upper()}) concluída!\n\n"
            mensagem += f"✓ {importadas} despesas importadas\n"
            if erros > 0:
                mensagem += f"✗ {erros} erros"
            
            messagebox.showinfo("Sucesso", mensagem)
            
        except Exception as e:
            self.progress.stop()
            self.log(f"✗ Erro na importação: {e}", 'error')
            messagebox.showerror("Erro", f"Erro durante a importação:\n{e}")
    
    def _obter_id_categoria(self, cursor, nome):
        """Obtém ID da categoria no Postgres (cria se não existir)"""
        if not nome:
            return None
            
        # Tentar encontrar
        cursor.execute("SELECT id FROM categorias_despesa WHERE nome = %s", (nome,))
        resultado = cursor.fetchone()
        
        if resultado:
            return resultado[0]
            
        # Criar se não existir
        try:
            cursor.execute("INSERT INTO categorias_despesa (nome, ativo) VALUES (%s, true) RETURNING id", (nome,))
            return cursor.fetchone()[0]
        except Exception as e:
            self.log(f"Erro ao criar categoria '{nome}': {e}", 'error')
            return None

    def _obter_id_meio_pagamento(self, cursor, nome):
        """Obtém ID do meio de pagamento no Postgres (cria se não existir)"""
        if not nome:
            return None
            
        # Tentar encontrar
        cursor.execute("SELECT id FROM meios_pagamento WHERE nome = %s", (nome,))
        resultado = cursor.fetchone()
        
        if resultado:
            return resultado[0]
            
        # Criar se não existir
        try:
            # Define um tipo padrão 'outros' se não soubermos mapear
            cursor.execute("INSERT INTO meios_pagamento (nome, tipo, ativo) VALUES (%s, 'outros', true) RETURNING id", (nome,))
            return cursor.fetchone()[0]
        except Exception as e:
            self.log(f"Erro ao criar meio de pagamento '{nome}': {e}", 'error')
            return None

    def _importar_orcamentos(self, flask_cursor, desktop_cursor, modo):
        """Importa orçamentos do Flask para Desktop"""
        try:
            self.log("Sincronizando orçamentos...", 'info')
            
            # Buscar orçamentos do Flask
            flask_cursor.execute("""
                SELECT cd.nome, o.valor_orcado
                FROM orcamentos o
                JOIN categorias_despesa cd ON o.categoria_id = cd.id
                WHERE o.user_id = %s
            """, (self.admin_id,))
            
            orcamentos_flask = flask_cursor.fetchall()
            
            if not orcamentos_flask:
                self.log("Nenhum orçamento encontrado no Flask.", 'info')
                return

            # Se modo total, limpar orçamentos do desktop
            if modo == 'total':
                desktop_cursor.execute("DELETE FROM orcamento")
            
            count = 0
            for nome_categoria, valor in orcamentos_flask:
                # Garantir que a categoria existe no desktop (tabela 'categorias')
                try:
                    desktop_cursor.execute("INSERT OR IGNORE INTO categorias (nome) VALUES (?)", (nome_categoria,))
                except Exception as e:
                    self.log(f"Aviso: Não foi possível criar categoria '{nome_categoria}' no Desktop: {e}", 'warning')

                # Upsert no orçamento do desktop
                # Primeiro verifica se já existe
                desktop_cursor.execute("SELECT id FROM orcamento WHERE conta_despesa = ?", (nome_categoria,))
                exists = desktop_cursor.fetchone()
                
                if exists:
                    desktop_cursor.execute("UPDATE orcamento SET valor_orcado = ? WHERE conta_despesa = ?", (valor, nome_categoria))
                else:
                    desktop_cursor.execute("INSERT INTO orcamento (conta_despesa, valor_orcado) VALUES (?, ?)", (nome_categoria, valor))
                count += 1
                
            self.log(f"✓ {count} orçamentos sincronizados.", 'success')
            
        except Exception as e:
            self.log(f"Erro ao sincronizar orçamentos: {e}", 'error')

    def _exportar_orcamentos(self, desktop_cursor, flask_cursor, modo):
        """Exporta orçamentos do Desktop para Flask"""
        try:
            self.log("Sincronizando orçamentos...", 'info')
            
            # Buscar orçamentos do Desktop
            desktop_cursor.execute("SELECT conta_despesa, valor_orcado FROM orcamento")
            orcamentos_desktop = desktop_cursor.fetchall()
            
            if not orcamentos_desktop:
                self.log("Nenhum orçamento encontrado no Desktop.", 'info')
                return

            # Se modo total, limpar orçamentos do usuário no Flask
            if modo == 'total':
                flask_cursor.execute("DELETE FROM orcamentos WHERE user_id = %s", (self.admin_id,))
            
            count = 0
            for nome_categoria, valor in orcamentos_desktop:
                # Obter ID da categoria no Flask
                categoria_id = self._obter_id_categoria(flask_cursor, nome_categoria)
                
                if not categoria_id:
                    self.log(f"Erro ao sincronizar orçamento: Categoria '{nome_categoria}' não encontrada/criada no Flask.", 'error')
                    continue
                
                # Upsert no orçamento do Flask
                # PostgreSQL suporta ON CONFLICT, mas vamos fazer manual para garantir compatibilidade
                flask_cursor.execute("""
                    SELECT id FROM orcamentos 
                    WHERE user_id = %s AND categoria_id = %s
                """, (self.admin_id, categoria_id))
                exists = flask_cursor.fetchone()
                
                if exists:
                    flask_cursor.execute("""
                        UPDATE orcamentos SET valor_orcado = %s 
                        WHERE id = %s
                    """, (valor, exists[0]))
                else:
                    flask_cursor.execute("""
                        INSERT INTO orcamentos (user_id, categoria_id, valor_orcado)
                        VALUES (%s, %s, %s)
                    """, (self.admin_id, categoria_id, valor))
                count += 1
                
            self.log(f"✓ {count} orçamentos sincronizados.", 'success')
            
        except Exception as e:
            self.log(f"Erro ao sincronizar orçamentos: {e}", 'error')

    def exportar_desktop_para_flask(self):
        """Exporta dados do Desktop para Flask (como admin)"""
        if not os.path.exists(self.desktop_db):
            messagebox.showerror("Erro", "Banco Desktop não encontrado!")
            return
        
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            messagebox.showerror("Erro", "Configuração do banco Flask (PostgreSQL) não encontrada!")
            return
        
        try:
            # Conectar aos bancos
            desktop_conn = sqlite3.connect(self.desktop_db)
            desktop_cursor = desktop_conn.cursor()
            
            flask_conn = psycopg2.connect(db_url, connect_timeout=10)
            flask_cursor = flask_conn.cursor()
            
            # Verificar se usuário admin existe no Flask
            flask_cursor.execute("SELECT id FROM users WHERE username = 'admin'")
            admin_user = flask_cursor.fetchone()
            
            if not admin_user:
                messagebox.showerror(
                    "Erro",
                    "Usuário 'admin' não encontrado no Flask!\n"
                    "Execute o app Flask primeiro e crie o usuário."
                )
                desktop_conn.close()
                flask_conn.close()
                return
            
            admin_id_flask = admin_user[0]
            
            # Contar despesas no Desktop
            desktop_cursor.execute("SELECT COUNT(*) FROM despesas")
            total_desktop = desktop_cursor.fetchone()[0]
            
            if total_desktop == 0:
                messagebox.showinfo("Informação", "Nenhuma despesa encontrada no Desktop.")
                desktop_conn.close()
                flask_conn.close()
                return
            
            # Perguntar modo de sincronização
            modo = self._perguntar_modo_sync(
                "Modo de Exportação",
                f"Existem {total_desktop} despesas no Desktop.\n"
                "Como deseja exportar para o Flask?"
            )
            
            if not modo:
                desktop_conn.close()
                flask_conn.close()
                return
            
            # Exportar
            self.log(f"Iniciando exportação ({modo.upper()}) de {total_desktop} despesas...")
            self.progress.start()
            
            # Se for total, limpar dados do usuário no Flask
            if modo == 'total':
                try:
                    flask_cursor.execute("DELETE FROM despesas WHERE user_id = %s", (admin_id_flask,))
                    self.log(f"Dados antigos do Admin no Flask apagados (Modo Total)", 'warning')
                except Exception as e:
                    self.log(f"Erro ao limpar Flask: {e}", 'error')
                    self.progress.stop()
                    return
            
            desktop_cursor.execute("""
                SELECT descricao, meio_pagamento, conta_despesa, valor,
                       num_parcelas, data_registro, data_pagamento
                FROM despesas
                ORDER BY data_registro
            """)
            
            exportadas = 0
            erros = 0
            
            for despesa in desktop_cursor.fetchall():
                try:
                    # Desempacotar dados do Desktop
                    # 0: descricao, 1: meio_pagamento, 2: conta_despesa, 3: valor, 
                    # 4: num_parcelas, 5: data_registro, 6: data_pagamento
                    descricao = despesa[0]
                    nome_meio = despesa[1]
                    nome_categoria = despesa[2]
                    valor = despesa[3]
                    num_parcelas = despesa[4]
                    data_registro = despesa[5]
                    data_pagamento = despesa[6]
                    
                    # Obter IDs (Foreign Keys)
                    categoria_id = self._obter_id_categoria(flask_cursor, nome_categoria)
                    meio_pagamento_id = self._obter_id_meio_pagamento(flask_cursor, nome_meio)
                    
                    if not categoria_id or not meio_pagamento_id:
                        erros += 1
                        self.log(f"Erro: Categoria '{nome_categoria}' ou Meio '{nome_meio}' inválidos", 'error')
                        continue

                    # Criar savepoint para isolar erro
                    flask_cursor.execute("SAVEPOINT sp_insert")
                    
                    flask_cursor.execute("""
                        INSERT INTO despesas
                        (descricao, valor, num_parcelas, data_registro, data_pagamento, 
                         user_id, categoria_id, meio_pagamento_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (descricao, valor, num_parcelas, data_registro, data_pagamento, 
                          admin_id_flask, categoria_id, meio_pagamento_id))
                    
                    flask_cursor.execute("RELEASE SAVEPOINT sp_insert")
                    exportadas += 1
                except Exception as e:
                    # Rollback para o savepoint em caso de erro
                    flask_cursor.execute("ROLLBACK TO SAVEPOINT sp_insert")
                    erros += 1
                    self.log(f"Erro ao exportar registro: {e}", 'error')
            
            # Sincronizar Orçamentos
            self._exportar_orcamentos(desktop_cursor, flask_cursor, modo)

            flask_conn.commit()
            desktop_conn.close()
            flask_conn.close()
            
            self.progress.stop()
            
            self.log(f"✓ Exportação concluída: {exportadas} OK, {erros} erros", 'success')
            self.verificar_bancos()
            
            mensagem = f"Exportação concluída!\n\n"
            mensagem += f"✓ {exportadas} despesas exportadas\n"
            if erros > 0:
                mensagem += f"✗ {erros} erros"
            
            messagebox.showinfo("Sucesso", mensagem)
            
        except Exception as e:
            self.progress.stop()
            self.log(f"✗ Erro na exportação: {e}", 'error')
            messagebox.showerror("Erro", f"Erro durante a exportação:\n{e}")
    
    def _encontrar_pg_dump(self):
        """Tenta encontrar o executável pg_dump"""
        # 1. Tentar configuração salva no BD
        try:
            conn = sqlite3.connect(self.desktop_db)
            cursor = conn.cursor()
            cursor.execute("SELECT valor FROM configuracoes WHERE chave = 'pg_bin_path'")
            res = cursor.fetchone()
            conn.close()
            
            if res and res[0]:
                bin_path = res[0]
                pg_dump_path = os.path.join(bin_path, 'pg_dump.exe')
                if os.path.exists(pg_dump_path):
                    return pg_dump_path
        except:
            pass

        # 2. Tentar no PATH
        pg_dump_path = shutil.which('pg_dump')
        if pg_dump_path:
            return pg_dump_path
            
        # 2. Tentar caminhos comuns no Windows
        caminhos_comuns = [
            r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe",
            r"C:\Program Files\PostgreSQL\15\bin\pg_dump.exe",
            r"C:\Program Files\PostgreSQL\14\bin\pg_dump.exe",
            r"C:\Program Files\PostgreSQL\13\bin\pg_dump.exe",
            r"C:\Program Files\PostgreSQL\12\bin\pg_dump.exe",
        ]
        
        for caminho in caminhos_comuns:
            if os.path.exists(caminho):
                return caminho
                
        # 3. Perguntar ao usuário
        messagebox.showinfo(
            "Configuração",
            "O executável 'pg_dump' não foi encontrado automaticamente.\n"
            "Por favor, localize o arquivo 'pg_dump.exe' na pasta de instalação do PostgreSQL."
        )
        selected_file = filedialog.askopenfilename(
            title="Localizar pg_dump.exe",
            filetypes=[("Executável", "pg_dump.exe"), ("Todos os arquivos", "*.*")]
        )
        
        if selected_file:
            # Salvar o caminho da pasta no banco de dados para uso futuro
            try:
                bin_path = os.path.dirname(selected_file)
                conn = sqlite3.connect(self.desktop_db)
                cursor = conn.cursor()
                cursor.execute("CREATE TABLE IF NOT EXISTS configuracoes (chave TEXT PRIMARY KEY, valor TEXT)")
                cursor.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)", ('pg_bin_path', bin_path))
                conn.commit()
                conn.close()
                self.log(f"Configuração salva: Caminho do PostgreSQL definido para {bin_path}", 'success')
            except Exception as e:
                self.log(f"Erro ao salvar configuração do PostgreSQL: {e}", 'warning')
                
            return selected_file
            
        return None

    def backup_flask(self):
        """Backup do banco Flask (PostgreSQL)"""
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            messagebox.showerror("Erro", "Configuração do banco Flask não encontrada!")
            return

        try:
            # Parse da URL
            url = urlparse(db_url)
            dbname = url.path[1:]
            user = url.username
            password = url.password
            host = url.hostname
            port = url.port or 5432
            
            # Localizar pg_dump
            pg_dump_cmd = self._encontrar_pg_dump()
            if not pg_dump_cmd:
                return

            # Escolher local para salvar
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            arquivo_destino = filedialog.asksaveasfilename(
                title="Salvar Backup Flask",
                initialfile=f"backup_flask_{dbname}_{timestamp}.sql",
                defaultextension=".sql",
                filetypes=[("Arquivo SQL", "*.sql")]
            )
            
            if not arquivo_destino:
                return

            self.log("Iniciando backup do Flask DB (PostgreSQL)...")
            self.progress.start()
            
            # Configurar ambiente com senha
            env = os.environ.copy()
            env['PGPASSWORD'] = password
            
            # Comando
            cmd = [
                pg_dump_cmd,
                '-h', host,
                '-p', str(port),
                '-U', user,
                '-F', 'p', # Formato plain text (SQL)
                '-f', arquivo_destino,
                dbname
            ]
            
            # Executar em thread para não travar UI
            def run_backup():
                try:
                    process = subprocess.run(
                        cmd, 
                        env=env, 
                        capture_output=True, 
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    )
                    
                    if process.returncode == 0:
                        self.root.after(0, lambda: self.log(f"✓ Backup Flask criado: {arquivo_destino}", 'success'))
                        self.root.after(0, lambda: messagebox.showinfo("Sucesso", f"Backup criado com sucesso!\n\n{arquivo_destino}"))
                    else:
                        erro_msg = process.stderr
                        self.root.after(0, lambda: self.log(f"✗ Erro no backup: {erro_msg}", 'error'))
                        self.root.after(0, lambda: messagebox.showerror("Erro no Backup", f"Falha ao criar backup:\n{erro_msg}"))
                        
                except Exception as e:
                    self.root.after(0, lambda: self.log(f"✗ Erro ao executar pg_dump: {e}", 'error'))
                    self.root.after(0, lambda: messagebox.showerror("Erro", f"Erro ao executar backup:\n{e}"))
                finally:
                    self.root.after(0, self.progress.stop)

            threading.Thread(target=run_backup, daemon=True).start()

        except Exception as e:
            self.progress.stop()
            self.log(f"Erro ao preparar backup: {e}", 'error')
            messagebox.showerror("Erro", f"Erro ao preparar backup:\n{e}")

    def backup_desktop(self):
        """Backup dos bancos Desktop (SQLite)"""
        try:
            # Criar pasta de backups se não existir
            backup_dir = os.path.join(self.base_dir, 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Backup Despesas
            if os.path.exists(self.desktop_db):
                dest = os.path.join(backup_dir, f'financas_backup_{timestamp}.db')
                shutil.copy2(self.desktop_db, dest)
                self.log(f"Backup Despesas criado: {os.path.basename(dest)}", 'success')
            
            # Backup Receitas
            if os.path.exists(self.desktop_receitas_db):
                dest = os.path.join(backup_dir, f'financas_receitas_backup_{timestamp}.db')
                shutil.copy2(self.desktop_receitas_db, dest)
                self.log(f"Backup Receitas criado: {os.path.basename(dest)}", 'success')
                
            messagebox.showinfo("Sucesso", f"Backups criados na pasta:\n{backup_dir}")
            
        except Exception as e:
            self.log(f"Erro ao criar backup: {e}", 'error')
            messagebox.showerror("Erro", f"Erro ao criar backup:\n{e}")

    def _encontrar_psql(self):
        """Tenta encontrar o executável psql"""
        # 1. Tentar configuração salva no BD
        try:
            conn = sqlite3.connect(self.desktop_db)
            cursor = conn.cursor()
            cursor.execute("SELECT valor FROM configuracoes WHERE chave = 'pg_bin_path'")
            res = cursor.fetchone()
            conn.close()
            
            if res and res[0]:
                bin_path = res[0]
                psql_path = os.path.join(bin_path, 'psql.exe')
                if os.path.exists(psql_path):
                    return psql_path
        except:
            pass

        # 2. Tentar no PATH
        psql_path = shutil.which('psql')
        if psql_path:
            return psql_path
            
        # 2. Tentar caminhos comuns no Windows
        caminhos_comuns = [
            r"C:\Program Files\PostgreSQL\16\bin\psql.exe",
            r"C:\Program Files\PostgreSQL\15\bin\psql.exe",
            r"C:\Program Files\PostgreSQL\14\bin\psql.exe",
            r"C:\Program Files\PostgreSQL\13\bin\psql.exe",
            r"C:\Program Files\PostgreSQL\12\bin\psql.exe",
        ]
        
        for caminho in caminhos_comuns:
            if os.path.exists(caminho):
                return caminho
                
        # 3. Perguntar ao usuário
        messagebox.showinfo(
            "Configuração",
            "O executável 'psql' não foi encontrado automaticamente.\n"
            "Por favor, localize o arquivo 'psql.exe' na pasta de instalação do PostgreSQL."
        )
        selected_file = filedialog.askopenfilename(
            title="Localizar psql.exe",
            filetypes=[("Executável", "psql.exe"), ("Todos os arquivos", "*.*")]
        )
        
        if selected_file:
            # Salvar o caminho da pasta no banco de dados para uso futuro
            try:
                bin_path = os.path.dirname(selected_file)
                conn = sqlite3.connect(self.desktop_db)
                cursor = conn.cursor()
                cursor.execute("CREATE TABLE IF NOT EXISTS configuracoes (chave TEXT PRIMARY KEY, valor TEXT)")
                cursor.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)", ('pg_bin_path', bin_path))
                conn.commit()
                conn.close()
                self.log(f"Configuração salva: Caminho do PostgreSQL definido para {bin_path}", 'success')
            except Exception as e:
                self.log(f"Erro ao salvar configuração do PostgreSQL: {e}", 'warning')
                
            return selected_file
            
        return None

    def restaurar_flask(self):
        """Restaura banco Flask de um backup SQL (PostgreSQL)"""
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            messagebox.showerror("Erro", "Configuração do banco Flask não encontrada!")
            return

        backup_path = filedialog.askopenfilename(
            title="Selecione o backup do Flask DB (SQL)",
            filetypes=[("Arquivo SQL", "*.sql"), ("Todos os arquivos", "*.*")]
        )
        
        if not backup_path:
            return
        
        # Perguntar modo de restauração
        modo = self._perguntar_modo_sync(
            "Modo de Restauração",
            "Como deseja restaurar o banco de dados?"
        )
        
        if not modo:
            return
        
        try:
            # Parse da URL
            url = urlparse(db_url)
            dbname = url.path[1:]
            user = url.username
            password = url.password
            host = url.hostname
            port = url.port or 5432
            
            # Localizar psql
            psql_cmd = self._encontrar_psql()
            if not psql_cmd:
                return

            self.log(f"Iniciando restauração ({modo.upper()}) do Flask DB...")
            self.progress.start()
            
            # Se for total, limpar banco (Recriar schema public)
            if modo == 'total':
                try:
                    conn = psycopg2.connect(db_url)
                    conn.autocommit = True
                    cursor = conn.cursor()
                    cursor.execute("DROP SCHEMA public CASCADE")
                    cursor.execute("CREATE SCHEMA public")
                    cursor.execute("GRANT ALL ON SCHEMA public TO public")
                    conn.close()
                    self.log("Schema public recriado (Modo Total)", 'warning')
                except Exception as e:
                    self.log(f"Erro ao limpar banco: {e}", 'error')
                    messagebox.showerror("Erro", f"Erro ao limpar banco para substituição:\n{e}")
                    self.progress.stop()
                    return
            
            # Configurar ambiente com senha
            env = os.environ.copy()
            env['PGPASSWORD'] = password
            
            # Comando: psql -h host -p port -U user -d dbname -f file.sql
            cmd = [
                psql_cmd,
                '-h', host,
                '-p', str(port),
                '-U', user,
                '-d', dbname,
                '-f', backup_path
            ]
            
            # Executar em thread
            def run_restore():
                try:
                    process = subprocess.run(
                        cmd, 
                        env=env, 
                        capture_output=True, 
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    )
                    
                    if process.returncode == 0:
                        self.root.after(0, lambda: self.log(f"✓ Flask DB restaurado: {backup_path}", 'success'))
                        self.root.after(0, lambda: messagebox.showinfo("Sucesso", "Restauração concluída com sucesso!"))
                        self.root.after(0, self.verificar_bancos)
                    else:
                        erro_msg = process.stderr
                        self.root.after(0, lambda: self.log(f"✗ Erro na restauração: {erro_msg}", 'error'))
                        self.root.after(0, lambda: messagebox.showerror("Erro na Restauração", f"Falha ao restaurar:\n{erro_msg}"))
                        
                except Exception as e:
                    self.root.after(0, lambda: self.log(f"✗ Erro ao executar psql: {e}", 'error'))
                    self.root.after(0, lambda: messagebox.showerror("Erro", f"Erro ao executar restauração:\n{e}"))
                finally:
                    self.root.after(0, self.progress.stop)

            threading.Thread(target=run_restore, daemon=True).start()
            
        except Exception as e:
            self.progress.stop()
            self.log(f"✗ Erro ao preparar restauração: {e}", 'error')
            messagebox.showerror("Erro", f"Erro ao preparar restauração:\n{e}")
    
    def restaurar_desktop(self):
        """Restaura bancos Desktop de backups"""
        messagebox.showinfo(
            "Restaurar Desktop DBs",
            "Selecione os arquivos de backup:\n\n"
            "1. Backup de Despesas (financas.db)\n"
            "2. Backup de Receitas (financas_receitas.db) - OPCIONAL"
        )
        
        # Restaurar Despesas
        despesas_backup = filedialog.askopenfilename(
            title="Selecione o backup de DESPESAS",
            filetypes=[("SQLite Database", "*.db")]
        )
        
        if not despesas_backup:
            return
        
        # Perguntar sobre Receitas
        restaurar_receitas = messagebox.askyesno(
            "Receitas",
            "Deseja restaurar também o banco de RECEITAS?"
        )
        
        receitas_backup = None
        if restaurar_receitas:
            receitas_backup = filedialog.askopenfilename(
                title="Selecione o backup de RECEITAS",
                filetypes=[("SQLite Database", "*.db")]
            )
        
        # Confirmar
        msg_confirm = "⚠️ ATENÇÃO: Isso irá SUBSTITUIR os bancos Desktop atuais!\n\n"
        msg_confirm += "- Despesas: SIM\n"
        msg_confirm += f"- Receitas: {'SIM' if receitas_backup else 'NÃO'}\n\n"
        msg_confirm += "Todos os dados atuais serão perdidos.\n\nDeseja continuar?"
        
        resposta = messagebox.askyesno("Confirmar Restauração", msg_confirm)
        
        if not resposta:
            return
        
        try:
            self.progress.start()
            
            # Restaurar Despesas
            self.log("Restaurando Desktop DB (Despesas)...")
            shutil.copy2(despesas_backup, self.desktop_db)
            self.log("✓ Despesas restauradas!", 'success')
            
            # Restaurar Receitas se selecionado
            if receitas_backup:
                self.log("Restaurando Desktop DB (Receitas)...")
                shutil.copy2(receitas_backup, self.desktop_receitas_db)
                self.log("✓ Receitas restauradas!", 'success')
            
            self.progress.stop()
            self.verificar_bancos()
            
            messagebox.showinfo("Sucesso", "Bancos Desktop restaurados com sucesso!")
            
        except Exception as e:
            self.progress.stop()
            self.log(f"✗ Erro na restauração: {e}", 'error')
            messagebox.showerror("Erro", f"Erro ao restaurar:\n{e}")


def iniciar_gerenciador_sync(parent_root):
    """Função para iniciar o gerenciador de sincronização"""
    GerenciadorSyncBancos(parent_root)


if __name__ == "__main__":
    # Teste standalone
    root = tk.Tk()
    root.withdraw()
    iniciar_gerenciador_sync(root)
    root.mainloop()
