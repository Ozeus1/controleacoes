
from app import app, db, Asset
from datetime import date

# Data extracted from user image
# Format: (Ticker, Quantity, Avg Price)
data = [
    ('BBSE3', 100, 34.25),
    ('CPFE3', 40, 39.88),
    ('AXIA6', 50, 57.78),   # Preserving AXIA6 as in image (likely typo for AXIA3 but keeping user data)
    ('GOLD11', 380, 21.92), # ETF, treating as ACAO
    ('KLBN11', 101, 18.67), # Unit
    ('ITSA4', 510, 10.26),
    ('PETR4', 200, 31.45),
    ('ECOR3', 100, 10.46),
    ('GRND3', 200, 5.28),
    ('MATD3', 100, 5.17)
]

with app.app_context():
    count_new = 0
    count_updated = 0
    
    for ticker_raw, qty, price in data:
        ticker = ticker_raw.upper()
        
        # Check for existing
        asset = Asset.query.filter_by(ticker=ticker).first()
        
        if asset:
            # Update to match image
            asset.quantity = qty
            asset.avg_price = price
            count_updated += 1
            print(f"Updated {ticker}")
        else:
            # Create new
            asset = Asset(
                ticker=ticker,
                quantity=qty,
                avg_price=price,
                type='ACAO', # Defaulting to ACAO
                entry_date=date.today()
            )
            db.session.add(asset)
            count_new += 1
            print(f"Created {ticker}")
            
    db.session.commit()
    print(f"Done! Created: {count_new}, Updated: {count_updated}")
