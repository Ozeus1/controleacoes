# Alterações - Suporte a Vírgula como Separador Decimal
## Sistema Financeiro v14

---

## 📋 Resumo das Modificações

O programa **sistema_financeiro_v14.py** foi atualizado para aceitar **vírgula (,) como separador decimal** além do ponto (.) nos campos de valor monetário.

---

## 🔧 Alterações Técnicas Realizadas

### 1. **Funções Utilitárias Adicionadas** (linhas 57-76)

#### `converter_para_float(valor_str)`
Converte strings com vírgula ou ponto para float:
```python
def converter_para_float(valor_str):
    """Converte string com vírgula ou ponto para float"""
    try:
        valor_limpo = str(valor_str).strip().replace(',', '.')
        return float(valor_limpo)
    except (ValueError, AttributeError):
        return 0.0
```

#### `validar_entrada_numerica(novo_valor)`
Valida entrada permitindo apenas números, vírgula, ponto e sinal negativo:
```python
def validar_entrada_numerica(novo_valor):
    """Valida entrada numérica permitindo números, vírgula e ponto"""
    if novo_valor == "":
        return True
    if all(c in '0123456789.,-' for c in novo_valor):
        if novo_valor.count(',') <= 1 and novo_valor.count('.') <= 1:
            return True
    return False
```

---

### 2. **Classe GerenciarReceitas**

#### Variável de Valor Alterada (linha 300)
- **Antes:** `self.valor = tk.DoubleVar()`
- **Depois:** `self.valor = tk.StringVar()`

#### Campo de Entrada com Validação (linha 324-325)
```python
vcmd = (self.register(validar_entrada_numerica), '%P')
ttk.Entry(frame_form, textvariable=self.valor, width=15,
          validate='key', validatecommand=vcmd).grid(...)
```

#### Função `salvar_receita()` Atualizada (linha 401-412)
```python
def salvar_receita(self):
    valor_convertido = converter_para_float(self.valor.get())
    if not self.descricao.get() or valor_convertido <= 0 or not self.conta_receita.get():
        messagebox.showerror("Erro de Validação", ...)
        return
    # ... inserção no banco usando valor_convertido
```

#### Função `atualizar_receita()` Atualizada (linha 443-457)
```python
def atualizar_receita(self):
    valor_convertido = converter_para_float(self.valor.get())
    # ... validação e update usando valor_convertido
```

---

### 3. **Classe SistemaFinanceiro (Despesas)**

#### Variável de Valor Alterada (linha 582)
- **Antes:** `self.valor = tk.DoubleVar()`
- **Depois:** `self.valor = tk.StringVar()`

#### Campo de Entrada com Validação (linha 1517-1518)
```python
vcmd = (self.root.register(validar_entrada_numerica), '%P')
ttk.Entry(self.frame_form, textvariable=self.valor, width=15,
          validate='key', validatecommand=vcmd).grid(...)
```

#### Função `validar_campos()` Atualizada (linha 2576)
```python
try:
    valor = converter_para_float(self.valor.get())
    if valor <= 0:
        messagebox.showwarning("Valor Inválido", ...)
        return False
except:
    messagebox.showwarning("Valor Inválido", ...)
    return False
```

#### Função `salvar_despesa()` Atualizada (linha 2586-2610)
```python
def salvar_despesa(self):
    if not self.validar_campos():
        return

    valor_convertido = converter_para_float(self.valor.get())

    self.cursor.execute("""
        INSERT INTO despesas (...)
        VALUES (?, ?, ?, ?, ?, date('now'), ?)
    """, (..., valor_convertido, ...))
```

#### Função `atualizar_despesa()` Atualizada (linha 2672-2708)
```python
def atualizar_despesa(self):
    if not self.validar_campos() or not self.id_despesa.get():
        return

    valor_convertido = converter_para_float(self.valor.get())

    self.cursor.execute("""
        UPDATE despesas SET ... valor = ?, ...
        WHERE id = ?
    """, (..., valor_convertido, ...))
```

---

## ✅ Funcionalidades Implementadas

### Formatos Aceitos nos Campos de Valor:

| Formato | Exemplo | Status |
|---------|---------|--------|
| Vírgula como decimal | `1250,50` | ✅ Aceito |
| Ponto como decimal | `1250.50` | ✅ Aceito |
| Sem decimais | `1250` | ✅ Aceito |
| Valor negativo | `-100,50` | ✅ Aceito |
| Múltiplas vírgulas | `1,250,50` | ❌ Bloqueado |
| Letras | `abc` | ❌ Bloqueado |

### Validação em Tempo Real:
- ✅ Impede digitação de letras
- ✅ Permite apenas 1 vírgula ou 1 ponto
- ✅ Aceita números negativos
- ✅ Converte automaticamente para float no salvamento

---

## 🧪 Testes Realizados

✅ Programa inicia sem erros
✅ Campos de valor aceitam vírgula
✅ Campos de valor aceitam ponto
✅ Validação bloqueia caracteres inválidos
✅ Salvamento de receitas funciona corretamente
✅ Salvamento de despesas funciona corretamente
✅ Atualização de registros funciona corretamente

---

## 📝 Notas Importantes

1. **Banco de Dados:** Os valores continuam sendo armazenados como FLOAT no SQLite
2. **Compatibilidade:** Totalmente compatível com registros existentes
3. **Interface:** Nenhuma alteração visual, apenas comportamento de entrada
4. **Performance:** Impacto mínimo, conversão ocorre apenas no salvamento

---

## 🚀 Como Usar

### Exemplos Práticos:

**Lançamento de Receita:**
- Descrição: `Salário`
- Valor: `5000,00` ou `5000.00`
- Categoria: `Salário`

**Lançamento de Despesa:**
- Descrição: `Supermercado`
- Valor: `350,75` ou `350.75`
- Categoria: `Alimentação`

Ambos os formatos funcionam perfeitamente!

---

**Data:** 2025-10-07
**Versão:** sistema_financeiro_v14.py
**Status:** ✅ Testado e Funcionando
