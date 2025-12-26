# Sistema de Gerenciamento Financeiro - Web

Sistema completo de gerenciamento financeiro desenvolvido em Flask, com controle de despesas, receitas, meios de pagamento, categorias configuráveis, controle de usuários com níveis de acesso e relatórios financeiros.

## 🚀 Funcionalidades

### Principais Recursos
- **Gestão de Despesas**: Cadastro, edição, exclusão e listagem de despesas
- **Gestão de Receitas**: Controle completo de receitas
- **Categorias Configuráveis**: Personalize categorias de despesas e receitas
- **Meios de Pagamento**: Gerencie meios de pagamento e recebimento
- **Controle de Usuários**: Sistema de autenticação com 3 níveis de acesso
- **Relatórios Financeiros**: Diversos relatórios com gráficos interativos
- **Exportação Excel**: Exporte despesas e receitas para Excel

### Níveis de Usuário
1. **Usuário**: Acesso básico, visualiza apenas seus próprios dados
2. **Gerente**: Visualiza todos os dados, pode gerenciar configurações
3. **Administrador**: Acesso total, incluindo gestão de usuários

### Relatórios Disponíveis
- Balanço mensal (receitas vs despesas)
- Despesas mensais por categoria
- Receitas mensais por categoria
- Top 10 contas de despesa
- Orçado vs Gasto
- Previsão de faturas de cartão de crédito

## 📋 Requisitos

- Python 3.8+
- pip (gerenciador de pacotes Python)

## 🔧 Instalação

### 1. Clone ou extraia o projeto

```bash
cd c:\Users\orlei\OneDrive\ProjPython\FINAN
```

### 2. Crie um ambiente virtual (recomendado)

```bash
python -m venv venv
```

### 3. Ative o ambiente virtual

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 4. Instale as dependências

```bash
pip install -r requirements.txt
```

### 5. Configure as variáveis de ambiente

Copie o arquivo `.env.example` para `.env` e ajuste conforme necessário:

```bash
copy .env.example .env
```

Edite o arquivo `.env` e configure:
```
SECRET_KEY=sua-chave-secreta-aqui
DATABASE_URL=sqlite:///financeiro.db
FLASK_ENV=development
FLASK_DEBUG=True
```

## 🚀 Executando o Sistema

### Desenvolvimento

```bash
python app.py
```

O sistema estará disponível em: `http://localhost:5000`

### Produção

Para produção, é recomendado usar um servidor WSGI como Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 👤 Acesso Inicial

O sistema cria automaticamente um usuário administrador:

- **Usuário**: admin
- **Senha**: admin123

> ⚠️ **IMPORTANTE**: Altere a senha padrão após o primeiro acesso!

## 📁 Estrutura do Projeto

```
FINAN/
├── app.py                    # Aplicação principal Flask
├── config.py                 # Configurações
├── models.py                 # Modelos do banco de dados
├── requirements.txt          # Dependências
├── .env.example              # Exemplo de variáveis de ambiente
├── routes/                   # Blueprints
│   ├── auth.py              # Autenticação
│   ├── main.py              # Rotas principais
│   ├── despesas.py          # Gestão de despesas
│   ├── receitas.py          # Gestão de receitas
│   ├── configuracao.py      # Configurações do sistema
│   └── relatorios.py        # Relatórios e análises
├── templates/               # Templates HTML
│   ├── base.html
│   ├── dashboard.html
│   ├── auth/
│   ├── despesas/
│   ├── receitas/
│   ├── config/
│   └── relatorios/
├── static/                  # Arquivos estáticos
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
└── financeiro.db            # Banco de dados SQLite (gerado automaticamente)
```

## 🔐 Segurança

- Senhas são armazenadas com hash seguro (Werkzeug)
- Proteção CSRF em formulários
- Controle de acesso baseado em níveis de usuário
- Validação de dados em todas as entradas

## 📊 Banco de Dados

O sistema usa SQLite por padrão, ideal para desenvolvimento e instalações pequenas. Para produção com muitos usuários, considere migrar para PostgreSQL ou MySQL.

### Tabelas Principais
- `users`: Usuários do sistema
- `despesas`: Registros de despesas
- `receitas`: Registros de receitas
- `categorias_despesa`: Categorias de despesas
- `categorias_receita`: Categorias de receitas
- `meios_pagamento`: Meios de pagamento
- `meios_recebimento`: Meios de recebimento
- `orcamentos`: Orçamentos por categoria
- `fechamentos_cartao`: Configuração de cartões de crédito

## 🛠️ Tecnologias Utilizadas

- **Backend**: Flask, SQLAlchemy, Flask-Login
- **Frontend**: Bootstrap 5, Chart.js, jQuery
- **Banco de Dados**: SQLite (desenvolvimento), PostgreSQL/MySQL (produção)
- **Exportação**: pandas, openpyxl

## 📝 Como Usar

### Cadastrar uma Despesa
1. Acesse o menu "Despesas" > "Nova Despesa"
2. Preencha os dados (descrição, valor, categoria, etc.)
3. Clique em "Salvar"

### Gerar Relatórios
1. Acesse o menu "Relatórios"
2. Escolha o tipo de relatório desejado
3. Configure os filtros (mês, ano, categoria)
4. Visualize ou exporte os dados

### Configurar Categorias
1. Acesse "Configurações" > "Categorias Despesa" (ou Receita)
2. Adicione novas categorias ou edite existentes
3. Ative/desative categorias conforme necessário

### Gerenciar Usuários (Admin)
1. Acesse "Configurações" > "Gerenciar Usuários"
2. Crie novos usuários com "Novo Usuário"
3. Altere níveis de acesso conforme necessário
4. Ative/desative usuários

## 🐛 Resolução de Problemas

### Erro ao iniciar o servidor
- Verifique se todas as dependências estão instaladas
- Confirme que o ambiente virtual está ativado
- Verifique se a porta 5000 não está em uso

### Erro de banco de dados
- Delete o arquivo `financeiro.db` e reinicie o sistema
- O banco será recriado automaticamente

### Problemas com gráficos
- Verifique sua conexão com a internet (Chart.js é carregado via CDN)
- Limpe o cache do navegador

## 📞 Suporte

Para questões, problemas ou sugestões, entre em contato com o administrador do sistema.

## 📄 Licença

Este projeto é proprietário. Todos os direitos reservados.

## 🔄 Atualizações Futuras

Funcionalidades planejadas:
- Importação de extratos bancários
- Notificações por email
- Dashboard com mais métricas
- App mobile
- Relatórios em PDF
- Integração com APIs bancárias

---

**Versão**: 2.0  
**Desenvolvido em**: 2024  
**Base**: Sistema original sistema_financeiro_v14.py
