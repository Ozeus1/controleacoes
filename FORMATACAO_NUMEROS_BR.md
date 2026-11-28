# Correção de Formatação de Números em Real Brasileiro

## Problema
Os números monetários nas templates não estavam formatados corretamente com separador de milhar (.). 
Exemplo do problema: `R$ 4264,00` deveria ser `R$ 4.264,00`

## Solução Implementada

### 1. Arquivo de Filtros Python (filters.py)
Criado arquivo `filters.py` com duas abordagens:

#### Função `format_brl(value)`
Formata valores em Real com separador de milhar (.) e decimal (,)
```
Entrada: 1234567.89
Saída: R$ 1.234.567,89
```

#### Função `format_number_br(value, decimal_places=2)`
Formata números simples com separador de milhar (.) e decimal (,)
```
Entrada: 1234567.89
Saída: 1.234.567,89
```

#### Função `register_filters(app)`
Registra os filtros na aplicação Flask:
```python
from filters import register_filters
register_filters(app)
```

Isso permite usar nos templates:
```
{{ value|format_brl }}
```

### 2. Macros Jinja2 (_format_helpers.html)
Criado arquivo `_format_helpers.html` com macros reutilizáveis:

```jinja2
{% import '_format_helpers.html' as fmt %}

{{ fmt.format_brl(value) }}
{{ fmt.format_number_br(value) }}
{{ fmt.format_pct(value) }}
```

### 3. Templates Atualizadas

#### opcoes.html
Adicionado import:
```jinja2
{% import '_format_helpers.html' as fmt %}
```

Substituições realizadas:
- `R$ {{ "%.2f"|format(value)|replace('.', ',') }}` → `{{ fmt.format_brl(value) }}`

Todos os valores monetários foram atualizados para usar o novo macro.

### 4. Templates JavaScript (busca_operacoes.html)
Já possui função `brl()` que usa `toLocaleString('pt-BR')`, o que é a abordagem correta para formatar no cliente.

## Como Usar

### Opção 1: Usar Filtros Python (Recomendado)

1. Importar os filtros no arquivo principal da aplicação Flask:
```python
from filters import register_filters
register_filters(app)
```

2. Usar nos templates:
```jinja2
{{ valor_monetario|format_brl }}
{{ valor_numero|format_br }}
```

### Opção 2: Usar Macros Jinja2

1. Adicionar import no início da template:
```jinja2
{% import '_format_helpers.html' as fmt %}
```

2. Usar os macros:
```jinja2
{{ fmt.format_brl(valor) }}
{{ fmt.format_number_br(valor) }}
{{ fmt.format_pct(percentual) }}
```

## Arquivos Criados/Modificados

### Criados:
- `filters.py` - Filtros Python para formatação
- `templates/_format_helpers.html` - Macros Jinja2 para formatação

### Modificados:
- `templates/opcoes.html` - Atualizado para usar o novo macro `format_brl()`

## Próximos Passos

1. **Registrar os filtros** no arquivo principal da aplicação Flask
2. **Atualizar outras templates** que usam a formatação antiga:
   - acoes.html
   - balanceamento.html
   - historico.html
   - etc.

Padrão a procurar e substituir:
```
R$ {{ "%.2f"|format(...)|replace('.', ',') }}
```

Por:
```
{{ fmt.format_brl(...) }}
```

Ou (se usar filtros):
```
{{ ...|format_brl }}
```

## Formato Brasileiro

- **Separador de milhar**: . (ponto)
- **Separador decimal**: , (vírgula)
- **Exemplo**: R$ 1.234.567,89

## Funcionalidade JavaScript (toLocaleString)

A função JavaScript `toLocaleString('pt-BR')` já formata corretamente em Real brasileiro:
```javascript
(1234567.89).toLocaleString('pt-BR', {minimumFractionDigits:2, maximumFractionDigits:2})
// Resultado: "1.234.567,89"
```

Isso é usado em templates como `busca_operacoes.html` e funciona perfeitamente.
