# config_example.py
# ==================
# Copie este arquivo para config.py e preencha com seus dados.
# NÃO comite config.py no git (ele já está no .gitignore).

# URL do endpoint no VPS
API_URL = "https://www.invest.casatemporadaceara.cloud/api/update_quotes"

# API Key — deve ser a mesma definida no .env do VPS como MT5_API_KEY
# Exemplo: MT5_API_KEY=minha_chave_secreta_123
API_KEY = "coloque_sua_chave_aqui"

# ID do usuário no site (normalmente 1 para o admin)
USER_ID = 1

# Intervalo de atualização em segundos (ex: 30 = a cada 30 segundos)
INTERVALO_SEGUNDOS = 30

# Mapeamento: "TICKER_NO_SITE" -> "SÍMBOLO_NO_MT5"
# O símbolo no MT5 pode ter sufixo diferente dependendo da corretora.
# Para descobrir o nome exato, abra o MT5 > Market Watch e veja o nome do ativo.
# Exemplos comuns:
#   BTG Pactual: PETR4 (sem sufixo)
#   XP:          PETR4 (sem sufixo)
#   Rico:        PETR4 (sem sufixo)
TICKER_MAP = {
    "PETR4":  "PETR4",
    "VALE3":  "VALE3",
    "ITUB4":  "ITUB4",
    "BBDC4":  "BBDC4",
    "ABEV3":  "ABEV3",
    "WEGE3":  "WEGE3",
    "RENT3":  "RENT3",
    "HGLG11": "HGLG11",
    "KNRI11": "KNRI11",
    # Adicione quantos quiser...
}
