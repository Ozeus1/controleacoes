"""Diagnóstico da série de volatilidade: até onde a OpLab realmente devolve?

Uso na VPS (do diretório do projeto, o que tem venv/ e app.py):
    ./venv/bin/python scripts/diag_vol_hist.py MULT3

Responde: a série vai até hoje ou está truncada? A HV tem candles até
quando? Serve para separar "a OpLab não tem o dado" de "nosso código está
cortando".
"""
import collections
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A                                   # noqa: E402
from models import Settings, User, ChartCache     # noqa: E402


def main():
    tk = (sys.argv[1] if len(sys.argv) > 1 else 'PETR4').upper()

    with A.app.app_context():
        user = User.query.first()
        token = Settings.get_value('oplab_token', user_id=user.id) if user else None
        if not token:
            print('Token OpLab não configurado.')
            return

        ini = (date.today() - timedelta(days=183)).isoformat()
        fim = date.today().isoformat()
        print(f'== {tk} ==  janela pedida: {ini} .. {fim}   (hoje = {date.today()})\n')

        # 1) O que a OpLab devolve
        try:
            raw = A._oplab_get_json(
                f'/market/historical/options/{tk}/{ini}/{fim}', token, timeout=90)
        except Exception as e:
            print(f'ERRO na consulta: {e}')
            return
        if not isinstance(raw, list):
            print(f'Resposta inesperada: {type(raw).__name__}')
            return

        dias = collections.Counter(str(r.get('time'))[:10]
                                   for r in raw if isinstance(r, dict))
        ds = sorted(dias)
        print(f'[OpLab] registros brutos : {len(raw)}')
        print(f'[OpLab] dias distintos   : {len(ds)}')
        if ds:
            print(f'[OpLab] primeiro dia     : {ds[0]}')
            print(f'[OpLab] ÚLTIMO dia       : {ds[-1]}')
            atraso = (date.today() - date.fromisoformat(ds[-1])).days
            print(f'[OpLab] atraso vs hoje   : {atraso} dia(s)'
                  + ('   <-- SÉRIE TRUNCADA' if atraso > 4 else ''))
            print(f'[OpLab] últimos dias     : {ds[-6:]}')
            if len(raw) in (1000, 5000, 10000, 20000, 50000):
                print(f'  !! {len(raw)} é redondo: possível limite de paginação da API')

        # 2) O que sobra depois dos nossos filtros
        serie = A._vol_hist_series(tk, token, meses=6)
        print(f'\n[nosso] pontos na série  : {len(serie)}')
        if serie:
            print(f'[nosso] primeiro         : {serie[0]["d"]}  iv={serie[0]["iv"]}')
            print(f'[nosso] último           : {serie[-1]["d"]}  iv={serie[-1]["iv"]}')
            sem_hv = sum(1 for p in serie if p.get('hv') is None)
            print(f'[nosso] pontos sem HV    : {sem_hv} de {len(serie)}')

        # 3) Os candles que alimentam a HV
        cc = ChartCache.query.get(tk)
        if cc:
            print(f'\n[candles] cache existe, último dia: {cc.last_date}')
            atraso_c = (date.today() - date.fromisoformat(cc.last_date)).days
            print(f'[candles] atraso vs hoje : {atraso_c} dia(s)'
                  + ('   <-- CACHE VELHO (por isso HV falta no fim)' if atraso_c > 4 else ''))
        else:
            print('\n[candles] SEM cache para este ticker '
                  '(a HV foi buscada no Yahoo na hora)')


if __name__ == '__main__':
    main()
