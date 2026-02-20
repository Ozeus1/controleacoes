"""
mt5_feeder.py
=============
Script local que lê cotações do MetaTrader 5 e envia periodicamente
ao site https://www.invest.casatemporadaceara.cloud/api/update_quotes

Envia:
  - quotes:  preços de ações/FIIs/ETFs  → atualiza Asset.current_price
  - changes: variação % do dia           → atualiza Asset.daily_change
  - options: preços de opções            → atualiza Option.current_option_price

Requisitos:
    pip install -r requirements.txt

Configuração:
    Copie config_example.py para config.py e edite os valores.
"""

import time
import requests
import sys
from datetime import datetime

try:
    import config as cfg
except ImportError:
    print("ERRO: config.py não encontrado. Copie config_example.py para config.py e edite.")
    sys.exit(1)

try:
    import MetaTrader5 as mt5
except ImportError:
    print("ERRO: pip install MetaTrader5")
    sys.exit(1)


# ── MT5 helpers ───────────────────────────────────────────────────────────────

def conectar_mt5():
    if not mt5.initialize():
        print(f"[MT5] Falha ao inicializar: {mt5.last_error()}")
        return False
    info = mt5.terminal_info()
    if info is None:
        print("[MT5] Terminal não encontrado. Abra o MT5 primeiro.")
        return False
    print(f"[MT5] Conectado: {info.name} | build {info.build}")
    return True


def _get_price(symbol):
    """Retorna (price, change_pct) para o símbolo. Tenta habilitar se necessário."""
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        mt5.symbol_select(symbol, True)
        time.sleep(0.15)
        tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return None, None

    price = tick.last if tick.last > 0 else tick.bid
    if price <= 0:
        return None, None

    # Variação do dia via symbol_info
    info = mt5.symbol_info(symbol)
    change_pct = 0.0
    if info and info.session_open > 0:
        change_pct = round((price - info.session_open) / info.session_open * 100, 2)

    return round(price, 2), change_pct


def obter_cotacoes():
    """Lê ações/FIIs/ETFs. Retorna (quotes_dict, changes_dict)."""
    quotes, changes = {}, {}
    print("  [Ativos]")
    for ticker_site, simbolo_mt5 in cfg.TICKER_MAP.items():
        price, change = _get_price(simbolo_mt5)
        if price:
            quotes[ticker_site]  = price
            changes[ticker_site] = change
            print(f"    {ticker_site:12s} ({simbolo_mt5:15s}) = R$ {price:.2f}  ({change:+.2f}%)")
        else:
            print(f"    {ticker_site:12s} ({simbolo_mt5:15s}) = sem preço")
    return quotes, changes


def obter_cotacoes_opcoes():
    """Lê opções. Retorna dict {ticker_opcao: price}."""
    option_map = getattr(cfg, 'OPTION_MAP', {})
    if not option_map:
        return {}

    options = {}
    print("  [Opções]")
    for ticker_site, simbolo_mt5 in option_map.items():
        price, _ = _get_price(simbolo_mt5)
        if price is not None:
            options[ticker_site] = price
            print(f"    {ticker_site:12s} ({simbolo_mt5:15s}) = R$ {price:.2f}")
        else:
            print(f"    {ticker_site:12s} ({simbolo_mt5:15s}) = sem preço")
    return options


# ── HTTP ──────────────────────────────────────────────────────────────────────

def enviar_cotacoes(quotes, changes, options):
    if not quotes and not options:
        print("[API] Nada para enviar.")
        return False

    payload = {
        "user_id": cfg.USER_ID,
        "quotes":  quotes,
        "changes": changes,
        "options": options,
    }
    headers = {"X-API-Key": cfg.API_KEY, "Content-Type": "application/json"}

    try:
        resp = requests.post(cfg.API_URL, json=payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print(f"[API] ✓ Ativos: {data.get('updated_assets',[])}  |  Opções: {data.get('updated_options',[])}")
            nfa = data.get('not_found_assets', [])
            nfo = data.get('not_found_options', [])
            if nfa: print(f"[API] ⚠ Ativos não encontrados no site: {nfa}")
            if nfo: print(f"[API] ⚠ Opções não encontradas no site: {nfo}")
            return True
        elif resp.status_code == 401:
            print("[API] ✗ 401 Unauthorized — verifique API_KEY em config.py e MT5_API_KEY no .env do VPS")
        else:
            print(f"[API] ✗ Erro {resp.status_code}: {resp.text[:200]}")
    except requests.exceptions.ConnectionError:
        print("[API] ✗ Sem conexão com o site.")
    except requests.exceptions.Timeout:
        print("[API] ✗ Timeout.")
    except Exception as e:
        print(f"[API] ✗ {e}")
    return False


# ── Loop principal ────────────────────────────────────────────────────────────

def loop_principal():
    print("=" * 60)
    print("  MT5 Feeder — invest.casatemporadaceara.cloud")
    print("=" * 60)
    print(f"  Intervalo : {cfg.INTERVALO_SEGUNDOS}s")
    print(f"  URL       : {cfg.API_URL}")
    print(f"  Ativos    : {list(cfg.TICKER_MAP.keys())}")
    opt_map = getattr(cfg, 'OPTION_MAP', {})
    if opt_map:
        print(f"  Opções    : {list(opt_map.keys())}")
    print("  Pressione Ctrl+C para parar.\n")

    if not conectar_mt5():
        sys.exit(1)

    sem_conexao = 0
    try:
        while True:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Lendo MT5...")

            if not mt5.terminal_info():
                sem_conexao += 1
                print(f"[MT5] Desconectado. Tentando reconectar ({sem_conexao})...")
                if not conectar_mt5():
                    time.sleep(cfg.INTERVALO_SEGUNDOS)
                    continue
                sem_conexao = 0

            quotes, changes = obter_cotacoes()
            options = obter_cotacoes_opcoes()
            enviar_cotacoes(quotes, changes, options)

            print(f"  Próxima em {cfg.INTERVALO_SEGUNDOS}s...")
            time.sleep(cfg.INTERVALO_SEGUNDOS)

    except KeyboardInterrupt:
        print("\nFeeder encerrado.")
    finally:
        mt5.shutdown()
        print("[MT5] Desconectado.")


if __name__ == "__main__":
    loop_principal()
