import psycopg2
import os
from dotenv import load_dotenv
import sys

# Tentar definir codificação do cliente antes de conectar
os.environ["PGCLIENTENCODING"] = "latin1"

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

load_dotenv()

# Pegar URL original
original_url = os.environ.get('DATABASE_URL')
print(f"URL Original: {original_url}")

# Criar URL para conectar no banco 'postgres' (padrão)
from urllib.parse import urlparse, urlunparse
parsed = urlparse(original_url)
# Substituir o path (nome do banco) por 'postgres'
postgres_url = parsed._replace(path='/postgres').geturl()

print(f"Tentando conectar no banco 'postgres' para testar autenticação...")
print(f"URL: {postgres_url}")

try:
    conn = psycopg2.connect(postgres_url)
    print("✅ Conexão com banco 'postgres' BEM SUCEDIDA!")
    print("Isso significa que usuário e senha estão corretos.")
    conn.close()
    
    # Se funcionou, tentar o banco original
    print(f"\nAgora tentando conectar no banco original: {parsed.path[1:]}")
    try:
        conn = psycopg2.connect(original_url)
        print(f"✅ Conexão com banco '{parsed.path[1:]}' BEM SUCEDIDA!")
        conn.close()
    except Exception as e:
        print(f"❌ Falha ao conectar no banco '{parsed.path[1:]}':")
        print(e)
        print("\nProvavelmente o banco de dados não existe.")
        
except UnicodeDecodeError as e:
    print(f"❌ Erro de Unicode (Provável erro de senha/autenticação em Português): {e}")
except Exception as e:
    print(f"❌ Erro ao conectar no 'postgres': {e}")
