from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from models import db, Despesa, Receita, CategoriaDespesa
from sqlalchemy import func, extract
from datetime import datetime, timedelta
import calendar

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Página inicial"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard principal do sistema"""
    hoje = datetime.now()
    mes_atual = hoje.month
    ano_atual = hoje.year
    
    # Query base baseada no nível de acesso
    if current_user.is_gerente():
        # Gerente e admin veem todos os dados
        despesas_query = Despesa.query
        receitas_query = Receita.query
    else:
        # Usuário comum vê apenas seus próprios dados
        despesas_query = Despesa.query.filter_by(user_id=current_user.id)
        receitas_query = Receita.query.filter_by(user_id=current_user.id)
    
    # Total de despesas do mês (Excluindo 'Pagamentos')
    total_despesas_mes = db.session.query(func.sum(Despesa.valor)).join(CategoriaDespesa).filter(
        extract('month', Despesa.data_pagamento) == mes_atual,
        extract('year', Despesa.data_pagamento) == ano_atual,
        func.lower(CategoriaDespesa.nome) != 'pagamentos'
    )
    if not current_user.is_gerente():
        total_despesas_mes = total_despesas_mes.filter(Despesa.user_id == current_user.id)
    total_despesas_mes = total_despesas_mes.scalar() or 0
    
    # Total de receitas do mês
    total_receitas_mes = db.session.query(func.sum(Receita.valor)).filter(
        extract('month', Receita.data_recebimento) == mes_atual,
        extract('year', Receita.data_recebimento) == ano_atual
    )
    if not current_user.is_gerente():
        total_receitas_mes = total_receitas_mes.filter(Receita.user_id == current_user.id)
    total_receitas_mes = total_receitas_mes.scalar() or 0
    
    # Saldo do mês (Geral)
    saldo_mes = total_receitas_mes - total_despesas_mes
    
    # --- CÁLCULO DO FLUXO DE CAIXA ---
    from models import MeioPagamento, EventoCaixaAvulso
    from sqlalchemy import or_
    
    MEIOS_PAGAMENTO_CAIXA = ['Boleto', 'Dinheiro', 'PIX', 'Transferência', 'Débito em Conta']
    
    # Saídas de Caixa (Despesas em dinheiro/pix/etc OU Categoria 'Pagamentos')
    saidas_caixa_query = db.session.query(func.sum(Despesa.valor)).join(
        Despesa.meio_pagamento
    ).join(
        Despesa.categoria
    ).filter(
        extract('month', Despesa.data_pagamento) == mes_atual,
        extract('year', Despesa.data_pagamento) == ano_atual,
        or_(
            func.lower(MeioPagamento.nome).in_([m.lower() for m in MEIOS_PAGAMENTO_CAIXA]),
            func.lower(CategoriaDespesa.nome) == 'pagamentos'
        )
    )
    if not current_user.is_gerente():
        saidas_caixa_query = saidas_caixa_query.filter(Despesa.user_id == current_user.id)
    
    saidas_caixa = saidas_caixa_query.scalar() or 0.0
    
    # Eventos Avulsos (Saídas)
    eventos_caixa_query = db.session.query(func.sum(EventoCaixaAvulso.valor)).filter(
        extract('month', EventoCaixaAvulso.data) == mes_atual,
        extract('year', EventoCaixaAvulso.data) == ano_atual
    )
    if not current_user.is_gerente():
        eventos_caixa_query = eventos_caixa_query.filter(EventoCaixaAvulso.user_id == current_user.id)
        
    eventos_caixa = eventos_caixa_query.scalar() or 0.0
    
    fluxo_saidas = saidas_caixa + eventos_caixa
    fluxo_entradas = total_receitas_mes # Receitas são entradas de caixa
    fluxo_saldo = fluxo_entradas - fluxo_saidas
    
    # Últimas despesas
    ultimas_despesas = despesas_query.order_by(Despesa.data_registro.desc()).limit(5).all()
    
    # Últimas receitas
    ultimas_receitas = receitas_query.order_by(Receita.data_registro.desc()).limit(5).all()
    
    # Nome do mês
    nome_mes = calendar.month_name[mes_atual]
    
    return render_template('dashboard.html',
                         total_despesas=total_despesas_mes,
                         total_receitas=total_receitas_mes,
                         saldo=saldo_mes,
                         fluxo_entradas=fluxo_entradas,
                         fluxo_saidas=fluxo_saidas,
                         fluxo_saldo=fluxo_saldo,
                         ultimas_despesas=ultimas_despesas,
                         ultimas_receitas=ultimas_receitas,
                         mes_atual=nome_mes,
                         ano_atual=ano_atual)
