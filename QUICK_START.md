# Guia de Início Rápido - Sistema Financeiro Web

## 🚀 Iniciar o Sistema

### Opção 1: Comando Direto

```bash
cd c:\Users\orlei\OneDrive\ProjPython\FINAN
python app.py
```

### Opção 2: Ambiente Virtual (Recomendado)

```bash
cd c:\Users\orlei\OneDrive\ProjPython\FINAN

# Criar ambiente virtual (primeira vez apenas)
python -m venv venv

# Ativar ambiente
venv\Scripts\activate

# Instalar dependências (primeira vez apenas)
pip install -r requirements.txt

# Executar sistema
python app.py
```

## 📝 Acesso

Após iniciar o sistema, acesse:
```
http://localhost:5000
```

**Login Padrão:**
- Usuário: `admin`
- Senha: `admin123`

> ⚠️ **IMPORTANTE**: Altere a senha após o primeiro acesso!

## 🔧 Solução de Problemas

### Erro de Importação / Compatibilidade

Se encontrar erros ao iniciar, tente:

1. Verificar versão Python (recomendado 3.8 a 3.11):
```bash
python --version
```

2. Reinstalar dependências:
```bash
pip install --upgrade -r requirements.txt
```

3. Limpar cache Python:
```bash
del /s /q __pycache__
del /s /q *.pyc
```

### Porta em Uso

Se a porta 5000 já estiver em uso, edite `app.py` linha final:
```python
app.run(host='0.0.0.0', port=5001, debug=True)  # Mudar para 5001 ou outra porta
```

### Banco de Dados Corrompido

Delete o arquivo `financeiro.db` e reinicie - será recriado automaticamente:
```bash
del financeiro.db
python app.py
```

## ✅ Primeiros Passos Após Login

1. **Alterar Senha**
   - Acesse "Perfil" no menu do usuário
   - Atualize sua senha

2. **Criar Usuários** (se admin)
   - Menu: Configurações > Novo Usuário
   - Defina nome, email, senha e nível de acesso

3. **Configurar Categorias**
   - Menu: Configurações > Categorias Despesa/Receita
   - Adicione ou edite conforme necessário

4. **Lançar uma Despesa**
   - Menu: Despesas > Nova Despesa
   - Preencha os dados e salve

5. **Visualizar Dashboard**
   - Menu: Dashboard
   - Veja resumo financeiro do mês

6. **Gerar Relatórios**
   - Menu: Relatórios
   - Escolha o tipo desejado

## 📱 Acessar de Outros Dispositivos

Para acessar de outros computadores/celulares na mesma rede:

1. Descubra seu IP local:
```bash
ipconfig
```

2. Inicie o servidor:
```python
# Em app.py, última linha:
app.run(host='0.0.0.0', port=5000, debug=True)
```

3. Acesse de outros dispositivos:
```
http://SEU_IP:5000
```
Exemplo: `http://192.168.1.100:5000`

## 🎯 Funcionalidades Principais

- ✅ Gestão de Despesas e Receitas
- ✅ Categorias Configuráveis  
- ✅ Meios de Pagamento/Recebimento
- ✅ 3 Níveis de Usuário (Admin/Gerente/Usuário)
- ✅ Relatórios com Gráficos
- ✅ Exportação para Excel
- ✅ Orçamentos por Categoria
- ✅ Previsão de Faturas de Cartão

## ⏱️ Estrutura de Acesso

**Usuário Comum:**
- Ver apenas seus lançamentos
- Criar/editar/excluir próprias despesas e receitas
- Visualizar relatórios de seus dados

**Gerente:**
- Ver TODOS os lançamentos
- Gerenciar configurações (categorias, meios, etc.)
- Acessar todos os relatórios
- Configurar orçamentos

**Administrador:**
- Acesso total
- Gerenciar usuários
- Criar novos usuários
- Alterar níveis de acesso

## 📊 Relatórios Disponíveis

1. **Balanço Mensal** - Receitas vs Despesas
2. **Despesas Mensais** - Por categoria
3. **Receitas Mensais** - Por categoria
4. **Top 10 Contas** - Maiores despesas
5. **Orçado vs Gasto** - Controle orçamentário
6. **Previsão Cartões** - Faturas previstas

Todos com:
- Gráficos interativos (Chart.js)
- Filtros por período
- Exportação para Excel

## 🔐 Segurança

- Senhas criptografadas (hash)
- Controle de sessão
- Proteção por nível de acesso
- Validação de dados

## 💡 Dicas

- Use filtros para encontrar lançamentos rapidamente
- Export para Excel para análises offline
- Configure orçamentos para controle mensal
- Cadastre cartões para previsão de faturas

---

**Sistema desenvolvido em Flask** | Versão 2.0
