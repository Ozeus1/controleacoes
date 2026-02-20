"""
mt5_feeder.py
=============
Script local que lê cotações do MetaTrader 5 e envia periodicamente
ao site https://www.invest.casatemporadaceara.cloud/api/update_quotes

Requisitos:
    pip install MetaTrader5 requests python-dotenv

Configuração:
    Edite o arquivo config.py com:
    - URL do site
    - API Key (mesma cadastrada no .env do VPS como MT5_API_KEY)
    - Lista de tickers e seus símbolos no MT5
    - Intervalo de atualização em segundos
"""

import time
import requests
import sys
import os
from datetime import datetime

# ── Carrega configurações ────────────────────────────────────────────────────
try:
    import config as cfg
except ImportError:
    print("ERRO: Arquivo config.py não encontrado. Copie config_example.py para config.py e edite.")
    sys.exit(1)

# ── MetaTrader 5 ─────────────────────────────────────────────────────────────
try:
    import MetaTrader5 as mt5
except ImportError:
    print("ERRO: Biblioteca MetaTrader5 não instalada.")
    print("Execute: pip install MetaTrader5")
    sys.exit(1)


def conectar_mt5():
    """Inicializa e conecta ao terminal MT5."""
    if not mt5.initialize():
        print(f"[MT5] Falha ao inicializar: {mt5.last_error()}")
        return False
    info = mt5.terminal_info()
    if info is None:
        print("[MT5] Terminal não encontrado. Certifique-se que o MT5 está aberto.")
        return False
    print(f"[MT5] Conectado: {info.name} | build {info.build}")
    return True


def obter_cotacoes():
    """
    Lê o último preço (ask ou last) de cada símbolo configurado.
    Retorna dict: {TICKER_SITE: preco_float}
    """
    cotacoes = {}
    for ticker_site, simbolo_mt5 in cfg.TICKER_MAP.items():
        tick = mt5.symbol_info_tick(simbolo_mt5)
        if tick is None:
            # Tenta habilitar o símbolo no MT5
            mt5.symbol_select(simbolo_mt5, True)
            time.sleep(0.2)
            tick = mt5.symbol_info_tick(simbolo_mt5)

        if tick is not None:
            # Usa 'last' se disponível, senão 'bid'
            preco = tick.last if tick.last > 0 else tick.bid
            if preco > 0:
                cotacoes[ticker_site] = round(preco, 2)
                print(f"  {ticker_site:10s} ({simbolo_mt5:15s}) = R$ {preco:.2f}")
            else:
                print(f"  {ticker_site:10s} ({simbolo_mt5:15s}) = sem preço")
        else:
            print(f"  {ticker_site:10s} ({simbolo_mt5:15s}) = símbolo não encontrado no MT5")

    return cotacoes


def enviar_cotacoes(cotacoes: dict):
    """Envia as cotações ao endpoint da API do site."""
    if not cotacoes:
        print("[API] Nenhuma cotação para enviar.")
        return False

    payload = {
        "quotes": cotacoes,
        "user_id": cfg.USER_ID
    }
    headers = {
        "X-API-Key": cfg.API_KEY,
        "Content-Type": "application/json"
    }

    try:
        resp = requests.post(
            cfg.API_URL,
            json=payload,
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            print(f"[API] ✓ Atualizados: {data.get('updated', [])}")
            if data.get('not_found'):
                print(f"[API] ⚠ Não encontrados no site: {data.get('not_found', [])}")
            return True
        elif resp.status_code == 401:
            print("[API] ✗ Erro 401: API Key inválida. Verifique config.py e o .env do VPS.")
        else:
            print(f"[API] ✗ Erro {resp.status_code}: {resp.text[:200]}")
    except requests.exceptions.ConnectionError:
        print("[API] ✗ Sem conexão com o site. Verifique a internet ou URL.")
    except requests.exceptions.Timeout:
        print("[API] ✗ Timeout ao enviar cotações.")
    except Exception as e:
        print(f"[API] ✗ Erro inesperado: {e}")

    return False


def loop_principal():
    """Loop principal: lê MT5 e envia cotações a cada N segundos."""
    print("=" * 60)
    print("  MT5 Feeder — Cotações para invest.casatemporadaceara.cloud")
    print("=" * 60)
    print(f"  Intervalo: {cfg.INTERVALO_SEGUNDOS}s | URL: {cfg.API_URL}")
    print(f"  Tickers configurados: {list(cfg.TICKER_MAP.keys())}")
    print("  Pressione Ctrl+C para parar.\n")

    if not conectar_mt5():
        print("Não foi possível conectar ao MT5. Encerrando.")
        sys.exit(1)

    ciclos_sem_conexao = 0

    try:
        while True:
            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{agora}] Lendo cotações do MT5...")

            # Verifica conexão MT5
            if not mt5.terminal_info():
                ciclos_sem_conexao += 1
                print(f"[MT5] Terminal desconectado. Tentando reconectar ({ciclos_sem_conexao})...")
                if not conectar_mt5():
                    print(f"[MT5] Aguardando {cfg.INTERVALO_SEGUNDOS}s para nova tentativa...")
                    time.sleep(cfg.INTERVALO_SEGUNDOS)
                    continue
                ciclos_sem_conexao = 0

            cotacoes = obter_cotacoes()
            if cotacoes:
                enviar_cotacoes(cotacoes)
            else:
                print("[MT5] Nenhuma cotação lida.")

            print(f"  Próxima atualização em {cfg.INTERVALO_SEGUNDOS}s...")
            time.sleep(cfg.INTERVALO_SEGUNDOS)

    except KeyboardInterrupt:
        print("\n\nFeeder encerrado pelo usuário.")
    finally:
        mt5.shutdown()
        print("[MT5] Conexão encerrada.")


if __name__ == "__main__":
    loop_principal()
