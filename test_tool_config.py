import os
from google import genai
from google.genai import types

# Configuração mínima para teste
api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    print("API Key não encontrada")
    exit()

client = genai.Client(api_key=api_key)

try:
    # Tentar criar um objeto Tool e ver se funciona
    print("Tentando criar Tool...")
    
    # Abordagem 1: Como estava antes
    tool1 = types.Tool(
        file_search=types.FileSearch(
            file_search_store_names=["projects/123/locations/us-central1/stores/456"]
        )
    )
    print("Tool 1 criada:", tool1)
    
    # Abordagem 2: Usando dicionário (se suportado)
    # tool2 = {'file_search': {'file_search_store_names': [...]}}
    
except Exception as e:
    print("Erro ao criar Tool:", e)

print("\nTentando listar stores para validar cliente...")
try:
    # Apenas para validar que o cliente funciona
    pager = client.file_search_stores.list()
    print("Listagem funcionou")
except Exception as e:
    print("Erro na listagem:", e)
