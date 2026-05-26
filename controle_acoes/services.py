
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


def _brapi_one(ticker, token):
    """Busca um único ticker na brapi.dev."""
    params = {'range': '1d', 'interval': '1d', 'fundamental': 'false', 'dividends': 'false', 'token': token}
    try:
        r = requests.get(f"{BASE_URL}/{ticker}", params=params, timeout=10)
        if r.status_code != 200:
            return ticker, None
        for item in r.json().get('results', []):
            price = item.get('regularMarketPrice') or item.get('currentPrice')
            change = item.get('regularMarketChangePercent', 0.0)
            if price and price > 0:
                return ticker, {
                    'price': float(price),
                    'change_percent': float(change or 0),
                    'logo': item.get('logourl', ''),
                    'shortName': item.get('shortName', ticker),
                }
    except Exception as e:
        print(f"brapi error {ticker}: {e}")
    return ticker, None


def _brapi_quotes(tickers, token):
    """Busca cotações via brapi.dev em paralelo (1 ticker/request — plano gratuito)."""
    if not tickers or not token:
        return {}
    from concurrent.futures import ThreadPoolExecutor
    results = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for ticker, data in ex.map(lambda t: _brapi_one(t, token), tickers):
            if data:
                results[ticker] = data
    return results


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
    """Busca em batch via yf.download — ignora linhas com Close=0 (intraday sem dados)."""
    import yfinance as yf
    import pandas as pd
    results = {}
    failed = []
    try:
        data = yf.download(' '.join(yf_tickers), period='5d', progress=False, group_by='ticker', timeout=15)
        for yf_t in yf_tickers:
            clean_key = map_yf_to_clean[yf_t]
            try:
                df_t = None
                if hasattr(data.columns, 'levels') and yf_t in data.columns.levels[0]:
                    df_t = data[yf_t]
                if df_t is None:
                    try:
                        df_t = data[yf_t]
                    except Exception:
                        pass
                if df_t is None or len(df_t) == 0:
                    failed.append(yf_t)
                    continue

                # Filtra linhas com Close > 0 (remove dias sem dados / zeros intraday)
                def _val(v):
                    return float(v.iloc[0]) if hasattr(v, 'iloc') else float(v)

                valid_rows = []
                for idx in range(len(df_t)):
                    try:
                        c = _val(df_t.iloc[idx]['Close'])
                        if not pd.isna(c) and c > 0:
                            valid_rows.append(c)
                    except Exception:
                        pass

                if not valid_rows:
                    failed.append(yf_t)
                    continue

                price = valid_rows[-1]
                prev  = valid_rows[-2] if len(valid_rows) >= 2 else 0.0
                change = ((price - prev) / prev * 100) if prev > 0 else 0.0
                results[clean_key] = {'price': price, 'change_percent': change, 'logo': '', 'shortName': clean_key}
            except Exception:
                failed.append(yf_t)
    except Exception as e:
        print(f"yf.download error: {e}")
        failed = list(yf_tickers)
    return results, failed


def get_quotes(tickers, user_id=None):
    """
    Busca cotações de ações/FIIs/ETFs BR.
    - Com token brapi: um único request para todos os tickers (~0.5s).
    - Sem token brapi: fast_info em paralelo via ThreadPoolExecutor (~3s para 15 tickers).
    """
    if not tickers:
        return {}

    clean_tickers = [t.strip().upper() for t in tickers]
    token = get_token(user_id)

    if token:
        results = {}
        for i in range(0, len(clean_tickers), 50):
            results.update(_brapi_quotes(clean_tickers[i:i+50], token))
        # fallback paralelo para os que a brapi não retornou
        missing = [t for t in clean_tickers if t not in results]
        if missing:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            def _fetch(t):
                return t, _yf_fast_info(f"{t}.SA" if '.' not in t else t, t)
            with ThreadPoolExecutor(max_workers=8) as ex:
                for t, r in ex.map(_fetch, missing):
                    if r:
                        results[t] = r
        return results

    # Sem token: fast_info em paralelo (preciso, sem depender de histórico)
    from concurrent.futures import ThreadPoolExecutor
    def _fetch(t):
        yf_t = t if '.' in t else f"{t}.SA"
        return t, _yf_fast_info(yf_t, t)

    results = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for t, r in ex.map(_fetch, clean_tickers):
            if r:
                results[t] = r
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
