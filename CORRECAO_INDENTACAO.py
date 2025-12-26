"""
CORREÇÃO PARA O ERRO: AttributeError: 'SistemaFinanceiro' object has no attribute 'abrir_gerenciador_sync'

PROBLEMA: A função abrir_gerenciador_sync foi adicionada SEM indentação (como função global)
SOLUÇÃO: Adicionar 4 espaços de indentação para torná-la um método da classe

PROCURE NO ARQUIVO sistema_financeiro_v15.py por volta da linha 892-897:
"""

# ====================================================================
# VERSÃO INCORRETA (SEM INDENTAÇÃO - ESTÁ ASSIM AGORA):
# ====================================================================
def abrir_gerenciador_sync(self):
    """Abre o gerenciador de sincronização de bancos Flask ↔ Desktop"""
    gerenciador_sync_bancos.iniciar_gerenciador_sync(self.root)


# ====================================================================
# VERSÃO CORRETA (COM INDENTAÇÃO - DEVE FICAR ASSIM):
# ====================================================================
    def abrir_gerenciador_sync(self):
        """Abre o gerenciador de sincronização de bancos Flask ↔ Desktop"""
        gerenciador_sync_bancos.iniciar_gerenciador_sync(self.root)


"""
INSTRUÇÕES:
1. Abra sistema_financeiro_v15.py
2. Procure pela função abrir_gerenciador_sync (linha ~894)
3. Adicione 4 ESPAÇOS antes de 'def'
4. Adicione 4 ESPAÇOS adicionais (total 8) nas linhas internas
5. Salve

ALTERNATIVA: Copie e cole o trecho correto acima substituindo o incorreto.

OBS: Se o arquivo estiver muito corrompido, você pode:
1. Fazer um git reset (se estiver usando git)
2. Ou restaurar de um backup
3. Ou aplicar apenas esta correção de indentação manualmente
"""
