"""
Script de teste RAG (Retrieval-Augmented Generation) com Google GenAI
Permite fazer perguntas sobre documentos usando IA
"""
import time
import os
from google import genai
from google.genai import types

# ========================================
# CONFIGURAÇÃO - ALTERE ESTES VALORES:
# ========================================

# 1. Configurar a API Key
# Opção A: Definir como variável de ambiente (RECOMENDADO)
# No PowerShell: $env:GOOGLE_API_KEY = "sua-chave-aqui"
# OU
# Opção B: Definir diretamente aqui (NÃO RECOMENDADO para produção)
# os.environ['GOOGLE_API_KEY'] = 'SUA_CHAVE_API_AQUI'

# 2. Caminho do documento para indexar
DOCUMENT_PATH = 'path/to/your/document.pdf'  # ← ALTERE AQUI

# 3. Pergunta que você quer fazer sobre o documento
QUERY = 'O que o documento diz sobre...'  # ← ALTERE AQUI

# ========================================

def main():
    # Verificar se a API key está configurada
    if not os.getenv('GOOGLE_API_KEY'):
        print("❌ ERRO: API Key não configurada!")
        print("\n📝 Como configurar:")
        print("1. No PowerShell, execute:")
        print('   $env:GOOGLE_API_KEY = "sua-chave-aqui"')
        print("\n2. Ou edite este arquivo e descomente a linha:")
        print("   os.environ['GOOGLE_API_KEY'] = 'SUA_CHAVE_API_AQUI'")
        print("\n💡 Para obter uma API key: https://aistudio.google.com/apikey")
        return
    
    # Verificar se o arquivo existe
    if not os.path.exists(DOCUMENT_PATH):
        print(f"❌ ERRO: Arquivo não encontrado: {DOCUMENT_PATH}")
        print("\n📝 Edite a variável DOCUMENT_PATH no início do script")
        return
    
    try:
        print("🚀 Iniciando RAG com Google GenAI...\n")
        
        # Criar cliente
        client = genai.Client()
        
        # Criar file search store
        print("📦 Criando file search store...")
        store = client.file_search_stores.create()
        print(f"✓ Store criado: {store.name}\n")
        
        # Upload do documento
        print(f"📤 Fazendo upload do documento: {DOCUMENT_PATH}")
        upload_op = client.file_search_stores.upload_to_file_search_store(
            file_search_store_name=store.name,
            file=DOCUMENT_PATH
        )
        
        # Aguardar conclusão do upload
        while not upload_op.done:
            print("⏳ Aguardando processamento...")
            time.sleep(5)
            upload_op = client.operations.get(upload_op)
        
        print("✓ Upload concluído!\n")
        
        # Fazer a query usando o documento como contexto
        print(f"🔍 Processando query: '{QUERY}'")
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',  # ou 'gemini-1.5-pro'
            contents=QUERY,
            config=types.GenerateContentConfig(
                tools=[types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=[store.name]
                    )
                )]
            )
        )
        
        # Exibir resposta
        print("\n" + "="*70)
        print("📄 RESPOSTA:")
        print("="*70)
        print(response.text)
        print("="*70)
        
        # Exibir fontes de fundamentação
        grounding = response.candidates[0].grounding_metadata
        if not grounding:
            print('\n⚠️ Nenhuma fonte de fundamentação encontrada')
        else:
            sources = {c.retrieved_context.title for c in grounding.grounding_chunks}
            print(f'\n📚 Fontes utilizadas: {", ".join(sources)}')
        
        print("\n✅ Processo concluído com sucesso!")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
