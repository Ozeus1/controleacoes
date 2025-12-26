import unittest
import sys
import os

# Adicionar diretório pai ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from models import User, BalancoMensal, EventoCaixaAvulso
from flask_login import login_user

class TestFluxoCaixa(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        
        # Configurar banco de dados de teste
        db.create_all()
        
        # Criar usuário de teste
        self.user = User(username='test_user', email='test@example.com', nivel_acesso='admin')
        self.user.set_password('password')
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login(self):
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.user.id)
            sess['_fresh'] = True

    def test_index_route(self):
        self.login()
        response = self.client.get('/fluxo-caixa/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Fluxo de Caixa', response.data)

    def test_criar_evento(self):
        self.login()
        response = self.client.post('/fluxo-caixa/eventos', data={
            'data': '2023-10-25',
            'descricao': 'Teste Evento',
            'valor': '150.00'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Evento registrado com sucesso!', response.data)
        
        # Verificar no banco
        evento = EventoCaixaAvulso.query.first()
        self.assertIsNotNone(evento)
        self.assertEqual(evento.descricao, 'Teste Evento')
        self.assertEqual(evento.valor, 150.00)

    def test_criar_balanco(self):
        self.login()
        response = self.client.post('/fluxo-caixa/balanco/salvar', data={
            'ano': '2023',
            'mes': '10',
            'total_entradas': '1000.00',
            'total_saidas': '500.00',
            'observacoes': 'Teste Balanco'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Balan\xc3\xa7o criado com sucesso!', response.data.decode('utf-8').encode('utf-8'))
        
        # Verificar no banco
        balanco = BalancoMensal.query.first()
        self.assertIsNotNone(balanco)
        self.assertEqual(balanco.saldo_mes, 500.00)

if __name__ == '__main__':
    unittest.main()
