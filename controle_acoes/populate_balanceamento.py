from app import app
from models import db, FixedIncome, InvestmentFund, Crypto, Pension, International
from datetime import datetime

def parse_val(s):
    if not s: return 0.0
    s = s.replace('R$', '').replace('$', '').strip()
    s = s.replace('.', '').replace(',', '.')
    return float(s)

def parse_date(s):
    if not s or s.lower() == 'diária' or s.lower() == 'diaria':
        return None
    try:
        return datetime.strptime(s.strip(), '%d/%m/%Y').date()
    except:
        return None

def run():
    with app.app_context():
        # Clear existing data before populating
        print("Clearing existing data...")
        db.session.query(FixedIncome).delete()
        db.session.query(InvestmentFund).delete()
        db.session.query(Crypto).delete()
        db.session.query(Pension).delete()
        db.session.query(International).delete()
        db.session.commit()
        print("Data cleared. Inserting new data...")
        
        # Renda Fixa Pós
        rf_pos_data = [
            ('MERCADO PAGO', 'MP cofrinho 120 do cdi', 'R$ 10.042,55', '120%', 'diária'),
            ('MERCADO PAGO', 'cdb ML 107', 'R$ 21.078,96', '110%', '15/01/2026'),
            ('MERCADO PAGO', 'LCI MP Banco BRB', 'R$ 5.326,04', '100%', '01/07/2026'),
            ('MERCADO PAGO', 'cdb ML 107', 'R$ 265,07', '107%', '01/02/2026'),
            ('NUBANK', 'nu Caixinha', 'R$ 10.234,19', '120%', 'diária'),
            ('SANTANDER', 'CDB santander', 'R$ 6.272,65', '100%', 'diaria'),
            ('SANTANDER', 'LCA DI santander', 'R$ 4.083,18', '96%', '20/07/2028'),
            ('BRADESCO', 'CDB Bradesco', 'R$ 68.294,24', '100%', 'diaria'),
            ('EQI', 'CRI MOURA DUBEUX', 'R$ 5.095,10', '100%', '15/03/2030'),
            ('EQI', 'CDB BTG', 'R$ 20.831,83', '100%', 'DIARIA'),
            ('EQI', 'BRB BANCO BRASILIA', 'R$ 18.561,43', '108%', '09/04/2026'),
            ('EQI', 'LCA BANCO DES EXTREMO SUL', 'R$ 7.264,19', '100%', '30/08/2027'),
            ('EQI', 'LCA BANCO DES EXTREMO SUL', 'R$ 36.363,78', '100%', '31/08/2027'),
        ]
        
        for inst, name, val, rate, mat in rf_pos_data:
            db.session.add(FixedIncome(
                category='POS', product_type='CDB/LCI', institution=inst, name=name, 
                value=parse_val(val), rate=rate, maturity_date=parse_date(mat)
            ))

        # Renda Fixa Pré
        rf_pre_data = [
            ('NUBANK', 'Nu CDB banco C6', 'R$ 4.673,32', '11,70%', '11/05/2026'),
            ('C6', 'C6 CDB 4 anos', 'R$ 8.854,90', '12,95%', '09/05/2028'),
            ('C6', 'C6 CDB 4 anos', 'R$ 1.045,86', '12,20%', '15/02/2028'),
            ('C6', 'C6 CDB 4 anos', 'R$ 8.533,73', '12,05%', '14/12/2027'),
            ('EQI', 'EQI CRA MINERVA', 'R$ 22.212,17', '14,20%', '15/09/2028'),
            ('EQI', 'EQI CRA FS FLORESTAL', 'R$ 2.168,91', '14,86%', '15/03/2030'),
            ('EQI', 'EQI CRA MINERVA', 'R$ 2.220,60', '14,00%', '16/04/2035'),
            ('EQI', 'LCA BTG', 'R$ 1.027,45', '12,72%', '02/07/2026'),
            ('EQI', 'LCA BTG', 'R$ 1.029,18', '12,62%', '28/09/2026'),
            ('EQI', 'LCA BTG', 'R$ 5.136,02', '12,60%', '02/10/2026'),
            ('EQI', 'LCA ORIGINAL', 'R$ 1.004,52', '12,04%', '11/12/2028'),
        ]
        
        for inst, name, val, rate, mat in rf_pre_data:
            db.session.add(FixedIncome(
                category='PRE', product_type='CDB/CRA/LCA', institution=inst, name=name, 
                value=parse_val(val), rate=rate, maturity_date=parse_date(mat)
            ))

        # Renda Fixa IPCA
        rf_ipca_data = [
            ('SANTANDER', 'toro NTN 60', 'R$ 162,00', '7,06%', '15/08/2060'), # Fixed 1960 -> 2060
            ('EQI', 'eqi NTNB 60', 'R$ 1.991,85', '7,06%', '16/08/2060'),
            ('EQI', 'eqi prev 65', 'R$ 2.998,01', '6,95%', '15/12/2084'),
            ('EQI', 'EQI CRI ASSAI ATACADISTA', 'R$ 2.322,77', '8,12%', '16/10/2028'),
        ]
        
        for inst, name, val, rate, mat in rf_ipca_data:
            db.session.add(FixedIncome(
                category='IPCA', product_type='Tesouro/CRI', institution=inst, name=name, 
                value=parse_val(val), rate=rate, maturity_date=parse_date(mat)
            ))

        # Fundos
        funds_data = [
            ('EQI', 'LESTE RENDA BTS FUNDO', 'R$ 32.015,50', 'CDI'),
            ('EQI', 'MANATI RENDA IMOBILIARIA', 'R$ 10.000,00', 'IPCA'),
        ]
        for inst, name, val, idx in funds_data:
             db.session.add(InvestmentFund(
                institution=inst, name=name, value=parse_val(val), indexer=idx
            ))

        # Crypto
        crypto_data = [
            ('EQI', 'BITCOIN', '0,00766245', 'R$ 4.529,83', 'R$ 3.716,02'), # Inst, Name, Qty, Invested, Current
            ('EQI', 'ETHER', '0,07260084', 'R$ 1.694,84', 'R$ 1.193,09'),
        ]
        for inst, name, qty, inv, curr in crypto_data:
            db.session.add(Crypto(
                institution=inst, name=name, quantity=parse_val(qty), 
                invested_value=parse_val(inv), current_value=parse_val(curr)
            ))

        # Previdencia
        prev_data = [
            ('EQI', 'BTG CRED CORP IIFIC CRPR', 'R$ 10.015,49', 'Ação', '323182'),
            ('EQI', 'BTG AUTIN BALANCEADO PREV FIM CRPR', 'R$ 5.000,00', 'Renda Fixa', '328427'),
            ('EQI', 'BTG CRED CORP IIFIC CRPR', 'R$ 1.800,00', 'Renda Fixa', '345403'), # Assumed Type
            ('EQI', 'Angaprev Previdencia FIF RF', 'R$ 2.000,00', 'Renda Fixa', '351812'), # Assumed Type
        ]
        for inst, name, val, typ, cert in prev_data:
             db.session.add(Pension(
                institution=inst, name=name, value=parse_val(val), type=typ, certificate=cert
            ))

        # International
        intl_data = [
            ('INTER', 'AMZ', '$120,49'),
            ('INTER', 'HMS', '$114,52'),
            ('INTER', 'BLKB', '$114,50'),
            ('INTER', 'DIS', '$100,68'),
            ('INTER', 'NFLX', '$98,95'),
            ('NOMAD', 'ADBE', '$116,44'),
            ('AVENUE', 'BRKB', '$117,54'),
            ('AVENUE', 'GOOG', '$226,39'),
            ('AVENUE', 'JNJ', '$126,59'),
            ('AVENUE', 'JPM', '$126,84'),
            ('AVENUE', 'META', '$159,32'),
            ('INTER', 'AMZ (Renda Fixa/Moeda)', '$120,49'), # From image 3
        ]
        for inst, name, val in intl_data:
            # assuming quantity 1 or unknown, rate 5.5 default
            db.session.add(International(
                institution=inst, name=name, value_usd=parse_val(val), rate_usd=5.5
            ))

        db.session.commit()
        print("Database populated successfully.")

if __name__ == '__main__':
    run()
