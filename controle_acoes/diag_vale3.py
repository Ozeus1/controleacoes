# -*- coding: utf-8 -*-
"""Diagnóstico: por que o crédito de um trade de opções não chega ao PM.

Uso no VPS, dentro da pasta do projeto e com o venv ativo:

    python diag_vale3.py VALE3

Só LÊ o banco — não altera nada.
"""
import sys
from datetime import date

from app import app, _pm_earned_items, _pm_state
from models import Asset, TradeHistory, PMEvent

TICKER = (sys.argv[1] if len(sys.argv) > 1 else 'VALE3').upper()

with app.app_context():
    a = Asset.query.filter(Asset.ticker == TICKER,
                           Asset.type.in_(('ACAO', 'FII'))).first()
    if not a:
        print('Ativo %s não encontrado.' % TICKER)
        sys.exit(1)
    uid = a.user_id
    print('=' * 70)
    print('%s — qtd %s | PM oficial R$ %.2f | user_id %s'
          % (TICKER, a.quantity, a.avg_price or 0, uid))
    print('=' * 70)

    # 1) Todos os trades que MENCIONAM o ticker de algum jeito
    print()
    print('TRADES QUE MENCIONAM %s (qualquer campo):' % TICKER)
    achou = False
    for th in TradeHistory.query.filter_by(user_id=uid).all():
        campos = ' '.join([th.ticker or '', th.underlying or '',
                           th.notes or '', th.strategy or '']).upper()
        if TICKER in campos:
            achou = True
            print('  id=%-5s exit=%-10s lucro=%10.2f' %
                  (th.id, th.exit_date, th.profit_value or 0))
            print('        strategy  = %r' % th.strategy)
            print('        ticker    = %r' % th.ticker)
            print('        underlying= %r' % th.underlying)
            print('        notes     = %r' % ((th.notes or '')[:70]))
    if not achou:
        print('  (nenhum)')

    # 2) O que a varredura do PM enxerga
    print()
    print('CRÉDITOS QUE O PM RECONHECE:')
    itens = _pm_earned_items(uid, TICKER)
    for i in itens:
        print('  %-12s %-12s %10.2f  %s' %
              (i['key'], i['kind'], i['valor'], i['date']))
    print('  TOTAL opções  : %.2f' % sum(i['valor'] for i in itens if i['kind'] == 'OPCOES'))
    print('  TOTAL dividend: %.2f' % sum(i['valor'] for i in itens if i['kind'] == 'DIVIDENDO'))

    # 3) Eventos já aplicados
    print()
    print('EVENTOS JÁ APLICADOS AO PM:')
    evs = PMEvent.query.filter_by(user_id=uid, ticker=TICKER).all()
    for e in evs:
        print('  id=%-5s %-10s %10.2f  key=%-12s %s' %
              (e.id, e.kind, e.valor or 0, e.source_key, e.event_date))
    print('  TOTAL aplicado: %.2f' % sum(e.valor or 0 for e in evs))

    # 4) Órfãos: evento aplicado cuja origem a varredura não vê mais
    keys_vistas = {i['key'] for i in itens}
    orfaos = [e for e in evs
              if e.source_key and e.kind != 'IGNORADO' and e.source_key not in keys_vistas]
    print()
    if orfaos:
        print('*** EVENTOS ÓRFÃOS (aplicados, mas a origem sumiu da varredura): ***')
        for e in orfaos:
            print('  id=%-5s %-10s %10.2f  key=%s' %
                  (e.id, e.kind, e.valor or 0, e.source_key))
        print('  soma órfã: %.2f  <- infla o "Aplicado" sem crédito correspondente'
              % sum(e.valor or 0 for e in orfaos))
    else:
        print('Nenhum evento órfão.')

    # 5) Resumo como a tela mostra
    _a, evs2, earned, pending, pool, custo_of, custo_aj = _pm_state(uid, TICKER)
    print()
    print('COMO A TELA MOSTRA:')
    print('  Dividendos   : %.2f' % sum(i['valor'] for i in earned if i['kind'] == 'DIVIDENDO'))
    print('  Lucro opções : %.2f' % sum(i['valor'] for i in earned if i['kind'] == 'OPCOES'))
    print('  Aplicado     : %.2f' % (custo_of - custo_aj))
    print('  Disponível   : %.2f  (pendentes: %d)' % (pool, len(pending)))
    print('  PM ajustado  : %.2f' % (custo_aj / a.quantity if a.quantity else 0))
