import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
# Force Postgres to send messages in Latin-1 (common on Windows/Portuguese)
os.environ["PGCLIENTENCODING"] = "latin1"

from dotenv import load_dotenv
import sys

# Force console encoding
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

# Parse URL manually to get credentials
db_url = os.environ.get('DATABASE_URL')
# Expected format: postgresql://user:pass@host:port/dbname
try:
    # Simple parsing logic (robust enough for standard connection strings)
    from urllib.parse import urlparse
    result = urlparse(db_url)
    username = result.username
    password = result.password
    hostname = result.hostname
    if hostname == 'localhost':
        hostname = '127.0.0.1'
        print("ℹ️ Forçando uso de 127.0.0.1 em vez de localhost")
    
    port = result.port
    dbname = result.path[1:] # remove leading /
    
    print(f"Configuração lida:")
    print(f"User: {username}")
    print(f"Host: {hostname}")
    print(f"Port: {port}")
    print(f"Database Alvo: {dbname}")
    
    # 1. Try connecting using psql.exe found in system
    psql_path = r"C:\Program Files\PostgreSQL\18\bin\psql.exe"
    
    if not os.path.exists(psql_path):
        print(f"❌ psql.exe não encontrado em: {psql_path}")
        # Try to find it dynamically if needed, but for now use the found path
    else:
        print(f"1. Usando psql.exe para verificar conexão...")
        import subprocess
        
        # Set password in env
        env = os.environ.copy()
        env['PGPASSWORD'] = password
        
        # Command to list databases: psql -U user -h host -p port -l
        cmd = [psql_path, '-U', username, '-h', hostname, '-p', str(port), '-l']
        
        try:
            result = subprocess.run(
                cmd, 
                env=env, 
                capture_output=True, 
                text=False # Capture as bytes
            )
            
            # Decode output safely
            stdout = result.stdout.decode('cp850', errors='replace') # Windows console default
            stderr = result.stderr.decode('cp850', errors='replace')
            
            if result.returncode == 0:
                print("✅ Conexão via psql BEM SUCEDIDA!")
                
                # Check if database exists in output
                if dbname in stdout:
                    print(f"✅ Banco '{dbname}' já existe na lista.")
                else:
                    print(f"❌ Banco '{dbname}' NÃO encontrado na lista.")
                    print(f"2. Criando banco '{dbname}' via psql...")
                    
                    create_cmd = [psql_path, '-U', username, '-h', hostname, '-p', str(port), '-c', f'CREATE DATABASE {dbname};']
                    create_result = subprocess.run(create_cmd, env=env, capture_output=True, text=False)
                    
                    if create_result.returncode == 0:
                        print(f"✅ Banco '{dbname}' criado com sucesso!")
                    else:
                        err = create_result.stderr.decode('cp850', errors='replace')
                        print(f"❌ Erro ao criar banco: {err}")
            else:
                print("❌ Falha ao conectar via psql:")
                print(stderr)
                
        except Exception as e:
            print(f"Erro ao executar psql: {e}")

except Exception as e:
    print(f"Erro ao processar URL ou script: {e}")
