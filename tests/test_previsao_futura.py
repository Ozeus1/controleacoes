import unittest
import sys
import os
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

# Adicionar diretório pai ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from models import User, Despesa, MeioPagamento, FechamentoCartao, CategoriaDespesa

class TestPrevisaoFutura(unittest.TestCase):
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
        
        # Configurar fechamento (dia 10, vence dia 20)
        self.fechamento = FechamentoCartao(
            meio_pagamento_id=self.cartao.id,
            dia_fechamento=10,
            dia_vencimento=20
        )
        db.session.add(self.fechamento)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_projecao_parcelas(self):
        # Criar despesa parcelada em 5x de R$ 100,00
        # Primeira parcela vence em 20/12/2023
        
        valor_parcela = 100.0
        data_base = date(2023, 12, 20) # Vencimento da 1ª parcela
        
        for i in range(5):
            d = Despesa(
                descricao=f'Compra Parcelada {i+1}/5',
                valor=valor_parcela,
                data_pagamento=data_base + relativedelta(months=i),
                categoria_id=self.categoria.id,
                meio_pagamento_id=self.cartao.id,
                user_id=self.user.id
            )
            db.session.add(d)
        db.session.commit()
        
        # Testar a query para o mês de Dezembro/2023
        # A lógica agora é simples: soma das despesas onde month=12 e year=2023
        
        from sqlalchemy import extract, func
        
        total_dez = db.session.query(func.sum(Despesa.valor)).filter(
            Despesa.meio_pagamento_id == self.cartao.id,
            extract('month', Despesa.data_pagamento) == 12,
            extract('year', Despesa.data_pagamento) == 2023
        ).scalar() or 0
        
        print(f"Total Dezembro: {total_dez}")
        self.assertEqual(total_dez, 100.0, "Deve encontrar a 1ª parcela em Dezembro")
        
        # Testar a query para o mês de Janeiro/2024
        total_jan = db.session.query(func.sum(Despesa.valor)).filter(
            Despesa.meio_pagamento_id == self.cartao.id,
            extract('month', Despesa.data_pagamento) == 1,
            extract('year', Despesa.data_pagamento) == 2024
        ).scalar() or 0
        
        print(f"Total Janeiro: {total_jan}")
        self.assertEqual(total_jan, 100.0, "Deve encontrar a 2ª parcela em Janeiro")
        
        # Testar mês sem parcela (Novembro/2023)
        total_nov = db.session.query(func.sum(Despesa.valor)).filter(
            Despesa.meio_pagamento_id == self.cartao.id,
            extract('month', Despesa.data_pagamento) == 11,
            extract('year', Despesa.data_pagamento) == 2023
        ).scalar() or 0
        
        self.assertEqual(total_nov, 0.0, "Não deve haver parcela em Novembro")

if __name__ == '__main__':
    unittest.main()
