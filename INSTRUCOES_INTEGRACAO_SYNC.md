# INSTRUÇÕES DE INTEGRAÇÃO DO GERENCIADOR DE SINCRONIZAÇÃO
# =========================================================

## Arquivos Criados
✓ gerenciador_sync_bancos.py - Ferramenta completa de sincronização Flask ↔ Desktop

## Como Integrar no sistema_financeiro_v15.py

### 1. Adicionar o Import (próximo à linha 33)
```python
import gerenciador_sync_bancos
```

### 2. Adicionar método na classe SistemaFinanceiro (após outras funções de menu)
```python
def abrir_gerenciador_sync(self):
    """Abre o gerenciador de sincronização de bancos Flask ↔ Desktop"""
    gerenciador_sync_bancos.iniciar_gerenciador_sync(self.root)
```

### 3. Adicionar item no menu (procurar onde os menus são criados)
No menu "Ferramentas" ou "Arquivo", adicionar:
```python
ferramentas_menu.add_command(
    label="🔄 Sincronizar Bancos (Flask ↔ Desktop)",
    command=self.abrir_gerenciador_sync
)
```

OU se preferir no menu Arquivo:
```python
arquivo_menu.add_separator()
arquivo_menu.add_command(
    label="Sincronizar com Flask...",
    command=self.abrir_gerenciador_sync
)
```

## Funcionalidades do Gerenciador

### 📦 BACKUPS
- **Backup Flask DB**: Faz backup do banco Flask (instance/financas.db)
- **Backup Desktop DBs**: Faz backup dos bancos Desktop (financas.db + financas_receitas.db)

### 🔄 SINCRONIZAÇÃO
- **Flask → Desktop (Importar)**: Importa despesas do admin do Flask para o Desktop
- **Desktop → Flask (Exportar)**: Exporta despesas do Desktop para o usuário admin no Flask

### 📂 RESTAURAÇÃO
- **Restaurar Flask DB**: Restaura banco Flask de um backup
- **Restaurar Desktop DBs**: Restaura bancos Desktop de backups

## Recursos
- ✓ Interface gráfica intuitiva
- ✓ Log em tempo real de todas as operações
- ✓ Barra de progresso
- ✓ Status visual dos bancos
- ✓ Confirmações antes de operações destrutivas
- ✓ Tratamento de erros robusto

## Observações Importantes
1. A sincronização considera apenas o usuário "admin" (user_id = 1) do Flask
2. A única diferença entre os bancos é a coluna user_id (presente no Flask, ausente no Desktop)
3. Cuidado com duplicações - o sistema avisa mas não previne automaticamente
4. Sempre faça backup antes de operações de sincronização!

## Exemplo de Uso
1. Abra "Ferramentas" → "Sincronizar Bancos"
2. Verifique o status dos bancos na parte superior
3. Escolha a operação desejada
4. Acompanhe o progresso no log
5. Confirme as operações quando solicitado
