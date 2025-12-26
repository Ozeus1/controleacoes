from flask import Flask
from flask_login import LoginManager
from config import config
from models import db, init_db, User
import os

def create_app(config_name='default'):
    """Factory function para criar a aplicação Flask"""
    app = Flask(__name__)
    
    # Carregar configurações
    app.config.from_object(config[config_name])
    
    # Inicializar extensões
    init_db(app)
    
    # Configurar Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'warning'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Registrar blueprints
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.despesas import despesas_bp
    from routes.receitas import receitas_bp
    from routes.configuracao import config_bp
    from routes.relatorios import relatorios_bp
    from routes.fluxo_caixa import fluxo_caixa_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(despesas_bp, url_prefix='/despesas')
    app.register_blueprint(receitas_bp, url_prefix='/receitas')
    app.register_blueprint(config_bp, url_prefix='/configuracao')
    app.register_blueprint(relatorios_bp, url_prefix='/relatorios')
    app.register_blueprint(fluxo_caixa_bp)
    
    return app

if __name__ == '__main__':
    # Obter ambiente da variável de ambiente ou usar 'development'
    env = os.environ.get('FLASK_ENV', 'development')
    app = create_app(env)
    app.run(host='0.0.0.0', port=5000, debug=True)
