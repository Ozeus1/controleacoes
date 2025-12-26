from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from routes.auth import gerente_required
from models import db, Despesa, Receita, CategoriaDespesa, Orcamento, MeioPagamento, FechamentoCartao
from sqlalchemy import func, extract, desc
from datetime import datetime, timedelta, date
import calendar
from dateutil.relativedelta import relativedelta

relatorios_bp = Blueprint('relatorios', __name__)

@relatorios_bp.route('/balanco')
@login_required
def balanco():
    """Relatório de balanço mensal (receitas vs despesas)"""
    # Obter período do filtro ou usar últimos 12 meses
    meses = request.args.get('meses', 12, type=int)
    
    # Query base
    if current_user.is_gerente():
        despesas_query = Despesa.query
        receitas_query = Receita.query
    else:
        despesas_query = Despesa.query.filter_by(user_id=current_user.id)
        receitas_query = Receita.query.filter_by(user_id=current_user.id)
    
    # Agrupar por mês
    despesas_mensais = db.session.query(
        extract('year', Despesa.data_pagamento).label('ano'),
        extract('month', Despesa.data_pagamento).label('mes'),
        func.sum(Despesa.valor).label('total')
    ).join(Despesa.categoria).filter(
        func.lower(CategoriaDespesa.nome) != 'pagamentos'
    ).group_by('ano', 'mes').order_by('ano', 'mes')
    
    if not current_user.is_gerente():
        despesas_mensais = despesas_mensais.filter(Despesa.user_id == current_user.id)
    
    despesas_mensais = despesas_mensais.all()
    
    receitas_mensais = db.session.query(
        extract('year', Receita.data_recebimento).label('ano'),
        extract('month', Receita.data_recebimento).label('mes'),
        func.sum(Receita.valor).label('total')
    ).group_by('ano', 'mes').order_by('ano', 'mes')
    
    if not current_user.is_gerente():
        receitas_mensais = receitas_mensais.filter(Receita.user_id == current_user.id)
    
    receitas_mensais = receitas_mensais.all()
    
    return render_template('relatorios/balanco.html',
                         despesas_mensais=despesas_mensais,
                         receitas_mensais=receitas_mensais)

@relatorios_bp.route('/despesas-mensal')
@login_required
def despesas_mensal():
    """Relatório mensal de despesas"""
    mes = request.args.get('mes', datetime.now().month, type=int)
    ano = request.args.get('ano', datetime.now().year, type=int)
    
    # Query por categoria
    query = db.session.query(
        CategoriaDespesa.id,
        CategoriaDespesa.nome,
        func.sum(Despesa.valor).label('total'),
        func.count(Despesa.id).label('quantidade')
    ).join(Despesa).filter(
        extract('month', Despesa.data_pagamento) == mes,
        extract('year', Despesa.data_pagamento) == ano,
        func.lower(CategoriaDespesa.nome) != 'pagamentos'
    )
    
    if not current_user.is_gerente():
        query = query.filter(Despesa.user_id == current_user.id)
    
    despesas_por_categoria = query.group_by(CategoriaDespesa.id, CategoriaDespesa.nome).order_by(func.sum(Despesa.valor).desc()).all()
    
    total_mes = sum([d[2] for d in despesas_por_categoria])
    nome_mes = calendar.month_name[mes]
    
    return render_template('relatorios/despesas_mensal.html',
                         despesas_por_categoria=despesas_por_categoria,
                         total_mes=total_mes,
                         mes=mes,
                         ano=ano,
                         nome_mes=nome_mes)

@relatorios_bp.route('/receitas-mensal')
@login_required
def receitas_mensal():
    """Relatório mensal de receitas"""
    mes = request.args.get('mes', datetime.now().month, type=int)
    ano = request.args.get('ano', datetime.now().year, type=int)
    
    from models import CategoriaReceita
    
    # Query por categoria
    query = db.session.query(
        CategoriaReceita.nome,
        func.sum(Receita.valor).label('total')
    ).join(Receita).filter(
        extract('month', Receita.data_recebimento) == mes,
        extract('year', Receita.data_recebimento) == ano
    )
    
    if not current_user.is_gerente():
        query = query.filter(Receita.user_id == current_user.id)
    
    receitas_por_categoria = query.group_by(CategoriaReceita.nome).order_by(func.sum(Receita.valor).desc()).all()
    
    total_mes = sum([r[1] for r in receitas_por_categoria])
    nome_mes = calendar.month_name[mes]
    
    return render_template('relatorios/receitas_mensal.html',
                         receitas_por_categoria=receitas_por_categoria,
                         total_mes=total_mes,
                         mes=mes,
                         ano=ano,
                         nome_mes=nome_mes)

@relatorios_bp.route('/top-contas')
@login_required
def top_contas():
    """Top 10 contas de despesa"""
    mes = request.args.get('mes', datetime.now().month, type=int)
    ano = request.args.get('ano', datetime.now().year, type=int)
    
    # Query top 10
    query = db.session.query(
        CategoriaDespesa.nome,
        func.sum(Despesa.valor).label('total'),
        func.count(Despesa.id).label('quantidade')
    ).join(Despesa).filter(
        extract('month', Despesa.data_pagamento) == mes,
        extract('year', Despesa.data_pagamento) == ano,
        func.lower(CategoriaDespesa.nome) != 'pagamentos'
    )
    
    if not current_user.is_gerente():
        query = query.filter(Despesa.user_id == current_user.id)
    
    top_contas = query.group_by(CategoriaDespesa.nome).order_by(func.sum(Despesa.valor).desc()).limit(10).all()
    
    # Total do mês
    total_mes_query = db.session.query(func.sum(Despesa.valor)).join(Despesa.categoria).filter(
        extract('month', Despesa.data_pagamento) == mes,
        extract('year', Despesa.data_pagamento) == ano,
        func.lower(CategoriaDespesa.nome) != 'pagamentos'
    )
    
    if not current_user.is_gerente():
        total_mes_query = total_mes_query.filter(Despesa.user_id == current_user.id)
    
    total_mes = total_mes_query.scalar() or 0
    
    nome_mes = calendar.month_name[mes]
    
    return render_template('relatorios/top_contas.html',
                         top_contas=top_contas,
                         total_mes=total_mes,
                         mes=mes,
                         ano=ano,
                         nome_mes=nome_mes)

@relatorios_bp.route('/detalhes-despesas')
@login_required
def detalhes_despesas():
    """Detalhes de despesas filtradas por categoria, mês e ano"""
    categoria_nome = request.args.get('categoria')
    mes = request.args.get('mes', type=int)
    ano = request.args.get('ano', type=int)
    
    if not categoria_nome or not mes or not ano:
        return "Parâmetros inválidos", 400
    
    # Construir query para despesas filtradas
    query = Despesa.query.join(CategoriaDespesa).filter(
        CategoriaDespesa.nome == categoria_nome,
        extract('month', Despesa.data_pagamento) == mes,
        extract('year', Despesa.data_pagamento) == ano
    )
    
    # Filtrar por usuário se não for gerente
    if not current_user.is_gerente():
        query = query.filter(Despesa.user_id == current_user.id)
    
    # Ordenar por data
    despesas = query.order_by(Despesa.data_pagamento.desc()).all()
    
    # Calcular total
    total = sum(d.valor for d in despesas)
    
    nome_mes = calendar.month_name[mes]
    
    return render_template('relatorios/detalhes_despesas.html',
                         despesas=despesas,
                         categoria_nome=categoria_nome,
                         mes=mes,
                         ano=ano,
                         total=total,
                         nome_mes=nome_mes)

@relatorios_bp.route('/orcado-vs-gasto')
@login_required
@gerente_required
def orcado_vs_gasto():
    """Relatório de orçado vs gasto"""
    mes = request.args.get('mes', datetime.now().month, type=int)
    ano = request.args.get('ano', datetime.now().year, type=int)
    
    # Buscar orçamentos do usuário (orçamento é geral, não mensal)
    orcamentos = Orcamento.query.filter_by(user_id=current_user.id).all()
    
    # Para cada orçamento, calcular o gasto
    comparativo = []
    for orc in orcamentos:
        gasto = db.session.query(func.sum(Despesa.valor)).filter(
            Despesa.categoria_id == orc.categoria_id,
            extract('month', Despesa.data_pagamento) == mes,
            extract('year', Despesa.data_pagamento) == ano,
            Despesa.user_id == current_user.id
        ).scalar() or 0
        
        diferenca = orc.valor_orcado - gasto
        percentual = (gasto / orc.valor_orcado * 100) if orc.valor_orcado > 0 else 0
        
        comparativo.append({
            'categoria': orc.categoria.nome,
            'orcado': orc.valor_orcado,
            'gasto': gasto,
            'diferenca': diferenca,
            'percentual': percentual
        })
    
    nome_mes = calendar.month_name[mes]
    
    return render_template('relatorios/orcado_vs_gasto.html',
                         comparativo=comparativo,
                         mes=mes,
                         ano=ano,
                         nome_mes=nome_mes)

@relatorios_bp.route('/previsao-cartoes')
@login_required
def previsao_cartoes():
    """Previsão de faturas de cartões de crédito (Histórico Completo)"""
    # Buscar todos os meios de pagamento do tipo cartão
    cartoes = MeioPagamento.query.filter_by(tipo='cartao', ativo=True).all()
    
    # Determinar intervalo de datas
    min_db_date = db.session.query(func.min(Despesa.data_pagamento)).scalar()
    max_db_date = db.session.query(func.max(Despesa.data_pagamento)).scalar()
    
    hoje = datetime.now().date()
    futuro_12m = hoje + relativedelta(months=12)
    
    # Definir início: menor data do banco ou hoje (se vazio)
    # Se a menor data for muito antiga (ex: > 2 anos), podemos limitar para não ficar gigante?
    # O usuário pediu "todos os meses", então vamos respeitar o histórico.
    start_date = min_db_date if min_db_date else hoje
    
    # Definir fim: maior data entre (banco, hoje + 12 meses, maior data de parcela)
    # Buscar despesas parceladas para calcular a data final real
    max_parcela_date = max_db_date
    
    # Query para buscar a maior data final de parcelamento
    query_parcelas = db.session.query(Despesa.data_pagamento, Despesa.num_parcelas).filter(
        Despesa.num_parcelas > 1
    )
    
    # Filtrar por usuário se não for gerente
    if not current_user.is_gerente():
        query_parcelas = query_parcelas.filter(Despesa.user_id == current_user.id)
        
    despesas_parceladas = query_parcelas.all()
    
    # Debug logging (print to console which shows in terminal)
    print(f"DEBUG: Found {len(despesas_parceladas)} parcel expenses for user {current_user.id}")
    
    for d_data, d_parcelas in despesas_parceladas:
        data_final = d_data + relativedelta(months=d_parcelas - 1)
        if not max_parcela_date or data_final > max_parcela_date:
            max_parcela_date = data_final
            
    # O final deve ser o maior entre:
    # 1. 12 meses a frente (mínimo garantido)
    # 2. Maior data de registro no banco
    # 3. Maior data de vencimento de parcela calculada
    
    candidates = [futuro_12m]
    if max_db_date:
        candidates.append(max_db_date)
    if max_parcela_date:
        candidates.append(max_parcela_date)
        
    end_date = max(candidates)
    
    print(f"DEBUG: End Date calculated: {end_date}")
    print(f"DEBUG: Max DB: {max_db_date}, Max Parcela: {max_parcela_date}, Futuro 12m: {futuro_12m}")
        
    # Ajustar para o primeiro dia do mês
    start_date = start_date.replace(day=1)
    end_date = end_date.replace(day=1)
    
    # Gerar lista de meses para projeção (Todo o intervalo)
    meses_projecao = []
    curr_date = start_date
    while curr_date <= end_date:
        meses_projecao.append(curr_date)
        curr_date += relativedelta(months=1)
            
    previsoes = []
    
    for cartao in cartoes:
        faturas = []
        total_restante = 0
        
        # Verificar configuração de fechamento
        config = FechamentoCartao.query.filter_by(meio_pagamento_id=cartao.id).first()
        dia_vencimento = config.dia_vencimento if config else 10
        dia_fechamento = config.dia_fechamento if config else 31 # Se não tem fechamento, considera fim do mês
        
        # Buscar TODAS as despesas deste cartão
        query_despesas = Despesa.query.filter_by(meio_pagamento_id=cartao.id)
        if not current_user.is_gerente():
            query_despesas = query_despesas.filter_by(user_id=current_user.id)
        
        despesas = query_despesas.all()
        
        # Dicionário para acumular totais por mês (ano, mes) -> valor
        totais_por_mes = {}
        
        for despesa in despesas:
            valor_parcela = despesa.valor / despesa.num_parcelas
            data_base = despesa.data_pagamento
            
            # Ajustar data inicial baseado no fechamento
            # Se a compra foi feita DEPOIS do fechamento, a primeira parcela cai no mês seguinte (ou próximo vencimento)
            # Simplificação: Se dia > dia_fechamento, pula 1 mês no início
            if data_base.day > dia_fechamento:
                data_base = data_base + relativedelta(months=1)
                
            # Distribuir parcelas
            for i in range(despesa.num_parcelas):
                data_parcela = data_base + relativedelta(months=i)
                chave = (data_parcela.year, data_parcela.month)
                
                if chave not in totais_por_mes:
                    totais_por_mes[chave] = 0
                totais_por_mes[chave] += valor_parcela
        
        for data_ref in meses_projecao:
            mes = data_ref.month
            ano = data_ref.year
            
            # Pegar total calculado
            total = totais_por_mes.get((ano, mes), 0)
            
            # Estimar data exata de vencimento
            try:
                vencimento = date(ano, mes, dia_vencimento)
            except ValueError:
                ultimo_dia = calendar.monthrange(ano, mes)[1]
                vencimento = date(ano, mes, ultimo_dia)
            
            # Status e cálculo de restante
            is_futuro = False
            if date.today() > vencimento:
                status = 'Fechada'
            else:
                status = 'Previsto'
                is_futuro = True
                # Acumular no total restante apenas faturas futuras
                total_restante += total
            
            # Adicionar fatura à lista
            faturas.append({
                'mes_referencia': data_ref.strftime('%b/%Y'),
                'mes_int': mes,
                'ano_int': ano,
                'vencimento': vencimento,
                'total': total,
                'status': status,
                'is_futuro': is_futuro
            })
            
        # Adicionar cartão (se tiver faturas ou for ativo)
        previsoes.append({
            'cartao': cartao.nome,
            'cartao_id': cartao.id,
            'faturas': faturas,
            'total_restante': total_restante
        })
    
    # Gerar labels para o cabeçalho (não mais usado no layout vertical, mas mantido por compatibilidade se precisar)
    meses_labels = [d.strftime('%b/%Y') for d in meses_projecao]
    
    # Calcular resumo global (soma de todas as faturas previstas de todos os cartões)
    resumo_global = {
        'total_geral': 0,
        'detalhes_mensais': []
    }
    
    # Agregar por mês através de todos os cartões
    totais_globais_por_mes = {}
    for previsao in previsoes:
        for fatura in previsao['faturas']:
            if fatura['status'] == 'Previsto':  # Apenas faturas futuras
                chave = (fatura['mes_int'], fatura['ano_int'])
                if chave not in totais_globais_por_mes:
                    totais_globais_por_mes[chave] = {
                        'mes_referencia': fatura['mes_referencia'],
                        'mes_int': fatura['mes_int'],
                        'ano_int': fatura['ano_int'],
                        'total': 0
                    }
                totais_globais_por_mes[chave]['total'] += fatura['total']
                resumo_global['total_geral'] += fatura['total']
    
    # Ordenar por ano/mês e converter para lista
    resumo_global['detalhes_mensais'] = sorted(
        totais_globais_por_mes.values(),
        key=lambda x: (x['ano_int'], x['mes_int'])
    )

    return render_template('relatorios/previsao_cartoes.html', 
                         previsoes=previsoes,
                         meses_labels=meses_labels,
                         resumo_global=resumo_global)

@relatorios_bp.route('/api/fatura-detalhes/<int:cartao_id>/<int:mes>/<int:ano>')
@login_required
def api_fatura_detalhes(cartao_id, mes, ano):
    """API para retornar detalhes da fatura (transações)"""
    try:
        # Buscar TODAS as despesas deste cartão
        query = Despesa.query.filter_by(meio_pagamento_id=cartao_id)
        
        if not current_user.is_gerente():
            query = query.filter_by(user_id=current_user.id)
            
        despesas = query.order_by(Despesa.data_pagamento, Despesa.id).all()
        
        # Verificar configuração de fechamento para este cartão
        config = FechamentoCartao.query.filter_by(meio_pagamento_id=cartao_id).first()
        dia_fechamento = config.dia_fechamento if config else 31
        
        detalhes = []
        
        for d in despesas:
            valor_parcela = d.valor / d.num_parcelas
            data_base = d.data_pagamento
            
            # Ajustar data inicial baseado no fechamento
            if data_base.day > dia_fechamento:
                data_base = data_base + relativedelta(months=1)
                
            # Verificar se alguma parcela cai no mês/ano solicitado
            for i in range(d.num_parcelas):
                data_parcela = data_base + relativedelta(months=i)
                
                if data_parcela.month == mes and data_parcela.year == ano:
                    # Encontrou! Adicionar aos detalhes
                    detalhes.append({
                        'data': d.data_pagamento.strftime('%d/%m/%Y'),
                        'descricao': d.descricao,
                        'valor': valor_parcela, # Valor da parcela, não total
                        'categoria': d.categoria.nome,
                        'parcelas': f"{i+1}/{d.num_parcelas}" if d.num_parcelas > 1 else "À vista"
                    })
                    # Não precisa verificar outras parcelas desta despesa (uma por mês)
                    break
            
        # Ordenar por data de compra
        detalhes.sort(key=lambda x: datetime.strptime(x['data'], '%d/%m/%Y'))
            
        return jsonify(detalhes)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# APIs para gráficos
@relatorios_bp.route('/api/graficos/despesas-categoria')
@login_required
def api_despesas_categoria():
    """API JSON para gráfico de despesas por categoria"""
    mes = request.args.get('mes', datetime.now().month, type=int)
    ano = request.args.get('ano', datetime.now().year, type=int)
    
    query = db.session.query(
        CategoriaDespesa.nome,
        func.sum(Despesa.valor).label('total')
    ).join(Despesa).filter(
        extract('month', Despesa.data_pagamento) == mes,
        extract('year', Despesa.data_pagamento) == ano,
        func.lower(CategoriaDespesa.nome) != 'pagamentos'
    )
    
    if not current_user.is_gerente():
        query = query.filter(Despesa.user_id == current_user.id)
    
    dados = query.group_by(CategoriaDespesa.nome).all()
    
    return jsonify({
        'labels': [d[0] for d in dados],
        'values': [float(d[1]) for d in dados]
    })

@relatorios_bp.route('/api/graficos/balanco-mensal')
@login_required
def api_balanco_mensal():
    """API JSON para gráfico de balanço mensal"""
    # Últimos 12 meses
    despesas = db.session.query(
        extract('year', Despesa.data_pagamento).label('ano'),
        extract('month', Despesa.data_pagamento).label('mes'),
        func.sum(Despesa.valor).label('total')
    ).join(Despesa.categoria).filter(
        func.lower(CategoriaDespesa.nome) != 'pagamentos'
    ).group_by('ano', 'mes').order_by('ano', 'mes').limit(12)
    
    if not current_user.is_gerente():
        despesas = despesas.filter(Despesa.user_id == current_user.id)
    
    despesas = despesas.all()
    
    receitas = db.session.query(
        extract('year', Receita.data_recebimento).label('ano'),
        extract('month', Receita.data_recebimento).label('mes'),
        func.sum(Receita.valor).label('total')
    ).group_by('ano', 'mes').order_by('ano', 'mes').limit(12)
    
    if not current_user.is_gerente():
        receitas = receitas.filter(Receita.user_id == current_user.id)
    
    receitas = receitas.all()
    
    labels = [f"{int(d.mes):02d}/{int(d.ano)}" for d in despesas]
    
    return jsonify({
        'labels': labels,
        'despesas': [float(d.total) for d in despesas],
        'receitas': [float(r.total) for r in receitas]
    })

@relatorios_bp.route('/despesas_por_categoria_evolucao')
@login_required
def despesas_por_categoria_evolucao():
    # Get filter parameters
    categoria_id = request.args.get('categoria_id')
    mes_inicio = request.args.get('mes_inicio')
    mes_fim = request.args.get('mes_fim')
    
    # Base query
    query = db.session.query(
        func.to_char(Despesa.data_pagamento, 'YYYY-MM').label('mes_ano'),
        func.sum(Despesa.valor).label('total'),
        func.count(Despesa.id).label('quantidade')
    ).join(CategoriaDespesa)
    
    # Apply filters
    if categoria_id:
        query = query.filter(Despesa.categoria_id == categoria_id)
        
    if mes_inicio:
        query = query.filter(func.to_char(Despesa.data_pagamento, 'YYYY-MM') >= mes_inicio)
        
    if mes_fim:
        query = query.filter(func.to_char(Despesa.data_pagamento, 'YYYY-MM') <= mes_fim)
        
    # Group and order
    query = query.group_by('mes_ano').order_by(desc('mes_ano'))
    
    resultados = query.all()
    
    # Get all categories for the filter dropdown
    categorias = CategoriaDespesa.query.order_by(CategoriaDespesa.nome).all()
    
    # Prepare data for chart
    chart_labels = []
    chart_data = []
    
    # Process results for display and chart (reverse for chronological chart)
    resultados_processados = []
    for r in reversed(resultados):
        mes_ano_obj = datetime.strptime(r.mes_ano, '%Y-%m')
        mes_ano_fmt = mes_ano_obj.strftime('%m/%Y')
        chart_labels.append(mes_ano_fmt)
        chart_data.append(float(r.total))
        
        # Calculate start and end date for the month
        import calendar
        ultimo_dia = calendar.monthrange(mes_ano_obj.year, mes_ano_obj.month)[1]
        data_inicio_mes = date(mes_ano_obj.year, mes_ano_obj.month, 1).strftime('%Y-%m-%d')
        data_fim_mes = date(mes_ano_obj.year, mes_ano_obj.month, ultimo_dia).strftime('%Y-%m-%d')
        
        resultados_processados.append({
            'mes_ano': r.mes_ano,
            'total': r.total,
            'quantidade': r.quantidade,
            'data_inicio': data_inicio_mes,
            'data_fim': data_fim_mes
        })

    # Reverse back to show most recent first in table
    resultados_processados.reverse()

    return render_template(
        'relatorios/despesas_por_categoria_evolucao.html',
        resultados=resultados_processados,
        categorias=categorias,

        categoria_selecionada=int(categoria_id) if categoria_id else None,
        mes_inicio=mes_inicio,
        mes_fim=mes_fim,
        chart_labels=chart_labels,
        chart_data=chart_data
    )

@relatorios_bp.route('/despesas_por_pagamento')
@login_required
def despesas_por_pagamento():
    # Get filter parameters
    meio_pagamento = request.args.get('meio_pagamento')
    
    # Base query
    query = db.session.query(
        func.to_char(Despesa.data_pagamento, 'YYYY-MM').label('mes_ano'),
        func.sum(Despesa.valor).label('total'),
        func.count(Despesa.id).label('quantidade')
    ).join(MeioPagamento)
    
    # Apply filters
    if meio_pagamento:
        query = query.filter(MeioPagamento.nome == meio_pagamento)
        
    # Group and order
    query = query.group_by('mes_ano').order_by(desc('mes_ano'))
    
    resultados = query.all()
    
    # Get all payment methods for the filter dropdown
    meios_pagamento = [m.nome for m in MeioPagamento.query.order_by(MeioPagamento.nome).all()]
    
    # Prepare data for chart
    chart_labels = []
    chart_data = []
    
    # Get payment method ID if selected
    meio_pagamento_id = None
    if meio_pagamento:
        mp = MeioPagamento.query.filter_by(nome=meio_pagamento).first()
        if mp:
            meio_pagamento_id = mp.id

    # Process results for display and chart (reverse for chronological chart)
    resultados_processados = []
    for r in reversed(resultados):
        mes_ano_obj = datetime.strptime(r.mes_ano, '%Y-%m')
        mes_ano_fmt = mes_ano_obj.strftime('%m/%Y')
        chart_labels.append(mes_ano_fmt)
        chart_data.append(float(r.total))
        
        # Calculate start and end date for the month
        import calendar
        ultimo_dia = calendar.monthrange(mes_ano_obj.year, mes_ano_obj.month)[1]
        data_inicio_mes = date(mes_ano_obj.year, mes_ano_obj.month, 1).strftime('%Y-%m-%d')
        data_fim_mes = date(mes_ano_obj.year, mes_ano_obj.month, ultimo_dia).strftime('%Y-%m-%d')
        
        resultados_processados.append({
            'mes_ano': r.mes_ano,
            'total': r.total,
            'quantidade': r.quantidade,
            'data_inicio': data_inicio_mes,
            'data_fim': data_fim_mes
        })
        
    # Reverse back to show most recent first in table
    resultados_processados.reverse()

    return render_template(
        'relatorios/despesas_por_pagamento.html',
        resultados=resultados_processados,
        meios_pagamento=meios_pagamento,
        meio_selecionado=meio_pagamento,
        meio_pagamento_id=meio_pagamento_id,
        chart_labels=chart_labels,
        chart_data=chart_data
    )

@relatorios_bp.route('/despesas_entre_datas')
@login_required
def despesas_entre_datas():
    # Get filter parameters
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    resultados = []
    total_geral = 0
    chart_labels = []
    chart_data = []
    
    if data_inicio and data_fim:
        # Query
        query = db.session.query(
            CategoriaDespesa.id.label('categoria_id'),
            CategoriaDespesa.nome.label('categoria'),
            func.sum(Despesa.valor).label('total'),
            func.count(Despesa.id).label('quantidade')
        ).join(CategoriaDespesa).filter(
            Despesa.data_pagamento.between(data_inicio, data_fim)
        )
        
        # Group and order
        query = query.group_by(CategoriaDespesa.id, CategoriaDespesa.nome).order_by(desc('total'))
        
        resultados = query.all()
        
        # Calculate total
        total_geral = sum(r.total for r in resultados)
        
        # Prepare data for chart
        for r in resultados:
            chart_labels.append(r.categoria)
            chart_data.append(float(r.total))
            
    return render_template(
        'relatorios/despesas_entre_datas.html',
        resultados=resultados,
        data_inicio=data_inicio,
        data_fim=data_fim,
        total_geral=total_geral,
        chart_labels=chart_labels,
        chart_data=chart_data
    )

@relatorios_bp.route('/despesas_mensais_periodo')
@login_required
def despesas_mensais_periodo():
    # Get filter parameters
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    resultados = []
    total_geral = 0
    chart_labels = []
    chart_data = []
    
    if data_inicio and data_fim:
        # Query
        query = db.session.query(
            func.to_char(Despesa.data_pagamento, 'YYYY-MM').label('mes_ano'),
            func.sum(Despesa.valor).label('total'),
            func.count(Despesa.id).label('quantidade')
        ).filter(
            Despesa.data_pagamento.between(data_inicio, data_fim)
        )
        
        # Group and order
        query = query.group_by('mes_ano').order_by('mes_ano')
        
        resultados = query.all()
        
        # Calculate total
        total_geral = sum(r.total for r in resultados)
        
        # Prepare data for chart
        resultados_processados = []
        for r in resultados:
            mes_ano_obj = datetime.strptime(r.mes_ano, '%Y-%m')
            mes_ano_fmt = mes_ano_obj.strftime('%m/%Y')
            chart_labels.append(mes_ano_fmt)
            chart_data.append(float(r.total))
            
            # Calculate start and end date for the month
            import calendar
            ultimo_dia = calendar.monthrange(mes_ano_obj.year, mes_ano_obj.month)[1]
            data_inicio_mes = date(mes_ano_obj.year, mes_ano_obj.month, 1).strftime('%Y-%m-%d')
            data_fim_mes = date(mes_ano_obj.year, mes_ano_obj.month, ultimo_dia).strftime('%Y-%m-%d')
            
            resultados_processados.append({
                'mes_ano': r.mes_ano,
                'total': r.total,
                'quantidade': r.quantidade,
                'data_inicio': data_inicio_mes,
                'data_fim': data_fim_mes
            })
        resultados = resultados_processados
            
    return render_template(
        'relatorios/despesas_mensais_periodo.html',
        resultados=resultados,
        data_inicio=data_inicio,
        data_fim=data_fim,
        total_geral=total_geral,
        chart_labels=chart_labels,
        chart_data=chart_data
    )
