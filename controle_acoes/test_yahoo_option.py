import requests

def test_yahoo(ticker):
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        r = requests.get(url, headers=headers)
        print(f"--- {ticker} ---")
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            try:
                meta = data['chart']['result'][0]['meta']
                print(f"Symbol: {meta['symbol']}")
                print(f"Price: {meta['regularMarketPrice']}")
            except:
                print("No result in body")
        else:
            print("Error")
    except Exception as e:
        print(f"Exception: {e}")

test_yahoo("PETR4.SA")
# Try a more standard near term option if possible. 
# Dec 2025. Jan 2026 option 'A' is correct (Jan). 
# Maybe PETRA20? (Hypothetical)
