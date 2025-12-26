"""
Interface Gráfica para RAG (Retrieval-Augmented Generation)
Permite fazer perguntas sobre documentos usando Google Gemini (Long Context)
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import os
import time
import threading
import google.generativeai as genai

import json
import datetime

class RAGInterface:
    def __init__(self, root):
        self.root = root
        self.root.title("📚 RAG - Consulta em Documentos com IA (Gemini)")
        self.root.geometry("1000x800")
        self.root.configure(bg='#f0f0f0')
        
        # Configuração
        self.config_file = os.path.join(os.path.dirname(__file__), 'rag_config.json')
        self.config = self.carregar_config()
        
        # Variáveis
        self.api_key_var = tk.StringVar(value=self.config.get('api_key', ''))
        self.model_var = tk.StringVar(value=self.config.get('model', 'gemini-1.5-flash'))
        self.cache_dir_var = tk.StringVar(value=self.config.get('cache_dir', os.path.join(os.path.dirname(__file__), 'rag_cache')))
        
        # Garantir que diretório de cache existe
        if not os.path.exists(self.cache_dir_var.get()):
            try:
                os.makedirs(self.cache_dir_var.get())
            except:
                pass

        self.documentos_paths = [] # Caminhos locais
        self.documentos_uploaded = [] # Objetos de arquivo do GenAI (ou dicts do cache)
        self.historico = []
        self.model = None
        
        # Carregar cache de arquivos
        self.cache_file = os.path.join(self.cache_dir_var.get(), 'rag_cache.json')
        self.file_cache = self.carregar_cache()
        
        self.criar_interface()
        
        # Restaurar arquivos do cache na interface
        self.restaurar_arquivos_cache()
        
    def carregar_config(self):
        """Carrega configuração do arquivo JSON"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Erro ao carregar config: {e}")
        return {}
        
    def carregar_cache(self):
        """Carrega cache de arquivos processados"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Erro ao carregar cache: {e}")
        return {'files': []}
        
    def salvar_config_arquivo(self):
        """Salva configuração no arquivo JSON"""
        config = {
            'api_key': self.api_key_var.get().strip(),
            'model': self.model_var.get(),
            'cache_dir': self.cache_dir_var.get()
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar configuração: {e}")
            
    def salvar_cache(self):
        """Salva cache de arquivos no JSON"""
        try:
            # Garantir diretório
            if not os.path.exists(self.cache_dir_var.get()):
                os.makedirs(self.cache_dir_var.get())
                
            # Atualizar caminho do arquivo de cache caso tenha mudado
            self.cache_file = os.path.join(self.cache_dir_var.get(), 'rag_cache.json')
            
            with open(self.cache_file, 'w') as f:
                json.dump(self.file_cache, f, indent=2)
        except Exception as e:
            print(f"Erro ao salvar cache: {e}")

    def criar_interface(self):
        # Frame superior - Configuração
        frame_config = ttk.LabelFrame(self.root, text="⚙️ Configuração", padding="10")
        frame_config.pack(fill=tk.X, padx=10, pady=5)
        
        # Grid layout para config
        frame_config.columnconfigure(1, weight=1)
        
        # API Key
        ttk.Label(frame_config, text="API Key do Google:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        api_entry = ttk.Entry(frame_config, textvariable=self.api_key_var, width=50, show="*")
        api_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        
        ttk.Button(frame_config, text="👁️", width=3, command=self.toggle_api_key).grid(row=0, column=2, padx=2)
        
        # Seleção de Modelo
        ttk.Label(frame_config, text="Modelo:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        
        modelos_disponiveis = [
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
            "gemini-1.5-pro",
            "gemini-1.0-pro",
            "gemini-2.0-flash-exp"
        ]
        
        combo_modelo = ttk.Combobox(frame_config, textvariable=self.model_var, values=modelos_disponiveis, state="readonly")
        combo_modelo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Diretório de Cache
        ttk.Label(frame_config, text="Pasta de Cache:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        frame_cache = ttk.Frame(frame_config)
        frame_cache.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Entry(frame_cache, textvariable=self.cache_dir_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(frame_cache, text="📂", width=3, command=self.selecionar_cache_dir).pack(side=tk.LEFT, padx=2)

        # Botões de Ação (Frame dedicado)
        frame_btns = ttk.Frame(frame_config)
        frame_btns.grid(row=0, column=3, rowspan=3, padx=5, sticky="ns")
        
        ttk.Button(frame_btns, text="💾 Salvar Config", command=self.salvar_api_key).pack(fill=tk.X, pady=2)
        ttk.Button(frame_btns, text="📋 Listar Modelos", command=self.listar_modelos).pack(fill=tk.X, pady=2)
        ttk.Button(frame_btns, text="☁️ Arquivos na Nuvem", command=self.listar_arquivos_nuvem).pack(fill=tk.X, pady=2)
        
        ttk.Label(frame_config, text="💡 Obtenha sua key em: https://aistudio.google.com/apikey", 
                 foreground="blue", cursor="hand2").grid(row=3, column=0, columnspan=4, sticky=tk.W, padx=5)
        frame_docs = ttk.LabelFrame(self.root, text="📁 Documentos", padding="10")
        frame_docs.pack(fill=tk.BOTH, padx=10, pady=5, expand=False)
        
        # Lista de documentos
        frame_lista = ttk.Frame(frame_docs)
        frame_lista.pack(fill=tk.BOTH, expand=True)
        
        self.lista_docs = tk.Listbox(frame_lista, height=6)
        self.lista_docs.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(frame_lista, orient="vertical", command=self.lista_docs.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.lista_docs.config(yscrollcommand=scrollbar.set)
        
        # Botões de documentos
        frame_btn_docs = ttk.Frame(frame_docs)
        frame_btn_docs.pack(fill=tk.X, pady=5)
        
        ttk.Button(frame_btn_docs, text="➕ Adicionar Arquivo(s)", command=self.adicionar_documentos).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_btn_docs, text="🗑️ Remover Selecionado", command=self.remover_documento).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_btn_docs, text="🚀 Processar Documentos", command=self.processar_documentos).pack(side=tk.LEFT, padx=5)
        
        self.label_status = ttk.Label(frame_btn_docs, text="Status: Aguardando...", foreground="gray")
        self.label_status.pack(side=tk.LEFT, padx=20)
        
        # Frame de perguntas
        frame_perguntas = ttk.LabelFrame(self.root, text="❓ Fazer Pergunta", padding="10")
        frame_perguntas.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(frame_perguntas, text="Digite sua pergunta:").pack(anchor=tk.W)
        
        frame_input = ttk.Frame(frame_perguntas)
        frame_input.pack(fill=tk.X, pady=5)
        
        self.pergunta_entry = ttk.Entry(frame_input, font=("Arial", 10))
        self.pergunta_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.pergunta_entry.bind('<Return>', lambda e: self.fazer_pergunta())
        
        self.btn_perguntar = ttk.Button(frame_input, text="🔍 Perguntar", 
                                        command=self.fazer_pergunta, state="disabled")
        self.btn_perguntar.pack(side=tk.LEFT)
        
        ttk.Button(frame_input, text="🗑️ Limpar Histórico", command=self.limpar_historico).pack(side=tk.LEFT, padx=5)
        
        # Frame de respostas
        frame_respostas = ttk.LabelFrame(self.root, text="💬 Histórico de Conversas", padding="10")
        frame_respostas.pack(fill=tk.BOTH, padx=10, pady=5, expand=True)
        
        self.texto_respostas = scrolledtext.ScrolledText(frame_respostas, wrap=tk.WORD, 
                                                         font=("Arial", 10), height=20)
        self.texto_respostas.pack(fill=tk.BOTH, expand=True)
        
        # Tags para formatação
        self.texto_respostas.tag_config("pergunta", foreground="#0066cc", font=("Arial", 10, "bold"))
        self.texto_respostas.tag_config("resposta", foreground="#006600")
        self.texto_respostas.tag_config("fonte", foreground="#666666", font=("Arial", 9, "italic"))
        self.texto_respostas.tag_config("separador", foreground="#cccccc")
        
        # Status bar
        self.status_bar = ttk.Label(self.root, text="Pronto", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
    def toggle_api_key(self):
        """Mostra/oculta a API key"""
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.LabelFrame) and "Configuração" in widget.cget("text"):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Entry) and child.cget("textvariable") == str(self.api_key_var):
                        if child.cget("show") == "*":
                            child.config(show="")
                        else:
                            child.config(show="*")
                        break
                        
    def selecionar_cache_dir(self):
        """Seleciona diretório de cache"""
        dir_path = filedialog.askdirectory(title="Selecione a pasta para salvar arquivos processados")
        if dir_path:
            self.cache_dir_var.set(dir_path)
            # Recarregar cache do novo diretório
            self.cache_file = os.path.join(dir_path, 'rag_cache.json')
            self.file_cache = self.carregar_cache()
            self.restaurar_arquivos_cache()
            
    def salvar_api_key(self):
        """Salva a API key e modelo no arquivo de configuração"""
        key = self.api_key_var.get().strip()
        if key:
            os.environ['GOOGLE_API_KEY'] = key
            self.salvar_config_arquivo()
            messagebox.showinfo("Sucesso", "Configuração salva com sucesso!")
        else:
            messagebox.showwarning("Aviso", "Digite uma API Key válida")
            
    def adicionar_documentos(self):
        """Adiciona documentos à lista"""
        arquivos = filedialog.askopenfilenames(
            title="Selecione documento(s)",
            filetypes=[
                ("Todos os arquivos", "*.*"),
                ("PDF", "*.pdf"),
                ("Texto", "*.txt"),
                ("Word", "*.docx"),
                ("Markdown", "*.md"),
                ("Imagens", "*.png;*.jpg;*.jpeg")
            ]
        )
        
        for arquivo in arquivos:
            # Verificar se já está na lista
            if arquivo not in self.documentos_paths:
                # Verificar se já está no cache
                cached_file = next((f for f in self.file_cache['files'] if f['local_path'] == arquivo), None)
                
                self.documentos_paths.append(arquivo)
                
                if cached_file:
                    self.lista_docs.insert(tk.END, f"✅ {os.path.basename(arquivo)} (Em Cache)")
                    # Adicionar aos uploaded se já estiver válido (será verificado no processar)
                else:
                    self.lista_docs.insert(tk.END, f"🆕 {os.path.basename(arquivo)}")
                
    def restaurar_arquivos_cache(self):
        """Restaura arquivos do cache na interface e carrega objetos"""
        self.lista_docs.delete(0, tk.END)
        self.documentos_paths = []
        self.documentos_uploaded = []
        
        # Adicionar menu de contexto na lista
        self.menu_contexto = tk.Menu(self.root, tearoff=0)
        self.menu_contexto.add_command(label="📋 Ver Detalhes (ID/URI)", command=self.ver_detalhes_arquivo)
        self.lista_docs.bind("<Button-3>", self.mostrar_menu_contexto)
        
        files_to_load = []
        
        for f in self.file_cache['files']:
            path = f.get('local_path')
            # Mesmo que o arquivo local não exista, se estiver no cache do Google, podemos usar?
            # Por segurança, vamos listar se tiver path ou se tiver nome
            display_name = f.get('display_name', os.path.basename(path) if path else "Arquivo Desconhecido")
            
            self.documentos_paths.append(path)
            self.lista_docs.insert(tk.END, f"⏳ {display_name} (Verificando...)")
            files_to_load.append(f)
            
        if files_to_load:
            # Iniciar thread para validar e carregar objetos do cache
            thread = threading.Thread(target=self._carregar_objetos_cache_thread, args=(files_to_load,), daemon=True)
            thread.start()
            
    def mostrar_menu_contexto(self, event):
        """Mostra menu de contexto na lista"""
        try:
            self.lista_docs.selection_clear(0, tk.END)
            self.lista_docs.selection_set(self.lista_docs.nearest(event.y))
            self.lista_docs.activate(self.lista_docs.nearest(event.y))
            self.menu_contexto.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu_contexto.grab_release()
            
    def ver_detalhes_arquivo(self):
        """Mostra detalhes do arquivo selecionado"""
        selecionado = self.lista_docs.curselection()
        if selecionado:
            idx = selecionado[0]
            # Tentar encontrar no cache
            # A lista visual está sincronizada com self.documentos_paths, mas precisamos achar o objeto no cache
            # O cache pode não estar na mesma ordem se houver mistura, mas vamos tentar pelo path
            path = self.documentos_paths[idx]
            cached_data = next((f for f in self.file_cache['files'] if f['local_path'] == path), None)
            
            if cached_data:
                info = f"Nome: {cached_data.get('display_name')}\n"
                info += f"ID (Name): {cached_data.get('name')}\n"
                info += f"URI: {cached_data.get('uri')}\n"
                info += f"Local: {cached_data.get('local_path')}\n"
                info += f"Upload: {cached_data.get('upload_time')}"
                
                # Copiar ID para clipboard
                self.root.clipboard_clear()
                self.root.clipboard_append(cached_data.get('name'))
                
                messagebox.showinfo("Detalhes do Arquivo (ID copiado!)", info)
            else:
                messagebox.showinfo("Detalhes", "Arquivo ainda não processado ou não encontrado no cache.")

    def _carregar_objetos_cache_thread(self, files):
        """Carrega objetos do cache em background"""
        key = self.api_key_var.get().strip()
        if not key:
            self.atualizar_status("Configure a API Key para validar o cache.")
            return
            
        try:
            genai.configure(api_key=key)
            self.atualizar_status("Validando arquivos em cache...")
            
            validos = 0
            
            for i, f in enumerate(files):
                try:
                    # Tentar recuperar objeto do Google
                    file_obj = genai.get_file(f['name'])
                    if file_obj.state.name == "ACTIVE":
                        self.documentos_uploaded.append(file_obj)
                        # Atualizar ícone na lista (precisa ser na thread principal)
                        self.root.after(0, self._atualizar_item_lista, i, f"✅ {f.get('display_name', 'Doc')} (Pronto)")
                        validos += 1
                    else:
                        self.root.after(0, self._atualizar_item_lista, i, f"⚠️ {f.get('display_name', 'Doc')} (Expirado)")
                except Exception as e:
                    print(f"Erro ao validar {f.get('name')}: {e}")
                    self.root.after(0, self._atualizar_item_lista, i, f"❌ {f.get('display_name', 'Doc')} (Erro)")
            
            self.atualizar_status(f"Cache carregado: {validos} arquivos prontos.")
            
            # Se tiver arquivos válidos, inicializar modelo automaticamente
            if validos > 0:
                self.root.after(0, self._inicializar_modelo_auto)
                
        except Exception as e:
            self.atualizar_status(f"Erro ao validar cache: {e}")

    def _atualizar_item_lista(self, index, texto):
        """Atualiza texto de um item na lista"""
        try:
            self.lista_docs.delete(index)
            self.lista_docs.insert(index, texto)
        except:
            pass
            
    def _inicializar_modelo_auto(self):
        """Inicializa modelo automaticamente se houver arquivos"""
        try:
            nome_modelo = self.model_var.get()
            self.model = genai.GenerativeModel(nome_modelo)
            self.btn_perguntar.config(state="normal")
            print(f"Modelo {nome_modelo} inicializado automaticamente.")
        except:
            pass

    def remover_documento(self):
        """Remove documento selecionado"""
        selecionado = self.lista_docs.curselection()
        if selecionado:
            idx = selecionado[0]
            path_removido = self.documentos_paths[idx]
            
            # Remover da lista visual e de paths
            self.lista_docs.delete(idx)
            del self.documentos_paths[idx]
            
            # Perguntar se quer remover do cache também
            if messagebox.askyesno("Remover do Cache", "Deseja remover este arquivo do cache também?\n(Isso exigirá novo upload se você adicioná-lo novamente)"):
                self.file_cache['files'] = [f for f in self.file_cache['files'] if f['local_path'] != path_removido]
                self.salvar_cache()
            
            self.label_status.config(text="⚠️ Lista alterada. Processe novamente.", foreground="orange")
            self.btn_perguntar.config(state="disabled")
            
    def processar_documentos(self):
        """Processa e faz upload dos documentos"""
        if not self.documentos_paths:
            messagebox.showwarning("Aviso", "Adicione pelo menos um documento!")
            return
            
        key = self.api_key_var.get().strip()
        if not key:
            messagebox.showerror("Erro", "Configure a API Key primeiro!")
            return
            
        # Configurar GenAI
        genai.configure(api_key=key)
            
        # Processar em thread separada
        thread = threading.Thread(target=self._processar_documentos_thread, daemon=True)
        thread.start()
        
    def _processar_documentos_thread(self):
        """Thread para upload de documentos"""
        try:
            self.atualizar_status("Verificando arquivos...")
            self.label_status.config(text="⏳ Processando...", foreground="orange")
            
            self.documentos_uploaded = []
            novos_uploads = False
            
            total = len(self.documentos_paths)
            
            for i, doc_path in enumerate(self.documentos_paths, 1):
                self.atualizar_status(f"Verificando {i}/{total}: {os.path.basename(doc_path)}...")
                
                # Verificar cache
                cached_data = next((f for f in self.file_cache['files'] if f['local_path'] == doc_path), None)
                file_obj = None
                
                if cached_data:
                    try:
                        # Verificar se ainda é válido no Google
                        print(f"Verificando cache para {doc_path}: {cached_data['name']}")
                        file_obj = genai.get_file(cached_data['name'])
                        
                        # Verificar estado
                        if file_obj.state.name == "ACTIVE":
                            print("Arquivo válido no cache!")
                            self.documentos_uploaded.append(file_obj)
                            continue # Pula upload
                        else:
                            print(f"Arquivo no cache com estado inválido: {file_obj.state.name}")
                    except Exception as e:
                        print(f"Erro ao verificar cache (arquivo pode ter expirado): {e}")
                        # Se der erro (ex: 404), precisa fazer upload de novo
                
                # Se chegou aqui, precisa fazer upload
                novos_uploads = True
                self.atualizar_status(f"Uploading {i}/{total}: {os.path.basename(doc_path)}...")
                
                file_obj = genai.upload_file(doc_path)
                
                # Aguardar processamento
                while file_obj.state.name == "PROCESSING":
                    time.sleep(2)
                    file_obj = genai.get_file(file_obj.name)
                
                if file_obj.state.name == "FAILED":
                    raise Exception(f"Falha no processamento do arquivo: {os.path.basename(doc_path)}")
                
                self.documentos_uploaded.append(file_obj)
                
                # Atualizar cache
                # Remover entrada antiga se existir
                self.file_cache['files'] = [f for f in self.file_cache['files'] if f['local_path'] != doc_path]
                
                self.file_cache['files'].append({
                    'local_path': doc_path,
                    'display_name': file_obj.display_name,
                    'name': file_obj.name,
                    'uri': file_obj.uri,
                    'upload_time': str(datetime.datetime.now())
                })
                
            # Salvar cache atualizado
            if novos_uploads:
                self.salvar_cache()
                
            self.label_status.config(text=f"✅ {total} arquivo(s) prontos!", foreground="green")
            self.atualizar_status("Documentos prontos! Pode perguntar.")
            
            # Atualizar lista visual com status
            self.root.after(0, self.restaurar_arquivos_cache)
            
            # Inicializar modelo com a escolha do usuário
            nome_modelo = self.model_var.get()
            self.atualizar_status(f"Inicializando modelo {nome_modelo}...")
            
            try:
                self.model = genai.GenerativeModel(nome_modelo)
                messagebox.showinfo("Sucesso", f"{total} documento(s) prontos!\n\nModelo ativo: {nome_modelo}")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao inicializar modelo {nome_modelo}:\n{e}")
                self.model = None
            
            # Habilitar botão de perguntar se o modelo foi carregado
            if self.model:
                self.btn_perguntar.config(state="normal")
            
        except Exception as e:
            self.label_status.config(text="❌ Erro no processamento", foreground="red")
            self.atualizar_status(f"Erro: {str(e)}")
            messagebox.showerror("Erro", f"Erro ao processar documentos:\n\n{str(e)}")
            
    def fazer_pergunta(self):
        """Faz uma pergunta sobre os documentos"""
        pergunta = self.pergunta_entry.get().strip()
        
        if not pergunta:
            messagebox.showwarning("Aviso", "Digite uma pergunta!")
            return
            
        if not self.model or not self.documentos_uploaded:
            messagebox.showwarning("Aviso", "Processe os documentos primeiro!")
            return
            
        # Limpar campo
        self.pergunta_entry.delete(0, tk.END)
        
        # Processar em thread separada
        thread = threading.Thread(target=self._fazer_pergunta_thread, args=(pergunta,), daemon=True)
        thread.start()
        
    def _fazer_pergunta_thread(self, pergunta):
        """Thread para fazer pergunta"""
        try:
            nome_modelo = self.model_var.get()
            self.atualizar_status(f"🤔 Pensando ({nome_modelo}): {pergunta[:50]}...")
            print(f"DEBUG: Usando modelo {nome_modelo}")
            
            # Instanciar modelo na hora para garantir que usa a seleção atual
            model = genai.GenerativeModel(nome_modelo)
            
            # Construir prompt com os arquivos e a pergunta
            # Usar estrutura explícita de Parts para evitar erros de serialização
            parts = []
            
            for file_obj in self.documentos_uploaded:
                parts.append({
                    "file_data": {
                        "mime_type": file_obj.mime_type,
                        "file_uri": file_obj.uri
                    }
                })
            
            parts.append({"text": pergunta})
            
            conteudo = parts # O SDK aceita uma lista de Parts diretamente como conteúdo do usuário
            
            # Gerar resposta
            try:
                print(f"DEBUG: Enviando {len(parts)} partes (arquivos+texto).")
                # Debug do primeiro arquivo
                if self.documentos_uploaded:
                    f = self.documentos_uploaded[0]
                    print(f"DEBUG: Exemplo de arquivo: {f.name} ({f.mime_type}) -> {f.uri}")

                response = model.generate_content(conteudo)
                resposta_texto = response.text
            except Exception as e:
                print(f"Erro na geração direta: {e}")
                
                # Tratamento específico para modelos que não suportam arquivos ou erro 400
                if "400" in str(e) or "INVALID_ARGUMENT" in str(e):
                    self.atualizar_status("Erro com arquivos. Tentando apenas texto...")
                    print("Tentando fallback para modo texto (sem arquivos)...")
                    
                    try:
                        # Fallback: Tenta enviar apenas a pergunta (sem contexto dos arquivos)
                        # Isso serve para validar se o modelo está funcionando pelo menos para texto
                        response_fallback = model.generate_content(pergunta)
                        resposta_texto = f"⚠️ **Aviso**: Não foi possível ler os arquivos com o modelo {nome_modelo}. Abaixo está a resposta baseada apenas no seu conhecimento prévio (sem os documentos):\n\n{response_fallback.text}"
                    except Exception as e_fallback:
                        # Se falhar até com texto, então o erro é grave
                        raise Exception(f"Erro fatal com modelo {nome_modelo}. Falhou com arquivos e com texto.\nErro original: {e}\nErro fallback: {e_fallback}")
                else:
                    raise e
            
            # Adicionar ao histórico
            self.root.after(0, self._adicionar_historico, pergunta, resposta_texto)
            self.atualizar_status("Resposta gerada com sucesso!")
            
        except Exception as e:
            self.atualizar_status(f"Erro: {str(e)}")
            self.root.after(0, messagebox.showerror, "Erro", f"Erro ao processar pergunta com {nome_modelo}:\n\n{str(e)}")
            
    def listar_modelos(self):
        """Lista modelos disponíveis na API"""
        key = self.api_key_var.get().strip()
        if not key:
            messagebox.showwarning("Aviso", "Configure a API Key primeiro!")
            return
            
        try:
            genai.configure(api_key=key)
            modelos = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    modelos.append(m.name.replace('models/', ''))
            
            msg = "Modelos disponíveis para sua Key:\n\n" + "\n".join(modelos)
            messagebox.showinfo("Modelos Disponíveis", msg)
            
            # Atualizar combobox se houver modelos
            if modelos:
                # Encontrar o widget combobox
                for widget in self.root.winfo_children():
                    if isinstance(widget, ttk.LabelFrame) and "Configuração" in widget.cget("text"):
                        for child in widget.winfo_children():
                            if isinstance(child, ttk.Combobox):
                                child['values'] = modelos
                                break
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao listar modelos: {e}")

    def listar_arquivos_nuvem(self):
        """Lista todos os arquivos presentes no projeto do Google"""
        key = self.api_key_var.get().strip()
        if not key:
            messagebox.showwarning("Aviso", "Configure a API Key primeiro!")
            return
            
        try:
            genai.configure(api_key=key)
            self.atualizar_status("Listando arquivos na nuvem...")
            
            # Criar janela de listagem
            top = tk.Toplevel(self.root)
            top.title("☁️ Arquivos no Google Cloud (File API)")
            top.geometry("800x500")
            
            # Treeview para listar
            cols = ("Display Name", "ID (Name)", "MIME Type", "Size", "State", "Created")
            tree = ttk.Treeview(top, columns=cols, show='headings')
            
            for col in cols:
                tree.heading(col, text=col)
                tree.column(col, width=100)
            tree.column("Display Name", width=200)
            tree.column("ID (Name)", width=150)
            
            tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Scrollbar
            sb = ttk.Scrollbar(top, orient=tk.VERTICAL, command=tree.yview)
            sb.pack(side=tk.RIGHT, fill=tk.Y)
            tree.configure(yscrollcommand=sb.set)
            
            count = 0
            for f in genai.list_files():
                # Converter bytes para KB/MB
                size_str = f"{f.size_bytes} B"
                if f.size_bytes > 1024*1024:
                    size_str = f"{f.size_bytes/(1024*1024):.2f} MB"
                elif f.size_bytes > 1024:
                    size_str = f"{f.size_bytes/1024:.2f} KB"
                    
                tree.insert("", tk.END, values=(
                    f.display_name,
                    f.name,
                    f.mime_type,
                    size_str,
                    f.state.name,
                    f.create_time.strftime('%Y-%m-%d %H:%M') if f.create_time else "-"
                ))
                count += 1
                
            self.atualizar_status(f"Listagem concluída: {count} arquivos encontrados.")
            
            # Botão para fechar
            ttk.Button(top, text="Fechar", command=top.destroy).pack(pady=5)
            
            # Botão para copiar ID
            def copiar_id():
                sel = tree.selection()
                if sel:
                    item = tree.item(sel[0])
                    file_id = item['values'][1]
                    self.root.clipboard_clear()
                    self.root.clipboard_append(file_id)
                    messagebox.showinfo("Copiado", f"ID {file_id} copiado!")
            
            ttk.Button(top, text="Copiar ID Selecionado", command=copiar_id).pack(pady=5)
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao listar arquivos: {e}")
            self.atualizar_status("Erro ao listar arquivos.")
            
    def _adicionar_historico(self, pergunta, resposta):
        """Adiciona resposta ao histórico"""
        # Separador
        if self.historico:
            self.texto_respostas.insert(tk.END, "\n" + "="*80 + "\n\n", "separador")
        
        # Pergunta
        self.texto_respostas.insert(tk.END, f"❓ Pergunta: ", "pergunta")
        self.texto_respostas.insert(tk.END, f"{pergunta}\n\n")
        
        # Resposta
        self.texto_respostas.insert(tk.END, f"💡 Resposta:\n", "resposta")
        self.texto_respostas.insert(tk.END, f"{resposta}\n\n")
        
        # Scroll para o final
        self.texto_respostas.see(tk.END)
        
        # Salvar no histórico
        self.historico.append({
            'pergunta': pergunta,
            'resposta': resposta
        })
        
    def limpar_historico(self):
        """Limpa o histórico de conversas"""
        if messagebox.askyesno("Confirmar", "Deseja limpar todo o histórico?"):
            self.texto_respostas.delete(1.0, tk.END)
            self.historico = []
            
    def atualizar_status(self, texto):
        """Atualiza a barra de status"""
        self.root.after(0, self.status_bar.config, {'text': texto})

def main():
    root = tk.Tk()
    app = RAGInterface(root)
    root.mainloop()

if __name__ == "__main__":
    main()
