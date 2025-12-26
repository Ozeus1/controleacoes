from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from models import db, Receita, CategoriaReceita, MeioRecebimento
from datetime import datetime, date
from sqlalchemy import extract, func

receitas_bp = Blueprint('receitas', __name__)

@receitas_bp.route('/')
@login_required
def lista():
    """Listar receitas com filtros"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Filtros
    categoria_id = request.args.get('categoria_id', type=int)
    meio_recebimento_id = request.args.get('meio_recebimento_id', type=int)
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
        query = Receita.query
    else:
        query = Receita.query.filter_by(user_id=current_user.id)
    
    # Aplicar filtros
    if categoria_id:
        query = query.filter_by(categoria_id=categoria_id)
    if meio_recebimento_id:
        query = query.filter_by(meio_recebimento_id=meio_recebimento_id)
        
    if data_inicio:
        query = query.filter(Receita.data_recebimento >= datetime.strptime(data_inicio, '%Y-%m-%d').date())
    if data_fim:
        query = query.filter(Receita.data_recebimento <= datetime.strptime(data_fim, '%Y-%m-%d').date())
        
    if busca:
        query = query.filter(Receita.descricao.ilike(f'%{busca}%'))
    
    # Ordenar e paginar
    receitas = query.order_by(Receita.data_recebimento.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Carregar opções para filtros
    categorias = CategoriaReceita.query.filter_by(ativo=True).order_by(CategoriaReceita.nome).all()
    meios_recebimento = MeioRecebimento.query.filter_by(ativo=True).order_by(MeioRecebimento.nome).all()
    
    # Args para paginação (excluindo page)
    filtros_url = {k: v for k, v in request.args.items() if k != 'page'}
    
    return render_template('receitas/lista.html',
                         receitas=receitas,
                         categorias=categorias,
                         meios_recebimento=meios_recebimento,
                         periodo=periodo,
                         data_inicio_filtro=data_inicio,
                         data_fim_filtro=data_fim,
                         filtros_url=filtros_url)

@receitas_bp.route('/criar', methods=['GET', 'POST'])
@login_required
def criar():
    """Criar nova receita"""
    if request.method == 'POST':
        descricao = request.form.get('descricao')
        valor = float(request.form.get('valor').replace(',', '.'))
        categoria_id = int(request.form.get('categoria_id'))
        meio_recebimento_id = int(request.form.get('meio_recebimento_id'))
        num_parcelas = int(request.form.get('num_parcelas', 1))
        data_recebimento = datetime.strptime(request.form.get('data_recebimento'), '%Y-%m-%d').date()
        
        nova_receita = Receita(
            descricao=descricao,
            valor=valor,
            categoria_id=categoria_id,
            meio_recebimento_id=meio_recebimento_id,
            num_parcelas=num_parcelas,
            data_recebimento=data_recebimento,
            user_id=current_user.id
        )
        
        db.session.add(nova_receita)
        db.session.commit()
        
        flash('Receita cadastrada com sucesso!', 'success')
        return redirect(url_for('receitas.lista'))
    
    categorias = CategoriaReceita.query.filter_by(ativo=True).order_by(CategoriaReceita.nome).all()
    meios_recebimento = MeioRecebimento.query.filter_by(ativo=True).order_by(MeioRecebimento.nome).all()
    
    return render_template('receitas/form.html',
                         categorias=categorias,
                         meios_recebimento=meios_recebimento,
                         hoje=datetime.now().date())

@receitas_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar(id):
    """Editar receita existente"""
    receita = Receita.query.get_or_404(id)
    
    # Capturar filtros da URL para persistência
    filtros = {k: v for k, v in request.args.items()}
    
    # Verificar permissão
    if not current_user.is_gerente() and receita.user_id != current_user.id:
        flash('Você não tem permissão para editar esta receita.', 'danger')
        return redirect(url_for('receitas.lista', **filtros))
    
    if request.method == 'POST':
        receita.descricao = request.form.get('descricao')
        receita.valor = float(request.form.get('valor').replace(',', '.'))
        receita.categoria_id = int(request.form.get('categoria_id'))
        receita.meio_recebimento_id = int(request.form.get('meio_recebimento_id'))
        receita.num_parcelas = int(request.form.get('num_parcelas', 1))
        receita.data_recebimento = datetime.strptime(request.form.get('data_recebimento'), '%Y-%m-%d').date()
        
        db.session.commit()
        
        # Recuperar filtros do form (se houver) ou usar padrão
        filtros_redirect = {}
        for key in ['periodo', 'data_inicio', 'data_fim', 'categoria_id', 'meio_recebimento_id', 'busca', 'page']:
            val = request.form.get(f'filtro_{key}')
            if val:
                filtros_redirect[key] = val
        
        flash('Receita atualizada com sucesso!', 'success')
        return redirect(url_for('receitas.lista', **filtros_redirect))
    
    categorias = CategoriaReceita.query.filter_by(ativo=True).order_by(CategoriaReceita.nome).all()
    meios_recebimento = MeioRecebimento.query.filter_by(ativo=True).order_by(MeioRecebimento.nome).all()
    
    return render_template('receitas/form.html',
                         receita=receita,
                         categorias=categorias,
                         meios_recebimento=meios_recebimento,
                         filtros=filtros)

@receitas_bp.route('/<int:id>/excluir', methods=['POST'])
@login_required
def excluir(id):
    """Excluir receita"""
    receita = Receita.query.get_or_404(id)
    
    # Verificar permissão
    if not current_user.is_gerente() and receita.user_id != current_user.id:
        flash('Você não tem permissão para excluir esta receita.', 'danger')
        return redirect(url_for('receitas.lista'))
    
    db.session.delete(receita)
    db.session.commit()
    
    flash('Receita excluída com sucesso!', 'success')
    return redirect(url_for('receitas.lista'))

@receitas_bp.route('/exportar')
@login_required
def exportar():
    """Exportar receitas para Excel"""
    import pandas as pd
    from io import BytesIO
    
    # Query base
    if current_user.is_gerente():
        receitas = Receita.query.all()
    else:
        receitas = Receita.query.filter_by(user_id=current_user.id).all()
    
    # Preparar dados
    dados = []
    for r in receitas:
        dados.append({
            'Data': r.data_recebimento.strftime('%d/%m/%Y'),
            'Descrição': r.descricao,
            'Categoria': r.categoria.nome,
            'Meio de Recebimento': r.meio_recebimento.nome,
            'Valor': r.valor,
            'Parcelas': r.num_parcelas,
            'Usuário': r.usuario.username
        })
    
    df = pd.DataFrame(dados)
    
    # Criar arquivo Excel em memória
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Receitas')
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'receitas_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )
