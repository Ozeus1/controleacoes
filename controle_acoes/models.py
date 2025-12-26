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

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
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
    
    # History/Duration
    entry_date = db.Column(db.Date, nullable=True)
    
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
    ticker = db.Column(db.String(10), nullable=False)
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


class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(255), nullable=True)

    @staticmethod
    def get_value(key, default=None):
        setting = Settings.query.filter_by(key=key).first()
        if setting:
            if key == 'brapi_token':
                try:
                    cipher = get_cipher_suite()
                    return cipher.decrypt(setting.value.encode()).decode()
                except Exception:
                    return default # Or handle error
            return setting.value
        return default

    @staticmethod
    def set_value(key, value):
        setting = Settings.query.filter_by(key=key).first()
        if not setting:
            setting = Settings(key=key)
            db.session.add(setting)
        
        if key == 'brapi_token':
            cipher = get_cipher_suite()
            encrypted_val = cipher.encrypt(value.encode()).decode()
            setting.value = encrypted_val
        else:
            setting.value = value
            
        db.session.commit()

