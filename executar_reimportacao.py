"""
Script para executar RESET E REIMPORTAÇÃO completa dos dados
"""

from app import app
from models import db, Despesa, Receita, BalancoMensal, EventoCaixaAvulso
from utils.importador import importar_dados_antigos, importar_fluxo_caixa
import os

def executar_reset_e_reimportacao():
    """Executa reset e reimportação automática"""
    with app.app_context():
        try:
            print("="*70)
            print("RESET E REIMPORTAÇÃO AUTOMÁTICA")
            print("="*70)
            
            # Passo 1: Contar registros antes
            total_despesas = Despesa.query.count()
            total_receitas = Receita.query.count()
            total_balancos = BalancoMensal.query.count()
            total_eventos = EventoCaixaAvulso.query.count()
            
            print(f"\n📊 Registros ANTES do reset:")
            print(f"  Despesas:         {total_despesas}")
            print(f"  Receitas:         {total_receitas}")
            print(f"  Balanços Mensais: {total_balancos}")
            print(f"  Eventos de Caixa: {total_eventos}")
            print(f"  TOTAL:            {total_despesas + total_receitas + total_balancos + total_eventos}")
            
            # Passo 2: Apagar dados
            print(f"\n🗑️  Removendo registros...")
            Despesa.query.delete()
            Receita.query.delete()
            BalancoMensal.query.delete()
            EventoCaixaAvulso.query.delete()
            db.session.commit()
            print("  ✓ Todos os registros removidos")
            
            # Passo 3: Importar dados
            print(f"\n📥 Importando dados...")
            
            # Importar despesas e receitas
            if os.path.exists('financas.db') and os.path.exists('financas_receitas.db'):
                print("  Importando despesas e receitas...")
                relatorio1 = importar_dados_antigos(
                    app,
                    'financas.db',
                    'financas_receitas.db',
                    user_id=1
                )
                
                if relatorio1['sucesso']:
                    print(f"  ✓ Despesas importadas: {relatorio1['despesas']}")
                    print(f"  ✓ Receitas importadas: {relatorio1['receitas']}")
                else:
                    print(f"  ❌ Erros: {relatorio1['erros']}")
            else:
                print("  ⚠️  Arquivos financas.db ou financas_receitas.db não encontrados")
            
            # Importar fluxo de caixa
            if os.path.exists('fluxo_caixa.db'):
                print("  Importando fluxo de caixa...")
                relatorio2 = importar_fluxo_caixa(
                    app,
                    'fluxo_caixa.db',
                    user_id=1
                )
                
                if relatorio2['sucesso']:
                    print(f"  ✓ Balanços Mensais: {relatorio2.get('balancos_mensais', 0)}")
                    print(f"  ✓ Eventos de Caixa: {relatorio2.get('eventos_caixa', 0)}")
                else:
                    print(f"  ❌ Erros: {relatorio2.get('erros', [])}")
            else:
                print("  ⚠️  Arquivo fluxo_caixa.db não encontrado")
            
            # Passo 4: Verificar resultado
            print(f"\n📊 Registros DEPOIS da reimportação:")
            total_despesas_novo = Despesa.query.count()
            total_receitas_novo = Receita.query.count()
            total_balancos_novo = BalancoMensal.query.count()
            total_eventos_novo = EventoCaixaAvulso.query.count()
            
            print(f"  Despesas:         {total_despesas_novo}")
            print(f"  Receitas:         {total_receitas_novo}")
            print(f"  Balanços Mensais: {total_balancos_novo}")
            print(f"  Eventos de Caixa: {total_eventos_novo}")
            print(f"  TOTAL:            {total_despesas_novo + total_receitas_novo + total_balancos_novo + total_eventos_novo}")
            
            print("\n" + "="*70)
            print("✅ RESET E REIMPORTAÇÃO CONCLUÍDOS!")
            print("="*70)
            
            # Verificar duplicação
            print(f"\n🔍 Verificação de duplicação:")
            if total_despesas > 0:
                proporcao = total_despesas_novo / 920  # Valor esperado do banco antigo
                print(f"  Proporção: {proporcao:.2f}x")
                if proporcao > 1.1:
                    print(f"  ⚠️  ATENÇÃO: Ainda há mais registros que o esperado!")
                else:
                    print(f"  ✓ Proporção adequada - sem duplicação!")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    executar_reset_e_reimportacao()
