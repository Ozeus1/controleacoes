
from app import app, db, Asset
from datetime import date

# Data extracted from user image
# Format: (Ticker, Quantity, Avg Price, FII Type)
data = [
    ('HGRE11', 30, 125.94, 'LAJES CORPORATIVAS'),
    ('HGRU11', 30, 125.61, 'HIBRIDO'),
    ('HSLG11', 11, 82.24, 'LOGISTICA'),
    ('HSML11', 11, 85.54, 'SHOPPING CENTER'),
    ('LVBI11', 35, 108.15, 'LOGISTICA'),
    ('MANA11', 420, 8.94, 'RECEBIVEIS'),
    ('MCCI11', 15, 88.35, 'RECEBIVEIS'),
    ('MCRE11', 400, 8.90, 'RECEBIVEIS'),
    ('NSLU11', 5, 171.28, 'LAJES CORPORATIVAS'),
    ('OIAG11', 300, 8.32, 'FIAGRO'), # Likely OIAG11 based on FIAGRO type
    ('PMLL11', 10, 100.03, 'SHOPPING CENTER'), # Transcribed as seen, verify if MALL11 intended? Keeping PMLL11.
    ('RBRL11', 12, 76.64, 'LOGISTICA'),
    ('RBRP11', 20, 49.57, 'LAJES CORPORATIVAS'),
    ('RBRR11', 10, 84.87, 'RECEBIVEIS'),
    ('RBRY11', 40, 95.71, 'RECEBIVEIS'),
    ('RBVA11', 210, 8.92, 'LAJES CORPORATIVAS'),
    ('RZAK11', 15, 82.93, 'RECEBIVEIS'),
    ('RZAT11', 12, 93.64, 'HIBRIDO'),
    ('RZTR11', 15, 91.77, 'HIBRIDO'),
    ('SPXS11', 450, 8.51, 'HIBRIDO'),
    ('VCJR11', 50, 77.19, 'RECEBIVEIS'),
    ('VGIA11', 360, 8.78, 'FIAGRO'),
    ('VGIP11', 15, 80.18, 'RECEBIVEIS'),
    ('VISC11', 10, 112.83, 'SHOPPING CENTER'),
    ('XPCI11', 20, 83.84, 'RECEBIVEIS'),
    ('XPIN11', 20, 73.85, 'LOGISTICA'),
    ('XPML11', 35, 105.20, 'SHOPPING CENTER'),
    ('GGRC11', 110, 0.00, 'HIBRIDO') # Price 0 in image (Total 0), default to HIBRIDO/LOGISTICA based on asset knowledge or OUTROS? GGRC is Hibrido/Logistica.
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
