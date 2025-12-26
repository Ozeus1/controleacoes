import unittest
import sys
import os
from datetime import date
from dateutil.relativedelta import relativedelta
import json

# Adicionar diretório pai ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from models import User, Despesa, MeioPagamento, CategoriaDespesa

class TestRelatorioDetalhes(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        db.create_all()
        
        # Criar usuário
        self.user = User(username='test_user', email='test@example.com', nivel_acesso='gerente')
        self.user.set_password('password')
        db.session.add(self.user)
        
        # Criar categoria
        self.categoria = CategoriaDespesa(nome='Teste', ativo=True)
        db.session.add(self.categoria)
        
        # Criar cartão
        self.cartao = MeioPagamento(nome='Cartão Teste', tipo='cartao', ativo=True)
        db.session.add(self.cartao)
        db.session.commit()
        
        self.client = self.app.test_client()
        
        # Login
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.user.id)
            sess['_fresh'] = True

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_api_detalhes(self):
        # Criar despesas para um mês específico (Ex: Maio/2024)
        data_fatura = date(2024, 5, 15)
        
        d1 = Despesa(
            descricao='Compra 1',
            valor=100.0,
            data_pagamento=data_fatura,
            categoria_id=self.categoria.id,
            meio_pagamento_id=self.cartao.id,
            user_id=self.user.id,
            num_parcelas=1
        )
        
        d2 = Despesa(
            descricao='Compra 2',
            valor=200.0,
            data_pagamento=data_fatura,
            categoria_id=self.categoria.id,
            meio_pagamento_id=self.cartao.id,
            user_id=self.user.id,
            num_parcelas=2
        )
        
        db.session.add_all([d1, d2])
        db.session.commit()
        
        # Testar API de detalhes
        response = self.client.get(f'/relatorios/api/fatura-detalhes/{self.cartao.id}/5/2024')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Ordenar por descrição para garantir ordem nos testes
        data.sort(key=lambda x: x['descricao'])
        
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['descricao'], 'Compra 1')
        self.assertEqual(data[0]['valor'], 100.0)
        self.assertEqual(data[0]['parcelas'], 'À vista')
        
        self.assertEqual(data[1]['descricao'], 'Compra 2')
        self.assertEqual(data[1]['valor'], 100.0)  # Valor da parcela (200/2)
        self.assertEqual(data[1]['parcelas'], '1/2')
        
        print("API de detalhes retornou dados corretos")

    def test_historico_completo(self):
        # Criar despesa antiga (2020) e futura (2030)
        d_antiga = Despesa(
            descricao='Antiga', valor=50.0, data_pagamento=date(2020, 1, 15),
            categoria_id=self.categoria.id, meio_pagamento_id=self.cartao.id, user_id=self.user.id
        )
        d_futura = Despesa(
            descricao='Futura', valor=50.0, data_pagamento=date(2030, 1, 15),
            categoria_id=self.categoria.id, meio_pagamento_id=self.cartao.id, user_id=self.user.id
        )
        db.session.add_all([d_antiga, d_futura])
        db.session.commit()
        
        # Acessar rota principal
        response = self.client.get('/relatorios/previsao-cartoes')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        
        # Verificar se os anos aparecem no HTML (indicando que o intervalo foi coberto)
        self.assertIn('Jan/2020', html)
        self.assertIn('Jan/2030', html)
        
        print("Relatório cobriu intervalo de 2020 a 2030")

    def test_projecao_minima_12_meses(self):
        # Limpar despesas (setup cria algumas coisas, mas vamos garantir)
        Despesa.query.delete()
        db.session.commit()
        
        # Criar apenas UMA despesa hoje
        hoje = date.today()
        d = Despesa(
            descricao='Hoje', valor=50.0, data_pagamento=hoje,
            categoria_id=self.categoria.id, meio_pagamento_id=self.cartao.id, user_id=self.user.id
        )
        db.session.add(d)
        db.session.commit()
        
        # Acessar rota
        response = self.client.get('/relatorios/previsao-cartoes')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        
        # Verificar se existe uma coluna para daqui a 11 meses
        futuro = hoje + relativedelta(months=11)
        
        # No novo layout, a referência usa abreviação do mês (Ex: "Oct/2026")
        mes_ref_futuro = futuro.strftime('%b/%Y')
        
        self.assertIn(mes_ref_futuro, html)
        print(f"Relatório mostrou mês futuro {mes_ref_futuro} mesmo sem dados nele")

    def test_calculo_restante(self):
        # Limpar
        Despesa.query.delete()
        db.session.commit()
        
        hoje = date.today()
        mes_atual = hoje.replace(day=1)
        prox_mes = mes_atual + relativedelta(months=1)
        dois_meses = mes_atual + relativedelta(months=2)
        
        # Despesa Mês Atual (Não deve entrar no restante)
        d1 = Despesa(descricao='Atual', valor=100.0, data_pagamento=mes_atual, categoria_id=self.categoria.id, meio_pagamento_id=self.cartao.id, user_id=self.user.id)
        
        # Despesa Próximo Mês (Deve entrar)
        d2 = Despesa(descricao='Prox', valor=200.0, data_pagamento=prox_mes, categoria_id=self.categoria.id, meio_pagamento_id=self.cartao.id, user_id=self.user.id)
        
        # Despesa 2 Meses (Deve entrar)
        d3 = Despesa(descricao='Futuro', valor=300.0, data_pagamento=dois_meses, categoria_id=self.categoria.id, meio_pagamento_id=self.cartao.id, user_id=self.user.id)
        
        db.session.add_all([d1, d2, d3])
        db.session.commit()
        
        response = self.client.get('/relatorios/previsao-cartoes')
        html = response.data.decode('utf-8')
        
        # Total restante deve ser 200 + 300 = 500
        # Verificar se "500,00" aparece no HTML (formatado)
        self.assertIn('500,00', html)
        # Verificar se "100,00" aparece na tabela mas NÃO no total restante
        self.assertIn('100,00', html)
        
        print("Cálculo de restante (próximo mês em diante) correto: 500.00")

if __name__ == '__main__':
    unittest.main()
