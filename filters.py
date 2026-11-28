"""Filtros Jinja2 personalizados para formatação de moedas e números."""


def format_brl(value):
    """
    Formata um número em Real brasileiro (R$) com separador de milhar (.) e decimal (,).
    Exemplo: 1234567.89 → R$ 1.234.567,89
    """
    if value is None or value == '':
        return 'R$ 0,00'

    try:
        # Converte para float se for string
        num = float(value)

        # Formata com 2 casas decimais e separador de milhar
        formatted = f"{num:,.2f}"

        # Substitui vírgula por separador temporário para trocar ponto por vírgula
        # Format padrão em PT-BR: 1.234.567,89 (ponto para milhar, vírgula para decimal)
        # Format padrão em EN: 1,234,567.89 (vírgula para milhar, ponto para decimal)

        # Troca a vírgula (separador de milhar em EN) por ponto
        # e o ponto (separador decimal em EN) por vírgula
        parts = formatted.split('.')

        if len(parts) == 2:
            # Apenas 1 ponto: é o separador decimal
            integer_part = parts[0]
            decimal_part = parts[1]
        else:
            # Múltiplos pontos: alguns são separadores de milhar
            integer_part = ''.join(parts[:-1])
            decimal_part = parts[-1]

        # Formata a parte inteira com separadores de milhar (ponto)
        integer_part = integer_part.replace(',', '')  # Remove vírgulas
        integer_formatted = ''
        for i, digit in enumerate(reversed(integer_part)):
            if i > 0 and i % 3 == 0:
                integer_formatted = '.' + integer_formatted
            integer_formatted = digit + integer_formatted

        return f"R$ {integer_formatted},{decimal_part}"

    except (ValueError, AttributeError):
        return f"R$ {value}"


def format_number_br(value, decimal_places=2):
    """
    Formata um número com separador de milhar (.) e decimal (,) no padrão brasileiro.
    Exemplo: 1234567.89 → 1.234.567,89
    """
    if value is None or value == '':
        return '0,00'

    try:
        num = float(value)
        formatted = f"{num:,.{decimal_places}f}"

        # Troca separadores
        parts = formatted.split('.')

        if len(parts) == 2:
            integer_part = parts[0]
            decimal_part = parts[1]
        else:
            integer_part = ''.join(parts[:-1])
            decimal_part = parts[-1]

        # Formata a parte inteira com separadores de milhar (ponto)
        integer_part = integer_part.replace(',', '')
        integer_formatted = ''
        for i, digit in enumerate(reversed(integer_part)):
            if i > 0 and i % 3 == 0:
                integer_formatted = '.' + integer_formatted
            integer_formatted = digit + integer_formatted

        return f"{integer_formatted},{decimal_part}"

    except (ValueError, AttributeError):
        return str(value)


def register_filters(app):
    """Registra os filtros Jinja2 na aplicação Flask."""
    app.jinja_env.filters['brl'] = format_brl
    app.jinja_env.filters['format_brl'] = format_brl
    app.jinja_env.filters['format_br'] = format_number_br
