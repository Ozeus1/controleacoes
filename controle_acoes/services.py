
import requests
import os
import time

from flask import current_app

BASE_URL = "https://brapi.dev/api/quote"


def get_token(user_id=None):
    try:
        from models import Settings
        if user_id:
            token = Settings.get_value('brapi_token', user_id=user_id)
            if token:
                return token
    except Exception:
        pass
    return os.environ.get('BRAPI_API_KEY', '')


def _brapi_quotes(tickers, token):
    """Busca cotações via brapi.dev (requer token). Retorna dict {ticker: {price, change_percent}}."""
    if not tickers or not token:
        return {}
    joined = ','.join(tickers)
    params = {'range': '1d', 'interval': '1d', 'fundamental': 'false', 'dividends': 'false', 'token': token}
    try:
        r = requests.get(f"{BASE_URL}/{joined}", params=params, timeout=15)
        if r.status_code != 200:
            return {}
        results = {}
        for item in r.json().get('results', []):
            sym = item.get('symbol', '').upper()
            price = item.get('regularMarketPrice') or item.get('currentPrice')
            change = item.get('regularMarketChangePercent', 0.0)
            if price and price > 0:
                results[sym] = {
                    'price': float(price),
                    'change_percent': float(change or 0),
                    'logo': item.get('logourl', ''),
                    'shortName': item.get('shortName', sym),
                }
        return results
    except Exception as e:
        print(f"brapi error: {e}")
        return {}


def _yf_fast_info(yf_t, clean_key):
    """Busca cotação individual via yfinance fast_info (preço atual de mercado)."""
    import yfinance as yf
    try:
        fi = yf.Ticker(yf_t).fast_info
        price = fi.last_price
        prev  = fi.previous_close
        if price and price > 0:
            change = ((price - prev) / prev * 100) if prev and prev > 0 else 0.0
            return {'price': float(price), 'change_percent': float(change), 'logo': '', 'shortName': clean_key}
    except Exception as e:
        print(f"yf fast_info failed for {yf_t}: {e}")
    return None


def _yf_bulk(yf_tickers, map_yf_to_clean):
    """Busca em batch via yf.download — rápido mas usa fechamento histórico."""
    import yfinance as yf
    import pandas as pd
    results = {}
    failed = []
    try:
        data = yf.download(' '.join(yf_tickers), period='2d', progress=False, group_by='ticker', timeout=15)
        for yf_t in yf_tickers:
            clean_key = map_yf_to_clean[yf_t]
            try:
                df_t = None
                if hasattr(data.columns, 'levels') and yf_t in data.columns.levels[0]:
                    df_t = data[yf_t]
                if df_t is None:
                    df_t = data[yf_t]
                if df_t is None or len(df_t) == 0:
                    failed.append(yf_t)
                    continue
                price = df_t.iloc[-1]['Close']
                if hasattr(price, 'iloc'):
                    price = price.iloc[0]
                if pd.isna(price):
                    failed.append(yf_t)
                    continue
                prev = 0.0
                if len(df_t) > 1:
                    pc = df_t.iloc[-2]['Close']
                    if hasattr(pc, 'iloc'):
                        pc = pc.iloc[0]
                    if not pd.isna(pc):
                        prev = float(pc)
                change = ((float(price) - prev) / prev * 100) if prev > 0 else 0.0
                results[clean_key] = {'price': float(price), 'change_percent': change, 'logo': '', 'shortName': clean_key}
            except Exception:
                failed.append(yf_t)
    except Exception as e:
        print(f"yf.download error: {e}")
        failed = list(yf_tickers)
    return results, failed


def get_quotes(tickers, user_id=None):
    """
    Busca cotações de ações/FIIs/ETFs BR.
    - Com token brapi: usa brapi.dev (rápido, preciso, um request).
    - Sem token brapi: yf.download em batch + fast_info para corrigir variações absurdas.
    """
    if not tickers:
        return {}

    clean_tickers = [t.strip().upper() for t in tickers]
    token = get_token(user_id)

    if token:
        # brapi em chunks de 50
        results = {}
        for i in range(0, len(clean_tickers), 50):
            chunk = clean_tickers[i:i + 50]
            results.update(_brapi_quotes(chunk, token))
        # fallback para tickers não retornados
        missing = [t for t in clean_tickers if t not in results]
        for t in missing:
            r = _yf_fast_info(f"{t}.SA" if '.' not in t else t, t)
            if r:
                results[t] = r
            time.sleep(0.2)
        return results

    # Sem token: yf.download em batch (rápido)
    yf_map = {}
    for t in clean_tickers:
        yf_t = t if '.' in t else f"{t}.SA"
        yf_map[yf_t] = t

    chunk_size = 10
    yf_list = list(yf_map.keys())
    results = {}
    all_failed = []

    for i in range(0, len(yf_list), chunk_size):
        chunk = yf_list[i:i + chunk_size]
        sub_map = {k: yf_map[k] for k in chunk}
        if len(chunk) == 1:
            r = _yf_fast_info(chunk[0], sub_map[chunk[0]])
            if r:
                results[sub_map[chunk[0]]] = r
        else:
            got, failed = _yf_bulk(chunk, sub_map)
            results.update(got)
            all_failed.extend(failed)
        if i + chunk_size < len(yf_list):
            time.sleep(1)

    # Para tickers com variação absurda (>20%) corrige via fast_info
    for clean, v in list(results.items()):
        if abs(v.get('change_percent', 0)) > 20:
            yf_t = clean if '.' in clean else f"{clean}.SA"
            r = _yf_fast_info(yf_t, clean)
            if r:
                results[clean] = r

    # Fallback para os que falharam
    for yf_t in all_failed:
        clean = yf_map.get(yf_t, yf_t)
        if clean not in results:
            r = _yf_fast_info(yf_t, clean)
            if r:
                results[clean] = r
            time.sleep(0.3)

    return results


def get_raw_quote_data(ticker):
    """Retorna dados brutos da brapi.dev para um ticker."""
    token = get_token()
    params = {'range': '1d', 'interval': '1d'}
    if token:
        params['token'] = token
    try:
        response = requests.get(f"{BASE_URL}/{ticker}", params=params, timeout=10)
        if response.status_code == 200:
            return True, response.json()
        return False, {'error': f"Status {response.status_code}", 'body': response.text}
    except Exception as e:
        return False, {'error': str(e)}
