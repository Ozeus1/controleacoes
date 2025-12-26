# Guia de Importação de Dados do Sistema Antigo

## 📥 Como Importar Dados do sistema_financeiro_v14.py

O sistema Flask possui uma ferramenta integrada para importar todos os dados do sistema antigo em Tkinter.

### Passo a Passo

#### 1. Localizar os Bancos de Dados Antigos

Encontre os arquivos:
- `financas.db` (contém despesas)
- `financas_receitas.db` (contém receitas)

Normalmente estão na mesma pasta do arquivo `sistema_financeiro_v14.py`.

#### 2. Copiar para a Pasta do Projeto Flask

Copie os dois arquivos para a pasta raiz do projeto Flask:
```
c:\Users\orlei\OneDrive\ProjPython\FINAN\
```

Estrutura esperada:
```
FINAN/
├── app.py
├── financas.db              ← arquivo antigo
├── financas_receitas.db     ← arquivo antigo
├── financeiro.db            ← banco novo (será atualizado)
└── ...
```

#### 3. Fazer Backup (IMPORTANTE!)

Antes de importar, faça backup do banco atual:
```bash
copy financeiro.db financeiro_backup.db
```

#### 4. Acessar a Ferramenta de Importação

1. Acesse: http://localhost:5000
2. Faça login como **admin**
3. Menu: **Configurações** > **Importar Dados Antigos**

#### 5. Executar a Importação

1. A tela mostrará o status dos arquivos (encontrado/não encontrado)
2. Verifique os avisos importantes
3. Clique em **"Iniciar Importação"**
4. Confirme a operação
5. Aguarde a conclusão

#### 6. Verificar o Resultado

Após a importação, você verá um relatório com:
- ✅ Categorias de Despesa importadas
- ✅ Categorias de Receita importadas
- ✅ Meios de Pagamento importados
- ✅ Meios de Recebimento importados
- ✅ Total de Despesas importadas
- ✅ Total de Receitas importadas

### O Que é Importado?

#### ✅ Categorias
- Todas as categorias de despesa
- Todas as categorias de receita
- **Nota:** Categorias duplicadas não são reimportadas

#### ✅ Meios de Pagamento/Recebimento
- Todos os meios de pagamento
- Todos os meios de recebimento
- O tipo é determinado automaticamente (cartão, PIX, etc.)

#### ✅ Despesas
- Descrição
- Valor
- Data de pagamento
- Categoria
- Meio de pagamento
- Número de parcelas
- Data de registro

#### ✅ Receitas
- Descrição
- Valor
- Data de recebimento
- Categoria
- Meio de recebimento
- Número de parcelas
- Data de registro

### Propriedade dos Dados

Todos os dados importados serão atribuídos ao usuário **admin** (ou o usuário logado que fizer a importação).

Se você tiver múltiplos usuários e quiser separar os dados:
1. Importe como admin
2. Depois, edite manualmente as transações para atribuir a outros usuários

### Importações Múltiplas

Você pode executar a importação múltiplas vezes:
- Categorias e meios **duplicados não são reimportados**
- Despesas e receitas **serão reimportadas** (pode gerar duplicatas!)

**Recomendação:** Execute a importação apenas **uma vez** ou limpe os dados antes de reimportar.

### Solução de Problemas

#### Arquivos não encontrados
**Problema:** Sistema não encontra `financas.db` ou `financas_receitas.db`  
**Solução:** Verifique se os arquivos estão em `c:\Users\orlei\OneDrive\ProjPython\FINAN\`

#### Erro ao importar
**Problema:** Erro durante a importação  
**Solução:** 
1. Verifique se os bancos antigos não estão corrompidos
2. Tente abri-los com DB Browser for SQLite
3. Verifique se têm a estrutura esperada

#### Categorias não aparecem
**Problema:** Categorias importadas mas não aparecem nas listagens  
**Solução:** Verifique se foram marcadas como "ativo=True" em Configurações > Categorias

#### Datas erradas
**Problema:** Datas das transações aparecem incorretas  
**Solução:** O sistema tenta converter as datas do formato antigo. Se houver erro, usa a data atual.

### Via Linha de Comando (Alternativo)

Você também pode importar via script Python:

```python
from app import create_app
from utils.importador import importar_dados_antigos

app = create_app()
relatorio = importar_dados_antigos(
    app, 
    'financas.db',
    'financas_receitas.db',
    user_id=1  # ID do admin
)

print(relatorio)
```

Salve como `importar.py` e execute:
```bash
python importar.py
```

### Limpeza Após Importação

Depois de verificar que tudo foi importado corretamente, você pode:

1. **Mover os arquivos antigos para backup:**
```bash
mkdir backup_antigo
move financas.db backup_antigo\
move financas_receitas.db backup_antigo\
```

2. **Ou excluir se não precisar mais:**
```bash
del financas.db
del financas_receitas.db
```

### Resumo Rápido

```bash
# 1. Copiar bancos antigos
copy financas.db c:\Users\orlei\OneDrive\ProjPython\FINAN\
copy financas_receitas.db c:\Users\orlei\OneDrive\ProjPython\FINAN\

# 2. Fazer backup
cd c:\Users\orlei\OneDrive\ProjPython\FINAN
copy financeiro.db financeiro_backup.db

# 3. Acessar sistema
# http://localhost:5000
# Menu: Configurações > Importar Dados Antigos

# 4. Limpar após importação (opcional)
move financas.db backup\
move financas_receitas.db backup\
```

---

**Versão:** 2.0  
**Última atualização:** 2024
