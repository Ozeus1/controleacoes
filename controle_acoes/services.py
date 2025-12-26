
import requests
import os


from flask import current_app
# Circular import note: models imports db, services might need db/Settings inside function to avoid init issues
# or pass the token. Best to import Settings inside function if we are outside of app context scope issue, but we are inside Flask.
# Actually, services.py is just utils. Let's do a late import.

BASE_URL = "https://brapi.dev/api/quote"

def get_token():
    try:
        from models import Settings
        token = Settings.get_value('brapi_token')
        if token:
            return token
    except Exception:
        pass
    return os.environ.get('BRAPI_API_KEY', '')

def get_quotes(tickers):
    """
    Fetches quotes for a list of tickers.
    Returns a dict: {ticker: {price: float, change: float, logo: str, ...}}
    """
    if not tickers:
        return {}
    
    token = get_token()
    
    params = {}
    if token:
        params['token'] = token
    
    tickers_param = ','.join(tickers)
    url = f"{BASE_URL}/{tickers_param}"
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = {}
        if 'results' in data:
            for item in data['results']:
                symbol = item.get('symbol')
                results[symbol] = {
                    'price': item.get('regularMarketPrice', 0.0),
                    'change_percent': item.get('regularMarketChangePercent', 0.0),
                    'logo': item.get('logourl', ''),
                    'shortName': item.get('shortName', '')
                }
        return results
        
    except Exception as e:
        print(f"Error fetching quotes: {e}")
        return {}

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

