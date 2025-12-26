# Test Drill-Down Functionality

import sys
sys.path.insert(0, 'c:/Users/orlei/OneDrive/ProjPython/FINAN')

from app import create_app
from models import db, User, CategoriaDespesa, MeioPagamento, Despesa
from datetime import date

print("=" * 70)
print("Testando funcionalidade de drill-down")
print("=" * 70)

app = create_app('testing')

with app.app_context():
    # Criar tabelas
    db.create_all()
    
    # Criar usuário de teste
    user = User(username='test_user', email='test@example.com', nivel_acesso='gerente')
    user.set_password('test123')
    db.session.add(user)
    
    # Criar categoria e meio de pagamento
    categoria = CategoriaDespesa(nome='Mercado', ativo=True)
    db.session.add(categoria)
    
    meio = MeioPagamento(nome='Dinheiro', tipo='dinheiro', ativo=True)
    db.session.add(meio)
    
    db.session.commit()
    
    # Criar algumas despesas de teste
    despesa1 = Despesa(
        descricao='Compra no supermercado',
        valor=150.00,
        data_pagamento=date(2024, 11, 15),
        categoria_id=categoria.id,
        meio_pagamento_id=meio.id,
        user_id=user.id
    )
    
    despesa2 = Despesa(
        descricao='Feira',
        valor=80.00,
        data_pagamento=date(2024, 11, 20),
        categoria_id=categoria.id,
        meio_pagamento_id=meio.id,
        user_id=user.id
    )
    
    despesa3 = Despesa(
        descricao='Padaria',
        valor=25.50,
        data_pagamento=date(2024, 11, 25),
        categoria_id=categoria.id,
        meio_pagamento_id=meio.id,
        user_id=user.id
    )
    
    db.session.add_all([despesa1, despesa2, despesa3])
    db.session.commit()
    
    print(f"\n✓ Criado usuário: {user.username}")
    print(f"✓ Criada categoria: {categoria.nome}")
    print(f"✓ Criadas 3 despesas de teste para Nov/2024")
    
    # Testar o cliente Flask
    client = app.test_client()
    
    # Fazer login
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True
    
    print("\n" + "=" * 70)
    print("TESTE 1: Acessar página Despesas Mensais")
    print("=" * 70)
    
    response = client.get('/relatorios/despesas-mensal?mes=11&ano=2024')
    if response.status_code == 200:
        print(f"✓ Status code: {response.status_code}")
        html = response.data.decode('utf-8')
        
        # Verificar se tem o link para detalhes
        if 'detalhes-despesas' in html:
            print("✓ Link para detalhes encontrado no HTML")
        else:
            print("✗ ERRO: Link para detalhes NÃO encontrado")
            
        if 'clickable-row' in html:
            print("✓ Classe clickable-row encontrada")
        else:
            print("✗ ERRO: Classe clickable-row NÃO encontrada")
    else:
        print(f"✗ ERRO: Status code: {response.status_code}")
    
    print("\n" + "=" * 70)
    print("TESTE 2: Acessar página detalhes de despesas")
    print("=" * 70)
    
    response = client.get('/relatorios/detalhes-despesas?categoria=Mercado&mes=11&ano=2024')
    if response.status_code == 200:
        print(f"✓ Status code: {response.status_code}")
        html = response.data.decode('utf-8')
        
        # Verificar se mostra as 3 despesas
        if 'Compra no supermercado' in html:
            print("✓ Despesa 1 encontrada")
        if 'Feira' in html:
            print("✓ Despesa 2 encontrada")
        if 'Padaria' in html:
            print("✓ Despesa 3 encontrada")
            
        # Verificar total
        if '255,50' in html or '255.50' in html:
            print("✓ Total correto exibido (R$ 255,50)")
        else:
            print("⚠️  Total pode não estar sendo exibido corretamente")
    else:
        print(f"✗ ERRO: Status code: {response.status_code}")
    
    print("\n" + "=" * 70)
    print("TESTE 3: Acessar página Top Contas")
    print("=" * 70)
    
    response = client.get('/relatorios/top-contas?mes=11&ano=2024')
    if response.status_code == 200:
        print(f"✓ Status code: {response.status_code}")
        html = response.data.decode('utf-8')
        
        # Verificar se tem o link para detalhes
        if 'detalhes-despesas' in html:
            print("✓ Link para detalhes encontrado no HTML")
        else:
            print("✗ ERRO: Link para detalhes NÃO encontrado")
    else:
        print(f"✗ ERRO: Status code: {response.status_code}")
    
    print("\n" + "=" * 70)
    print("✅ TESTES CONCLUÍDOS")
    print("=" * 70)
