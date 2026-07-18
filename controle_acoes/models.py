from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
import os
import base64
from datetime import datetime

db = SQLAlchemy()

# Helper for Encryption
def get_cipher_suite():
    secret = os.environ.get('FLASK_SECRET_KEY', 'default_secret_key_must_be_32_bytes')
    key = secret.ljust(32)[:32].encode() 
    return Fernet(base64.urlsafe_b64encode(key))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='user') # 'admin' or 'user'
    expiry_date = db.Column(db.Date, nullable=True) # Access expiration
    full_name       = db.Column(db.String(120), nullable=True)
    email           = db.Column(db.String(120), nullable=True)
    phone           = db.Column(db.String(30),  nullable=True)
    avatar_filename = db.Column(db.String(120), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_active(self):
        if self.expiry_date and self.expiry_date < datetime.now().date():
            return False
        return True

class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, default=1)
    ticker = db.Column(db.String(10), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'ACAO' or 'FII'
    strategy = db.Column(db.String(10), nullable=False, default='HOLDER') # 'HOLDER' or 'SWING'
    quantity = db.Column(db.Integer, nullable=False, default=0)
    avg_price = db.Column(db.Float, nullable=False, default=0.0)
    
    # SwingTrade specific fields
    stop_loss = db.Column(db.Float, nullable=True)
    gain1 = db.Column(db.Float, nullable=True)
    gain2 = db.Column(db.Float, nullable=True)
    recommendation = db.Column(db.String(50), nullable=True)
    
    # Cached Quote Data
    current_price = db.Column(db.Float, default=0.0)
    daily_change = db.Column(db.Float, default=0.0)
    last_update = db.Column(db.DateTime,  nullable=True)
    
    # Dividend Data (New)
    last_dividend = db.Column(db.Float, nullable=True)
    last_dividend_date = db.Column(db.Date, nullable=True)
    dividend_yield = db.Column(db.Float, nullable=True)
    
    # History/Duration
    entry_date = db.Column(db.Date, nullable=True)
    exit_date  = db.Column(db.Date, nullable=True)   # data da saída total (posição zerada)

    # FII Specific
    fii_type = db.Column(db.String(50), nullable=True)
    
    # Optional fields for manual overrides or future use
    sector = db.Column(db.String(50), nullable=True) 

    def to_dict(self):
        return {
            'id': self.id,
            'ticker': self.ticker,
            'type': self.type,
            'quantity': self.quantity,
            'avg_price': self.avg_price,
            'total_invested': self.quantity * self.avg_price,
            'entry_date': self.entry_date.strftime('%Y-%m-%d') if self.entry_date else None
        }

class TradeHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, default=1)
    ticker = db.Column(db.String(20), nullable=False)
    strategy = db.Column(db.String(50)) # Previously recommendation
    entry_date = db.Column(db.Date)
    exit_date = db.Column(db.Date)
    buy_price = db.Column(db.Float)
    sell_price = db.Column(db.Float)
    quantity = db.Column(db.Integer)
    profit_value = db.Column(db.Float)
    profit_pct = db.Column(db.Float)
    days_held = db.Column(db.Integer)
    reason = db.Column(db.String(20)) # StopLoss, Gain, Partial, etc.
    underlying = db.Column(db.String(15), nullable=True)   # ativo base (PETR4, VALE3...)
    notes = db.Column(db.Text, nullable=True)              # tickers das pernas, detalhes

class Option(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, default=1)
    option_type = db.Column(db.String(20), nullable=False, default='VENDA_CALL') # VENDA_CALL, COMPRA_CALL, COMPRA_PUT
    ticker = db.Column(db.String(20), nullable=False) # e.g., PETRA40
    underlying_asset = db.Column(db.String(10), nullable=False) # e.g., PETR4
    quantity = db.Column(db.Integer, nullable=False)
    strike_price = db.Column(db.Float, nullable=False)
    expiration_date = db.Column(db.Date, nullable=False)
    sale_price = db.Column(db.Float, nullable=False) # Premium received per share
    
    # Manual update field
    current_option_price = db.Column(db.Float, default=0.0)
    daily_change         = db.Column(db.Float, nullable=True)  # variação % no dia

    # Entry Date (Requested Feature)
    entry_date = db.Column(db.Date, nullable=True)
    
    # Calculated/Fetched on fly, but maybe store last fetch for underlying?
    last_update = db.Column(db.DateTime, nullable=True)

    # Cotação do ativo subjacente (p/ opções cujo ativo não está na carteira)
    underlying_price  = db.Column(db.Float, nullable=True)
    underlying_change = db.Column(db.Float, nullable=True)

    # Study fields
    vdx   = db.Column(db.Float, nullable=True)   # calculado
    nv    = db.Column(db.Float, nullable=True)   # calculado
    ve    = db.Column(db.Float, nullable=True)   # informado manualmente
    delta = db.Column(db.Float, nullable=True)
    gama  = db.Column(db.Float, nullable=True)

    # Histórico de rolagens (JSON array)
    roll_history = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'ticker': self.ticker,
            'underlying': self.underlying_asset,
            'strike': self.strike_price,
            'current_price': self.current_option_price
        }


class OptionSpread(db.Model):
    __tablename__ = 'option_spread'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    spread_type = db.Column(db.String(20), nullable=False)  # TRAVA_ALTA_PUT, TRAVA_ALTA_CALL, TRAVA_BAIXA_PUT, TRAVA_BAIXA_CALL
    underlying_asset = db.Column(db.String(15), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    expiration_date = db.Column(db.Date, nullable=False)
    entry_date = db.Column(db.Date, nullable=True)

    # Leg Compra (Long)
    leg_long_ticker = db.Column(db.String(20), nullable=False)
    leg_long_strike = db.Column(db.Float, nullable=False)
    leg_long_price = db.Column(db.Float, nullable=False)   # prêmio pago
    leg_long_current = db.Column(db.Float, default=0.0)

    # Leg Venda (Short)
    leg_short_ticker = db.Column(db.String(20), nullable=False)
    leg_short_strike = db.Column(db.Float, nullable=False)
    leg_short_price = db.Column(db.Float, nullable=False)  # prêmio recebido
    leg_short_current = db.Column(db.Float, default=0.0)

    # Probability of Profit informado na montagem
    pop = db.Column(db.Float, nullable=True)

    # Cotação do ativo subjacente (atualizado via MT5/Excel/Yahoo)
    underlying_price  = db.Column(db.Float, nullable=True)
    underlying_change = db.Column(db.Float, nullable=True)

    # Histórico de rolagens (JSON array)
    roll_history = db.Column(db.Text, nullable=True)


class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, default=1)
    key = db.Column(db.String(50), nullable=False) # Removed unique constraint here, handled by (user_id, key) if possible or logic
    value = db.Column(db.String(255), nullable=True)
    
    # Unique constraint combo ideally: (user_id, key)

    _ENCRYPTED_KEYS = {'brapi_token', 'oplab_token'}

    @staticmethod
    def get_value(key, user_id, default=None):
        setting = Settings.query.filter_by(key=key, user_id=user_id).first()
        if setting:
            if key in Settings._ENCRYPTED_KEYS:
                try:
                    cipher = get_cipher_suite()
                    return cipher.decrypt(setting.value.encode()).decode()
                except Exception:
                    # Valor salvo antes da criptografia — retorna como texto plano
                    # e re-salva criptografado para migrações futuras
                    return setting.value
            return setting.value
        return default

    @staticmethod
    def set_value(key, value, user_id):
        setting = Settings.query.filter_by(key=key, user_id=user_id).first()
        if not setting:
            setting = Settings(key=key, user_id=user_id)
            db.session.add(setting)

        if key in Settings._ENCRYPTED_KEYS:
            cipher = get_cipher_suite()
            setting.value = cipher.encrypt(value.encode()).decode()
        else:
            setting.value = value

        db.session.commit()


class FixedIncome(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, default=1)
    category = db.Column(db.String(20), nullable=False) # 'POS', 'PRE', 'IPCA'
    product_type = db.Column(db.String(20), nullable=True) # 'CDB', 'LCI', etc.
    institution = db.Column(db.String(50), nullable=False) # Bank/Issuer
    name = db.Column(db.String(100), nullable=False) # Description/Fund Name
    value = db.Column(db.Float, nullable=False, default=0.0)
    rate = db.Column(db.String(50), nullable=True) # '120% CDI', '12% a.a.'
    maturity_date = db.Column(db.Date, nullable=True)

class InvestmentFund(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, default=1)
    institution = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Float, nullable=False, default=0.0)
    indexer = db.Column(db.String(20), nullable=True)
    maturity_date = db.Column(db.Date, nullable=True)

class Crypto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, default=1)
    institution = db.Column(db.String(50), nullable=False) # Exchange
    name = db.Column(db.String(50), nullable=False) # BTC, ETH
    quantity = db.Column(db.Float, nullable=True)
    invested_value = db.Column(db.Float, nullable=True) # Cost basis (Legacy, now calc from avg_price)
    current_value = db.Column(db.Float, nullable=False) # Market value (manual or calc)
    quote = db.Column(db.Float, nullable=True)
    avg_price = db.Column(db.Float, nullable=True, default=0.0) # New field

class Pension(db.Model): # Previdencia
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, default=1)
    institution = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(20), nullable=True) # 'Acao' or 'Renda Fixa'
    certificate = db.Column(db.String(50), nullable=True)

class International(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, default=1)
    institution = db.Column(db.String(50), nullable=False) # Broker
    name = db.Column(db.String(20), nullable=False) # Ticker
    quantity = db.Column(db.Float, nullable=True)
    avg_price = db.Column(db.Float, nullable=True)
    quote = db.Column(db.Float, nullable=True)
    value_usd = db.Column(db.Float, nullable=False) # Value in USD (Current Value for RF, Total for RV)
    rate_usd = db.Column(db.Float, nullable=True) # BRL/USD Rate for conversion
    
    # New Fields for Refactor
    category = db.Column(db.String(10), default='RV') # 'RV' or 'RF'
    purchase_price = db.Column(db.Float) # Price in USD at purchase
    invested_value = db.Column(db.Float) # Total Invested in USD
    current_price = db.Column(db.Float) # Current Price (Quote) in USD
    daily_change = db.Column(db.Float, default=0.0) # New: Daily Change %
    description = db.Column(db.String(100)) # Extra details

class StudyOption(db.Model):
    """Opções extras (não VENDA_CALL) adicionadas para estudo."""
    __tablename__ = 'study_option'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ticker = db.Column(db.String(20), nullable=False)          # ticker da opção
    underlying_asset = db.Column(db.String(15), nullable=False)
    underlying_price = db.Column(db.Float, nullable=True)      # cotação do ativo
    avg_price_stock = db.Column(db.Float, nullable=True)       # preço médio da ação
    strike = db.Column(db.Float, nullable=True)
    expiration_date = db.Column(db.Date, nullable=True)
    option_price = db.Column(db.Float, nullable=True)          # cotação da opção
    vdx   = db.Column(db.Float, nullable=True)   # calculado
    nv    = db.Column(db.Float, nullable=True)   # calculado
    ve    = db.Column(db.Float, nullable=True)   # informado manualmente
    delta = db.Column(db.Float, nullable=True)
    gama  = db.Column(db.Float, nullable=True)


class StudyIntlStock(db.Model):
    """Análise de ações internacionais para decisão de estratégia."""
    __tablename__ = 'study_intl_stock'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ticker = db.Column(db.String(15), nullable=False)
    trend = db.Column(db.String(10), nullable=True)
    rsi = db.Column(db.Float, nullable=True)
    volatility = db.Column(db.String(10), nullable=True)   # legado
    ve = db.Column(db.Float, nullable=True)                # legado
    iv_rank = db.Column(db.Float, nullable=True)
    iv_percentil = db.Column(db.Float, nullable=True)
    atr_pct = db.Column(db.Float, nullable=True)   # ATR14 / preço × 100 (%)
    strategy = db.Column(db.String(60), nullable=True)
    study_date = db.Column(db.Date, nullable=True)
    strategy_active = db.Column(db.String(100), nullable=True)
    entry_date = db.Column(db.Date, nullable=True)


class StudyStock(db.Model):
    """Análise de ações para decisão de estratégia."""
    __tablename__ = 'study_stock'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ticker = db.Column(db.String(15), nullable=False)
    trend = db.Column(db.String(10), nullable=True)            # Alta / Baixa / Lateral
    rsi = db.Column(db.Float, nullable=True)
    volatility = db.Column(db.String(10), nullable=True)       # legado — não usado
    ve = db.Column(db.Float, nullable=True)                    # legado — não usado
    iv_rank = db.Column(db.Float, nullable=True)               # IV Rank % (0-100)
    iv_percentil = db.Column(db.Float, nullable=True)          # IV Percentil % (0-100)
    atr_pct = db.Column(db.Float, nullable=True)   # ATR14 / preço × 100 (%)
    strategy = db.Column(db.String(60), nullable=True)
    study_date = db.Column(db.Date, nullable=True)
    strategy_active = db.Column(db.String(100), nullable=True)
    entry_date = db.Column(db.Date, nullable=True)


class RankingVol(db.Model):
    """Ranking de Volatilidade — lista de ações monitoradas com IV Rank, IV Percentil e Vol. Implícita."""
    __tablename__ = 'ranking_vol'
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ticker       = db.Column(db.String(15), nullable=False)
    var_pct      = db.Column(db.Float, nullable=True)   # Var % dia
    last_price   = db.Column(db.Float, nullable=True)   # Último preço
    last_date    = db.Column(db.String(10), nullable=True)  # "dd/mm"
    iv_rank      = db.Column(db.Float, nullable=True)   # IV Rank (0-100)
    iv_percentil = db.Column(db.Float, nullable=True)   # IV Percentil (0-100)
    vol_impl     = db.Column(db.Float, nullable=True)   # Vol. Implícita % anualizada
    updated_at   = db.Column(db.DateTime, nullable=True)
    grupo        = db.Column(db.String(10), nullable=True, default='LIQ')  # LIQ (com liquidez) | GERAL


class StructuredOp(db.Model):
    """Operação estruturada multi-perna (condors, borboletas, strangles, etc.)."""
    __tablename__ = 'structured_op'
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name                  = db.Column(db.String(100), default='')
    underlying_asset      = db.Column(db.String(15), default='')
    underlying_price      = db.Column(db.Float, nullable=True)
    underlying_change     = db.Column(db.Float, nullable=True)
    uses_stock_collateral = db.Column(db.Boolean, default=False)  # ação em carteira como garantia
    status                = db.Column(db.String(10), default='OPEN')   # OPEN | CLOSED
    pop                   = db.Column(db.Float, nullable=True)  # POP salvo ao abrir o payoff
    intl                  = db.Column(db.Boolean, default=False)  # Tastytrade: opções internacionais (atualização manual)
    created_at    = db.Column(db.DateTime, default=datetime.now)
    roll_history  = db.Column(db.Text, nullable=True)  # JSON array de rolagens
    legs = db.relationship('StructuredLeg', backref='operation', lazy=True,
                           cascade='all, delete-orphan',
                           order_by='StructuredLeg.id')


class StructuredLeg(db.Model):
    """Uma perna de uma operação estruturada."""
    __tablename__ = 'structured_leg'
    id             = db.Column(db.Integer, primary_key=True)
    op_id          = db.Column(db.Integer, db.ForeignKey('structured_op.id'), nullable=False)
    ticker         = db.Column(db.String(20), default='')
    side           = db.Column(db.String(4),  default='SELL')   # BUY | SELL
    opt_type       = db.Column(db.String(4),  default='CALL')   # CALL | PUT
    quantity       = db.Column(db.Integer, default=1)
    strike         = db.Column(db.Float, default=0.0)
    expiration_date = db.Column(db.Date, nullable=True)
    entry_price    = db.Column(db.Float, default=0.0)
    current_price  = db.Column(db.Float, default=0.0)
    last_update    = db.Column(db.DateTime, nullable=True)


class SimulacaoOpcoes(db.Model):
    """Simulação/estudo de operação com opções — gráfico de payoff interativo."""
    __tablename__ = 'simulacao_opcoes'
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name         = db.Column(db.String(120), default='')
    underlying   = db.Column(db.String(15), default='')
    created_at   = db.Column(db.DateTime, default=datetime.now)
    legs = db.relationship('SimulacaoLeg', backref='simulacao', lazy=True,
                           cascade='all, delete-orphan',
                           order_by='SimulacaoLeg.id')


class SimulacaoLeg(db.Model):
    """Uma perna de uma SimulacaoOpcoes."""
    __tablename__ = 'simulacao_leg'
    id          = db.Column(db.Integer, primary_key=True)
    sim_id      = db.Column(db.Integer, db.ForeignKey('simulacao_opcoes.id'), nullable=False)
    leg_type    = db.Column(db.String(6),  default='CALL')   # CALL | PUT | STOCK
    side        = db.Column(db.String(4),  default='BUY')    # BUY | SELL
    quantity    = db.Column(db.Integer, default=1)
    strike      = db.Column(db.Float, default=0.0)           # 0 para STOCK
    premium     = db.Column(db.Float, default=0.0)           # prêmio ou preço médio
    expiration  = db.Column(db.Date, nullable=True)
    ticker      = db.Column(db.String(20), default='')
    iv          = db.Column(db.Float, default=0.0)   # volatilidade implícita % (ex: 30.0)


class OptionRollSimulation(db.Model):
    """Simulacao salva de rolagem de opcoes."""
    __tablename__ = 'option_roll_simulation'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name       = db.Column(db.String(120), default='')
    underlying = db.Column(db.String(15), default='')
    roll_type  = db.Column(db.String(10), default='TIME')  # TIME | STRIKE
    payload    = db.Column(db.Text, nullable=False, default='{}')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


class PutSale(db.Model):
    """Simulação de venda de put."""
    __tablename__ = 'put_sale'
    id                = db.Column(db.Integer, primary_key=True)
    user_id           = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ticker            = db.Column(db.String(20), nullable=False)
    underlying_asset  = db.Column(db.String(15), nullable=False, default='')
    underlying_price  = db.Column(db.Float, nullable=True)      # cotação do ativo
    strike            = db.Column(db.Float, nullable=False)
    expiration_date   = db.Column(db.Date, nullable=False)
    premium           = db.Column(db.Float, nullable=False)     # prêmio recebido por ação
    quantity          = db.Column(db.Integer, nullable=False, default=100)
    entry_date        = db.Column(db.Date, nullable=True)
    notes             = db.Column(db.String(200), nullable=True)
    created_at        = db.Column(db.DateTime, default=datetime.now)
    roll_history      = db.Column(db.Text, nullable=True)  # JSON array de rolagens


class CollarSimulation(db.Model):
    """Simulação de estratégia colar: compra ação + compra PUT + venda CALL."""
    __tablename__ = 'collar_simulation'
    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    underlying_asset = db.Column(db.String(15), nullable=False)   # ex: BRAP4
    stock_price      = db.Column(db.Float, nullable=False)         # cotação da ação na entrada
    quantity         = db.Column(db.Integer, nullable=False, default=100)
    put_ticker       = db.Column(db.String(20), nullable=False)
    put_strike       = db.Column(db.Float, nullable=False)
    put_premium      = db.Column(db.Float, nullable=False)         # prêmio pago
    call_ticker      = db.Column(db.String(20), nullable=False)
    call_strike      = db.Column(db.Float, nullable=False)
    call_premium     = db.Column(db.Float, nullable=False)         # prêmio recebido
    expiration_date  = db.Column(db.Date, nullable=False)
    entry_date       = db.Column(db.Date, nullable=True)
    notes            = db.Column(db.String(200), nullable=True)
    created_at       = db.Column(db.DateTime, default=datetime.now)


class SelicMensal(db.Model):
    """Taxa Selic mensal (% ao mês) — compartilhada entre todos os usuários."""
    __tablename__ = 'selic_mensal'
    id         = db.Column(db.Integer, primary_key=True)
    mes_ano    = db.Column(db.String(7), unique=True, nullable=False)  # 'YYYY-MM'
    taxa       = db.Column(db.Float, nullable=False)                   # % a.m. ex: 1.16


class Dividend(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=False)
    # ticker not strictly needed if linked to Asset, but good for quick verify
    ticker = db.Column(db.String(10), nullable=False) 
    type = db.Column(db.String(20), nullable=False) # 'DIVIDENDO' or 'JCP'
    payment_date = db.Column(db.Date, nullable=True)
    ex_date = db.Column(db.Date, nullable=True) # Data Com
    amount = db.Column(db.Float, nullable=False)          # total = per_share × qty_used
    per_share = db.Column(db.Float, nullable=True)        # valor por ação (do provento)
    qty_used  = db.Column(db.Integer, nullable=True)      # qtd de ações usada no cálculo (editável)

    asset = db.relationship('Asset', backref=db.backref('dividends', lazy=True, cascade="all, delete-orphan"))

class AssetTxn(db.Model):
    """Livro de transações da carteira: cada compra/venda com data, qtd e
    preço. Fontes: MANUAL (botões Comprar/Vender), INICIAL (Adicionar Ativo),
    B3 (importação do CSV de negociação), PM_LUCRO (compra com lucro).
    Permite reconstruir a posição em qualquer data (ex.: qtd na data-com de
    um dividendo). Swing trade fica fora do livro."""
    __tablename__ = 'asset_txn'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ticker     = db.Column(db.String(10), nullable=False)
    txn_date   = db.Column(db.Date, nullable=False)
    side       = db.Column(db.String(1), nullable=False, default='C')   # C | V
    quantity   = db.Column(db.Integer, nullable=False)
    price      = db.Column(db.Float, nullable=False, default=0.0)
    source     = db.Column(db.String(12), default='MANUAL')  # MANUAL | INICIAL | B3 | PM_LUCRO
    notes      = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)


class PMEvent(db.Model):
    """Evento do Preço Médio didático (página Preço Médio).
    Cada crédito (dividendo recebido ou lucro de opções do ativo) é usado UMA
    única vez: ou APLICADO ao PM (reduz o custo ajustado) ou FINANCIANDO uma
    compra com lucro (as ações novas entram a PM zero). Guarda pm_before/after
    para o histórico didático das mudanças."""
    __tablename__ = 'pm_event'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ticker     = db.Column(db.String(10), nullable=False)
    kind       = db.Column(db.String(15), nullable=False)  # DIVIDENDO | OPCOES | COMPRA_LUCRO | MANUAL
    event_date = db.Column(db.Date, nullable=True)
    valor      = db.Column(db.Float, nullable=False, default=0.0)  # redução do custo ajustado (na compra = valor financiado)
    buy_qty    = db.Column(db.Integer, nullable=True)   # COMPRA_LUCRO: unidades compradas
    buy_price  = db.Column(db.Float, nullable=True)     # COMPRA_LUCRO: preço unitário pago
    source_key = db.Column(db.String(30), nullable=True)  # 'div:<id>' | 'th:<id>' — dedupe da varredura
    ref        = db.Column(db.String(200), nullable=True)
    pm_before  = db.Column(db.Float, nullable=True)
    pm_after   = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)


class MarketIndex(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, default=0.0)
    change_percent = db.Column(db.Float, default=0.0)
    last_update = db.Column(db.String(20))

    def __repr__(self):
        return f'<MarketIndex {self.ticker}>'



class PortfolioSnapshot(db.Model):
    """Foto diária do patrimônio para a curva de evolução.
    Um registro por (usuário, dia); o último do dia sobrescreve.
    total_equity = ações + FIIs + ETFs (a preço de mercado)."""
    __tablename__ = 'portfolio_snapshot'
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    snap_date    = db.Column(db.String(10), nullable=False, index=True)   # YYYY-MM-DD
    total_equity = db.Column(db.Float, nullable=False, default=0.0)
    total_acoes  = db.Column(db.Float, nullable=False, default=0.0)
    total_fiis   = db.Column(db.Float, nullable=False, default=0.0)
    total_etfs   = db.Column(db.Float, nullable=False, default=0.0)
    estimated    = db.Column(db.Boolean, nullable=False, default=False)   # True = reconstruído do histórico
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)


class ChartCache(db.Model):
    """Cache persistente de OHLCV por ticker (sobrevive restart do servidor)."""
    __tablename__ = 'chart_cache'
    ticker     = db.Column(db.String(20), primary_key=True)
    last_date  = db.Column(db.String(12), nullable=False)   # último candle: YYYY-MM-DD
    fetched_at = db.Column(db.DateTime,   nullable=False, default=datetime.utcnow)
    candles_gz = db.Column(db.LargeBinary, nullable=False)   # JSON gzip dos candles


class UserChartLine(db.Model):
    """Linhas de tendência desenhadas pelo usuário no gráfico de candlestick."""
    __tablename__ = 'user_chart_lines'
    id      = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ticker  = db.Column(db.String(20), nullable=False, index=True)
    x1      = db.Column(db.String(12), nullable=False)   # data ISO YYYY-MM-DD
    y1      = db.Column(db.Float, nullable=False)
    x2      = db.Column(db.String(12), nullable=False)
    y2      = db.Column(db.Float, nullable=False)
    color   = db.Column(db.String(10), default='#3b82f6')
    width   = db.Column(db.Float, default=1.5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SearchedOption(db.Model):
    """Opções pesquisadas pelo usuário na tela Busca de Opção.
    Ficam na lista RTD por 10 dias e são limpas automaticamente na próxima busca."""
    __tablename__ = 'searched_option'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ticker     = db.Column(db.String(20), nullable=False)
    underlying = db.Column(db.String(20), nullable=True)
    searched_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'ticker', name='uq_searched_option'),)


class RtdOptionData(db.Model):
    """Dados de opções importados da planilha Excel (sheets rtd/opcao/C_put/V_put).
    Serve como cache local para preencher campos que a OpLab não retorna."""
    __tablename__ = 'rtd_option_data'
    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ticker          = db.Column(db.String(20), nullable=False)
    underlying      = db.Column(db.String(20), nullable=True)
    last_price      = db.Column(db.Float, nullable=True)
    open_price      = db.Column(db.Float, nullable=True)
    high_price      = db.Column(db.Float, nullable=True)
    low_price       = db.Column(db.Float, nullable=True)
    prev_close      = db.Column(db.Float, nullable=True)
    change_pct      = db.Column(db.Float, nullable=True)
    strike          = db.Column(db.Float, nullable=True)
    expiration      = db.Column(db.String(20), nullable=True)   # DD/MM/YYYY
    volume          = db.Column(db.Float, nullable=True)
    open_interest   = db.Column(db.Float, nullable=True)
    bid             = db.Column(db.Float, nullable=True)
    ask             = db.Column(db.Float, nullable=True)
    iv              = db.Column(db.Float, nullable=True)        # Volatilidade Implícita %
    iv_ask          = db.Column(db.Float, nullable=True)
    iv_bid          = db.Column(db.Float, nullable=True)
    iv_over_hv      = db.Column(db.Float, nullable=True)
    delta           = db.Column(db.Float, nullable=True)
    gamma           = db.Column(db.Float, nullable=True)
    theta           = db.Column(db.Float, nullable=True)
    rho             = db.Column(db.Float, nullable=True)
    vega            = db.Column(db.Float, nullable=True)
    bs_price        = db.Column(db.Float, nullable=True)
    intrinsic_value = db.Column(db.Float, nullable=True)
    extrinsic_value = db.Column(db.Float, nullable=True)
    spot_price      = db.Column(db.Float, nullable=True)
    option_type     = db.Column(db.String(10), nullable=True)   # CALL / PUT
    imported_at     = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'ticker', name='uq_rtd_option_data'),)
