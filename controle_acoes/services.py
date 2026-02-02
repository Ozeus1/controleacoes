
import requests
import os


from flask import current_app
# Circular import note: models imports db, services might need db/Settings inside function to avoid init issues
# or pass the token. Best to import Settings inside function if we are outside of app context scope issue, but we are inside Flask.
# Actually, services.py is just utils. Let's do a late import.

BASE_URL = "https://brapi.dev/api/quote"

def get_token(user_id=None):
    try:
        from models import Settings
        if user_id:
            token = Settings.get_value('brapi_token', user_id=user_id)
            if token:
                return token
        # Fallback to env or maybe a "System Admin" user (ID 1)?
        # For now, if no user specific token, maybe return None or Env
    except Exception:
        pass
    return os.environ.get('BRAPI_API_KEY', '')

def _fetch_single_ticker(yf_t, clean_key):
    """Fallback: fetch a single ticker using yf.Ticker when bulk download fails."""
    import yfinance as yf
    try:
        t_obj = yf.Ticker(yf_t)
        info = t_obj.fast_info
        last_price = info.last_price
        prev_close = info.previous_close
        if last_price and last_price > 0:
            change = 0.0
            if prev_close and prev_close > 0:
                change = ((last_price - prev_close) / prev_close) * 100
            return {
                'price': float(last_price),
                'change_percent': float(change),
                'logo': '',
                'shortName': clean_key
            }
    except Exception as e:
        print(f"Fallback fetch failed for {yf_t}: {e}")
    return None


def _parse_bulk_download(data, yf_tickers, map_yf_to_clean):
    """Parse results from yf.download for a chunk of tickers."""
    import pandas as pd
    results = {}
    failed = []

    if len(yf_tickers) == 1:
        # Single ticker: use individual fetch (more reliable)
        yf_t = yf_tickers[0]
        clean_key = map_yf_to_clean[yf_t]
        result = _fetch_single_ticker(yf_t, clean_key)
        if result:
            results[clean_key] = result
        else:
            failed.append(yf_t)
        return results, failed

    # Multiple tickers: parse MultiIndex DataFrame
    for yf_t in yf_tickers:
        try:
            df_t = None
            # Try MultiIndex access (group_by='ticker')
            if hasattr(data.columns, 'levels') and len(data.columns.levels) > 0:
                if yf_t in data.columns.levels[0]:
                    df_t = data[yf_t]
            # Try direct column access (newer yfinance or flat structure)
            if df_t is None:
                try:
                    df_t = data[yf_t]
                except (KeyError, TypeError):
                    pass

            if df_t is None or len(df_t) == 0:
                failed.append(yf_t)
                continue

            last_row = df_t.iloc[-1]
            price = last_row['Close']

            # Handle Series (when Close has sub-index)
            if hasattr(price, 'iloc'):
                price = price.iloc[0]

            if pd.isna(price):
                failed.append(yf_t)
                continue

            prev_close = 0.0
            if len(df_t) > 1:
                pc = df_t.iloc[-2]['Close']
                if hasattr(pc, 'iloc'):
                    pc = pc.iloc[0]
                if not pd.isna(pc):
                    prev_close = pc
            elif len(df_t) == 1:
                pc = df_t.iloc[-1]['Open']
                if hasattr(pc, 'iloc'):
                    pc = pc.iloc[0]
                if not pd.isna(pc):
                    prev_close = pc

            change = 0.0
            if prev_close and prev_close > 0:
                change = ((price - prev_close) / prev_close) * 100

            clean_key = map_yf_to_clean[yf_t]
            results[clean_key] = {
                'price': float(price),
                'change_percent': float(change),
                'logo': '',
                'shortName': clean_key
            }
        except Exception as inner_e:
            print(f"Error parsing {yf_t}: {inner_e}")
            failed.append(yf_t)
            continue

    return results, failed


def get_quotes(tickers, user_id=None):
    """
    Fetches quotes for a list of tickers using Yahoo Finance (yfinance).
    Returns a dict: {ticker: {price: float, change: float, logo: str, ...}}
    Processes in chunks to avoid timeouts on slow connections.
    """
    if not tickers:
        return {}

    import yfinance as yf
    import time

    # Prepare tickers for Yahoo (Append .SA if not present)
    yf_tickers = []
    map_yf_to_clean = {}

    for t in tickers:
        clean = t.strip().upper()
        if '.' not in clean:
             yf_t = f"{clean}.SA"
        else:
             yf_t = clean
        yf_tickers.append(yf_t)
        map_yf_to_clean[yf_t] = clean

    results = {}
    all_failed = []

    # Process in chunks of 8 to avoid timeouts
    chunk_size = 8
    chunks = [yf_tickers[i:i + chunk_size] for i in range(0, len(yf_tickers), chunk_size)]

    for chunk in chunks:
        try:
            str_tickers = " ".join(chunk)
            data = yf.download(str_tickers, period="2d", progress=False, group_by='ticker', timeout=15)

            chunk_results, failed = _parse_bulk_download(data, chunk, map_yf_to_clean)
            results.update(chunk_results)
            all_failed.extend(failed)
        except Exception as e:
            print(f"Error downloading chunk {chunk}: {e}")
            all_failed.extend(chunk)

        if len(chunks) > 1:
            time.sleep(1)

    # Retry failed tickers individually
    if all_failed:
        print(f"Retrying {len(all_failed)} failed tickers individually...")
        for yf_t in all_failed:
            clean_key = map_yf_to_clean[yf_t]
            if clean_key not in results:
                result = _fetch_single_ticker(yf_t, clean_key)
                if result:
                    results[clean_key] = result
                time.sleep(0.5)

    return results

def get_raw_quote_data(ticker):
    """
    Fetches raw JSON for a single ticker to display to the user.
    """
    token = get_token()
    params = {}
    if token:
        params['token'] = token
    
    url = f"{BASE_URL}/{ticker}"
    
    try:
        response = requests.get(url, params=params, timeout=10)
        # We return the JSON body even if error status, or construct error dict
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, {'error': f"Status {response.status_code}", 'body': response.text}
    except Exception as e:
        return False, {'error': str(e)}

