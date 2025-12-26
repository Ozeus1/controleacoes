from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, BalancoMensal, EventoCaixaAvulso, Receita, Despesa, CategoriaDespesa, MeioPagamento
from datetime import datetime, date
from sqlalchemy import extract, and_, func, or_
import calendar
import pandas as pd
import io

fluxo_caixa_bp = Blueprint('fluxo_caixa', __name__, url_prefix='/fluxo-caixa')

# Meios de pagamento considerados como saída de caixa
MEIOS_PAGAMENTO_CAIXA = ['Boleto', 'Dinheiro', 'PIX', 'Transferência', 'Débito em Conta']


@fluxo_caixa_bp.route('/')
@login_required
def index():
    """Página principal do fluxo de caixa"""
    # Buscar balanços mensais do usuário
    balancos = BalancoMensal.query.filter_by(user_id=current_user.id)\
        .order_by(BalancoMensal.ano.desc(), BalancoMensal.mes.desc()).all()
    
    # Buscar eventos de caixa avulsos
    eventos = EventoCaixaAvulso.query.filter_by(user_id=current_user.id)\
        .order_by(EventoCaixaAvulso.data.desc()).all()
    # Obter ano e mês atual para o formulário
    hoje = date.today()
    ano_atual = hoje.year
    mes_atual = hoje.month
    
    return render_template('fluxo_caixa/index.html',
                         balancos=balancos,
                         eventos=eventos,
                         ano_atual=ano_atual,
                         mes_atual=mes_atual,
                         meses=calendar.month_name[1:],
                         date=date)


@fluxo_caixa_bp.route('/balanco/salvar', methods=['POST'])
@login_required
def salvar_balanco():
    """Criar ou atualizar balanço mensal"""
    try:
        balanco_id = request.form.get('balanco_id')
        ano = int(request.form.get('ano'))
        mes = int(request.form.get('mes'))
        total_entradas = float(request.form.get('total_entradas', 0))
        total_saidas = float(request.form.get('total_saidas', 0))
        observacoes = request.form.get('observacoes', '').strip()
        
        saldo_mes = total_entradas - total_saidas
        
        if balanco_id:
            # Atualizar balanço existente
            balanco = BalancoMensal.query.get_or_404(balanco_id)
            if balanco.user_id != current_user.id:
                flash('Acesso negado', 'danger')
                return redirect(url_for('fluxo_caixa.index'))
            
            balanco.ano = ano
            balanco.mes = mes
            balanco.total_entradas = total_entradas
            balanco.total_saidas = total_saidas
            balanco.saldo_mes = saldo_mes
            balanco.observacoes = observacoes
            
            mensagem = 'Balanço atualizado com sucesso!'
        else:
            # Criar novo balanço
            balanco = BalancoMensal(
                user_id=current_user.id,
                ano=ano,
                mes=mes,
                total_entradas=total_entradas,
                total_saidas=total_saidas,
                saldo_mes=saldo_mes,
                observacoes=observacoes
            )
            db.session.add(balanco)
            mensagem = 'Balanço criado com sucesso!'
        
        db.session.commit()
        flash(mensagem, 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao salvar balanço: {str(e)}', 'danger')
    
    return redirect(url_for('fluxo_caixa.index'))


@fluxo_caixa_bp.route('/balanco/calcular-entradas', methods=['POST'])
@login_required
def calcular_entradas():
    """Calcular automaticamente total de entradas (receitas) para um mês"""
    try:
        ano = int(request.form.get('ano'))
        mes = int(request.form.get('mes'))
        
        # Somar todas as receitas do usuário no mês/ano especificado
        total = db.session.query(func.sum(Receita.valor)).filter(
            and_(
                Receita.user_id == current_user.id,
                extract('year', Receita.data_recebimento) == ano,
                extract('month', Receita.data_recebimento) == mes
            )
        ).scalar() or 0.0
        
        return jsonify({'success': True, 'total_entradas': total})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@fluxo_caixa_bp.route('/balanco/calcular-saidas', methods=['POST'])
@login_required
def calcular_saidas():
    """Calcular automaticamente total de saídas (despesas de caixa + eventos avulsos) para um mês"""
    try:
        ano = int(request.form.get('ano'))
        mes = int(request.form.get('mes'))
        
        # Somar despesas com meios de pagamento considerados como caixa OU categoria 'Pagamentos'
        total_despesas = db.session.query(func.sum(Despesa.valor)).join(
            Despesa.meio_pagamento
        ).join(
            Despesa.categoria
        ).filter(
            and_(
                Despesa.user_id == current_user.id,
                extract('year', Despesa.data_pagamento) == ano,
                extract('month', Despesa.data_pagamento) == mes,
                or_(
                    func.lower(MeioPagamento.nome).in_([m.lower() for m in MEIOS_PAGAMENTO_CAIXA]),
                    func.lower(CategoriaDespesa.nome) == 'pagamentos'
                )
            )
        ).scalar() or 0.0
        
        # Somar eventos de caixa avulsos
        total_eventos = db.session.query(func.sum(EventoCaixaAvulso.valor)).filter(
            and_(
                EventoCaixaAvulso.user_id == current_user.id,
                extract('year', EventoCaixaAvulso.data) == ano,
                extract('month', EventoCaixaAvulso.data) == mes
            )
        ).scalar() or 0.0
        
        total_saidas = total_despesas + total_eventos
        
        return jsonify({
            'success': True,
            'total_saidas': total_saidas,
            'total_despesas': total_despesas,
            'total_eventos': total_eventos
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@fluxo_caixa_bp.route('/balanco/recalcular-tudo', methods=['POST'])
@login_required
def recalcular_tudo():
    """Recalcular todos os balanços mensais baseado nas transações"""
    try:
        # Remover todos os balanços do usuário
        BalancoMensal.query.filter_by(user_id=current_user.id).delete()
        
        # Encontrar todos os meses com transações
        meses_receitas = db.session.query(
            extract('year', Receita.data_recebimento).label('ano'),
            extract('month', Receita.data_recebimento).label('mes')
        ).filter_by(user_id=current_user.id).distinct().all()
        
        meses_despesas = db.session.query(
            extract('year', Despesa.data_pagamento).label('ano'),
            extract('month', Despesa.data_pagamento).label('mes')
        ).filter_by(user_id=current_user.id).distinct().all()
        
        meses_eventos = db.session.query(
            extract('year', EventoCaixaAvulso.data).label('ano'),
            extract('month', EventoCaixaAvulso.data).label('mes')
        ).filter_by(user_id=current_user.id).distinct().all()
        
        # Combinar todos os meses únicos
        meses_unicos = set()
        for ano, mes in meses_receitas:
            meses_unicos.add((int(ano), int(mes)))
        for ano, mes in meses_despesas:
            meses_unicos.add((int(ano), int(mes)))
        for ano, mes in meses_eventos:
            meses_unicos.add((int(ano), int(mes)))
        
        # Criar balanço para cada mês
        for ano, mes in sorted(meses_unicos):
            # Calcular entradas
            total_entradas = db.session.query(func.sum(Receita.valor)).filter(
                and_(
                    Receita.user_id == current_user.id,
                    extract('year', Receita.data_recebimento) == ano,
                    extract('month', Receita.data_recebimento) == mes
                )
            ).scalar() or 0.0
            
            # Calcular saídas (despesas de caixa OU Pagamentos)
            total_despesas = db.session.query(func.sum(Despesa.valor)).join(
                Despesa.meio_pagamento
            ).join(
                Despesa.categoria
            ).filter(
                and_(
                    Despesa.user_id == current_user.id,
                    extract('year', Despesa.data_pagamento) == ano,
                    extract('month', Despesa.data_pagamento) == mes,
                    or_(
                        func.lower(MeioPagamento.nome).in_([m.lower() for m in MEIOS_PAGAMENTO_CAIXA]),
                        func.lower(CategoriaDespesa.nome) == 'pagamentos'
                    )
                )
            ).scalar() or 0.0
            
            # Calcular saídas (eventos avulsos)
            total_eventos = db.session.query(func.sum(EventoCaixaAvulso.valor)).filter(
                and_(
                    EventoCaixaAvulso.user_id == current_user.id,
                    extract('year', EventoCaixaAvulso.data) == ano,
                    extract('month', EventoCaixaAvulso.data) == mes
                )
            ).scalar() or 0.0
            
            total_saidas = total_despesas + total_eventos
            saldo_mes = total_entradas - total_saidas
            
            # Criar balanço
            balanco = BalancoMensal(
                user_id=current_user.id,
                ano=ano,
                mes=mes,
                total_entradas=total_entradas,
                total_saidas=total_saidas,
                saldo_mes=saldo_mes
            )
            db.session.add(balanco)
        
        db.session.commit()
        flash('Todos os balanços foram recalculados com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao recalcular balanços: {str(e)}', 'danger')
    
    return redirect(url_for('fluxo_caixa.index'))


@fluxo_caixa_bp.route('/balanco/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_balanco(id):
    """Excluir balanço mensal"""
    try:
        balanco = BalancoMensal.query.get_or_404(id)
        
        if balanco.user_id != current_user.id:
            flash('Acesso negado', 'danger')
            return redirect(url_for('fluxo_caixa.index'))
        
        db.session.delete(balanco)
        db.session.commit()
        flash('Balanço excluído com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir balanço: {str(e)}', 'danger')
    
    return redirect(url_for('fluxo_caixa.index'))


@fluxo_caixa_bp.route('/eventos', methods=['POST'])
@login_required
def criar_evento():
    """Criar novo evento de caixa avulso"""
    try:
        data_str = request.form.get('data')
        descricao = request.form.get('descricao', '').strip()
        valor_str = request.form.get('valor', '0')
        
        # Tratar valor (substituir vírgula por ponto se necessário)
        if isinstance(valor_str, str):
            valor_str = valor_str.replace(',', '.')
        
        valor = float(valor_str)
        
        if not descricao:
            flash('Descrição é obrigatória', 'warning')
            return redirect(url_for('fluxo_caixa.index', tab='eventos'))
        
        if valor <= 0:
            flash('Valor deve ser maior que zero', 'warning')
            return redirect(url_for('fluxo_caixa.index', tab='eventos'))
        
        data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
        
        evento = EventoCaixaAvulso(
            user_id=current_user.id,
            data=data_obj,
            descricao=descricao,
            valor=valor
        )
        
        db.session.add(evento)
        db.session.commit()
        
        flash('Evento registrado com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao criar evento: {str(e)}', 'danger')
    
    return redirect(url_for('fluxo_caixa.index'))


@fluxo_caixa_bp.route('/eventos/<int:id>', methods=['POST'])
@login_required
def atualizar_evento(id):
    """Atualizar evento de caixa avulso"""
    try:
        evento = EventoCaixaAvulso.query.get_or_404(id)
        
        if evento.user_id != current_user.id:
            flash('Acesso negado', 'danger')
            return redirect(url_for('fluxo_caixa.index', tab='eventos'))
            
        data_str = request.form.get('data')
        descricao = request.form.get('descricao', '').strip()
        valor_str = request.form.get('valor', '0')
        
        # Tratar valor
        if isinstance(valor_str, str):
            valor_str = valor_str.replace(',', '.')
        valor = float(valor_str)
        
        if not descricao:
            flash('Descrição é obrigatória', 'warning')
            return redirect(url_for('fluxo_caixa.index', tab='eventos'))
            
        if valor <= 0:
            flash('Valor deve ser maior que zero', 'warning')
            return redirect(url_for('fluxo_caixa.index', tab='eventos'))
            
        evento.data = datetime.strptime(data_str, '%Y-%m-%d').date()
        evento.descricao = descricao
        evento.valor = valor
        
        db.session.commit()
        flash('Evento atualizado com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar evento: {str(e)}', 'danger')
    
    return redirect(url_for('fluxo_caixa.index'))


@fluxo_caixa_bp.route('/api/grafico-dados')
@login_required
def grafico_dados():
    """API para dados do gráfico de fluxo de caixa"""
    try:
        # Parâmetros de filtro
        ano_inicio = request.args.get('ano_inicio', type=int)
        mes_inicio = request.args.get('mes_inicio', type=int)
        ano_fim = request.args.get('ano_fim', type=int)
        mes_fim = request.args.get('mes_fim', type=int)
        
        # Construir query
        query = BalancoMensal.query.filter_by(user_id=current_user.id)
        
        if ano_inicio and mes_inicio:
            query = query.filter(
                db.or_(
                    BalancoMensal.ano > ano_inicio,
                    db.and_(
                        BalancoMensal.ano == ano_inicio,
                        BalancoMensal.mes >= mes_inicio
                    )
                )
            )
        
        if ano_fim and mes_fim:
            query = query.filter(
                db.or_(
                    BalancoMensal.ano < ano_fim,
                    db.and_(
                        BalancoMensal.ano == ano_fim,
                        BalancoMensal.mes <= mes_fim
                    )
                )
            )
        
        balancos = query.order_by(BalancoMensal.ano, BalancoMensal.mes).all()
        
        # Formatar dados para o gráfico
        labels = []
        entradas = []
        saidas = []
        saldos = []
        
        for balanco in balancos:
            labels.append(f'{balanco.mes:02d}/{balanco.ano}')
            entradas.append(balanco.total_entradas)
            saidas.append(balanco.total_saidas)
            saldos.append(balanco.saldo_mes)
        
        return jsonify({
            'labels': labels,
            'entradas': entradas,
            'saidas': saidas,
            'saldos': saldos
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@fluxo_caixa_bp.route('/exportar/<int:ano>/<int:mes>')
@login_required
def exportar_excel(ano, mes):
    """Exportar detalhes do mês para Excel"""
    try:
        # Buscar receitas do mês
        receitas = Receita.query.filter(
            and_(
                Receita.user_id == current_user.id,
                extract('year', Receita.data_recebimento) == ano,
                extract('month', Receita.data_recebimento) == mes
            )
        ).all()
        
        # Buscar despesas de caixa do mês OU Pagamentos
        despesas = Despesa.query.join(Despesa.meio_pagamento).join(Despesa.categoria).filter(
            and_(
                Despesa.user_id == current_user.id,
                extract('year', Despesa.data_pagamento) == ano,
                extract('month', Despesa.data_pagamento) == mes,
                or_(
                    func.lower(MeioPagamento.nome).in_([m.lower() for m in MEIOS_PAGAMENTO_CAIXA]),
                    func.lower(CategoriaDespesa.nome) == 'pagamentos'
                )
            )
        ).all()
        
        # Buscar eventos avulsos do mês
        eventos = EventoCaixaAvulso.query.filter(
            and_(
                EventoCaixaAvulso.user_id == current_user.id,
                extract('year', EventoCaixaAvulso.data) == ano,
                extract('month', EventoCaixaAvulso.data) == mes
            )
        ).all()
        
        # Criar DataFrames
        df_receitas = pd.DataFrame([{
            'Data': r.data_recebimento.strftime('%d/%m/%Y'),
            'Descrição': r.descricao,
            'Categoria': r.categoria.nome,
            'Valor': r.valor
        } for r in receitas])
        
        df_despesas = pd.DataFrame([{
            'Data': d.data_pagamento.strftime('%d/%m/%Y'),
            'Descrição': d.descricao,
            'Categoria': d.categoria.nome,
            'Meio de Pagamento': d.meio_pagamento.nome,
            'Valor': d.valor
        } for d in despesas])
        
        df_eventos = pd.DataFrame([{
            'Data': e.data.strftime('%d/%m/%Y'),
            'Descrição': e.descricao,
            'Valor': e.valor
        } for e in eventos])
        
        # Criar arquivo Excel em memória
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            if not df_receitas.empty:
                df_receitas.to_excel(writer, sheet_name='Entradas (Receitas)', index=False)
            if not df_despesas.empty:
                df_despesas.to_excel(writer, sheet_name='Saídas (Despesas)', index=False)
            if not df_eventos.empty:
                df_eventos.to_excel(writer, sheet_name='Saídas (Eventos Avulsos)', index=False)
        
        output.seek(0)
        
        nome_arquivo = f'Fluxo_Caixa_{ano}_{mes:02d}.xlsx'
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=nome_arquivo
        )
        
    except Exception as e:
        flash(f'Erro ao exportar: {str(e)}', 'danger')
        return redirect(url_for('fluxo_caixa.index'))


@fluxo_caixa_bp.route('/detalhes/<int:ano>/<int:mes>')
@login_required
def detalhes_mes(ano, mes):
    """Visualizar detalhes de um mês específico"""
    # Buscar receitas
    receitas = Receita.query.filter(
        and_(
            Receita.user_id == current_user.id,
            extract('year', Receita.data_recebimento) == ano,
            extract('month', Receita.data_recebimento) == mes
        )
    ).order_by(Receita.data_recebimento).all()
    
    # Buscar despesas de caixa OU Pagamentos
    despesas = Despesa.query.join(Despesa.meio_pagamento).join(Despesa.categoria).filter(
        and_(
            Despesa.user_id == current_user.id,
            extract('year', Despesa.data_pagamento) == ano,
            extract('month', Despesa.data_pagamento) == mes,
            or_(
                func.lower(MeioPagamento.nome).in_([m.lower() for m in MEIOS_PAGAMENTO_CAIXA]),
                func.lower(CategoriaDespesa.nome) == 'pagamentos'
            )
        )
    ).order_by(Despesa.data_pagamento).all()
    
    # Buscar eventos avulsos
    eventos = EventoCaixaAvulso.query.filter(
        and_(
            EventoCaixaAvulso.user_id == current_user.id,
            extract('year', EventoCaixaAvulso.data) == ano,
            extract('month', EventoCaixaAvulso.data) == mes
        )
    ).order_by(EventoCaixaAvulso.data).all()
    
    # Calcular totais
    total_receitas = sum(r.valor for r in receitas)
    total_despesas = sum(d.valor for d in despesas)
    total_eventos = sum(e.valor for e in eventos)
    
    mes_nome = calendar.month_name[mes]
    
    return render_template('fluxo_caixa/detalhes.html',
                         ano=ano,
                         mes=mes,
                         mes_nome=mes_nome,
                         receitas=receitas,
                         despesas=despesas,
                         eventos=eventos,
                         total_receitas=total_receitas,
                         total_despesas=total_despesas,
                         total_eventos=total_eventos)
