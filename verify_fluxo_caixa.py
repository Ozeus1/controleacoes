import sys
import os
from flask import url_for

# Adicionar diretório atual ao path
sys.path.append(os.getcwd())

from app import create_app, db
from models import User, BalancoMensal, EventoCaixaAvulso

def verify():
    print("Iniciando verificação do Fluxo de Caixa...")
    
    # Usar configuração de teste
    app = create_app('testing')
    
    with app.app_context():
        # Criar tabelas
        db.create_all()
        print("Banco de dados em memória criado.")
        
        # Criar usuário
        user = User(username='test_user', email='test@example.com', nivel_acesso='admin')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        print(f"Usuário criado: {user.username}")
        
        # Cliente de teste
        client = app.test_client()
        
        # Login
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            sess['_fresh'] = True
        print("Login simulado realizado.")
        
        # 1. Testar acesso à página principal
        response = client.get('/fluxo-caixa/')
        if response.status_code == 200:
            print("✅ Rota /fluxo-caixa/ acessada com sucesso (200 OK)")
        else:
            print(f"❌ Falha ao acessar /fluxo-caixa/: {response.status_code}")
            return
            
        # 2. Testar criação de evento
        print("Testando criação de evento...")
        response = client.post('/fluxo-caixa/eventos', data={
            'data': '2023-11-23',
            'descricao': 'Pagamento Teste',
            'valor': '123.45'
        }, follow_redirects=True)
        
        if response.status_code == 200 and b'Evento registrado com sucesso' in response.data:
            print("✅ Evento criado com sucesso via POST")
        else:
            print(f"❌ Falha ao criar evento. Status: {response.status_code}")
            
        # Verificar no banco
        evento = EventoCaixaAvulso.query.first()
        if evento and evento.valor == 123.45:
            print(f"✅ Evento verificado no banco: {evento.descricao} - R$ {evento.valor}")
        else:
            print("❌ Evento não encontrado no banco de dados")
            
        # 3. Testar criação de balanço
        print("Testando criação de balanço...")
        response = client.post('/fluxo-caixa/balanco/salvar', data={
            'ano': '2023',
            'mes': '11',
            'total_entradas': '5000.00',
            'total_saidas': '2000.00',
            'observacoes': 'Balanço de Teste'
        }, follow_redirects=True)
        
        if response.status_code == 200 and b'criado com sucesso' in response.data:
            print("✅ Balanço criado com sucesso via POST")
        else:
            print(f"❌ Falha ao criar balanço. Status: {response.status_code}")
            
        # Verificar no banco
        balanco = BalancoMensal.query.first()
        if balanco and balanco.saldo_mes == 3000.00:
            print(f"✅ Balanço verificado no banco: Saldo R$ {balanco.saldo_mes}")
        else:
            print("❌ Balanço não encontrado ou incorreto no banco")

if __name__ == "__main__":
    try:
        verify()
        print("\nVerificação concluída!")
    except Exception as e:
        print(f"\n❌ Erro fatal durante verificação: {e}")
