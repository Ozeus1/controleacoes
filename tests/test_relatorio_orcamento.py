import unittest
import sys
import os
from datetime import date

# Adicionar diretório pai ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from models import User, Despesa, CategoriaDespesa, Orcamento

class TestRelatorioOrcamento(unittest.TestCase):
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
        db.session.commit()
        
        # Criar orçamento (GERAL, sem mês/ano)
        self.orcamento = Orcamento(
            categoria_id=self.categoria.id,
            user_id=self.user.id,
            valor_orcado=1000.0
        )
        db.session.add(self.orcamento)
        
        # Criar despesa
        self.despesa = Despesa(
            descricao='Gasto Teste',
            valor=200.0,
            data_pagamento=date(2023, 11, 15),
            categoria_id=self.categoria.id,
            meio_pagamento_id=1, # Mock
            user_id=self.user.id
        )
        db.session.add(self.despesa)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_relatorio_orcado_vs_gasto_erro(self):
        # Simular a query da rota que está errada
        mes = 11
        ano = 2023
        
        print("Tentando buscar orçamentos com filtro de mês/ano (deve falhar)...")
        try:
            # Esta query deve falhar porque Orcamento não tem mes/ano
            orcamentos = Orcamento.query.filter_by(mes=mes, ano=ano, user_id=self.user.id).all()
            print("❌ Query passou (inesperado se o modelo estiver correto)")
        except Exception as e:
            print(f"✅ Erro esperado capturado: {e}")
            
        # Simular a query CORRETA
        print("Tentando buscar orçamentos corretamente...")
        try:
            # Buscar todos os orçamentos do usuário (pois são gerais)
            orcamentos = Orcamento.query.filter_by(user_id=self.user.id).all()
            print(f"✅ Query correta retornou {len(orcamentos)} orçamentos")
            self.assertEqual(len(orcamentos), 1)
            self.assertEqual(orcamentos[0].valor_orcado, 1000.0)
        except Exception as e:
            print(f"❌ Erro na query correta: {e}")
            self.fail(f"Erro na query correta: {e}")

if __name__ == '__main__':
    unittest.main()
