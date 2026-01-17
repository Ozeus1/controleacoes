def migrate():
    with app.app_context():
        # Ensure table exists
        inspector = sqlalchemy.inspect(db.engine)
        if 'market_index' not in inspector.get_table_names():
            print("Creating market_index table...")
            MarketIndex.__table__.create(db.engine)
        
        # Upsert Defaults
        defaults = [
            {'ticker': '^BVSP', 'name': 'IBOV'},
            {'ticker': 'IFIX.SA', 'name': 'IFIX'},
            {'ticker': 'BRL=X', 'name': 'Dólar'},
            {'ticker': 'EURBRL=X', 'name': 'Euro'},
            {'ticker': 'BTC-BRL', 'name': 'Bitcoin'},
            {'ticker': 'ETH-BRL', 'name': 'Ethereum'},
            {'ticker': '^IXIC', 'name': 'Nasdaq'},
            {'ticker': '^GSPC', 'name': 'S&P 500'},
            {'ticker': '^DJI', 'name': 'Dow Jones'}
        ]
        
        print("Checking/Adding default indices...")
        added = 0
        for d in defaults:
            current = MarketIndex.query.filter_by(ticker=d['ticker']).first()
            if not current:
                print(f"Adding {d['name']} ({d['ticker']})")
                db.session.add(MarketIndex(ticker=d['ticker'], name=d['name']))
                added += 1
            else:
                # Optional: Update name if changed
                current.name = d['name']
        
        db.session.commit()
        print(f"Migration complete. {added} indices added.")
