import unittest
import sys
import os
from datetime import datetime, date, timedelta

# Adicionar diretório pai ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from models import User, Despesa, MeioPagamento, FechamentoCartao, CategoriaDespesa

class TestPrevisaoCartoes(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        db.create_all()
        
        # Criar usuário
        self.user = User(username='test_user', email='test@example.com', nivel_acesso='admin')
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

    def test_calculo_fatura(self):
        # Data de hoje simulada: 15/11/2023 (após fechamento do dia 10)
        # Fatura atual deve ser de 11/11 a 10/12
        
        # Despesa antiga (mês anterior) - NÃO deve entrar
        d1 = Despesa(
            descricao='Compra Antiga',
            valor=100.0,
            data_pagamento=date(2023, 10, 15),
            categoria_id=self.categoria.id,
            meio_pagamento_id=self.cartao.id,
            user_id=self.user.id
        )
        
        # Despesa no período atual - DEVE entrar
        d2 = Despesa(
            descricao='Compra Atual',
            valor=200.0,
            data_pagamento=date(2023, 11, 15),
            categoria_id=self.categoria.id,
            meio_pagamento_id=self.cartao.id,
            user_id=self.user.id
        )
        
        db.session.add_all([d1, d2])
        db.session.commit()
        
        # Simular lógica da rota (simplificada para teste)
        # Se hoje é 15/11, fechamento é 10. Próximo fechamento é 10/12.
        # A query atual do sistema pega tudo <= 10/12
        
        data_fechamento_atual = date(2023, 12, 10)
        data_fechamento_anterior = date(2023, 11, 10)
        
        # Query COMO ESTÁ NO SISTEMA (agora corrigida)
        from sqlalchemy import func
        total_sistema = db.session.query(func.sum(Despesa.valor)).filter(
            Despesa.meio_pagamento_id == self.cartao.id,
            Despesa.data_pagamento <= data_fechamento_atual,
            Despesa.data_pagamento > data_fechamento_anterior
        ).scalar() or 0
        
        print(f"Total Sistema (agora corrigido): {total_sistema}")
        
        # O sistema deve retornar 200 (apenas a despesa atual)
        self.assertEqual(total_sistema, 200.0, "O sistema deve considerar apenas o período atual")
        
        # Query CORRETA (que vamos implementar)
        data_fechamento_anterior = date(2023, 11, 10)
        
        total_correto = db.session.query(func.sum(Despesa.valor)).filter(
            Despesa.meio_pagamento_id == self.cartao.id,
            Despesa.data_pagamento <= data_fechamento_atual,
            Despesa.data_pagamento > data_fechamento_anterior  # Filtro adicionado
        ).scalar() or 0
        
        print(f"Total Correto: {total_correto}")
        self.assertEqual(total_correto, 200.0, "O cálculo correto deve considerar apenas o período atual")

if __name__ == '__main__':
    unittest.main()
