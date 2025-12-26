"""
Verifica se o usuário admin existe e testa a senha
"""

from app import create_app
from models import User

app = create_app('development')

with app.app_context():
    # Buscar usuário admin
    admin = User.query.filter_by(username='admin').first()
    
    if admin:
        print("✓ Usuário admin encontrado!")
        print(f"  Username: {admin.username}")
        print(f"  Email: {admin.email}")
        print(f"  Nível: {admin.nivel_acesso}")
        print(f"  Ativo: {admin.ativo}")
        
        # Testar senha
        if admin.check_password('admin123'):
            print("\n✓ Senha 'admin123' está CORRETA!")
        else:
            print("\n✗ Senha 'admin123' está INCORRETA!")
            print("  Tentando recriar a senha...")
            admin.set_password('admin123')
            from models import db
            db.session.commit()
            print("  ✓ Senha redefinida para 'admin123'")
    else:
        print("✗ Usuário admin NÃO encontrado!")
        print("  Criando usuário admin...")
        
        from models import db
        admin = User(
            username='admin',
            email='admin@financeiro.com',
            nivel_acesso='admin',
            ativo=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("  ✓ Usuário admin criado com sucesso!")
        print("\nCredenciais:")
        print("  Usuário: admin")
        print("  Senha: admin123")
