from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db, Despesa, CategoriaDespesa, MeioPagamento
from datetime import datetime, date
from sqlalchemy import extract, func

despesas_bp = Blueprint('despesas', __name__)

@despesas_bp.route('/')
@login_required
def lista():
    """Listar despesas com filtros"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Filtros
    categoria_id = request.args.get('categoria_id', type=int)
    meio_pagamento_id = request.args.get('meio_pagamento_id', type=int)
    busca = request.args.get('busca', '').strip()
    
    # Periodo (padrão: mes_atual)
    periodo = request.args.get('periodo', 'mes_atual')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    # Lógica do período
    if periodo == 'mes_atual':
        hoje = datetime.now()
        import calendar
        ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
        data_inicio = date(hoje.year, hoje.month, 1).strftime('%Y-%m-%d')
        data_fim = date(hoje.year, hoje.month, ultimo_dia).strftime('%Y-%m-%d')
    elif periodo == 'todos':
        data_inicio = None
        data_fim = None
    # Se personalizado, usa os valores de data_inicio e data_fim recebidos
    
    # Query base
    if current_user.is_gerente():
        query = Despesa.query
    else:
        query = Despesa.query.filter_by(user_id=current_user.id)
    
    # Aplicar filtros
    if categoria_id:
        query = query.filter_by(categoria_id=categoria_id)
    if meio_pagamento_id:
        query = query.filter_by(meio_pagamento_id=meio_pagamento_id)
        
    if data_inicio:
        query = query.filter(Despesa.data_pagamento >= datetime.strptime(data_inicio, '%Y-%m-%d').date())
    if data_fim:
        query = query.filter(Despesa.data_pagamento <= datetime.strptime(data_fim, '%Y-%m-%d').date())
        
    if busca:
        query = query.filter(Despesa.descricao.ilike(f'%{busca}%'))
    
    # Ordenar e paginar
    despesas = query.order_by(Despesa.data_pagamento.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Carregar opções para filtros
    categorias = CategoriaDespesa.query.filter_by(ativo=True).order_by(CategoriaDespesa.nome).all()
    meios_pagamento = MeioPagamento.query.filter_by(ativo=True).order_by(MeioPagamento.nome).all()
    
    # Args para paginação (excluindo page)
    filtros_url = {k: v for k, v in request.args.items() if k != 'page'}
    
    return render_template('despesas/lista.html',
                         despesas=despesas,
                         categorias=categorias,
                         meios_pagamento=meios_pagamento,
                         periodo=periodo,
                         data_inicio_filtro=data_inicio,
                         data_fim_filtro=data_fim,
                         filtros_url=filtros_url)

@despesas_bp.route('/criar', methods=['GET', 'POST'])
@login_required
def criar():
    """Criar nova despesa"""
    if request.method == 'POST':
        descricao = request.form.get('descricao')
        valor = float(request.form.get('valor').replace(',', '.'))
        categoria_id = int(request.form.get('categoria_id'))
        meio_pagamento_id = int(request.form.get('meio_pagamento_id'))
        num_parcelas = int(request.form.get('num_parcelas', 1))
        data_pagamento = datetime.strptime(request.form.get('data_pagamento'), '%Y-%m-%d').date()
        
        nova_despesa = Despesa(
            descricao=descricao,
            valor=valor,
            categoria_id=categoria_id,
            meio_pagamento_id=meio_pagamento_id,
            num_parcelas=num_parcelas,
            data_pagamento=data_pagamento,
            user_id=current_user.id
        )
        
        db.session.add(nova_despesa)
        db.session.commit()
        
        flash('Despesa cadastrada com sucesso!', 'success')
        return redirect(url_for('despesas.lista'))
    
    categorias = CategoriaDespesa.query.filter_by(ativo=True).order_by(CategoriaDespesa.nome).all()
    meios_pagamento = MeioPagamento.query.filter_by(ativo=True).order_by(MeioPagamento.nome).all()
    
    return render_template('despesas/form.html',
                         categorias=categorias,
                         meios_pagamento=meios_pagamento,
                         hoje=datetime.now().date())

@despesas_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar(id):
    """Editar despesa existente"""
    despesa = Despesa.query.get_or_404(id)
    
    # Capturar filtros da URL para persistência
    filtros = {k: v for k, v in request.args.items()}
    
    # Verificar permissão
    if not current_user.is_gerente() and despesa.user_id != current_user.id:
        flash('Você não tem permissão para editar esta despesa.', 'danger')
        return redirect(url_for('despesas.lista', **filtros))
    
    if request.method == 'POST':
        despesa.descricao = request.form.get('descricao')
        despesa.valor = float(request.form.get('valor').replace(',', '.'))
        despesa.categoria_id = int(request.form.get('categoria_id'))
        despesa.meio_pagamento_id = int(request.form.get('meio_pagamento_id'))
        despesa.num_parcelas = int(request.form.get('num_parcelas', 1))
        data_pagamento = datetime.strptime(request.form.get('data_pagamento'), '%Y-%m-%d').date()
        
        db.session.commit()
        
        # Recuperar filtros do form (se houver) ou usar padrão
        filtros_redirect = {}
        for key in ['periodo', 'data_inicio', 'data_fim', 'categoria_id', 'meio_pagamento_id', 'busca', 'page']:
            val = request.form.get(f'filtro_{key}')
            if val:
                filtros_redirect[key] = val
        
        flash('Despesa atualizada com sucesso!', 'success')
        return redirect(url_for('despesas.lista', **filtros_redirect))
    
    categorias = CategoriaDespesa.query.filter_by(ativo=True).order_by(CategoriaDespesa.nome).all()
    meios_pagamento = MeioPagamento.query.filter_by(ativo=True).order_by(MeioPagamento.nome).all()
    
    return render_template('despesas/form.html',
                         despesa=despesa,
                         categorias=categorias,
                         meios_pagamento=meios_pagamento,
                         filtros=filtros)

@despesas_bp.route('/<int:id>/excluir', methods=['POST'])
@login_required
def excluir(id):
    """Excluir despesa"""
    despesa = Despesa.query.get_or_404(id)
    
    # Verificar permissão
    if not current_user.is_gerente() and despesa.user_id != current_user.id:
        flash('Você não tem permissão para excluir esta despesa.', 'danger')
        return redirect(url_for('despesas.lista'))
    
    db.session.delete(despesa)
    db.session.commit()
    
    flash('Despesa excluída com sucesso!', 'success')
    return redirect(url_for('despesas.lista'))

@despesas_bp.route('/exportar')
@login_required
def exportar():
    """Exportar despesas para Excel"""
    import pandas as pd
    from io import BytesIO
    from flask import send_file
    
    # Query base
    if current_user.is_gerente():
        despesas = Despesa.query.all()
    else:
        despesas = Despesa.query.filter_by(user_id=current_user.id).all()
    
    # Preparar dados
    dados = []
    for d in despesas:
        dados.append({
            'Data': d.data_pagamento.strftime('%d/%m/%Y'),
            'Descrição': d.descricao,
            'Categoria': d.categoria.nome,
            'Meio de Pagamento': d.meio_pagamento.nome,
            'Valor': d.valor,
            'Parcelas': d.num_parcelas,
            'Usuário': d.usuario.username
        })
    
    df = pd.DataFrame(dados)
    
    # Criar arquivo Excel em memória
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Despesas')
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'despesas_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )
