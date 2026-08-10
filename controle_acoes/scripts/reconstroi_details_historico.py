"""Reconstrói TradeHistory.details a partir do texto salvo em `notes`.

Trades encerrados antes da criação do campo `details` guardam as pernas só como
texto. Este script faz o parse desse texto e grava o detalhamento estruturado,
para o botão 🔍 do Histórico funcionar também no que já existia.

Formatos reconhecidos (os dois que o sistema gera):

  Estruturada:
    BRAP4 | C:BRAPT222 PUT K=22.20 entrada@0.78 saída@0.96 | V:BRAPH232 ...
    [| inclui R$ 174.00 realizados em manejos anteriores]

  Trava (spread):
    TRAVA_BAIXA_CALL | BBAS3 | C:BBASH205 K=20.40 entrada@0.72 saída@0.46 |
    V:BBASI240 K=23.56 entrada@0.14 saída@0.08

O que NÃO dá para recuperar: o extrato de rolagens/manejos. Ele nunca foi
gravado de forma estruturada — o texto só diz o total realizado, sem as datas
e os tickers de cada movimento. Esse total vai para `realized_manejos`, e o
detalhe fica vazio (a tabela de manejos simplesmente não aparece nesses casos).

Uso (na VPS, do diretório que tem venv/ e app.py):
    ./venv/bin/python scripts/reconstroi_details_historico.py          # simulação
    ./venv/bin/python scripts/reconstroi_details_historico.py --gravar # aplica
"""
import json
import os
import re
import sys

# O console do Windows usa cp1252 por padrão e quebra em acentos/emoji ao
# imprimir. Como o relatório abaixo tem acento, força UTF-8 na saída.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A                          # noqa: E402
from models import db, TradeHistory      # noqa: E402

# C:TICKER [TIPO ]K=00.00 entrada@0.00 saída@0.00
#   - o TIPO (CALL/PUT/STOCK) só existe no formato das estruturadas
#   - aceita "saída" e "saida" (por segurança contra variação de acento)
LEG_RE = re.compile(
    r'([CV]):\s*(\S+?)\s+'                       # lado + ticker
    r'(?:(CALL|PUT|STOCK)\s+)?'                  # tipo (opcional)
    r'K=(-?[\d.,]+)\s+'                          # strike
    r'entrada@(-?[\d.,]+)\s+'                    # preço de entrada
    r'sa[íi]da@(-?[\d.,]+)',                     # preço de saída
    re.IGNORECASE)

REALIZED_RE = re.compile(
    r'inclui\s+R\$\s*(-?[\d.,]+)\s+realizados em manejos', re.IGNORECASE)


def _num(s):
    """'22.20' ou '22,20' -> float."""
    s = (s or '').strip().replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_notes(notes, quantity):
    """Extrai as pernas do texto. Devolve (legs, realized) ou (None, 0) se não
    reconhecer nada."""
    if not notes:
        return None, 0.0

    legs = []
    for m in LEG_RE.finditer(notes):
        lado, ticker, tipo, strike, entrada, saida = m.groups()
        side = 'SELL' if lado.upper() == 'V' else 'BUY'
        buy = _num(entrada)
        sell = _num(saida)
        qty = int(quantity or 0)
        # Convenção do sistema: vendido lucra quando o prêmio cai.
        pnl = ((buy - sell) if side == 'SELL' else (sell - buy)) * qty
        legs.append({
            'ticker':   ticker.strip().upper(),
            'side':     side,
            'opt_type': (tipo or '').upper() or ('STOCK' if strike in ('0', '0.00') else 'CALL'),
            'strike':   round(_num(strike), 2),
            'qty':      qty,
            'buy':      round(buy, 4),
            'sell':     round(sell, 4),
            'pnl':      round(pnl, 2),
        })

    realized = 0.0
    mr = REALIZED_RE.search(notes)
    if mr:
        realized = _num(mr.group(1))

    return (legs or None), realized


def main():
    gravar = '--gravar' in sys.argv
    with A.app.app_context():
        trades = TradeHistory.query.order_by(TradeHistory.id).all()
        total = recuperados = pulados_com_details = sem_pernas = 0

        for t in trades:
            total += 1
            if t.details:
                pulados_com_details += 1
                continue

            legs, realized = parse_notes(t.notes, t.quantity)
            if not legs:
                sem_pernas += 1
                continue

            det = {'legs': legs, 'events': []}
            if abs(realized) > 0.005:
                det['realized_manejos'] = round(realized, 2)
            det['reconstruido_de_notes'] = True   # marca a origem do dado

            recuperados += 1
            print(f"\nid={t.id}  {t.ticker}  ({t.quantity}x)")
            for l in legs:
                print(f"   {l['side']:4} {l['ticker']:12} {l['opt_type']:5} "
                      f"K={l['strike']:>7.2f}  compra={l['buy']:>7.2f} "
                      f"venda={l['sell']:>7.2f}  pnl={l['pnl']:>+9.2f}")
            soma = sum(l['pnl'] for l in legs)
            print(f"   soma das pernas: {soma:>+10.2f}"
                  + (f"  + manejos {realized:+.2f}" if realized else '')
                  + f"   (profit_value gravado: {t.profit_value:+.2f})")
            if abs(soma + realized - (t.profit_value or 0)) > 0.05:
                print("   [!] soma difere do resultado gravado - o resultado do "
                      "historico continua valendo; o detalhe e so o rastro.")

            if gravar:
                t.details = json.dumps(det, ensure_ascii=False)

        if gravar:
            db.session.commit()

        print(f"\n{'='*66}")
        print(f"trades no histórico ......... {total}")
        print(f"já tinham detalhamento ...... {pulados_com_details}")
        print(f"pernas reconhecidas ......... {recuperados}")
        print(f"sem pernas no texto ......... {sem_pernas}")
        print('GRAVADO.' if gravar else
              'SIMULAÇÃO — nada foi gravado. Rode com --gravar para aplicar.')


if __name__ == '__main__':
    main()
