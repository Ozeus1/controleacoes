"""
Script para criar dados de teste no banco Flask
"""
from app import create_app
from models import db, User, Despesa
from datetime import datetime, timedelta
import random

app = create_app('development')

with app.app_context():
    # Verificar/Criar usuário admin
    admin = User.query.filter_by(username='admin').first()
    
    if not admin:
        print("Criando usuário admin...")
        admin = User(username='admin', email='admin@example.com')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("✓ Usuário admin criado!")
    else:
        print(f"✓ Usuário admin já existe (ID: {admin.id})")
    
    # Verificar quantas despesas o admin tem
    count_despesas = Despesa.query.filter_by(user_id=admin.id).count()
    print(f"📊 Despesas atuais do admin: {count_despesas}")
    
    if count_despesas == 0:
        print("\n💡 Criando despesas de teste...")
        
        categorias = ['Alimentação', 'Transporte', 'Saúde', 'Lazer', 'Moradia', 'Educação']
        meios = ['Dinheiro', 'Cartão de Crédito', 'Débito', 'PIX']
        descricoes = {
            'Alimentação': ['Supermercado', 'Restaurant', 'Lanchonete', 'Feira'],
            'Transporte': ['Uber', 'Gasolina', 'Estacionamento', 'Pedágio'],
            'Saúde': ['Farmácia', 'Consulta médica', 'Exames'],
            'Lazer': ['Cinema', 'Streaming', 'Livros', 'Jogos'],
            'Moradia': ['Aluguel', 'Condomínio', 'Água', 'Luz', 'Internet'],
            'Educação': ['Curso', 'Livros', 'Material escolar']
        }
        
        # Criar 50 despesas nos últimos 3 meses
        hoje = datetime.now()
        
        for i in range(50):
            # Data aleatória nos últimos 90 dias
            dias_atras = random.randint(0, 90)
            data_despesa = hoje - timedelta(days=dias_atras)
            
            categoria = random.choice(categorias)
            descricao = random.choice(descricoes[categoria])
            meio = random.choice(meios)
            valor = round(random.uniform(10, 500), 2)
            
            despesa = Despesa(
                descricao=descricao,
                valor=valor,
                conta_despesa=categoria,
                meio_pagamento=meio,
                data_registro=data_despesa.date(),
                data_pagamento=data_despesa.date(),
                num_parcelas=1,
                user_id=admin.id
            )
            
            db.session.add(despesa)
        
        db.session.commit()
        print(f"✓ 50 despesas de teste criadas!")
    
    # Resumo final
    print("\n" + "="*60)
    print("RESUMO DO BANCO FLASK")
    print("="*60)
    
    total_users = User.query.count()
    total_despesas = Despesa.query.count()
    total_admin = Despesa.query.filter_by(user_id=admin.id).count()
    
    print(f"👥 Usuários: {total_users}")
    print(f"💰 Total de despesas: {total_despesas}")
    print(f"   - Admin: {total_admin} despesas")
    
    if total_admin > 0:
        soma_admin = db.session.query(db.func.sum(Despesa.valor)).filter_by(user_id=admin.id).scalar()
        print(f"   - Valor total: R$ {soma_admin:.2f}")
    
    print("\n✓ Banco Flask pronto para sincronização!")
    print("="*60)
