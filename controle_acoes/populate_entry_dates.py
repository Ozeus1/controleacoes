from app import app, db, Asset
from datetime import date

def populate_dates():
    with app.app_context():
        # Select all Stocks and FIIs
        assets = Asset.query.filter(Asset.type.in_(['ACAO', 'FII'])).all()
        
        count = 0
        default_date = date(2025, 1, 1)
        
        for asset in assets:
            # Update all, or only those without date? 
            # User said "Povoe ... como 01/01/2025", implying a bulk set.
            # I will set it for everyone to ensure consistency as requested.
            asset.entry_date = default_date
            count += 1
            
        db.session.commit()
        print(f"Updated {count} assets with entry_date = 01/01/2025")

if __name__ == "__main__":
    populate_dates()
