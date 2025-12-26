"""
Importador de dados do sistema antigo (sistema_financeiro_v14.py)
para o novo sistema Flask

Este módulo importa dados de:
- financas.db (despesas antigas)
- financas_receitas.db (receitas antigas)

Para o novo banco unificado: financeiro.db
"""

import sqlite3
from datetime import datetime
from models import db, User, CategoriaDespesa, CategoriaReceita, MeioPagamento, MeioRecebimento, Despesa, Receita, BalancoMensal, EventoCaixaAvulso

class ImportadorDadosAntigos:
    def __init__(self, app, user_id=1):
        """
        Inicializa o importador
        
        Args:
            app: Instância da aplicação Flask
            user_id: ID do usuário proprietário dos dados (padrão: 1 = admin)
        """
        self.app = app
        self.user_id = user_id
        self.relatorio = {
            'categorias_despesa': 0,
            'categorias_receita': 0,
            'meios_pagamento': 0,
            'meios_recebimento': 0,
            'despesas': 0,
            'receitas': 0,
            'balancos_mensais': 0,
            'eventos_caixa': 0,
            'erros': [],
            'sucesso': False
        }
    
    def importar_tudo(self, caminho_financas_db='financas.db', caminho_receitas_db='financas_receitas.db'):
        """
        Importa todos os dados dos bancos antigos
        
        Args:
            caminho_financas_db: Caminho para financas.db
            caminho_receitas_db: Caminho para financas_receitas.db
            
        Returns:
            dict: Relatório da importação
        """
        with self.app.app_context():
            try:
                # Importar categorias e meios de pagamento de despesas
                self._importar_categorias_despesa(caminho_financas_db)
                self._importar_meios_pagamento(caminho_financas_db)
                
                # Importar categorias e meios de recebimento de receitas
                self._importar_categorias_receita(caminho_receitas_db)
                self._importar_meios_recebimento(caminho_receitas_db)
                
                # Importar despesas
                self._importar_despesas(caminho_financas_db)
                
                # Importar receitas
                self._importar_receitas(caminho_receitas_db)
                
                db.session.commit()
                self.relatorio['sucesso'] = True
                
            except Exception as e:
                db.session.rollback()
                self.relatorio['sucesso'] = False
                self.relatorio['erros'].append(f"Erro geral: {str(e)}")
                
        return self.relatorio
    
    def _importar_categorias_despesa(self, caminho_db):
        """Importa categorias de despesa do banco antigo"""
        try:
            conn = sqlite3.connect(caminho_db)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, nome FROM categorias")
            categorias_antigas = cursor.fetchall()
            
            for id_antigo, nome in categorias_antigas:
                # Verificar se já existe
                categoria_existente = CategoriaDespesa.query.filter_by(nome=nome).first()
                if not categoria_existente:
                    nova_categoria = CategoriaDespesa(nome=nome, ativo=True)
                    db.session.add(nova_categoria)
                    self.relatorio['categorias_despesa'] += 1
            
            conn.close()
            db.session.commit()
            
        except Exception as e:
            self.relatorio['erros'].append(f"Erro ao importar categorias de despesa: {str(e)}")
    
    def _importar_categorias_receita(self, caminho_db):
        """Importa categorias de receita do banco antigo"""
        try:
            conn = sqlite3.connect(caminho_db)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, nome FROM categorias_receita")
            categorias_antigas = cursor.fetchall()
            
            for id_antigo, nome in categorias_antigas:
                categoria_existente = CategoriaReceita.query.filter_by(nome=nome).first()
                if not categoria_existente:
                    nova_categoria = CategoriaReceita(nome=nome, ativo=True)
                    db.session.add(nova_categoria)
                    self.relatorio['categorias_receita'] += 1
            
            conn.close()
            db.session.commit()
            
        except Exception as e:
            self.relatorio['erros'].append(f"Erro ao importar categorias de receita: {str(e)}")
    
    def _importar_meios_pagamento(self, caminho_db):
        """Importa meios de pagamento do banco antigo"""
        try:
            conn = sqlite3.connect(caminho_db)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, nome FROM meios_pagamento")
            meios_antigos = cursor.fetchall()
            
            for id_antigo, nome in meios_antigos:
                meio_existente = MeioPagamento.query.filter_by(nome=nome).first()
                if not meio_existente:
                    # Determinar tipo baseado no nome
                    tipo = 'outro'
                    nome_lower = nome.lower()
                    if 'cartão' in nome_lower or 'cartao' in nome_lower:
                        tipo = 'cartao'
                    elif 'pix' in nome_lower:
                        tipo = 'pix'
                    elif 'transferência' in nome_lower or 'transferencia' in nome_lower:
                        tipo = 'transferencia'
                    elif 'dinheiro' in nome_lower:
                        tipo = 'dinheiro'
                    elif 'boleto' in nome_lower:
                        tipo = 'boleto'
                    
                    novo_meio = MeioPagamento(nome=nome, tipo=tipo, ativo=True)
                    db.session.add(novo_meio)
                    self.relatorio['meios_pagamento'] += 1
            
            conn.close()
            db.session.commit()
            
        except Exception as e:
            self.relatorio['erros'].append(f"Erro ao importar meios de pagamento: {str(e)}")
    
    def _importar_meios_recebimento(self, caminho_db):
        """Importa meios de recebimento do banco antigo"""
        try:
            conn = sqlite3.connect(caminho_db)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, nome FROM meios_recebimento")
            meios_antigos = cursor.fetchall()
            
            for id_antigo, nome in meios_antigos:
                meio_existente = MeioRecebimento.query.filter_by(nome=nome).first()
                if not meio_existente:
                    novo_meio = MeioRecebimento(nome=nome, ativo=True)
                    db.session.add(novo_meio)
                    self.relatorio['meios_recebimento'] += 1
            
            conn.close()
            db.session.commit()
            
        except Exception as e:
            self.relatorio['erros'].append(f"Erro ao importar meios de recebimento: {str(e)}")
    
    def _importar_despesas(self, caminho_db):
        """Importa despesas do banco antigo"""
        try:
            print(f"[DEBUG] Conectando ao banco: {caminho_db}")
            conn = sqlite3.connect(caminho_db)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT d.id, d.data_pagamento, d.descricao, d.valor, d.conta_despesa, d.meio_pagamento, 
                       d.num_parcelas, d.data_registro
                FROM despesas d
            """)
            despesas_antigas = cursor.fetchall()
            print(f"[DEBUG] Despesas encontradas no banco antigo: {len(despesas_antigas)}")
            
            for (id_antigo, data, descricao, valor, categoria_nome, meio_nome, 
                 num_parcelas, data_registro) in despesas_antigas:
                
                # Buscar categoria correspondente
                categoria = CategoriaDespesa.query.filter_by(nome=categoria_nome).first()
                if not categoria:
                    # Criar categoria se não existir
                    categoria = CategoriaDespesa(nome=categoria_nome, ativo=True)
                    db.session.add(categoria)
                    db.session.flush()
                
                # Buscar  meio de pagamento correspondente
                meio = MeioPagamento.query.filter_by(nome=meio_nome).first()
                if not meio:
                    # Criar meio se não existir
                    meio = MeioPagamento(nome=meio_nome, tipo='outro', ativo=True)
                    db.session.add(meio)
                    db.session.flush()
                
                # Converter datas
                try:
                    data_pagamento = datetime.strptime(data, '%Y-%m-%d').date()
                except:
                    data_pagamento = datetime.now().date()
                
                try:
                    data_reg = datetime.strptime(data_registro, '%Y-%m-%d %H:%M:%S')
                except:
                    data_reg = datetime.now()
                
                # Verificar se a despesa já existe (evitar duplicatas)
                despesa_existente = Despesa.query.filter_by(
                    descricao=descricao,
                    valor=float(valor),
                    data_pagamento=data_pagamento,
                    user_id=self.user_id
                ).first()
                
                if not despesa_existente:
                    # Criar despesa
                    nova_despesa = Despesa(
                        descricao=descricao,
                        valor=float(valor),
                        data_pagamento=data_pagamento,
                        categoria_id=categoria.id,
                        meio_pagamento_id=meio.id,
                        num_parcelas=num_parcelas or 1,
                        user_id=self.user_id,
                        data_registro=data_reg
                    )
                    db.session.add(nova_despesa)
                    self.relatorio['despesas'] += 1
            
            conn.close()
            db.session.commit()
            print(f"[DEBUG] Despesas importadas com sucesso: {self.relatorio['despesas']}")
            
        except Exception as e:
            print(f"[DEBUG] ERRO ao importar despesas: {str(e)}")
            self.relatorio['erros'].append(f"Erro ao importar despesas: {str(e)}")
    
    def _importar_receitas(self, caminho_db):
        """Importa receitas do banco antigo"""
        try:
            print(f"[DEBUG] Conectando ao banco de receitas: {caminho_db}")
            conn = sqlite3.connect(caminho_db)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT r.id, r.data_recebimento, r.descricao, r.valor, r.conta_receita, r.meio_recebimento,
                       r.num_parcelas, r.data_registro
                FROM receitas r
            """)
            receitas_antigas = cursor.fetchall()
            print(f"[DEBUG] Receitas encontradas no banco antigo: {len(receitas_antigas)}")
            
            for (id_antigo, data, descricao, valor, categoria_nome, meio_nome,
                 num_parcelas, data_registro) in receitas_antigas:
                
                # Buscar categoria correspondente
                categoria = CategoriaReceita.query.filter_by(nome=categoria_nome).first()
                if not categoria:
                    categoria = CategoriaReceita(nome=categoria_nome, ativo=True)
                    db.session.add(categoria)
                    db.session.flush()
                
                # Buscar meio de recebimento correspondente
                meio = MeioRecebimento.query.filter_by(nome=meio_nome).first()
                if not meio:
                    meio = MeioRecebimento(nome=meio_nome, ativo=True)
                    db.session.add(meio)
                    db.session.flush()
                
                # Converter datas
                try:
                    data_recebimento = datetime.strptime(data, '%Y-%m-%d').date()
                except:
                    data_recebimento = datetime.now().date()
                
                try:
                    data_reg = datetime.strptime(data_registro, '%Y-%m-%d %H:%M:%S')
                except:
                    data_reg = datetime.now()
                
                # Verificar se a receita já existe (evitar duplicatas)
                receita_existente = Receita.query.filter_by(
                    descricao=descricao,
                    valor=float(valor),
                    data_recebimento=data_recebimento,
                    user_id=self.user_id
                ).first()
                
                if not receita_existente:
                    # Criar receita
                    nova_receita = Receita(
                        descricao=descricao,
                        valor=float(valor),
                        data_recebimento=data_recebimento,
                        categoria_id=categoria.id,
                        meio_recebimento_id=meio.id,
                        num_parcelas=num_parcelas or 1,
                        user_id=self.user_id,
                        data_registro=data_reg
                    )
                    db.session.add(nova_receita)
                    self.relatorio['receitas'] += 1
            
            conn.close()
            db.session.commit()
            print(f"[DEBUG] Receitas importadas com sucesso: {self.relatorio['receitas']}")
            
        except Exception as e:
            print(f"[DEBUG] ERRO ao importar receitas: {str(e)}")
            self.relatorio['erros'].append(f"Erro ao importar receitas: {str(e)}")
    
    def importar_fluxo_caixa(self, caminho_fluxo_caixa='fluxo_caixa.db'):
        """
        Importa dados de fluxo de caixa do banco antigo
        
        Args:
            caminho_fluxo_caixa: Caminho para fluxo_caixa.db
            
        Returns:
            dict: Relatório da importação
        """
        with self.app.app_context():
            try:
                # Importar balanços mensais
                self._importar_balancos_mensais(caminho_fluxo_caixa)
                
                # Importar eventos de caixa avulsos
                self._importar_eventos_caixa(caminho_fluxo_caixa)
                
                db.session.commit()
                self.relatorio['sucesso'] = True
                
            except Exception as e:
                db.session.rollback()
                self.relatorio['sucesso'] = False
                self.relatorio['erros'].append(f"Erro ao importar fluxo de caixa: {str(e)}")
                
        return self.relatorio
    
    def _importar_balancos_mensais(self, caminho_db):
        """Importa balanços mensais do banco antigo"""
        try:
            conn = sqlite3.connect(caminho_db)
            cursor = conn.cursor()
            
            # Verificar se a tabela existe
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='balanco_mensal'")
            if not cursor.fetchone():
                self.relatorio['erros'].append("Tabela 'balanco_mensal' não encontrada no fluxo_caixa.db")
                conn.close()
                return
            
            cursor.execute("""
                SELECT id, ano, mes, total_entradas, total_saidas, saldo_mes, observacoes
                FROM balanco_mensal
            """)
            balancos_antigos = cursor.fetchall()
            
            for (id_antigo, ano, mes, total_entradas, total_saidas, saldo_mes, observacoes) in balancos_antigos:
                # Verificar se já existe balanco para este mês/ano/usuário
                balanco_existente = BalancoMensal.query.filter_by(
                    user_id=self.user_id,
                    ano=ano,
                    mes=mes
                ).first()
                
                if not balanco_existente:
                    novo_balanco = BalancoMensal(
                        user_id=self.user_id,
                        ano=ano,
                        mes=mes,
                        total_entradas=float(total_entradas or 0),
                        total_saidas=float(total_saidas or 0),
                        saldo_mes=float(saldo_mes or 0),
                        observacoes=observacoes
                    )
                    db.session.add(novo_balanco)
                    self.relatorio['balancos_mensais'] += 1
            
            conn.close()
            db.session.commit()
            
        except Exception as e:
            self.relatorio['erros'].append(f"Erro ao importar balanços mensais: {str(e)}")
    
    def _importar_eventos_caixa(self, caminho_db):
        """Importa eventos de caixa avulsos do banco antigo"""
        try:
            conn = sqlite3.connect(caminho_db)
            cursor = conn.cursor()
            
            # Verificar se a tabela existe
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='eventos_caixa_avulsos'")
            if not cursor.fetchone():
                self.relatorio['erros'].append("Tabela 'eventos_caixa_avulsos' não encontrada no fluxo_caixa.db")
                conn.close()
                return
            
            cursor.execute("""
                SELECT id, data, descricao, valor
                FROM eventos_caixa_avulsos
            """)
            eventos_antigos = cursor.fetchall()
            
            for (id_antigo, data, descricao, valor) in eventos_antigos:
                # Converter data
                try:
                    data_evento = datetime.strptime(data, '%Y-%m-%d').date()
                except:
                    data_evento = datetime.now().date()
                
                # Verificar se o evento já existe (evitar duplicatas)
                evento_existente = EventoCaixaAvulso.query.filter_by(
                    user_id=self.user_id,
                    data=data_evento,
                    descricao=descricao,
                    valor=float(valor)
                ).first()
                
                if not evento_existente:
                    # Criar evento
                    novo_evento = EventoCaixaAvulso(
                        user_id=self.user_id,
                        data=data_evento,
                        descricao=descricao,
                        valor=float(valor)
                    )
                    db.session.add(novo_evento)
                    self.relatorio['eventos_caixa'] += 1
            
            conn.close()
            db.session.commit()
            
        except Exception as e:
            self.relatorio['erros'].append(f"Erro ao importar eventos de caixa: {str(e)}")


def importar_dados_antigos(app, caminho_financas='financas.db', caminho_receitas='financas_receitas.db', user_id=1):
    """
    Função auxiliar para importar dados do sistema antigo
    
    Args:
        app: Instância da aplicação Flask
        caminho_financas: Caminho para financas.db
        caminho_receitas: Caminho para financas_receitas.db  
        user_id: ID do usuário proprietário (padrão: 1 = admin)
        
    Returns:
        dict: Relatório da importação
    """
    importador = ImportadorDadosAntigos(app, user_id)
    return importador.importar_tudo(caminho_financas, caminho_receitas)


def importar_fluxo_caixa(app, caminho_fluxo_caixa='fluxo_caixa.db', user_id=1):
    """
    Função auxiliar para importar dados de fluxo de caixa
    
    Args:
        app: Instância da aplicação Flask
        caminho_fluxo_caixa: Caminho para fluxo_caixa.db
        user_id: ID do usuário proprietário (padrão: 1 = admin)
        
    Returns:
        dict: Relatório da importação
    """
    importador = ImportadorDadosAntigos(app, user_id)
    return importador.importar_fluxo_caixa(caminho_fluxo_caixa)
