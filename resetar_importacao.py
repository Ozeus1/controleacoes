"""
Script para resetar dados importados do banco de dados
Remove despesas, receitas e dados de fluxo de caixa mantendo categorias e configurações
"""

from app import app
from models import db, Despesa, Receita, BalancoMensal, EventoCaixaAvulso

def resetar_dados_importados():
    """Remove todos os dados importados do banco"""
    with app.app_context():
        try:
            print("="*70)
            print("RESETANDO DADOS IMPORTADOS")
            print("="*70)
            
            # Contar registros antes
            total_despesas = Despesa.query.count()
            total_receitas = Receita.query.count()
            total_balancos = BalancoMensal.query.count()
            total_eventos = EventoCaixaAvulso.query.count()
            
            print(f"\nRegistros antes do reset:")
            print(f"  Despesas:        {total_despesas}")
            print(f"  Receitas:        {total_receitas}")
            print(f"  Balanços Mensais: {total_balancos}")
            print(f"  Eventos de Caixa: {total_eventos}")
            
            # Confirmar ação
            confirmacao = input(f"\n⚠️  Deseja realmente apagar {total_despesas + total_receitas + total_balancos + total_eventos} registros? (sim/não): ")
            
            if confirmacao.lower() != 'sim':
                print("\n❌ Operação cancelada pelo usuário.")
                return False
            
            print("\n🗑️  Apagando registros...")
            
            # Apagar dados (manter categorias e meios de pagamento)
            Despesa.query.delete()
            print(f"  ✓ Despesas removidas")
            
            Receita.query.delete()
            print(f"  ✓ Receitas removidas")
            
            BalancoMensal.query.delete()
            print(f"  ✓ Balanços mensais removidos")
            
            EventoCaixaAvulso.query.delete()
            print(f"  ✓ Eventos de caixa removidos")
            
            # Commit
            db.session.commit()
            
            print("\n" + "="*70)
            print("✅ RESET CONCLUÍDO COM SUCESSO!")
            print("="*70)
            print("\nVocê pode agora executar a importação novamente.")
            print("Use: python -c \"from utils.importador import importar_dados_antigos, importar_fluxo_caixa; from app import app; importar_dados_antigos(app); importar_fluxo_caixa(app)\"")
            print("="*70)
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO ao resetar dados: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    resetar_dados_importados()
