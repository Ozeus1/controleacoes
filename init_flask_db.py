"""
Script para inicializar o banco de dados Flask
Cria todas as tabelas necessárias
"""
from app import create_app
from models import db, populate_db

app = create_app('development')

try:
    print(f"Tentando conectar ao banco de dados: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print("Criando tabelas e populando dados...")
    
    populate_db(app)
    
    with app.app_context():
        # Verificar que foram criadas
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tabelas = inspector.get_table_names()
        
        print(f"\n📋 Tabelas criadas ({len(tabelas)}):")
        for tabela in tabelas:
            print(f"  - {tabela}")
        
        print("\n✓ Banco Flask inicializado!")

except UnicodeDecodeError:
    print("\n❌ ERRO DE CONEXÃO (Codificação):")
    print("Ocorreu um erro ao tentar conectar ao banco de dados e a mensagem de erro contém caracteres que não puderam ser lidos.")
    print("Isso geralmente indica FALHA DE AUTENTICAÇÃO (Senha incorreta) ou BANCO INEXISTENTE.")
    print("Verifique no arquivo .env:")
    print("1. Se a senha do usuário 'postgres' está correta na DATABASE_URL")
    print("2. Se o nome do banco de dados está correto")
    
except Exception as e:
    print(f"\n❌ ERRO AO INICIALIZAR BANCO:")
    print(str(e))
    print("\nVerifique se o servidor PostgreSQL está rodando e se as credenciais no .env estão corretas.")
