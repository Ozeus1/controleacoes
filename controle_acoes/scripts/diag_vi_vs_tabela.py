"""Por que a VI do gráfico diverge da VI da tabela do Ranking?

São duas fontes diferentes da OpLab:
  - tabela  : /market/instruments/{t} -> iv_current (número pronto da OpLab)
  - gráfico : /market/historical/options/... -> agregado por nós a partir da
              VI de cada opção

Este script mostra as duas lado a lado para hoje e revela como a nossa
agregação se comporta: por vencimento, por distância do dinheiro, e o que
cada critério de seleção produziria.

Uso (na VPS, do diretório que tem venv/ e app.py):
    ./venv/bin/python scripts/diag_vi_vs_tabela.py BBAS3
"""
import os
import statistics
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A                              # noqa: E402
from models import Settings, User            # noqa: E402


def main():
    tk = (sys.argv[1] if len(sys.argv) > 1 else 'BBAS3').upper()

    with A.app.app_context():
        user = User.query.first()
        token = Settings.get_value('oplab_token', user_id=user.id) if user else None
    if not token:
        print('Token OpLab não configurado.')
        return

    print(f'===== {tk} =====\n')

    # 1) O número que a TABELA usa
    try:
        d = A._oplab_get_json(f'/market/instruments/{tk}', token, timeout=20)
        print('[TABELA] /market/instruments — números prontos da OpLab:')
        for k in ('iv_current', 'iv_1y_rank', 'iv_1y_percentile',
                  'iv_1y_min', 'iv_1y_max', 'ewma_current'):
            print(f'    {k:20} = {d.get(k)}')
        iv_tabela = d.get('iv_current')
    except Exception as e:
        print(f'[TABELA] ERRO: {e}')
        iv_tabela = None

    # 2) Os dados brutos que o GRÁFICO agrega — só o dia mais recente
    hoje = date.today()
    ini = (hoje - timedelta(days=10)).isoformat()
    try:
        raw = A._oplab_get_json(
            f'/market/historical/options/{tk}/{ini}/{hoje.isoformat()}',
            token, timeout=60)
    except Exception as e:
        print(f'\n[GRÁFICO] ERRO: {e}')
        return
    if not isinstance(raw, list) or not raw:
        print('\n[GRÁFICO] sem registros no período.')
        return

    ultimo = max(str(r.get('time'))[:10] for r in raw if isinstance(r, dict))
    dia = [r for r in raw if isinstance(r, dict) and str(r.get('time'))[:10] == ultimo]
    print(f'\n[GRÁFICO] /market/historical/options — dia {ultimo}: '
          f'{len(dia)} opções\n')

    linhas = []
    for r in dia:
        try:
            vol = float(r.get('volatility') or 0)
            k = float(r.get('strike') or 0)
            spot = float((r.get('spot') or {}).get('price') or 0)
        except (TypeError, ValueError):
            continue
        if vol <= 0 or k <= 0 or spot <= 0:
            continue
        linhas.append({
            'sym': r.get('symbol'), 'tipo': r.get('type'), 'vol': vol,
            'dist': abs(k - spot) / spot, 'dtm': r.get('days_to_maturity') or 0,
            'strike': k, 'spot': spot,
        })
    if not linhas:
        print('  nenhuma opção válida.')
        return

    linhas.sort(key=lambda x: x['dist'])
    print('  As 12 mais próximas do dinheiro:')
    print(f"    {'opção':12}{'tipo':6}{'strike':>8}{'spot':>8}{'dist%':>7}{'dtm':>5}{'VI':>7}")
    for x in linhas[:12]:
        print(f"    {str(x['sym'])[:11]:12}{str(x['tipo'])[:5]:6}{x['strike']:>8.2f}"
              f"{x['spot']:>8.2f}{x['dist']*100:>6.1f}%{x['dtm']:>5}{x['vol']:>6.1f}%")

    def med(v):
        return statistics.mean(v) if v else 0

    curtos = [x for x in linhas if x['dtm'] < 7]
    validos = [x for x in linhas if x['dtm'] >= 7]
    print(f"\n  Opções com menos de 7 dias (hoje DESCARTADAS): {len(curtos)}"
          f"{'  VI média ' + format(med([x['vol'] for x in curtos]), '.1f') + '%' if curtos else ''}")

    print('\n  O que cada critério produziria para este dia:')
    cands = [
        ('4 mais ATM, dtm>=7 (ATUAL)', [x['vol'] for x in validos[:4]]),
        ('4 mais ATM, sem filtro dtm', [x['vol'] for x in linhas[:4]]),
        ('2 mais ATM, dtm>=7',         [x['vol'] for x in validos[:2]]),
        ('8 mais ATM, dtm>=7',         [x['vol'] for x in validos[:8]]),
        ('só CALLs, 4 mais ATM',       [x['vol'] for x in validos if x['tipo'] == 'CALL'][:4]),
        ('só PUTs, 4 mais ATM',        [x['vol'] for x in validos if x['tipo'] == 'PUT'][:4]),
        ('todas as opções do dia',     [x['vol'] for x in linhas]),
        ('vencimento + próximo (>=7d)',
         [x['vol'] for x in sorted(validos, key=lambda y: (y['dtm'], y['dist']))[:6]]),
    ]
    alvo = f'{iv_tabela:.1f}' if iv_tabela else '?'
    for nome, vals in cands:
        if not vals:
            continue
        v = med(vals)
        dif = f'{v - iv_tabela:+.1f}' if iv_tabela else '?'
        print(f'    {nome:30} {v:>6.1f}%   (tabela {alvo}% | dif {dif})')

    print('\n  Obs.: a tabela usa iv_current, um número que a OpLab calcula com')
    print('  metodologia própria (não publicada). Divergência de alguns pontos')
    print('  é esperada; divergência sistemática indica critério diferente.')


if __name__ == '__main__':
    main()
