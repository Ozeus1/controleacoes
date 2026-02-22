#!/usr/bin/env python3
"""
mt5_live.py — Atualizador de cotações para o Desktop App
==========================================================
Roda em duas threads paralelas:

  • MT5Thread  — atualiza tickers mapeados em TICKER_MAP a cada 5 s
  • YahooThread — atualiza tickers NÃO mapeados via Yahoo Finance a cada 60 s

Se o MT5 não estiver disponível, todos os tickers vão pelo Yahoo (60 s).
A atualização é feita diretamente no SQLite via SQLAlchemy (sem HTTP).
"""

import sys
import os
import threading
import time
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger('mt5_live')

BR_TZ          = ZoneInfo('America/Sao_Paulo')
MT5_INTERVAL   = 5    # segundos entre atualizações MT5
YAHOO_INTERVAL = 60   # segundos entre atualizações Yahoo


# ══════════════════════════════════════════════════════════════════════════════
# Config
# ══════════════════════════════════════════════════════════════════════════════

def load_maps():
    """Carrega TICKER_MAP e OPTION_MAP do mt5_feeder/config.py."""
    _base = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
    feeder_dir = os.path.join(_base, 'mt5_feeder')
    if feeder_dir not in sys.path:
        sys.path.insert(0, feeder_dir)
    try:
        import config as cfg
        tm = getattr(cfg, 'TICKER_MAP', {})
        om = getattr(cfg, 'OPTION_MAP', {})
        logger.info(f"Config carregado: {len(tm)} ações, {len(om)} opções mapeadas no MT5")
        return tm, om
    except ImportError:
        logger.warning("mt5_feeder/config.py não encontrado — MT5 desabilitado")
        return {}, {}


# ══════════════════════════════════════════════════════════════════════════════
# MT5 helpers
# ══════════════════════════════════════════════════════════════════════════════

def mt5_connect():
    """Inicializa o MT5. Retorna o módulo ou None."""
    try:
        import MetaTrader5 as mt5
        if mt5.initialize():
            info = mt5.terminal_info()
            logger.info(f"MT5 conectado — {info.name} build {info.build}")
            return mt5
        logger.warning(f"MT5 não inicializou: {mt5.last_error()}")
    except ImportError:
        logger.warning("Pacote MetaTrader5 não instalado — usando só Yahoo Finance")
    return None


def mt5_get_price(mt5, symbol, retries=3, wait=0.3):
    """Retorna (price, change_pct) lendo do MT5. None se não disponível."""
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        mt5.symbol_select(symbol, True)
        for _ in range(retries):
            time.sleep(wait)
            tick = mt5.symbol_info_tick(symbol)
            if tick is not None:
                break
    if tick is None:
        return None, None

    price = tick.last if tick.last > 0 else tick.bid
    if price <= 0:
        return None, None

    info   = mt5.symbol_info(symbol)
    change = 0.0
    if info and info.session_open > 0:
        change = round((price - info.session_open) / info.session_open * 100, 2)

    return round(price, 2), change


# ══════════════════════════════════════════════════════════════════════════════
# Yahoo Finance helpers
# ══════════════════════════════════════════════════════════════════════════════

def yahoo_prices_batch(tickers: list) -> dict:
    """
    Retorna {ticker_site: (price, change_pct)} via yfinance.
    Adiciona sufixo .SA para tickers brasileiros automaticamente.
    """
    if not tickers:
        return {}

    try:
        import yfinance as yf

        # Monta mapeamento ticker_site → ticker_yf
        yf_map = {t: (t + '.SA' if '.' not in t else t) for t in tickers}
        yf_symbols = list(yf_map.values())

        raw = yf.download(
            tickers=yf_symbols,
            period='2d',
            interval='1d',
            progress=False,
            auto_adjust=True,
            group_by='ticker',
        )

        results = {}
        if raw.empty:
            return results

        single = len(yf_symbols) == 1

        for orig, yf_t in yf_map.items():
            try:
                col = raw['Close'] if single else raw[yf_t]['Close']
                vals = col.dropna()
                if len(vals) >= 1:
                    price  = float(vals.iloc[-1])
                    prev   = float(vals.iloc[-2]) if len(vals) >= 2 else price
                    change = round((price - prev) / prev * 100, 2) if prev else 0.0
                    results[orig] = (round(price, 2), change)
            except Exception:
                pass

        return results

    except Exception as e:
        logger.error(f"Yahoo batch error: {e}")
        return {}


# ══════════════════════════════════════════════════════════════════════════════
# DB update helper
# ══════════════════════════════════════════════════════════════════════════════

def apply_prices(flask_app, prices: dict, option_prices: dict = None):
    """
    Aplica preços no banco de dados.
    prices        = {ticker: (price, change_pct)}
    option_prices = {ticker: price}
    """
    if not prices and not option_prices:
        return

    now_dt = datetime.now(BR_TZ).replace(tzinfo=None)  # SQLite stores naive datetimes

    with flask_app.app_context():
        from models import db, Asset, Option

        count = 0
        for ticker, (price, change) in prices.items():
            asset = Asset.query.filter_by(ticker=ticker).first()
            if asset:
                asset.current_price = price
                asset.daily_change  = change
                asset.last_update   = now_dt
                count += 1

        if option_prices:
            for ticker, price in option_prices.items():
                opt = Option.query.filter_by(ticker=ticker).first()
                if opt:
                    opt.current_option_price = price
                    count += 1

        if count:
            db.session.commit()

    return count


# ══════════════════════════════════════════════════════════════════════════════
# Thread loops
# ══════════════════════════════════════════════════════════════════════════════

def mt5_thread_loop(flask_app, mt5_module, ticker_map: dict, option_map: dict):
    """
    Atualiza a cada MT5_INTERVAL segundos os tickers presentes no TICKER_MAP.
    Se o MT5 desconectar, tenta reconectar automaticamente.
    """
    logger.info(f"[MT5Thread] Iniciado — intervalo {MT5_INTERVAL}s")

    while True:
        try:
            # Verifica conexão MT5
            if not mt5_module.terminal_info():
                logger.warning("[MT5Thread] Conexão perdida, reconectando...")
                mt5_module.initialize()
                time.sleep(2)
                continue

            prices       = {}
            option_prices = {}
            now_str      = datetime.now(BR_TZ).strftime('%H:%M:%S')

            # Lê preços de ações/ETFs/FIIs/swings pelo ticker_map
            for site_ticker, mt5_symbol in ticker_map.items():
                price, change = mt5_get_price(mt5_module, mt5_symbol)
                if price is not None:
                    prices[site_ticker] = (price, change)
                    logger.debug(f"  MT5 {site_ticker:12s} = R$ {price:.2f} ({change:+.2f}%)")

            # Lê preços de opções pelo option_map
            for site_ticker, mt5_symbol in option_map.items():
                price, _ = mt5_get_price(mt5_module, mt5_symbol)
                if price is not None:
                    option_prices[site_ticker] = price

            count = apply_prices(flask_app, prices, option_prices)
            if count:
                logger.info(f"[MT5Thread] {count} cotações atualizadas às {now_str}")

        except Exception as e:
            logger.error(f"[MT5Thread] Erro: {e}")

        time.sleep(MT5_INTERVAL)


def yahoo_thread_loop(flask_app, mapped_tickers: set):
    """
    Atualiza a cada YAHOO_INTERVAL segundos os tickers NÃO presentes no TICKER_MAP.
    Se mapped_tickers estiver vazio (sem MT5), atualiza todos.
    """
    logger.info(f"[YahooThread] Iniciado — intervalo {YAHOO_INTERVAL}s")

    while True:
        try:
            with flask_app.app_context():
                from models import Asset
                all_assets    = Asset.query.all()
                yahoo_tickers = [
                    a.ticker for a in all_assets
                    if a.ticker not in mapped_tickers
                ]

            if yahoo_tickers:
                logger.info(f"[YahooThread] Buscando {len(yahoo_tickers)} tickers...")
                batch = yahoo_prices_batch(yahoo_tickers)
                count = apply_prices(flask_app, batch)
                now_str = datetime.now(BR_TZ).strftime('%H:%M:%S')
                if count:
                    logger.info(f"[YahooThread] {count} cotações atualizadas às {now_str}")
            else:
                logger.debug("[YahooThread] Sem tickers para atualizar pelo Yahoo")

        except Exception as e:
            logger.error(f"[YahooThread] Erro: {e}")

        time.sleep(YAHOO_INTERVAL)


# ══════════════════════════════════════════════════════════════════════════════
# Ponto de entrada público
# ══════════════════════════════════════════════════════════════════════════════

def start_updater(flask_app):
    """
    Carrega a configuração e inicia as threads de atualização.
    Chamado pelo desktop_app.py após o Flask estar pronto.
    """
    ticker_map, option_map = load_maps()
    mt5 = mt5_connect()

    if mt5:
        # Thread MT5 para tickers mapeados
        t1 = threading.Thread(
            target=mt5_thread_loop,
            args=(flask_app, mt5, ticker_map, option_map),
            daemon=True,
            name='MT5Thread',
        )
        t1.start()

        # Thread Yahoo para os demais
        t2 = threading.Thread(
            target=yahoo_thread_loop,
            args=(flask_app, set(ticker_map.keys())),
            daemon=True,
            name='YahooThread',
        )
        t2.start()

        logger.info(
            f"Updater iniciado: MT5 ({len(ticker_map)} mapeados, {MT5_INTERVAL}s) "
            f"+ Yahoo (demais, {YAHOO_INTERVAL}s)"
        )
    else:
        # Sem MT5 → tudo pelo Yahoo
        t = threading.Thread(
            target=yahoo_thread_loop,
            args=(flask_app, set()),   # set vazio = atualiza todos
            daemon=True,
            name='YahooThread',
        )
        t.start()
        logger.info(f"Updater iniciado: apenas Yahoo Finance ({YAHOO_INTERVAL}s) — MT5 indisponível")
