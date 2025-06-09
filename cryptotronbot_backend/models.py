Python


from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    holdings = db.relationship('Holding', backref='owner', lazy=True)
    # Premium feature flag
    is_premium_user = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<User {self.username}>'

class Holding(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    coin_id = db.Column(db.String(50), nullable=False) # e.g., 'bitcoin', 'ethereum'
    coin_symbol = db.Column(db.String(10), nullable=False) # e.g., 'BTC', 'ETH'
    quantity = db.Column(db.Float, nullable=False)
    average_buy_price = db.Column(db.Float, nullable=True) # Optional
    exchange_wallet = db.Column(db.String(100), nullable=True) # e.g., 'Binance', 'Ledger Nano S'
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Holding {self.quantity} {self.coin_symbol}>'

# Add other models as needed (e.g., Exchange, Wallet for API key storage if you build direct integrations)

