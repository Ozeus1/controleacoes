
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

def get_quotes(tickers, user_id=None):
    """
    Fetches quotes for a list of tickers using Yahoo Finance (yfinance).
    Returns a dict: {ticker: {price: float, change: float, logo: str, ...}}
    """
    if not tickers:
        return {}
        
    import yfinance as yf
    import pandas as pd
    
    # Prepare tickers for Yahoo (Append .SA if not present)
    # Assumes Brazilian market for now
    yf_tickers = []
    map_yf_to_clean = {}
    
    for t in tickers:
        clean = t.strip().upper()
        # Basic heuristic: if it doesn't have a dot and is not a crypto (usually), add .SA
        # Cryptos normally have -USD or similar. Let's assume Stocks/FIIs here.
        if not '.' in clean:
             yf_t = f"{clean}.SA"
        else:
             yf_t = clean
             
        yf_tickers.append(yf_t)
        map_yf_to_clean[yf_t] = clean

    str_tickers = " ".join(yf_tickers)
    
    try:
        # Fetch data
        # period='2d' to calculate change if needed, but '1d' might not give 'close' of yesterday easily.
        # Actually, yf download '1d' gives current data.
        # Efficient bulk download
        data = yf.download(str_tickers, period="2d", progress=False, group_by='ticker')
        
        results = {}
        
        # If single ticker, columns are Flat (Open, High...). If Multiple, MultiIndex (Ticker, Open...)
        # But group_by='ticker' makes it (Ticker, OHLC).
        
        # Handle Single Ticker case (DataFrame structure differs)
        if len(yf_tickers) == 1:
            t_obj = yf.Ticker(yf_tickers[0])
            info = t_obj.fast_info
            
            # fast_info is reliable for current price
            last_price = info.last_price
            prev_close = info.previous_close
            
            if last_price:
                change = 0.0
                if prev_close:
                    change = ((last_price - prev_close) / prev_close) * 100
                
                clean_key = map_yf_to_clean[yf_tickers[0]]
                results[clean_key] = {
                    'price': float(last_price),
                    'change_percent': float(change),
                    'logo': '',
                    'shortName': clean_key
                }
        else:
            # Bulk download structure
            # data.columns -> MultiIndex
            for yf_t in yf_tickers:
                try:
                    # Access data for this ticker
                    # If flat (unlikely with >1), checks needed.
                    if yf_t in data.columns.levels[0]:
                        df_t = data[yf_t]
                    else:
                        # Fallback check
                        continue

                    # Get last valid price
                    # Ilock -1 is current, -2 is yesterday
                    if len(df_t) > 0:
                        last_row = df_t.iloc[-1]
                        price = last_row['Close']
                        
                        # Calculate change
                        prev_close = 0.0
                        if len(df_t) > 1:
                            prev_close = df_t.iloc[-2]['Close']
                        elif len(df_t) == 1:
                             # Try accessing Open? Or assume 0 change
                             prev_close = df_t.iloc[-1]['Open']
                             
                        change = 0.0
                        if prev_close and prev_close > 0:
                            change = ((price - prev_close) / prev_close) * 100

                        clean_key = map_yf_to_clean[yf_t]
                        
                        # Handle NaN
                        if pd.isna(price): 
                             continue
                             
                        results[clean_key] = {
                            'price': float(price),
                            'change_percent': float(change),
                            'logo': '',
                            'shortName': clean_key
                        }
                except Exception as inner_e:
                    print(f"Error parsing {yf_t}: {inner_e}")
                    continue

        return results

    except Exception as e:
        print(f"Error calling yfinance: {e}")
        # Allow app.py to catch this
        raise e

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

