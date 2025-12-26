from app import create_app
from models import db

app = create_app('development')
with app.app_context():
    db.create_all()
    print("Tabelas criadas com sucesso!")
