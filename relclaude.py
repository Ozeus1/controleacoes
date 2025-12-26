import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns
from datetime import datetime, timedelta
import numpy as np
from tkinter import font

# Configurar estilo dos gráficos
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class RelatoriosFinanceiros:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Relatórios Financeiros")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')
        
        # Configurar fonte padrão
        self.font_title = font.Font(family="Arial", size=14, weight="bold")
        self.font_normal = font.Font(family="Arial", size=10)
        
        self.db_path = "financas.db"
        self.setup_ui()
        self.verificar_conexao_bd()
        
    def verificar_conexao_bd(self):
        """Verifica se o banco de dados existe e pode ser conectado"""
        try:
            # Verificar se o arquivo existe
            import os
            if not os.path.exists(self.db_path):
                messagebox.showerror("Erro", 
                    f"Arquivo de banco de dados '{self.db_path}' não encontrado!\n"
                    f"Diretório atual: {os.getcwd()}\n"
                    "Por favor, coloque o arquivo 'financas.db' no mesmo diretório do programa.")
                return
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Listar todas as tabelas
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            todas_tabelas = cursor.fetchall()
            
            print(f"Tabelas encontradas no banco: {[t[0] for t in todas_tabelas]}")
            
            if not todas_tabelas:
                messagebox.showwarning("Aviso", 
                    "Nenhuma tabela encontrada no banco de dados.\n"
                    "Verifique se o arquivo está correto.")
                conn.close()
                return
            
            # Verificar estrutura das tabelas
            for tabela in todas_tabelas:
                cursor.execute(f"PRAGMA table_info({tabela[0]})")
                colunas = cursor.fetchall()
                print(f"Tabela '{tabela[0]}' - Colunas: {[c[1] for c in colunas]}")
                
                # Verificar se há dados
                cursor.execute(f"SELECT COUNT(*) FROM {tabela[0]}")
                qtd_registros = cursor.fetchone()[0]
                print(f"Tabela '{tabela[0]}' - Registros: {qtd_registros}")
            
            conn.close()
            self.atualizar_periodo_disponivel()
            
            # Mostrar informações para o usuário
            info_msg = f"Banco conectado com sucesso!\n\nTabelas encontradas:\n"
            for tabela in todas_tabelas:
                info_msg += f"• {tabela[0]}\n"
            
            messagebox.showinfo("Conexão OK", info_msg)
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao conectar com o banco de dados: {e}")
            print(f"Erro detalhado: {e}")
    
    def setup_ui(self):
        """Configura a interface do usuário"""
        # Frame principal
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Título
        title_label = tk.Label(main_frame, text="Sistema de Relatórios Financeiros", 
                              font=self.font_title, bg='#f0f0f0', fg='#2c3e50')
        title_label.pack(pady=(0, 20))
        
        # Frame de controles
        controls_frame = tk.LabelFrame(main_frame, text="Controles de Relatório", 
                                     font=self.font_normal, bg='#f0f0f0')
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Primeira linha de controles
        row1_frame = tk.Frame(controls_frame, bg='#f0f0f0')
        row1_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Seleção do tipo de relatório
        tk.Label(row1_frame, text="Tipo de Relatório:", font=self.font_normal, bg='#f0f0f0').pack(side=tk.LEFT)
        self.tipo_relatorio = ttk.Combobox(row1_frame, width=20, font=self.font_normal)
        self.tipo_relatorio['values'] = [
            'Resumo Mensal',
            'Por Categoria',
            'Por Meio de Pagamento',
            'Por Conta',
            'Evolução Temporal',
            'Top 10 Despesas',
            'Análise de Parcelas',
            'Comparativo Mensal'
        ]
        self.tipo_relatorio.set('Resumo Mensal')
        self.tipo_relatorio.pack(side=tk.LEFT, padx=(5, 20))
        
        # Seleção do período
        tk.Label(row1_frame, text="Período:", font=self.font_normal, bg='#f0f0f0').pack(side=tk.LEFT)
        self.periodo_var = tk.StringVar()
        self.periodo_combo = ttk.Combobox(row1_frame, textvariable=self.periodo_var, 
                                        width=15, font=self.font_normal)
        self.periodo_combo.pack(side=tk.LEFT, padx=(5, 20))
        
        # Segunda linha de controles
        row2_frame = tk.Frame(controls_frame, bg='#f0f0f0')
        row2_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Data específica (opcional)
        tk.Label(row2_frame, text="Mês/Ano específico:", font=self.font_normal, bg='#f0f0f0').pack(side=tk.LEFT)
        self.data_especifica = tk.Entry(row2_frame, width=10, font=self.font_normal)
        self.data_especifica.pack(side=tk.LEFT, padx=(5, 10))
        tk.Label(row2_frame, text="(YYYY-MM)", font=('Arial', 8), bg='#f0f0f0', fg='gray').pack(side=tk.LEFT, padx=(0, 20))
        
        # Botões
        btn_frame = tk.Frame(row2_frame, bg='#f0f0f0')
        btn_frame.pack(side=tk.RIGHT)
        
        tk.Button(btn_frame, text="Gerar Relatório", command=self.gerar_relatorio,
                 bg='#3498db', fg='white', font=self.font_normal, width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Exportar Excel", command=self.exportar_excel,
                 bg='#27ae60', fg='white', font=self.font_normal, width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Atualizar", command=self.atualizar_periodo_disponivel,
                 bg='#f39c12', fg='white', font=self.font_normal, width=10).pack(side=tk.LEFT, padx=5)
        
        # Notebook para abas
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Aba de gráficos
        self.frame_grafico = tk.Frame(self.notebook, bg='white')
        self.notebook.add(self.frame_grafico, text="Gráficos")
        
        # Aba de dados tabulares
        self.frame_tabela = tk.Frame(self.notebook, bg='white')
        self.notebook.add(self.frame_tabela, text="Dados Detalhados")
        
        # Configurar Treeview para tabela de dados
        self.setup_treeview()
        
        # Frame para estatísticas
        self.frame_stats = tk.Frame(self.notebook, bg='white')
        self.notebook.add(self.frame_stats, text="Estatísticas")
        
    def setup_treeview(self):
        """Configura a tabela para exibir dados detalhados"""
        # Frame com scrollbars
        tree_frame = tk.Frame(self.frame_tabela)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        
        # Treeview
        self.tree = ttk.Treeview(tree_frame, 
                                yscrollcommand=v_scrollbar.set,
                                xscrollcommand=h_scrollbar.set)
        
        v_scrollbar.config(command=self.tree.yview)
        h_scrollbar.config(command=self.tree.xview)
        
        # Posicionamento
        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
    def atualizar_periodo_disponivel(self):
        """Atualiza os períodos disponíveis no combobox"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Buscar todas as tabelas
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tabelas = cursor.fetchall()
            
            print(f"Buscando períodos nas tabelas: {[t[0] for t in tabelas]}")
            
            if not tabelas:
                self.periodo_combo['values'] = ['Nenhum dado encontrado']
                return
            
            # Para cada tabela, tentar encontrar dados com datas
            periodos = set()
            for tabela in tabelas:
                tabela_nome = tabela[0]
                try:
                    cursor.execute(f"PRAGMA table_info({tabela_nome})")
                    colunas = cursor.fetchall()
                    
                    print(f"Colunas da tabela {tabela_nome}: {[c[1] for c in colunas]}")
                    
                    # Procurar coluna de data
                    coluna_data = None
                    for coluna in colunas:
                        if 'data' in coluna[1].lower():
                            coluna_data = coluna[1]
                            break
                    
                    if coluna_data:
                        print(f"Usando coluna de data: {coluna_data}")
                        cursor.execute(f"""
                            SELECT DISTINCT strftime('%Y-%m', {coluna_data}) as periodo
                            FROM {tabela_nome}
                            WHERE {coluna_data} IS NOT NULL AND {coluna_data} != ''
                            ORDER BY periodo DESC
                        """)
                        
                        dados_periodo = cursor.fetchall()
                        print(f"Períodos encontrados na tabela {tabela_nome}: {dados_periodo}")
                        
                        for periodo in dados_periodo:
                            if periodo[0]:
                                periodos.add(periodo[0])
                    else:
                        print(f"Nenhuma coluna de data encontrada na tabela {tabela_nome}")
                                
                except Exception as e:
                    print(f"Erro ao processar tabela {tabela_nome}: {e}")
                    continue
            
            if periodos:
                periodos_lista = ['Todos'] + sorted(list(periodos), reverse=True)
                self.periodo_combo['values'] = periodos_lista
                self.periodo_combo.set('Todos')
                print(f"Períodos disponíveis: {periodos_lista}")
            else:
                self.periodo_combo['values'] = ['Nenhum período encontrado']
                print("Nenhum período encontrado")
                
            conn.close()
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao atualizar períodos: {e}")
            print(f"Erro detalhado ao atualizar períodos: {e}")
    
    def obter_dados_financeiros(self, filtro_periodo=None):
        """Obtém dados financeiros do banco de dados"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Buscar todas as tabelas
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tabelas = cursor.fetchall()
            
            print(f"Obtendo dados das tabelas: {[t[0] for t in tabelas]}")
            
            if not tabelas:
                print("Nenhuma tabela encontrada")
                return pd.DataFrame()
            
            # Combinar dados de todas as tabelas
            dados_completos = []
            
            for tabela in tabelas:
                tabela_nome = tabela[0]
                try:
                    print(f"Processando tabela: {tabela_nome}")
                    query = f"SELECT * FROM {tabela_nome}"
                    df_temp = pd.read_sql_query(query, conn)
                    
                    print(f"Tabela {tabela_nome} - Registros: {len(df_temp)}")
                    print(f"Colunas: {list(df_temp.columns)}")
                    
                    if not df_temp.empty:
                        # Adicionar prefixo às colunas para evitar duplicatas
                        colunas_renomeadas = {}
                        for col in df_temp.columns:
                            if col.lower() in ['data', 'valor', 'descricao']:
                                # Manter nomes padrão para colunas principais
                                colunas_renomeadas[col] = col.lower()
                            else:
                                # Adicionar prefixo para outras colunas
                                colunas_renomeadas[col] = f"{tabela_nome}_{col}"
                        
                        df_temp = df_temp.rename(columns=colunas_renomeadas)
                        df_temp['tabela_origem'] = tabela_nome
                        dados_completos.append(df_temp)
                        
                except Exception as e:
                    print(f"Erro ao processar tabela {tabela_nome}: {e}")
                    continue
            
            conn.close()
            
            if not dados_completos:
                print("Nenhum dado encontrado em nenhuma tabela")
                return pd.DataFrame()
            
            # Combinar todos os dataframes - CORREÇÃO AQUI
            # Primeiro, vamos identificar todas as colunas únicas
            todas_colunas = set()
            for df in dados_completos:
                todas_colunas.update(df.columns)
            
            # Garantir que todos os DataFrames tenham as mesmas colunas
            for i, df in enumerate(dados_completos):
                for col in todas_colunas:
                    if col not in df.columns:
                        df[col] = None
                # Reordenar colunas para ter a mesma ordem
                dados_completos[i] = df[sorted(todas_colunas)]
            
            # Agora combinar com segurança
            df = pd.concat(dados_completos, ignore_index=True, sort=False)
            
            print(f"DataFrame combinado - Total de registros: {len(df)}")
            print(f"Colunas disponíveis: {list(df.columns)}")
            
            # Padronizar nomes de colunas principais
            colunas_map = {}
            for col in df.columns:
                col_lower = col.lower()
                if col_lower == 'data' or 'data' in col_lower:
                    if 'data' not in colunas_map.values():
                        colunas_map[col] = 'data'
                elif col_lower == 'valor' or 'valor' in col_lower:
                    if 'valor' not in colunas_map.values():
                        colunas_map[col] = 'valor'
                elif col_lower == 'descricao' or 'descri' in col_lower:
                    if 'descricao' not in colunas_map.values():
                        colunas_map[col] = 'descricao'
                elif 'meio' in col_lower and 'pag' in col_lower:
                    if 'meio_pagamento' not in colunas_map.values():
                        colunas_map[col] = 'meio_pagamento'
                elif 'conta' in col_lower:
                    if 'conta_despesa' not in colunas_map.values():
                        colunas_map[col] = 'conta_despesa'
                elif 'parcel' in col_lower:
                    if 'num_parcelas' not in colunas_map.values():
                        colunas_map[col] = 'num_parcelas'
            
            print(f"Mapeamento de colunas: {colunas_map}")
            df = df.rename(columns=colunas_map)
            
            # Garantir que temos as colunas básicas
            colunas_necessarias = ['data', 'valor', 'descricao']
            for col in colunas_necessarias:
                if col not in df.columns:
                    df[col] = ''
                    print(f"Coluna '{col}' não encontrada, criando vazia")
            
            # Converter data e filtrar por período se especificado
            if 'data' in df.columns:
                print(f"Convertendo coluna data. Primeiros valores: {df['data'].head()}")
                df['data'] = pd.to_datetime(df['data'], errors='coerce')
                
                # Remover linhas com data inválida
                dados_antes = len(df)
                df = df.dropna(subset=['data'])
                dados_depois = len(df)
                print(f"Dados com data válida: {dados_depois}/{dados_antes}")
                
                if filtro_periodo and filtro_periodo != 'Todos':
                    df['periodo'] = df['data'].dt.strftime('%Y-%m')
                    df = df[df['periodo'] == filtro_periodo]
                    print(f"Dados após filtro de período '{filtro_periodo}': {len(df)}")
            
            # Converter valor para numérico
            if 'valor' in df.columns:
                print(f"Convertendo coluna valor. Primeiros valores: {df['valor'].head()}")
                df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
                
                # Remover linhas com valor inválido
                dados_antes = len(df)
                df = df.dropna(subset=['valor'])
                dados_depois = len(df)
                print(f"Dados com valor válido: {dados_depois}/{dados_antes}")
            
            print(f"DataFrame final - Registros: {len(df)}")
            
            if len(df) > 0:
                print("Primeiras linhas do DataFrame:")
                print(df.head())
            
            return df
            
        except Exception as e:
            print(f"Erro detalhado ao obter dados: {e}")
            messagebox.showerror("Erro", f"Erro ao obter dados: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def gerar_relatorio(self):
        """Gera o relatório baseado nas seleções do usuário"""
        print("=== INICIANDO GERAÇÃO DE RELATÓRIO ===")
        
        tipo = self.tipo_relatorio.get()
        periodo = self.periodo_var.get() if self.periodo_var.get() != 'Todos' else None
        data_esp = self.data_especifica.get().strip()
        
        print(f"Tipo de relatório: {tipo}")
        print(f"Período selecionado: {periodo}")
        print(f"Data específica: {data_esp}")
        
        # Se data específica foi fornecida, usar ela
        if data_esp:
            periodo = data_esp
        
        # Obter dados
        print("Obtendo dados do banco...")
        df = self.obter_dados_financeiros(periodo)
        
        if df.empty:
            messagebox.showinfo("Info", "Nenhum dado encontrado para o período selecionado.")
            print("Nenhum dado encontrado!")
            return
        
        print(f"Dados obtidos com sucesso: {len(df)} registros")
        
        # Limpar frames anteriores
        self.limpar_frames()
        
        try:
            # Gerar relatório baseado no tipo selecionado
            print(f"Gerando relatório do tipo: {tipo}")
            
            if tipo == 'Resumo Mensal':
                self.relatorio_resumo_mensal(df)
            elif tipo == 'Por Categoria':
                self.relatorio_por_categoria(df)
            elif tipo == 'Por Meio de Pagamento':
                self.relatorio_por_meio_pagamento(df)
            elif tipo == 'Por Conta':
                self.relatorio_por_conta(df)
            elif tipo == 'Evolução Temporal':
                self.relatorio_evolucao_temporal(df)
            elif tipo == 'Top 10 Despesas':
                self.relatorio_top_despesas(df)
            elif tipo == 'Análise de Parcelas':
                self.relatorio_analise_parcelas(df)
            elif tipo == 'Comparativo Mensal':
                self.relatorio_comparativo_mensal(df)
            
            print("Relatório de gráfico gerado com sucesso")
            
            # Atualizar tabela de dados detalhados
            print("Atualizando tabela de dados...")
            self.atualizar_tabela_dados(df)
            
            # Gerar estatísticas
            print("Gerando estatísticas...")
            self.gerar_estatisticas(df)
            
            print("=== RELATÓRIO CONCLUÍDO COM SUCESSO ===")
            
        except Exception as e:
            print(f"Erro ao gerar relatório: {e}")
            messagebox.showerror("Erro", f"Erro ao gerar relatório: {e}")
            import traceback
            traceback.print_exc()
    
    def limpar_frames(self):
        """Limpa os widgets dos frames de gráfico e estatísticas"""
        for widget in self.frame_grafico.winfo_children():
            widget.destroy()
        for widget in self.frame_stats.winfo_children():
            widget.destroy()
    
    def relatorio_resumo_mensal(self, df):
        """Gera relatório de resumo mensal"""
        if 'data' not in df.columns:
            return
        
        # Agrupar por mês
        df['mes_ano'] = df['data'].dt.strftime('%Y-%m')
        resumo = df.groupby('mes_ano')['valor'].agg(['sum', 'count', 'mean']).round(2)
        
        # Criar gráfico
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Gráfico de barras - Total por mês
        resumo['sum'].plot(kind='bar', ax=ax1, color='skyblue')
        ax1.set_title('Total de Gastos por Mês', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Valor (R$)')
        ax1.tick_params(axis='x', rotation=45)
        
        # Gráfico de linha - Quantidade de transações
        resumo['count'].plot(kind='line', ax=ax2, color='red', marker='o')
        ax2.set_title('Número de Transações por Mês', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Quantidade')
        ax2.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        # Incorporar gráfico no tkinter
        canvas = FigureCanvasTkAgg(fig, self.frame_grafico)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def relatorio_por_categoria(self, df):
        """Gera relatório por categoria (baseado na descrição)"""
        # Criar categorias baseadas em palavras-chave na descrição
        categorias = {
            'Alimentação': ['mercado', 'supermercado', 'restaurante', 'lanche', 'comida', 'padaria'],
            'Transporte': ['combustível', 'gasolina', 'uber', 'taxi', 'ônibus', 'transporte'],
            'Saúde': ['farmácia', 'médico', 'hospital', 'saúde', 'remédio'],
            'Entretenimento': ['cinema', 'show', 'festa', 'entretenimento', 'diversão'],
            'Casa': ['aluguel', 'casa', 'móveis', 'decoração', 'limpeza'],
            'Educação': ['escola', 'curso', 'livro', 'educação', 'faculdade'],
            'Outros': []
        }
        
        def categorizar_despesa(descricao):
            descricao_lower = str(descricao).lower()
            for categoria, palavras in categorias.items():
                if categoria == 'Outros':
                    continue
                for palavra in palavras:
                    if palavra in descricao_lower:
                        return categoria
            return 'Outros'
        
        df['categoria'] = df['descricao'].apply(categorizar_despesa)
        
        # Agrupar por categoria
        categoria_resumo = df.groupby('categoria')['valor'].agg(['sum', 'count']).round(2)
        
        # Criar gráfico
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Gráfico de pizza
        ax1.pie(categoria_resumo['sum'], labels=categoria_resumo.index, autopct='%1.1f%%', startangle=90)
        ax1.set_title('Distribuição de Gastos por Categoria', fontweight='bold')
        
        # Gráfico de barras
        categoria_resumo['sum'].plot(kind='bar', ax=ax2, color='lightgreen')
        ax2.set_title('Total por Categoria', fontweight='bold')
        ax2.set_ylabel('Valor (R$)')
        ax2.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, self.frame_grafico)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def relatorio_por_meio_pagamento(self, df):
        """Gera relatório por meio de pagamento"""
        if 'meio_pagamento' not in df.columns:
            messagebox.showinfo("Info", "Coluna 'meio_pagamento' não encontrada nos dados.")
            return
        
        # Agrupar por meio de pagamento
        meio_resumo = df.groupby('meio_pagamento')['valor'].agg(['sum', 'count']).round(2)
        
        # Criar gráfico
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Gráfico de pizza
        ax1.pie(meio_resumo['sum'], labels=meio_resumo.index, autopct='%1.1f%%', startangle=90)
        ax1.set_title('Distribuição por Meio de Pagamento', fontweight='bold')
        
        # Gráfico de barras
        meio_resumo['sum'].plot(kind='bar', ax=ax2, color='orange')
        ax2.set_title('Total por Meio de Pagamento', fontweight='bold')
        ax2.set_ylabel('Valor (R$)')
        ax2.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, self.frame_grafico)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
      
    def relatorio_por_conta(self, df):
        """Gera relatório por conta"""
        if 'conta_despesa' not in df.columns:
            messagebox.showinfo("Info", "Coluna 'conta_despesa' não encontrada nos dados.")
            return
        
        # Agrupar por conta
        conta_resumo = df.groupby('conta_despesa')['valor'].agg(['sum', 'count']).round(2)
        
        # Criar gráfico
        fig, ax = plt.subplots(figsize=(12, 6))
        
        conta_resumo['sum'].plot(kind='bar', ax=ax, color='purple')
        ax.set_title('Total de Gastos por Conta', fontweight='bold')
        ax.set_ylabel('Valor (R$)')
        ax.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, self.frame_grafico)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def relatorio_evolucao_temporal(self, df):
        """Gera relatório de evolução temporal"""
        if 'data' not in df.columns:
            return
        
        # Agrupar por data
        df_diario = df.groupby(df['data'].dt.date)['valor'].sum().reset_index()
        df_diario.columns = ['data', 'valor']
        
        # Criar gráfico de linha
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(df_diario['data'], df_diario['valor'], marker='o', linewidth=2, markersize=4)
        ax.set_title('Evolução dos Gastos ao Longo do Tempo', fontweight='bold')
        ax.set_ylabel('Valor (R$)')
        ax.set_xlabel('Data')
        ax.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, self.frame_grafico)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def relatorio_top_despesas(self, df):
        """Gera relatório das top 10 maiores despesas"""
        # Ordenar por valor e pegar top 10
        top_despesas = df.nlargest(10, 'valor')[['descricao', 'valor', 'data']]
        
        # Criar gráfico
        fig, ax = plt.subplots(figsize=(12, 8))
        
        y_pos = np.arange(len(top_despesas))
        ax.barh(y_pos, top_despesas['valor'], color='red', alpha=0.7)
        ax.set_yticks(y_pos)
        ax.set_yticklabels([desc[:30] + '...' if len(desc) > 30 else desc for desc in top_despesas['descricao']])
        ax.set_xlabel('Valor (R$)')
        ax.set_title('Top 10 Maiores Despesas', fontweight='bold')
        
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, self.frame_grafico)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def relatorio_analise_parcelas(self, df):
        """Gera relatório de análise de parcelas"""
        if 'num_parcelas' not in df.columns:
            messagebox.showinfo("Info", "Coluna 'num_parcelas' não encontrada nos dados.")
            return
        
        # Filtrar apenas transações com parcelas
        df_parcelas = df[df['num_parcelas'] > 1]
        
        if df_parcelas.empty:
            messagebox.showinfo("Info", "Nenhuma transação com parcelas encontrada.")
            return
        
        # Agrupar por número de parcelas
        parcelas_resumo = df_parcelas.groupby('num_parcelas')['valor'].agg(['sum', 'count']).round(2)
        
        # Criar gráfico
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Distribuição por número de parcelas
        parcelas_resumo['count'].plot(kind='bar', ax=ax1, color='teal')
        ax1.set_title('Quantidade de Transações por Nº de Parcelas', fontweight='bold')
        ax1.set_ylabel('Quantidade')
        ax1.set_xlabel('Número de Parcelas')
        
        # Valor total por número de parcelas
        parcelas_resumo['sum'].plot(kind='bar', ax=ax2, color='navy')
        ax2.set_title('Valor Total por Nº de Parcelas', fontweight='bold')
        ax2.set_ylabel('Valor (R$)')
        ax2.set_xlabel('Número de Parcelas')
        
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, self.frame_grafico)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def relatorio_comparativo_mensal(self, df):
        """Gera relatório comparativo mensal"""
        if 'data' not in df.columns:
            return
        
        # Agrupar por mês e ano
        df['mes'] = df['data'].dt.month
        df['ano'] = df['data'].dt.year
        
        comparativo = df.groupby(['ano', 'mes'])['valor'].sum().reset_index()
        comparativo['mes_nome'] = comparativo['mes'].map({
            1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
            7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
        })
        
        # Criar gráfico
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Gráfico de barras agrupadas por ano
        anos = comparativo['ano'].unique()
        width = 0.35
        x = np.arange(1, 13)
        
        for i, ano in enumerate(anos):
            dados_ano = comparativo[comparativo['ano'] == ano]
            valores = [dados_ano[dados_ano['mes'] == mes]['valor'].sum() if not dados_ano[dados_ano['mes'] == mes].empty else 0 for mes in range(1, 13)]
            ax.bar(x + i*width, valores, width, label=f'{ano}', alpha=0.8)
        
        ax.set_xlabel('Mês')
        ax.set_ylabel('Valor (R$)')
        ax.set_title('Comparativo Mensal por Ano', fontweight='bold')
        ax.set_xticks(x + width/2)
        ax.set_xticklabels(['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                           'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'])
        ax.legend()
        
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, self.frame_grafico)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def atualizar_tabela_dados(self, df):
        """Atualiza a tabela com os dados detalhados"""
        # Limpar tabela existente
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if df.empty:
            return
        
        # Configurar colunas
        colunas_exibir = ['data', 'descricao', 'valor', 'meio_pagamento', 'conta_despesa', 'num_parcelas']
        colunas_disponiveis = [col for col in colunas_exibir if col in df.columns]
        
        self.tree['columns'] = colunas_disponiveis
        self.tree['show'] = 'headings'
        
        # Configurar cabeçalhos
        for col in colunas_disponiveis:
            self.tree.heading(col, text=col.replace('_', ' ').title())
            if col == 'valor':
                self.tree.column(col, width=100, anchor='e')
            elif col == 'data':
                self.tree.column(col, width=100)
            elif col == 'descricao':
                self.tree.column(col, width=250)
            else:
                self.tree.column(col, width=120)
        
        # Inserir dados
        for _, row in df.iterrows():
            valores = []
            for col in colunas_disponiveis:
                valor = row[col] if pd.notna(row[col]) else ''
                if col == 'valor' and valor != '':
                    valor = f'R$ {float(valor):.2f}'
                elif col == 'data' and valor != '':
                    valor = pd.to_datetime(valor).strftime('%d/%m/%Y')
                valores.append(str(valor))
            
            self.tree.insert('', 'end', values=valores)
    
    def gerar_estatisticas(self, df):
        """Gera estatísticas resumidas dos dados"""
        if df.empty:
            return
        
        # Criar frame principal para estatísticas
        stats_main_frame = tk.Frame(self.frame_stats, bg='white')
        stats_main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Título
        title_label = tk.Label(stats_main_frame, text="Estatísticas Gerais", 
                              font=self.font_title, bg='white', fg='#2c3e50')
        title_label.pack(pady=(0, 20))
        
        # Frame para cards de estatísticas
        cards_frame = tk.Frame(stats_main_frame, bg='white')
        cards_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Calcular estatísticas
        total_gastos = df['valor'].sum()
        media_gastos = df['valor'].mean()
        mediana_gastos = df['valor'].median()
        maior_gasto = df['valor'].max()
        menor_gasto = df['valor'].min()
        total_transacoes = len(df)
        
        # Criar cards de estatísticas
        stats_data = [
            ("Total de Gastos", f"R$ {total_gastos:.2f}", "#e74c3c"),
            ("Média por Transação", f"R$ {media_gastos:.2f}", "#3498db"),
            ("Mediana", f"R$ {mediana_gastos:.2f}", "#9b59b6"),
            ("Maior Gasto", f"R$ {maior_gasto:.2f}", "#e67e22"),
            ("Menor Gasto", f"R$ {menor_gasto:.2f}", "#1abc9c"),
            ("Total de Transações", str(total_transacoes), "#34495e")
        ]
        
        # Organizar cards em grid 3x2
        for i, (titulo, valor, cor) in enumerate(stats_data):
            row = i // 3
            col = i % 3
            
            card_frame = tk.Frame(cards_frame, bg=cor, relief='raised', bd=2)
            card_frame.grid(row=row, column=col, padx=10, pady=10, sticky='ew')
            
            titulo_label = tk.Label(card_frame, text=titulo, font=('Arial', 10, 'bold'),
                                   bg=cor, fg='white')
            titulo_label.pack(pady=(10, 5))
            
            valor_label = tk.Label(card_frame, text=valor, font=('Arial', 14, 'bold'),
                                  bg=cor, fg='white')
            valor_label.pack(pady=(0, 10))
            
            cards_frame.grid_columnconfigure(col, weight=1)
        
        # Estatísticas adicionais por período
        if 'data' in df.columns:
            periodo_frame = tk.LabelFrame(stats_main_frame, text="Estatísticas por Período",
                                        font=self.font_normal, bg='white')
            periodo_frame.pack(fill=tk.X, pady=20)
            
            # Agrupar por mês
            df_periodo = df.copy()
            df_periodo['mes_ano'] = df_periodo['data'].dt.strftime('%Y-%m')
            resumo_mensal = df_periodo.groupby('mes_ano')['valor'].agg(['sum', 'count', 'mean']).round(2)
            
            # Criar tabela de resumo mensal
            tree_frame = tk.Frame(periodo_frame)
            tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            tree_periodo = ttk.Treeview(tree_frame, columns=('Total', 'Transações', 'Média'), show='headings', height=6)
            tree_periodo.pack(fill=tk.BOTH, expand=True)
            
            # Configurar cabeçalhos
            tree_periodo.heading('#1', text='Mês/Ano')
            tree_periodo.heading('Total', text='Total (R$)')
            tree_periodo.heading('Transações', text='Nº Transações')
            tree_periodo.heading('Média', text='Média (R$)')
            
            # Configurar largura das colunas
            tree_periodo.column('#1', width=100, anchor='center')
            tree_periodo.column('Total', width=120, anchor='e')
            tree_periodo.column('Transações', width=120, anchor='center')
            tree_periodo.column('Média', width=120, anchor='e')
            
            # Inserir dados
            for mes_ano, dados in resumo_mensal.iterrows():
                tree_periodo.insert('', 'end', text=mes_ano, 
                                  values=(f'R$ {dados["sum"]:.2f}', 
                                         int(dados["count"]), 
                                         f'R$ {dados["mean"]:.2f}'))
        
        # Frame para análises adicionais
        analises_frame = tk.LabelFrame(stats_main_frame, text="Análises Adicionais",
                                     font=self.font_normal, bg='white')
        analises_frame.pack(fill=tk.X, pady=20)
        
        analises_text = tk.Text(analises_frame, height=8, wrap=tk.WORD, font=('Arial', 10))
        analises_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollbar para o texto
        scrollbar_text = ttk.Scrollbar(analises_frame, orient="vertical", command=analises_text.yview)
        scrollbar_text.pack(side="right", fill="y")
        analises_text.configure(yscrollcommand=scrollbar_text.set)
        
        # Gerar análises textuais
        analises = []
        
        # Análise de concentração de gastos
        if total_transacoes > 0:
            gastos_altos = df[df['valor'] > media_gastos * 2]
            perc_gastos_altos = (len(gastos_altos) / total_transacoes) * 100
            analises.append(f"• {perc_gastos_altos:.1f}% das transações são consideradas gastos altos (acima de 2x a média)")
        
        # Análise de frequência
        if 'data' in df.columns and len(df) > 1:
            dias_periodo = (df['data'].max() - df['data'].min()).days
            if dias_periodo > 0:
                freq_diaria = total_transacoes / dias_periodo
                analises.append(f"• Frequência média: {freq_diaria:.1f} transações por dia")
        
        # Análise por meio de pagamento (se disponível)
        if 'meio_pagamento' in df.columns:
            meio_mais_usado = df['meio_pagamento'].mode()
            if not meio_mais_usado.empty:
                analises.append(f"• Meio de pagamento mais utilizado: {meio_mais_usado.iloc[0]}")
        
        # Análise de variabilidade
        desvio_padrao = df['valor'].std()
        coef_variacao = (desvio_padrao / media_gastos) * 100 if media_gastos > 0 else 0
        if coef_variacao < 50:
            variabilidade = "baixa"
        elif coef_variacao < 100:
            variabilidade = "média"
        else:
            variabilidade = "alta"
        analises.append(f"• Variabilidade dos gastos: {variabilidade} (CV: {coef_variacao:.1f}%)")
        
        # Inserir análises no texto
        analises_text.insert(tk.END, "INSIGHTS AUTOMÁTICOS:\n\n")
        for analise in analises:
            analises_text.insert(tk.END, analise + "\n\n")
        
        analises_text.configure(state='disabled')  # Torna o texto apenas leitura
    
    def exportar_excel(self):
        """Exporta os dados atuais para Excel"""
        try:
            # Obter dados atuais
            periodo = self.periodo_var.get() if self.periodo_var.get() != 'Todos' else None
            data_esp = self.data_especifica.get().strip()
            
            if data_esp:
                periodo = data_esp
            
            df = self.obter_dados_financeiros(periodo)
            
            if df.empty:
                messagebox.showinfo("Info", "Nenhum dado para exportar.")
                return
            
            # Selecionar arquivo de destino
            arquivo = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                title="Salvar relatório como..."
            )
            
            if not arquivo:
                return
            
            # Criar arquivo Excel com múltiplas abas
            with pd.ExcelWriter(arquivo, engine='openpyxl') as writer:
                # Aba com dados brutos
                df_export = df.copy()
                if 'data' in df_export.columns:
                    df_export['data'] = df_export['data'].dt.strftime('%d/%m/%Y')
                df_export.to_excel(writer, sheet_name='Dados Brutos', index=False)
                
                # Aba com resumo mensal
                if 'data' in df.columns:
                    df_resumo = df.copy()
                    df_resumo['mes_ano'] = df_resumo['data'].dt.strftime('%Y-%m')
                    resumo_mensal = df_resumo.groupby('mes_ano')['valor'].agg(['sum', 'count', 'mean']).round(2)
                    resumo_mensal.columns = ['Total', 'Quantidade', 'Média']
                    resumo_mensal.to_excel(writer, sheet_name='Resumo Mensal')
                
                # Aba com estatísticas
                stats_data = {
                    'Estatística': ['Total de Gastos', 'Média por Transação', 'Mediana', 
                                   'Maior Gasto', 'Menor Gasto', 'Total de Transações'],
                    'Valor': [df['valor'].sum(), df['valor'].mean(), df['valor'].median(),
                             df['valor'].max(), df['valor'].min(), len(df)]
                }
                pd.DataFrame(stats_data).to_excel(writer, sheet_name='Estatísticas', index=False)
            
            messagebox.showinfo("Sucesso", f"Relatório exportado com sucesso para:\n{arquivo}")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar para Excel: {e}")

def main():
    """Função principal para executar o aplicativo"""
    root = tk.Tk()
    app = RelatoriosFinanceiros(root)
    
    # Configurar o fechamento da aplicação
    def on_closing():
        plt.close('all')  # Fechar todos os gráficos matplotlib
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()