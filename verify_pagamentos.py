from app import create_app, db
from models import User, Despesa, CategoriaDespesa, MeioPagamento, Receita
from datetime import date
from sqlalchemy import func, extract

def verify():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        
        # Setup data
        user = User(username='test_pag', email='pag@test.com', nivel_acesso='admin')
        user.set_password('123')
        db.session.add(user)
        
        cat_pag = CategoriaDespesa(nome='Pagamentos', ativo=True)
        cat_outra = CategoriaDespesa(nome='Outra', ativo=True)
        db.session.add_all([cat_pag, cat_outra])
        
        # Meio Dinheiro
        meio_dinheiro = MeioPagamento.query.filter_by(nome='Dinheiro').first()
        if not meio_dinheiro:
            meio_dinheiro = MeioPagamento(nome='Dinheiro', tipo='dinheiro', ativo=True)
            db.session.add(meio_dinheiro)
        
        # Meio Cartão (Non-Cash)
        meio_cartao = MeioPagamento.query.filter_by(nome='Cartão Teste').first()
        if not meio_cartao:
            meio_cartao = MeioPagamento(nome='Cartão Teste', tipo='cartao', ativo=True)
            db.session.add(meio_cartao)
            
        db.session.commit()
        
        # Create expenses
        # 1. Expense in 'Pagamentos' with Cartão (Should be IN Fluxo, OUT Relatorios)
        d1 = Despesa(
            descricao='Pgto Fatura',
            valor=1000.0,
            data_pagamento=date(2024, 5, 15),
            categoria_id=cat_pag.id,
            meio_pagamento_id=meio_cartao.id,
            user_id=user.id
        )
        
        # 2. Expense in 'Outra' with Dinheiro (Should be IN Fluxo, IN Relatorios)
        d2 = Despesa(
            descricao='Compra Normal',
            valor=500.0,
            data_pagamento=date(2024, 5, 15),
            categoria_id=cat_outra.id,
            meio_pagamento_id=meio_dinheiro.id,
            user_id=user.id
        )
        
        db.session.add_all([d1, d2])
        db.session.commit()
        
        print("--- Verification ---")
        
        # Check Relatorios (Balanco) - Should EXCLUDE Pagamentos
        total_relatorio = db.session.query(func.sum(Despesa.valor)).join(CategoriaDespesa).filter(
            extract('month', Despesa.data_pagamento) == 5,
            extract('year', Despesa.data_pagamento) == 2024,
            Despesa.user_id == user.id,
            func.lower(CategoriaDespesa.nome) != 'pagamentos'
        ).scalar()
        
        print(f"Total Relatório (New Logic): {total_relatorio}")
        print(f"Expected Relatório: 500.0 (Only 'Outra')")
        
        # Check Fluxo de Caixa - Should INCLUDE Pagamentos
        from sqlalchemy import or_
        MEIOS_PAGAMENTO_CAIXA = ['Boleto', 'Dinheiro', 'PIX', 'Transferência', 'Débito em Conta']
        total_fluxo = db.session.query(func.sum(Despesa.valor)).join(MeioPagamento).join(CategoriaDespesa).filter(
            extract('month', Despesa.data_pagamento) == 5,
            extract('year', Despesa.data_pagamento) == 2024,
            Despesa.user_id == user.id,
            or_(
                func.lower(MeioPagamento.nome).in_([m.lower() for m in MEIOS_PAGAMENTO_CAIXA]),
                func.lower(CategoriaDespesa.nome) == 'pagamentos'
            )
        ).scalar()
        
        print(f"Total Fluxo de Caixa (New Logic): {total_fluxo}")
        print(f"Expected Fluxo de Caixa: 1500.0 (Both)")

if __name__ == "__main__":
    verify()
