"""Corrige a faixa de cotacoes: Bitcoin em USD (nao mais BRL), remove Ethereum.

Rodar uma vez apos o deploy (na VPS, do diretorio com venv/ e app.py):
    ./venv/bin/python scripts/fix_market_indices_btc_eth.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A                    # noqa: E402
from models import db, MarketIndex # noqa: E402


def main():
    with A.app.app_context():
        eth = MarketIndex.query.filter_by(name='Ethereum').first()
        if eth:
            db.session.delete(eth)
            print('Removido: Ethereum')
        else:
            print('Ethereum: nao encontrado (ja removido ou nunca existiu)')

        btc = MarketIndex.query.filter_by(name='Bitcoin').first()
        if btc:
            if btc.ticker != 'BTC-USD':
                print(f'Bitcoin: ticker {btc.ticker!r} -> BTC-USD')
                btc.ticker = 'BTC-USD'
                btc.price = 0.0          # forca nova busca no proximo update_market_indices()
                btc.change_percent = 0.0
            else:
                print('Bitcoin: ja esta em BTC-USD')
        else:
            print('Bitcoin: nao encontrado — sera criado em BTC-USD na proxima atualizacao')

        db.session.commit()
        print('\nEstado final:')
        for i in MarketIndex.query.all():
            print(f'  {i.id:>3} {i.ticker:12} {i.name:12} price={i.price}')


if __name__ == '__main__':
    main()
