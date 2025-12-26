import sys
import os
from flask import url_for

# Adicionar diretório atual ao path
sys.path.append(os.getcwd())

from app import create_app, db
from models import User

def verify_route():
    print("Iniciando verificação da rota de Previsão de Cartões...")
    
    # Usar configuração de teste
    app = create_app('testing')
    
    with app.app_context():
        # Criar tabelas
        db.create_all()
        
        # Criar usuário gerente
        user = User(username='manager_user', email='manager@example.com', nivel_acesso='gerente')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        
        # Cliente de teste
        client = app.test_client()
        
        # Login
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            sess['_fresh'] = True
        
        # Acessar a rota
        print("Acessando /relatorios/previsao-cartoes...")
        try:
            response = client.get('/relatorios/previsao-cartoes')
            if response.status_code == 200:
                print("✅ Rota acessada com sucesso (200 OK)")
            else:
                print(f"❌ Falha ao acessar rota: {response.status_code}")
                print(response.data.decode('utf-8'))
        except Exception as e:
            print(f"❌ Erro ao acessar rota: {e}")

if __name__ == "__main__":
    verify_route()
