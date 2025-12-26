from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from routes.auth import admin_required, gerente_required
from models import db, User, CategoriaDespesa, CategoriaReceita, MeioPagamento, MeioRecebimento, Orcamento, FechamentoCartao, Configuracao, Despesa
from utils.supabase_client import SupabaseClient
import json
from datetime import datetime
import os

config_bp = Blueprint('config', __name__)

@config_bp.route('/importar-dados-antigos', methods=['GET', 'POST'])
@login_required
@admin_required
def importar_dados_antigos():
    """Importar dados do sistema antigo (apenas admin)"""
    if request.method == 'POST':
        from utils.importador import importar_dados_antigos, importar_fluxo_caixa
        from flask import current_app
        
        # Obter caminhos dos arquivos selecionados
        caminho_financas = request.form.get('caminho_financas')
        caminho_receitas = request.form.get('caminho_receitas')
        caminho_fluxo_caixa = request.form.get('caminho_fluxo_caixa')
        
        # Verificar qual tipo de importação fazer
        if caminho_fluxo_caixa:
            # Importar fluxo de caixa
            if not os.path.exists(caminho_fluxo_caixa):
                flash(f'Arquivo de fluxo de caixa não encontrado: {caminho_fluxo_caixa}', 'danger')
                return redirect(url_for('config.importar_dados_antigos'))
            
            try:
                relatorio = importar_fluxo_caixa(
                    current_app._get_current_object(),
                    caminho_fluxo_caixa,
                    user_id=current_user.id
                )
                
                if relatorio['sucesso']:
                    flash(f"""Importação de Fluxo de Caixa concluída!
                        Balanços Mensais: {relatorio['balancos_mensais']}
                        Eventos de Caixa: {relatorio['eventos_caixa']}
                    """, 'success')
                else:
                    flash(f"Erro na importação: {'; '.join(relatorio['erros'])}", 'danger')
                    
            except Exception as e:
                flash(f'Erro ao importar fluxo de caixa: {str(e)}', 'danger')
                
        elif caminho_financas and caminho_receitas:
            # Importar despesas e receitas
            # Verificar se os arquivos foram selecionados
            if not caminho_financas or not caminho_receitas:
                flash('Por favor, selecione os arquivos de despesas e receitas para importar!', 'warning')
                return redirect(url_for('config.importar_dados_antigos'))
            
            # Verificar se os arquivos existem
            if not os.path.exists(caminho_financas):
                flash(f'Arquivo de despesas não encontrado: {caminho_financas}', 'danger')
                return redirect(url_for('config.importar_dados_antigos'))
            
            if not os.path.exists(caminho_receitas):
                flash(f'Arquivo de receitas não encontrado: {caminho_receitas}', 'danger')
                return redirect(url_for('config.importar_dados_antigos'))
            
            try:
                # Executar importação
                relatorio = importar_dados_antigos(
                    current_app._get_current_object(),
                    caminho_financas,
                    caminho_receitas,
                    user_id=current_user.id
                )
                
                if relatorio['sucesso']:
                    flash(f"""Importação concluída com sucesso!
                        Categorias de Despesa: {relatorio['categorias_despesa']}
                        Categorias de Receita: {relatorio['categorias_receita']}
                        Meios de Pagamento: {relatorio['meios_pagamento']}
                        Meios de Recebimento: {relatorio['meios_recebimento']}
                        Despesas: {relatorio['despesas']}
                        Receitas: {relatorio['receitas']}
                    """, 'success')
                else:
                    flash(f"Erro na importação: {'; '.join(relatorio['erros'])}", 'danger')
                    
            except Exception as e:
                flash(f'Erro ao importar dados: {str(e)}', 'danger')
        else:
            flash('Selecione arquivos para importar!', 'warning')
        
        return redirect(url_for('config.importar_dados_antigos'))
    
    # GET - mostrar formulário
    # Buscar todos os arquivos .db na pasta do projeto
    diretorio_atual = os.getcwd()
    arquivos_db = []
    
    try:
        for arquivo in os.listdir(diretorio_atual):
            if arquivo.endswith('.db'):
                caminho_completo = os.path.join(diretorio_atual, arquivo)
                tamanho = os.path.getsize(caminho_completo)
                tamanho_mb = tamanho / (1024 * 1024)
                
                # Determinar tipo do banco
                tipo = 'desconhecido'
                if 'receita' in arquivo.lower():
                    tipo = 'receitas'
                elif 'fluxo' in arquivo.lower() or 'caixa' in arquivo.lower():
                    tipo = 'fluxo_caixa'
                elif arquivo.startswith('financas') and 'receita' not in arquivo.lower():
                    tipo = 'despesas'
                elif arquivo == 'financeiro.db':
                    tipo = 'sistema_novo'
                
                arquivos_db.append({
                    'nome': arquivo,
                    'caminho': caminho_completo,
                    'tamanho_mb': tamanho_mb,
                    'tipo': tipo
                })
    except Exception as e:
        flash(f'Erro ao listar arquivos: {str(e)}', 'warning')
    
    # Ordenar: despesas primeiro, depois receitas, depois outros
    ordem_tipo = {'despesas': 0, 'receitas': 1, 'fluxo_caixa': 2, 'desconhecido': 3, 'sistema_novo': 4}
    arquivos_db.sort(key=lambda x: (ordem_tipo.get(x['tipo'], 99), x['nome']))
    
    return render_template('config/importar_dados.html', 
                         arquivos_db=arquivos_db,
                         total_arquivos=len(arquivos_db))

@config_bp.route('/categorias-despesa', methods=['GET', 'POST'])
@login_required
@gerente_required
def categorias_despesa():
    """Gerenciar categorias de despesa"""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'criar':
            nome = request.form.get('nome')
            if CategoriaDespesa.query.filter_by(nome=nome).first():
                flash('Categoria já existe.', 'warning')
            else:
                nova_categoria = CategoriaDespesa(nome=nome, ativo=True)
                db.session.add(nova_categoria)
                db.session.commit()
                flash('Categoria criada com sucesso!', 'success')
        
        elif action == 'editar':
            id = int(request.form.get('id'))
            nome = request.form.get('nome')
            categoria = CategoriaDespesa.query.get(id)
            if categoria:
                categoria.nome = nome
                db.session.commit()
                flash('Categoria atualizada!', 'success')
        
        elif action == 'ativar_desativar':
            id = int(request.form.get('id'))
            categoria = CategoriaDespesa.query.get(id)
            if categoria:
                categoria.ativo = not categoria.ativo
                db.session.commit()
                status = 'ativada' if categoria.ativo else 'desativada'
                flash(f'Categoria {status}!', 'success')
        
        return redirect(url_for('config.categorias_despesa'))
    
    categorias = CategoriaDespesa.query.order_by(CategoriaDespesa.nome).all()
    return render_template('config/categorias_despesa.html', categorias=categorias)

@config_bp.route('/categorias-receita', methods=['GET', 'POST'])
@login_required
@gerente_required
def categorias_receita():
    """Gerenciar categorias de receita"""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'criar':
            nome = request.form.get('nome')
            if CategoriaReceita.query.filter_by(nome=nome).first():
                flash('Categoria já existe.', 'warning')
            else:
                nova_categoria = CategoriaReceita(nome=nome, ativo=True)
                db.session.add(nova_categoria)
                db.session.commit()
                flash('Categoria criada com sucesso!', 'success')
        
        elif action == 'editar':
            id = int(request.form.get('id'))
            nome = request.form.get('nome')
            categoria = CategoriaReceita.query.get(id)
            if categoria:
                categoria.nome = nome
                db.session.commit()
                flash('Categoria atualizada!', 'success')
        
        elif action == 'ativar_desativar':
            id = int(request.form.get('id'))
            categoria = CategoriaReceita.query.get(id)
            if categoria:
                categoria.ativo = not categoria.ativo
                db.session.commit()
                status = 'ativada' if categoria.ativo else 'desativada'
                flash(f'Categoria {status}!', 'success')
        
        return redirect(url_for('config.categorias_receita'))
    
    categorias = CategoriaReceita.query.order_by(CategoriaReceita.nome).all()
    return render_template('config/categorias_receita.html', categorias=categorias)

@config_bp.route('/meios-pagamento', methods=['GET', 'POST'])
@login_required
@gerente_required
def meios_pagamento():
    """Gerenciar meios de pagamento"""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'criar':
            nome = request.form.get('nome')
            tipo = request.form.get('tipo')
            if MeioPagamento.query.filter_by(nome=nome).first():
                flash('Meio de pagamento já existe.', 'warning')
            else:
                novo_meio = MeioPagamento(nome=nome, tipo=tipo, ativo=True)
                db.session.add(novo_meio)
                db.session.commit()
                flash('Meio de pagamento criado com sucesso!', 'success')
        
        elif action == 'editar':
            id = int(request.form.get('id'))
            nome = request.form.get('nome')
            tipo = request.form.get('tipo')
            meio = MeioPagamento.query.get(id)
            if meio:
                meio.nome = nome
                meio.tipo = tipo
                db.session.commit()
                flash('Meio de pagamento atualizado!', 'success')
        
        elif action == 'ativar_desativar':
            id = int(request.form.get('id'))
            meio = MeioPagamento.query.get(id)
            if meio:
                meio.ativo = not meio.ativo
                db.session.commit()
                status = 'ativado' if meio.ativo else 'desativado'
                flash(f'Meio de pagamento {status}!', 'success')
        
        return redirect(url_for('config.meios_pagamento'))
    
    meios = MeioPagamento.query.order_by(MeioPagamento.nome).all()
    return render_template('config/meios_pagamento.html', meios=meios)

@config_bp.route('/meios-recebimento', methods=['GET', 'POST'])
@login_required
@gerente_required
def meios_recebimento():
    """Gerenciar meios de recebimento"""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'criar':
            nome = request.form.get('nome')
            if MeioRecebimento.query.filter_by(nome=nome).first():
                flash('Meio de recebimento já existe.', 'warning')
            else:
                novo_meio = MeioRecebimento(nome=nome, ativo=True)
                db.session.add(novo_meio)
                db.session.commit()
                flash('Meio de recebimento criado com sucesso!', 'success')
        
        elif action == 'editar':
            id = int(request.form.get('id'))
            nome = request.form.get('nome')
            meio = MeioRecebimento.query.get(id)
            if meio:
                meio.nome = nome
                db.session.commit()
                flash('Meio de recebimento atualizado!', 'success')
        
        elif action == 'ativar_desativar':
            id = int(request.form.get('id'))
            meio = MeioRecebimento.query.get(id)
            if meio:
                meio.ativo = not meio.ativo
                db.session.commit()
                status = 'ativado' if meio.ativo else 'desativado'
                flash(f'Meio de recebimento {status}!', 'success')
        
        return redirect(url_for('config.meios_recebimento'))
    
    meios = MeioRecebimento.query.order_by(MeioRecebimento.nome).all()
    return render_template('config/meios_recebimento.html', meios=meios)

@config_bp.route('/usuarios', methods=['GET', 'POST'])
@login_required
@admin_required
def usuarios():
    """Gerenciar usuários (apenas admin)"""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'ativar_desativar':
            id = int(request.form.get('id'))
            user = User.query.get(id)
            if user and user.id != current_user.id:  # Não pode desativar a si mesmo
                user.ativo = not user.ativo
                db.session.commit()
                status = 'ativado' if user.ativo else 'desativado'
                flash(f'Usuário {status}!', 'success')
            elif user and user.id == current_user.id:
                flash('Você não pode desativar sua própria conta!', 'danger')
        
        elif action == 'alterar_nivel':
            id = int(request.form.get('id'))
            nivel = request.form.get('nivel')
            user = User.query.get(id)
            if user and user.id != current_user.id:
                user.nivel_acesso = nivel
                db.session.commit()
                flash('Nível de acesso alterado!', 'success')
        
        return redirect(url_for('config.usuarios'))
    
    usuarios = User.query.order_by(User.username).all()
    return render_template('config/usuarios.html', usuarios=usuarios)

@config_bp.route('/orcamento', methods=['GET', 'POST'])
@login_required
@gerente_required
def orcamento():
    """Gerenciar orçamento geral por categoria"""
    if request.method == 'POST':
        action = request.form.get('action', 'salvar')
        
        if action == 'excluir':
            orcamento_id = int(request.form.get('orcamento_id'))
            orcamento = Orcamento.query.get(orcamento_id)
            if orcamento and orcamento.user_id == current_user.id:
                db.session.delete(orcamento)
                db.session.commit()
                flash('Orçamento excluído!', 'success')
            return redirect(url_for('config.orcamento'))
        
        categoria_id = int(request.form.get('categoria_id'))
        valor_orcado = float(request.form.get('valor_orcado').replace(',', '.'))
        
        # Verificar se já existe orçamento para esta categoria
        orcamento_existente = Orcamento.query.filter_by(
            categoria_id=categoria_id,
            user_id=current_user.id
        ).first()
        
        if orcamento_existente:
            orcamento_existente.valor_orcado = valor_orcado
            flash('Orçamento atualizado!', 'success')
        else:
            novo_orcamento = Orcamento(
                categoria_id=categoria_id,
                valor_orcado=valor_orcado,
                user_id=current_user.id
            )
            db.session.add(novo_orcamento)
            flash('Orçamento cadastrado!', 'success')
        
        db.session.commit()
        return redirect(url_for('config.orcamento'))
    
    categorias = CategoriaDespesa.query.filter_by(ativo=True).order_by(CategoriaDespesa.nome).all()
    orcamentos = Orcamento.query.filter_by(user_id=current_user.id).all()
    
    return render_template('config/orcamento.html', 
                          categorias=categorias, 
                          orcamentos=orcamentos)

@config_bp.route('/cartoes', methods=['GET', 'POST'])
@login_required
@gerente_required
def cartoes():
    """Configurar fechamento de cartões"""
    if request.method == 'POST':
        meio_pagamento_id = int(request.form.get('meio_pagamento_id'))
        dia_fechamento = int(request.form.get('dia_fechamento'))
        dia_vencimento = int(request.form.get('dia_vencimento'))
        
        # Verificar se já existe configuração para este cartão
        config_existente = FechamentoCartao.query.filter_by(meio_pagamento_id=meio_pagamento_id).first()
        
        if config_existente:
            config_existente.dia_fechamento = dia_fechamento
            config_existente.dia_vencimento = dia_vencimento
            flash('Configuração de cartão atualizada!', 'success')
        else:
            nova_config = FechamentoCartao(
                meio_pagamento_id=meio_pagamento_id,
                dia_fechamento=dia_fechamento,
                dia_vencimento=dia_vencimento
            )
            db.session.add(nova_config)
            flash('Configuração de cartão cadastrada!', 'success')
        
        db.session.commit()
        return redirect(url_for('config.cartoes'))
    
    # Buscar apenas meios de pagamento do tipo cartão
    cartoes = MeioPagamento.query.filter_by(tipo='cartao', ativo=True).order_by(MeioPagamento.nome).all()
    configuracoes = FechamentoCartao.query.all()
    
    return render_template('config/cartoes.html', cartoes=cartoes, configuracoes=configuracoes)


@config_bp.route('/importar-supabase', methods=['GET'])
@login_required
@admin_required
def importar_supabase():
    """Página de importação do Supabase"""
    # Buscar configurações salvas
    config_url = Configuracao.query.filter_by(chave='supabase_url').first()
    config_key = Configuracao.query.filter_by(chave='supabase_key').first()
    config_table = Configuracao.query.filter_by(chave='supabase_table').first()
    
    return render_template('config/importar_supabase.html',
                         supabase_url=config_url.valor if config_url else '',
                         supabase_key=config_key.valor if config_key else '',
                         supabase_table=config_table.valor if config_table else '')

@config_bp.route('/importar-supabase/salvar-config', methods=['POST'])
@login_required
@admin_required
def salvar_config_supabase():
    """Salvar configurações do Supabase"""
    try:
        data = request.get_json()
        url = data.get('url')
        key = data.get('key')
        table = data.get('table')
        
        configs = {
            'supabase_url': url,
            'supabase_key': key,
            'supabase_table': table
        }
        
        for chave, valor in configs.items():
            config = Configuracao.query.filter_by(chave=chave).first()
            if config:
                config.valor = valor
            else:
                new_config = Configuracao(chave=chave, valor=valor)
                db.session.add(new_config)
        
        db.session.commit()
        return {'success': True}
    except Exception as e:
        return {'success': False, 'message': str(e)}

@config_bp.route('/importar-supabase/testar', methods=['POST'])
@login_required
@admin_required
def testar_conexao_supabase():
    """Testar conexão com Supabase"""
    try:
        data = request.get_json()
        client = SupabaseClient(data.get('url'), data.get('key'))
        result = client.test_connection(data.get('table'))
        return result
    except Exception as e:
        return {'success': False, 'message': str(e)}

@config_bp.route('/importar-supabase/buscar', methods=['POST'])
@login_required
@admin_required
def buscar_dados_supabase():
    """Buscar dados do Supabase"""
    try:
        data = request.get_json()
        client = SupabaseClient(data.get('url'), data.get('key'))
        result = client.fetch_data(data.get('table'))
        return result
    except Exception as e:
        return {'success': False, 'message': str(e)}

@config_bp.route('/importar-supabase/importar', methods=['POST'])
@login_required
@admin_required
def importar_dados_supabase():
    """Importar dados selecionados"""
    try:
        data = request.get_json()
        items = data.get('items', [])
        config_data = data.get('config', {})
        
        client = SupabaseClient(config_data.get('url'), config_data.get('key'))
        table = config_data.get('table')
        
        importados = 0
        erros = []
        
        for item in items:
            try:
                # Verificar/Criar Categoria
                cat_nome = item.get('categoria', 'Outros')
                categoria = CategoriaDespesa.query.filter_by(nome=cat_nome).first()
                if not categoria:
                    categoria = CategoriaDespesa(nome=cat_nome, ativo=True)
                    db.session.add(categoria)
                    db.session.commit()
                
                # Verificar/Criar Meio de Pagamento
                mp_nome = item.get('meio_pagamento', 'Outros')
                meio_pagamento = MeioPagamento.query.filter_by(nome=mp_nome).first()
                if not meio_pagamento:
                    meio_pagamento = MeioPagamento(nome=mp_nome, tipo='outros', ativo=True)
                    db.session.add(meio_pagamento)
                    db.session.commit()
                
                # Criar Despesa
                valor_str = str(item.get('valor', '0'))
                # Remove thousand separator (.) and replace decimal separator (,) with (.)
                valor_str = valor_str.replace('.', '').replace(',', '.')
                valor = float(valor_str)
                
                # Converter data (assumindo formato YYYY-MM-DD ou DD/MM/YYYY)
                data_str = item.get('data_despesa')
                try:
                    if '/' in data_str:
                        data_despesa = datetime.strptime(data_str, '%d/%m/%Y').date()
                    else:
                        data_despesa = datetime.strptime(data_str, '%Y-%m-%d').date()
                except:
                    data_despesa = datetime.today().date()
                
                nova_despesa = Despesa(
                    descricao=item.get('descricao'),
                    valor=valor,
                    data_pagamento=data_despesa,
                    num_parcelas=int(item.get('parcelas', 1)),
                    categoria_id=categoria.id,
                    meio_pagamento_id=meio_pagamento.id,
                    user_id=current_user.id
                )
                db.session.add(nova_despesa)
                
                # Marcar como importado no Supabase
                supabase_id = item.get('id')
                if supabase_id:
                    client.update_record(table, supabase_id, {'migrado': True})
                
                importados += 1
                
            except Exception as e:
                erros.append(f"Erro no item {item.get('descricao')}: {str(e)}")
        
        db.session.commit()
        
        return {
            'success': True, 
            'message': f'{importados} itens importados com sucesso!',
            'erros': erros
        }
        
    except Exception as e:
        return {'success': False, 'message': str(e)}

@config_bp.route('/importar-supabase/excluir-item', methods=['POST'])
@login_required
@admin_required
def excluir_item_supabase():
    """Excluir item do Supabase"""
    try:
        data = request.get_json()
        id = data.get('id')
        config_data = data.get('config', {})
        
        client = SupabaseClient(config_data.get('url'), config_data.get('key'))
        result = client.delete_record(config_data.get('table'), id)
        
        return result
    except Exception as e:
        return {'success': False, 'message': str(e)}
