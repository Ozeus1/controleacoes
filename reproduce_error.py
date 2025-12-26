from app import create_app, db
from models import User, Despesa, CategoriaDespesa, MeioPagamento
from datetime import date
from sqlalchemy import func, extract, or_, and_

def reproduce():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        
        # Setup data
        user = User.query.filter_by(email='error@test.com').first()
        if not user:
            user = User(username='test_error', email='error@test.com', nivel_acesso='admin')
            user.set_password('123')
            db.session.add(user)
        
        cat_pag = CategoriaDespesa.query.filter_by(nome='Pagamentos').first()
        if not cat_pag:
            cat_pag = CategoriaDespesa(nome='Pagamentos', ativo=True)
            db.session.add(cat_pag)

        cat_outra = CategoriaDespesa.query.filter_by(nome='Outra').first()
        if not cat_outra:
            cat_outra = CategoriaDespesa(nome='Outra', ativo=True)
            db.session.add(cat_outra)
        
        meio_cartao = MeioPagamento.query.filter_by(nome='Cartão Teste').first()
        if not meio_cartao:
            meio_cartao = MeioPagamento(nome='Cartão Teste', tipo='cartao', ativo=True)
            db.session.add(meio_cartao)
            
        meio_dinheiro = MeioPagamento.query.filter_by(nome='Dinheiro').first()
        if not meio_dinheiro:
            meio_dinheiro = MeioPagamento(nome='Dinheiro', tipo='dinheiro', ativo=True)
            db.session.add(meio_dinheiro)
        
        db.session.commit()
        
        # Create expenses
        d1 = Despesa(
            descricao='Pgto Fatura',
            valor=100.0,
            data_pagamento=date(2025, 12, 15),
            categoria_id=cat_pag.id,
            meio_pagamento_id=meio_cartao.id,
            user_id=user.id
        )
        d2 = Despesa(
            descricao='Compra Dinheiro',
            valor=50.0,
            data_pagamento=date(2025, 12, 16),
            categoria_id=cat_outra.id,
            meio_pagamento_id=meio_dinheiro.id,
            user_id=user.id
        )
        db.session.add_all([d1, d2])
        db.session.commit()
        
        print("--- Executing Query ---")
        try:
            MEIOS_PAGAMENTO_CAIXA = ['Boleto', 'Dinheiro', 'PIX', 'Transferência', 'Débito em Conta']
            ano = 2025
            mes = 12
            
            despesas = Despesa.query.join(Despesa.meio_pagamento).join(Despesa.categoria).filter(
                and_(
                    Despesa.user_id == user.id,
                    extract('year', Despesa.data_pagamento) == ano,
                    extract('month', Despesa.data_pagamento) == mes,
                    or_(
                        func.lower(MeioPagamento.nome).in_([m.lower() for m in MEIOS_PAGAMENTO_CAIXA]),
                        func.lower(CategoriaDespesa.nome) == 'pagamentos'
                    )
                )
            ).order_by(Despesa.data_pagamento).all()
            
            print(f"Query success! Found {len(despesas)} items.")
            for d in despesas:
                print(f"- {d.descricao}")
                
        except Exception as e:
            print(f"Query FAILED: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    reproduce()
