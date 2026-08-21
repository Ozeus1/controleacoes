"""Recria Assets apagados a partir do livro de transações (AssetTxn).

O botão 🗑️ Excluir de um ativo (Asset) NÃO apaga o livro de transações
(AssetTxn) — os dois são ligados só por ticker+user_id, sem cascade. Se um
ativo foi excluído mas ainda tem transações registradas, dá para reconstruir
a posição: quantidade líquida (compras - vendas) e preço médio ponderado
das compras, na ordem cronológica (vendas reduzem a quantidade mas não
alteram o preço médio nas compras seguintes — mesma lógica de qualquer
apuração de PM simples).

Só reconstrói tickers que:
  - têm transações no livro (AssetTxn) para o usuário-alvo, e
  - NÃO têm um Asset ativo correspondente (senão já existe na carteira).

Tipo do ativo (FII/ACAO/ETF) e demais campos (fii_type, sector, is_intl)
não vêm do livro de transações — perguntamos por linha de comando ou
usamos um padrão (FII), já que o pedido que motivou o script era sobre
FIIs excluídos. Ajuste TIPO_PADRAO / FII_TYPE_PADRAO abaixo se precisar.

Uso (na VPS, do diretório que tem venv/ e app.py):
    ./venv/bin/python scripts/recupera_ativos_excluidos.py                    # simulação, todos os tickers órfãos
    ./venv/bin/python scripts/recupera_ativos_excluidos.py --tickers MXRF11,KNCR11
    ./venv/bin/python scripts/recupera_ativos_excluidos.py --gravar          # aplica
    ./venv/bin/python scripts/recupera_ativos_excluidos.py --user-id 2 --gravar
"""
import argparse
import os
import sys
from datetime import date

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A                          # noqa: E402
from models import db, Asset, AssetTxn   # noqa: E402

TIPO_PADRAO = 'FII'
FII_TYPE_PADRAO = None   # ex.: 'RECEBIVEIS' — deixa em branco/None se não souber
STRATEGY_PADRAO = 'HOLDER'


def reconstroi_posicao(txns):
    """Recebe as transações de UM ticker, em ordem cronológica, e devolve
    (quantidade, preco_medio, data_primeira_compra, data_ultima_transacao).
    PM simples: vendas reduzem quantidade sem alterar o PM acumulado."""
    qty = 0
    pm = 0.0
    primeira_compra = None
    ultima = None
    for t in txns:
        ultima = t.txn_date
        if t.side == 'C':
            if primeira_compra is None:
                primeira_compra = t.txn_date
            total_atual = qty * pm
            novo_total = total_atual + t.quantity * t.price
            qty += t.quantity
            pm = (novo_total / qty) if qty > 0 else 0.0
        else:  # venda
            qty -= t.quantity
            if qty <= 0:
                qty = max(qty, 0)
                # zerou ou operação inconsistente (venda maior que compra
                # registrada) — PM some junto com a posição.
                if qty == 0:
                    pm = 0.0
    return qty, round(pm, 4), primeira_compra, ultima


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gravar', action='store_true', help='Aplica de verdade (padrão: só mostra o que faria)')
    ap.add_argument('--user-id', type=int, default=1, help='ID do usuário dono dos dados (padrão: 1)')
    ap.add_argument('--tickers', type=str, default='',
                     help='Lista separada por vírgula para restringir (padrão: todos os órfãos encontrados)')
    ap.add_argument('--tipo', type=str, default=TIPO_PADRAO, help='Asset.type a usar (padrão: FII)')
    args = ap.parse_args()

    gravar = args.gravar
    uid = args.user_id
    filtro_tickers = {t.strip().upper() for t in args.tickers.split(',') if t.strip()} or None

    with A.app.app_context():
        tickers_com_txn = {
            t for (t,) in db.session.query(AssetTxn.ticker)
                                     .filter(AssetTxn.user_id == uid).distinct().all()
        }
        tickers_com_asset = {
            a.ticker.upper() for a in Asset.query.filter_by(user_id=uid).all()
        }
        orfaos = sorted(tickers_com_txn - tickers_com_asset)
        if filtro_tickers is not None:
            orfaos = [t for t in orfaos if t in filtro_tickers]

        if not orfaos:
            print('Nenhum ticker com transações órfãs (sem Asset correspondente) encontrado.')
            if filtro_tickers:
                faltando = filtro_tickers - tickers_com_txn
                if faltando:
                    print(f'  (obs.: {", ".join(sorted(faltando))} não têm NENHUMA transação no livro)')
            return

        print(f'{len(orfaos)} ticker(s) com transações mas sem Asset ativo:\n')
        criados = 0
        for tk in orfaos:
            txns = (AssetTxn.query
                    .filter_by(user_id=uid, ticker=tk)
                    .order_by(AssetTxn.txn_date, AssetTxn.id)
                    .all())
            qty, pm, dt_entrada, dt_ultima = reconstroi_posicao(txns)

            n_compras = sum(1 for t in txns if t.side == 'C')
            n_vendas = sum(1 for t in txns if t.side == 'V')
            print(f'{tk:10} qtd={qty:>6}  pm=R$ {pm:>8.2f}  '
                  f'({n_compras} compra(s), {n_vendas} venda(s), '
                  f'{dt_entrada.isoformat() if dt_entrada else "?"} → {dt_ultima.isoformat() if dt_ultima else "?"})')

            if qty <= 0:
                print(f'   [!] posição líquida zerada/negativa — não recriado (provavelmente já foi vendido de vez)')
                continue

            if gravar:
                asset = Asset(
                    user_id=uid, ticker=tk, type=args.tipo, strategy=STRATEGY_PADRAO,
                    quantity=qty, avg_price=pm, entry_date=dt_entrada or date.today(),
                    fii_type=FII_TYPE_PADRAO,
                )
                db.session.add(asset)
                criados += 1

        if gravar:
            db.session.commit()
            print(f'\nGRAVADO. {criados} ativo(s) recriado(s).')
        else:
            print('\nSIMULAÇÃO — nada foi gravado. Confira os valores acima e rode com --gravar para aplicar.')
            print('Dica: se algum PM ou quantidade não bater com o que você lembra, NÃO grave —')
            print('me avise antes, pode haver transações de outra fonte (B3/import) fora do esperado.')


if __name__ == '__main__':
    main()
