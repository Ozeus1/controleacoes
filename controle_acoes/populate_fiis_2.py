
from app import app, db, Asset
from datetime import date

# Data extracted from second user image
# Format: (Ticker, Quantity, Avg Price, FII Type)
data = [
    ('AAZQ11', 300, 7.94, 'FIAGRO'),
    ('BDIF11', 19, 70.28, 'INFRA'),
    ('BRCO11', 12, 104.33, 'LOGISTICA'),
    ('BTCI11', 400, 9.34, 'RECEBIVEIS'),
    ('BTLG11', 36, 102.19, 'LOGISTICA'),
    ('CDII11', 13, 108.91, 'INFRA'),
    ('CPTS11', 300, 7.68, 'RECEBIVEIS'),
    ('FGAA11', 300, 8.99, 'FIAGRO'),
    ('GARE11', 410, 8.99, 'LOGISTICA'),
    ('HGBS11', 200, 20.19, 'SHOPPING CENTER'), 
    ('HGLG11', 10, 162.47, 'LOGISTICA')
]

with app.app_context():
    count_new = 0
    count_updated = 0
    
    for ticker_raw, qty, price, ftype in data:
        ticker = ticker_raw.upper()
        
        # Check for existing
        asset = Asset.query.filter_by(ticker=ticker).first()
        
        if asset:
            # Update
            asset.quantity = qty
            asset.avg_price = price
            asset.type = 'FII' # Ensure type is FII
            asset.fii_type = ftype
            count_updated += 1
            print(f"Updated {ticker}")
        else:
            # Create new
            asset = Asset(
                ticker=ticker,
                quantity=qty,
                avg_price=price,
                type='FII',
                fii_type=ftype,
                entry_date=date.today()
            )
            db.session.add(asset)
            count_new += 1
            print(f"Created {ticker}")
            
    db.session.commit()
    print(f"Done! Created: {count_new}, Updated: {count_updated}")
