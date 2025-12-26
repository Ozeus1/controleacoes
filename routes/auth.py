from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def admin_required(f):
    """Decorator para requerer nível admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Acesso negado. Apenas administradores podem acessar esta página.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def gerente_required(f):
    """Decorator para requerer nível gerente ou superior"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_gerente():
            flash('Acesso negado. Permissão de gerente necessária.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if not user.ativo:
                flash('Sua conta está inativa. Entre em contato com o administrador.', 'warning')
                return redirect(url_for('auth.login'))
            
            login_user(user, remember=remember)
            flash(f'Bem-vindo, {user.username}!', 'success')
            
            # Redirecionar para a página solicitada ou dashboard
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('Usuário ou senha incorretos.', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout do usuário"""
    logout_user()
    flash('Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required
@admin_required
def register():
    """Registrar novo usuário (apenas admin)"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        nivel_acesso = request.form.get('nivel_acesso', 'usuario')
        
        # Validações
        if User.query.filter_by(username=username).first():
            flash('Nome de usuário já existe.', 'danger')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email já cadastrado.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Criar novo usuário
        new_user = User(
            username=username,
            email=email,
            nivel_acesso=nivel_acesso,
            ativo=True
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash(f'Usuário {username} criado com sucesso!', 'success')
        return redirect(url_for('config.usuarios'))
    
    return render_template('auth/register.html')

@auth_bp.route('/profile')
@login_required
def profile():
    """Perfil do usuário"""
    return render_template('auth/profile.html')
