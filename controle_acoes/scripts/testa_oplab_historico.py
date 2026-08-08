"""Diagnóstico: o plano OpLab deste token cobre os endpoints de histórico?

Uso na VPS (a partir da raiz do projeto):
    ./venv/bin/python scripts/testa_oplab_historico.py

Lê o token do próprio banco (nunca o imprime) e consulta os endpoints de
histórico de volatilidade. O objetivo é decidir entre:
  - acumular histórico de VI a partir de hoje (sempre funciona), ou
  - baixar o histórico retroativo da OpLab (só se o plano cobrir).
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A                      # noqa: E402
from models import Settings, User    # noqa: E402

BASE = 'https://api.oplab.com.br/v3'


def _linha(status, rotulo, extra=''):
    marca = {'OK': '  OK  ', 'NAO': ' NAO  ', 'ERRO': ' ERRO '}.get(status, status)
    print(f'[{marca}] {rotulo}' + (f'\n         {extra}' if extra else ''))


def main():
    with A.app.app_context():
        user = User.query.first()
        if not user:
            print('Nenhum usuário no banco.')
            return
        token = Settings.get_value('oplab_token', user_id=user.id)

    if not token:
        print('Token OpLab não configurado para este usuário.')
        return
    print(f'Token encontrado (…{token.strip()[-4:]}), testando endpoints:\n')

    hoje = date.today()
    ini = hoje - timedelta(days=30)
    testes = [
        ('Tempo real (controle)', '/market/instruments/PETR4', None),
        ('Série histórica do ativo', f'/market/historical/PETR4/1d',
         {'from': ini.isoformat(), 'to': hoje.isoformat()}),
        ('EWMA por data (vol. histórica)', '/market/historical/instruments',
         {'tickers': 'PETR4', 'date': (hoje - timedelta(days=7)).isoformat()}),
        ('Histórico de opções (vol. implícita)',
         f'/market/historical/options/PETR4/{ini.isoformat()}/{hoje.isoformat()}', None),
    ]

    cobre_historico = False
    for rotulo, ep, params in testes:
        try:
            d = A._oplab_get_json(ep, token, params=params, timeout=30)
        except A.OplabApiError as e:
            _linha('NAO', rotulo, f'{e} (HTTP {e.status_code})')
            continue
        except Exception as e:
            _linha('ERRO', rotulo, f'{type(e).__name__}: {e}')
            continue

        n = len(d) if isinstance(d, list) else (len(d.get('data', [])) if isinstance(d, dict) else 0)
        amostra = ''
        if isinstance(d, list) and d:
            x = d[0]
            campos = {k: x.get(k) for k in ('symbol', 'time', 'volatility', 'ewma_current',
                                            'strike', 'days_to_maturity') if k in x}
            amostra = f'{n} registro(s). Ex.: {campos}'
        elif isinstance(d, dict):
            serie = d.get('data') or []
            amostra = f'{len(serie)} ponto(s).'
            if serie:
                amostra += f' Ex.: {serie[0]}'
        _linha('OK', rotulo, amostra)
        if 'historical' in ep:
            cobre_historico = True

    print('\n' + '=' * 62)
    if cobre_historico:
        print('RESULTADO: o plano cobre histórico — dá para preencher o gráfico')
        print('de VI retroativamente, sem esperar acumular.')
    else:
        print('RESULTADO: o plano NÃO cobre os endpoints de histórico.')
        print('Caminho viável: acumular a VI dia a dia a partir de agora')
        print('(os dados já são buscados no Ranking; falta só gravá-los).')


if __name__ == '__main__':
    main()
