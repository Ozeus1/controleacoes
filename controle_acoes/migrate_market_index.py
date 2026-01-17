from app import app, db
from models import MarketIndex
import sqlalchemy

def migrate():
    with app.app_context():
        inspector = sqlalchemy.inspect(db.engine)
        if 'market_index' not in inspector.get_table_names():
            print("Creating market_index table...")
            MarketIndex.__table__.create(db.engine)
            print("Table created.")
            
            # Pre-populate with default indices
            defaults = [
                {'ticker': '^BVSP', 'name': 'IBOV'},
                {'ticker': 'IFIX.SA', 'name': 'IFIX'},
                {'ticker': 'BRL=X', 'name': 'Dólar'}, # USD to BRL usually BRL=X in Yahoo means USD/BRL rate
                {'ticker': 'EURBRL=X', 'name': 'Euro'},
                {'ticker': 'BTC-BRL', 'name': 'Bitcoin'},
                {'ticker': 'ETH-BRL', 'name': 'Ethereum'},
                {'ticker': '^IXIC', 'name': 'Nasdaq'},
                {'ticker': '^GSPC', 'name': 'S&P 500'},
                {'ticker': '^DJI', 'name': 'Dow Jones'}
            ]
            
            for d in defaults:
                if not MarketIndex.query.filter_by(ticker=d['ticker']).first():
                    db.session.add(MarketIndex(ticker=d['ticker'], name=d['name']))
            
            db.session.commit()
            print("Default indices added.")
        else:
            print("Table market_index already exists.")

if __name__ == '__main__':
    migrate()
