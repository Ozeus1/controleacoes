
import os
from app import app, db, Asset
from services import get_quotes

def test_app():
    print("Testing Database...")
    # Create a fresh db for testing (in memory or file)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        print("Success: Database tables created.")
        
        # Test adding asset
        asset = Asset(ticker='PETR4', type='ACAO', quantity=100, avg_price=30.00)
        db.session.add(asset)
        db.session.commit()
        print(f"Success: Added asset {asset.ticker}")
        
        # Test reading asset
        read_asset = Asset.query.first()
        assert read_asset.ticker == 'PETR4'
        print("Success: Verified asset in DB.")
        
        # Test BRAPI Service
        print("\nTesting BRAPI Service (Free Tier)...")
        # PETR4 is usually available in free tier/mock if no key
        quotes = get_quotes(['PETR4'])
        
        if 'PETR4' in quotes:
            print(f"Success: Fetched quote for PETR4: {quotes['PETR4']}")
        else:
            print("Warning: Could not fetch PETR4 (Check Internet or API limits).")
            # This isn't a hard failure for the app structure, but good to know
            
if __name__ == "__main__":
    test_app()
