# cryptotronbot_backend/app.py
# Main Flask application file

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, JWTManager
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import requests # For fetching crypto prices
import os

# --- Application Configuration ---
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///cryptotronbot.db') # Use PostgreSQL/MySQL in production
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Security: JWT_SECRET_KEY should be set via environment variable in production
# Generate a secure key: python -c "import secrets; print(secrets.token_urlsafe(32))"
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-super-strong-and-unique-secret-key') # CHANGE THIS IN PRODUCTION!
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24) # Token expiration

# --- Database Setup ---
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- JWT Setup ---
jwt = JWTManager(app)

# --- Constants ---
FREE_TIER_HOLDING_LIMIT = 5 # Max holdings for free users
COINGECKO_API_URL = "https://api.coingecko.com/api/v3" # Example API

# --- Models ---
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_premium_user = db.Column(db.Boolean, default=False, nullable=False)
    data_monetization_consent = db.Column(db.Boolean, default=False) # For data monetization
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    holdings = db.relationship('Holding', backref='owner', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Holding(db.Model):
    __tablename__ = 'holdings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # coin_id from CoinGecko or similar (e.g., 'bitcoin', 'ethereum')
    coin_api_id = db.Column(db.String(100), nullable=False)
    coin_symbol = db.Column(db.String(20), nullable=False) # e.g., 'BTC', 'ETH'
    quantity = db.Column(db.Float, nullable=False)
    average_buy_price = db.Column(db.Float, nullable=True) # Optional, in USD
    exchange_wallet = db.Column(db.String(100), nullable=True) # e.g., 'Binance', 'Ledger'
    notes = db.Column(db.Text, nullable=True) # Optional user notes
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Holding {self.quantity} {self.coin_symbol} for User ID {self.user_id}>'

# --- Helper Functions ---
def get_current_prices_from_api(coin_api_ids_list):
    """
    Fetches current prices for a list of coin API IDs from CoinGecko.
    coin_api_ids_list: A list of strings, e.g., ['bitcoin', 'ethereum']
    Returns a dictionary: {'bitcoin': 60000, 'ethereum': 3000} or None for errors
    """
    if not coin_api_ids_list:
        return {}
    ids_string = ','.join(coin_api_ids_list)
    params = {'ids': ids_string, 'vs_currencies': 'usd'}
    try:
        response = requests.get(f"{COINGECKO_API_URL}/simple/price", params=params, timeout=10)
        response.raise_for_status()  # Raises an exception for 4XX/5XX errors
        data = response.json()
        # Data format: {'bitcoin': {'usd': 60000}, 'ethereum': {'usd': 3000}}
        prices = {coin_id: details['usd'] for coin_id, details in data.items() if 'usd' in details}
        return prices
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error fetching crypto prices from CoinGecko: {e}")
        # Return None for prices on error so frontend can show 'unavailable'
        return {coin_id: None for coin_id in coin_api_ids_list}


# --- API Routes ---

# Health Check Route
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for Kubernetes liveness and readiness probes"""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected"
        }), 200
    except Exception as e:
        app.logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }), 500

# Authentication Routes
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({"msg": "Missing username, email, or password"}), 400

    username = data['username']
    email = data['email']
    password = data['password']

    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "Username already exists"}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "Email already exists"}), 409

    new_user = User(username=username, email=email)
    new_user.set_password(password)
    # New users start as non-premium by default
    new_user.is_premium_user = False

    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"msg": "User created successfully. Please log in."}), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error during registration: {e}")
        return jsonify({"msg": "Could not create user, please try again."}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({"msg": "Missing username or password"}), 400

    user = User.query.filter_by(username=data['username']).first()

    if user and user.check_password(data['password']):
        access_token = create_access_token(identity=user.id)
        return jsonify(
            access_token=access_token,
            user_id=user.id,
            username=user.username,
            is_premium=user.is_premium_user,
            data_consent=user.data_monetization_consent
        ), 200
    return jsonify({"msg": "Bad username or password"}), 401

@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def get_current_user_profile():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
    return jsonify(
        id=user.id,
        username=user.username,
        email=user.email,
        is_premium=user.is_premium_user,
        data_consent=user.data_monetization_consent,
        created_at=user.created_at.isoformat()
    ), 200

# Portfolio Routes
@app.route('/api/portfolio', methods=['GET'])
@jwt_required()
def get_portfolio():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user: # Should not happen if JWT is valid but good practice
        return jsonify({"msg": "User not found"}), 404

    holdings = user.holdings.order_by(Holding.added_at.desc()).all()
    portfolio_data = []
    coin_api_ids_to_fetch = list(set([h.coin_api_id for h in holdings]))

    current_prices_from_api = {}
    if coin_api_ids_to_fetch:
        current_prices_from_api = get_current_prices_from_api(coin_api_ids_to_fetch)

    total_portfolio_value_usd = 0.0

    for holding in holdings:
        current_price = current_prices_from_api.get(holding.coin_api_id)
        current_value_usd = (holding.quantity * current_price) if current_price is not None else None

        if current_value_usd is not None:
            total_portfolio_value_usd += current_value_usd

        portfolio_data.append({
            "id": holding.id,
            "coin_api_id": holding.coin_api_id,
            "coin_symbol": holding.coin_symbol,
            "quantity": holding.quantity,
            "average_buy_price": holding.average_buy_price,
            "exchange_wallet": holding.exchange_wallet,
            "notes": holding.notes,
            "added_at": holding.added_at.isoformat(),
            "current_price_usd": current_price,
            "current_value_usd": current_value_usd
        })

    # Placeholder for AI-driven analytics for premium users
    premium_analytics = {}
    if user.is_premium_user:
        premium_analytics = {
            "portfolio_risk_assessment": "Medium", # Mock data
            "rebalancing_suggestions": [ # Mock data
                {"action": "Consider selling some BTC", "reason": "Over-concentration"},
                {"action": "Consider buying some DOT", "reason": "Diversification"}
            ],
            "market_sentiment": "Neutral" # Mock data
        }

    return jsonify({
        "holdings": portfolio_data,
        "total_portfolio_value_usd": total_portfolio_value_usd,
        "is_premium_user": user.is_premium_user,
        "premium_analytics": premium_analytics if user.is_premium_user else "Upgrade to Premium for advanced analytics and AI rebalancing suggestions."
    }), 200

@app.route('/api/portfolio/holdings', methods=['POST'])
@jwt_required()
def add_holding():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    # Freemium Model: Check holding limit for non-premium users
    if not user.is_premium_user:
        if user.holdings.count() >= FREE_TIER_HOLDING_LIMIT:
            return jsonify({"msg": f"Free tier limit of {FREE_TIER_HOLDING_LIMIT} holdings reached. Please upgrade to Premium to add more."}), 403

    data = request.get_json()
    required_fields = ['coin_api_id', 'coin_symbol', 'quantity']
    if not all(field in data for field in required_fields):
        return jsonify({"msg": "Missing required fields (coin_api_id, coin_symbol, quantity)"}), 400

    try:
        quantity = float(data['quantity'])
        if quantity <= 0:
            return jsonify({"msg": "Quantity must be positive"}), 400
        
        avg_buy_price = data.get('average_buy_price')
        if avg_buy_price is not None:
            avg_buy_price = float(avg_buy_price)
            if avg_buy_price < 0:
                 return jsonify({"msg": "Average buy price cannot be negative"}), 400
        
        new_holding = Holding(
            user_id=current_user_id,
            coin_api_id=data['coin_api_id'].lower(), # Standardize to lowercase
            coin_symbol=data['coin_symbol'].upper(), # Standardize to uppercase
            quantity=quantity,
            average_buy_price=avg_buy_price,
            exchange_wallet=data.get('exchange_wallet'),
            notes=data.get('notes')
        )
        db.session.add(new_holding)
        db.session.commit()
        # Return the newly created holding's data for immediate display
        # Fetch its price to include in the response
        price_info = get_current_prices_from_api([new_holding.coin_api_id])
        current_price = price_info.get(new_holding.coin_api_id)
        current_value = (new_holding.quantity * current_price) if current_price else None

        return jsonify({
            "msg": "Holding added successfully",
            "holding": {
                "id": new_holding.id,
                "coin_api_id": new_holding.coin_api_id,
                "coin_symbol": new_holding.coin_symbol,
                "quantity": new_holding.quantity,
                "average_buy_price": new_holding.average_buy_price,
                "exchange_wallet": new_holding.exchange_wallet,
                "notes": new_holding.notes,
                "added_at": new_holding.added_at.isoformat(),
                "current_price_usd": current_price,
                "current_value_usd": current_value
            }
        }), 201
    except ValueError:
        return jsonify({"msg": "Invalid data format for quantity or average_buy_price."}), 400
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding holding: {e}")
        return jsonify({"msg": "Could not add holding, please try again."}), 500

@app.route('/api/portfolio/holdings/<int:holding_id>', methods=['PUT'])
@jwt_required()
def update_holding(holding_id):
    current_user_id = get_jwt_identity()
    holding = Holding.query.filter_by(id=holding_id, user_id=current_user_id).first()
    if not holding:
        return jsonify({"msg": "Holding not found or you do not have permission to edit it."}), 404

    data = request.get_json()
    try:
        if 'quantity' in data:
            quantity = float(data['quantity'])
            if quantity <= 0: return jsonify({"msg": "Quantity must be positive"}), 400
            holding.quantity = quantity
        if 'average_buy_price' in data:
            avg_buy_price = data.get('average_buy_price')
            if avg_buy_price is not None:
                avg_buy_price = float(avg_buy_price)
                if avg_buy_price < 0: return jsonify({"msg": "Average buy price cannot be negative"}), 400
            holding.average_buy_price = avg_buy_price # Allow setting to None
        if 'exchange_wallet' in data:
            holding.exchange_wallet = data['exchange_wallet']
        if 'notes' in data:
            holding.notes = data['notes']
        # coin_api_id and coin_symbol are generally not updated, but if needed, add logic here.

        db.session.commit()
        # Fetch its price to include in the response
        price_info = get_current_prices_from_api([holding.coin_api_id])
        current_price = price_info.get(holding.coin_api_id)
        current_value = (holding.quantity * current_price) if current_price else None
        return jsonify({
            "msg": "Holding updated successfully",
            "holding": {
                "id": holding.id,
                "coin_api_id": holding.coin_api_id,
                "coin_symbol": holding.coin_symbol,
                "quantity": holding.quantity,
                "average_buy_price": holding.average_buy_price,
                "exchange_wallet": holding.exchange_wallet,
                "notes": holding.notes,
                "added_at": holding.added_at.isoformat(),
                "last_updated": holding.last_updated.isoformat(),
                "current_price_usd": current_price,
                "current_value_usd": current_value
            }
        }), 200
    except ValueError:
        return jsonify({"msg": "Invalid data format for quantity or average_buy_price."}), 400
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating holding {holding_id}: {e}")
        return jsonify({"msg": "Could not update holding."}), 500

@app.route('/api/portfolio/holdings/<int:holding_id>', methods=['DELETE'])
@jwt_required()
def delete_holding(holding_id):
    current_user_id = get_jwt_identity()
    holding = Holding.query.filter_by(id=holding_id, user_id=current_user_id).first()
    if not holding:
        return jsonify({"msg": "Holding not found or you do not have permission to delete it."}), 404

    try:
        db.session.delete(holding)
        db.session.commit()
        return jsonify({"msg": "Holding deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting holding {holding_id}: {e}")
        return jsonify({"msg": "Could not delete holding."}), 500

# Crypto Data Routes (e.g., for populating dropdowns)
@app.route('/api/cryptocurrencies', methods=['GET'])
# @jwt_required() # Optional: decide if this needs auth, probably not for a public list
def get_supported_cryptocurrencies():
    """
    Provides a list of cryptocurrencies supported for tracking.
    In a real app, this might come from CoinGecko's /coins/list endpoint and be cached.
    """
    # For this example, using a simplified list.
    # The 'id' should match what CoinGecko API expects for price lookups.
    # You should fetch this list from CoinGecko and cache it periodically in a real app.
    # GET https://api.coingecko.com/api/v3/coins/list
    
    # Mocked list for simplicity. Replace with actual API call and caching.
    # This is a small subset. CoinGecko has thousands.
    try:
        # Example: Fetch top N coins by market cap
        # response = requests.get(f"{COINGECKO_API_URL}/coins/markets", params={'vs_currency': 'usd', 'order': 'market_cap_desc', 'per_page': 100, 'page': 1}, timeout=10)
        # response.raise_for_status()
        # coins_market_data = response.json()
        # supported_coins = [{"id": coin['id'], "symbol": coin['symbol'].upper(), "name": coin['name']} for coin in coins_market_data]
        
        # Using a static list for this example to avoid API rate limits during development/testing
        supported_coins = [
            {"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin"},
            {"id": "ethereum", "symbol": "ETH", "name": "Ethereum"},
            {"id": "tether", "symbol": "USDT", "name": "Tether"},
            {"id": "binancecoin", "symbol": "BNB", "name": "BNB"},
            {"id": "solana", "symbol": "SOL", "name": "Solana"},
            {"id": "usd-coin", "symbol": "USDC", "name": "USD Coin"},
            {"id": "ripple", "symbol": "XRP", "name": "XRP"},
            {"id": "dogecoin", "symbol": "DOGE", "name": "Dogecoin"},
            {"id": "cardano", "symbol": "ADA", "name": "Cardano"},
            {"id": "avalanche-2", "symbol": "AVAX", "name": "Avalanche"},
            {"id": "shiba-inu", "symbol": "SHIB", "name": "Shiba Inu"},
            {"id": "polkadot", "symbol": "DOT", "name": "Polkadot"},
            {"id": "chainlink", "symbol": "LINK", "name": "Chainlink"},
            {"id": "tron", "symbol": "TRX", "name": "TRON"},
            {"id": "matic-network", "symbol": "MATIC", "name": "Polygon"},
            {"id": "litecoin", "symbol": "LTC", "name": "Litecoin"},
            {"id": "uniswap", "symbol": "UNI", "name": "Uniswap"},
            # Add more or fetch dynamically
        ]
        return jsonify(supported_coins), 200
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Failed to fetch coin list from CoinGecko: {e}")
        return jsonify({"msg": "Could not retrieve cryptocurrency list at this time."}), 503


# DeFi & Stablecoin Routes
@app.route('/api/defi/stablecoins', methods=['GET'])
def get_stablecoins():
    """Get list of supported stablecoins"""
    from utils.defi_api import get_supported_stablecoins
    try:
        stablecoins = get_supported_stablecoins()
        return jsonify(stablecoins), 200
    except Exception as e:
        app.logger.error(f"Error fetching stablecoins: {e}")
        return jsonify({"msg": "Could not retrieve stablecoin list."}), 500

@app.route('/api/defi/stablecoins/<symbol>', methods=['GET'])
def get_stablecoin_details(symbol):
    """Get detailed information for a specific stablecoin"""
    from utils.defi_api import DeFiAPIClient
    try:
        client = DeFiAPIClient()
        market_data = client.get_stablecoin_market_data(symbol.upper())
        if not market_data:
            return jsonify({"msg": f"Stablecoin {symbol} not found"}), 404
        return jsonify(market_data), 200
    except Exception as e:
        app.logger.error(f"Error fetching stablecoin details: {e}")
        return jsonify({"msg": "Could not retrieve stablecoin details."}), 500

@app.route('/api/defi/stablecoins/<symbol>/stability', methods=['GET'])
def get_stablecoin_stability(symbol):
    """Get stability analysis for a stablecoin"""
    from utils.defi_api import DeFiAPIClient
    try:
        days = request.args.get('days', 30, type=int)
        client = DeFiAPIClient()
        stability_data = client.analyze_stablecoin_stability(symbol.upper(), days=days)
        if not stability_data:
            return jsonify({"msg": f"Could not analyze stability for {symbol}"}), 404
        return jsonify(stability_data), 200
    except Exception as e:
        app.logger.error(f"Error analyzing stability: {e}")
        return jsonify({"msg": "Could not analyze stability."}), 500

@app.route('/api/defi/yield/opportunities', methods=['GET'])
def get_yield_opportunities():
    """Get all yield opportunities from DeFi protocols"""
    from utils.yield_aggregator import yield_aggregator
    try:
        asset_filter = request.args.get('asset', None)
        opportunities = yield_aggregator.get_all_yield_opportunities(asset_filter=asset_filter)
        return jsonify({
            "opportunities": opportunities,
            "count": len(opportunities),
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        app.logger.error(f"Error fetching yield opportunities: {e}")
        return jsonify({"msg": "Could not retrieve yield opportunities."}), 500

@app.route('/api/defi/yield/recommendations', methods=['GET'])
@jwt_required()
def get_yield_recommendations():
    """Get personalized yield recommendations based on user portfolio"""
    from utils.yield_aggregator import yield_aggregator
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({"msg": "User not found"}), 404
        
        # Get user's holdings
        holdings = user.holdings.all()
        portfolio = [{
            'coin_symbol': h.coin_symbol,
            'quantity': h.quantity,
            'coin_api_id': h.coin_api_id
        } for h in holdings]
        
        risk_tolerance = request.args.get('risk', 'medium', type=str)
        if risk_tolerance not in ['low', 'medium', 'high']:
            risk_tolerance = 'medium'
        
        recommendations = yield_aggregator.get_yield_recommendations(
            user_portfolio=portfolio,
            risk_tolerance=risk_tolerance
        )
        
        return jsonify({
            "recommendations": recommendations,
            "count": len(recommendations),
            "risk_tolerance": risk_tolerance,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        app.logger.error(f"Error generating recommendations: {e}")
        return jsonify({"msg": "Could not generate recommendations."}), 500

@app.route('/api/defi/portfolio/yield-potential', methods=['GET'])
@jwt_required()
def get_portfolio_yield_potential():
    """Calculate potential yield for user's portfolio"""
    from utils.yield_aggregator import yield_aggregator
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({"msg": "User not found"}), 404
        
        holdings = user.holdings.all()
        total_potential_yield = 0.0
        holdings_analysis = []
        
        for holding in holdings:
            if holding.coin_symbol.upper() in ['USDT', 'USDC', 'DAI', 'BUSD', 'FRAX']:
                opportunities = yield_aggregator.get_all_yield_opportunities(
                    asset_filter=holding.coin_symbol
                )
                if opportunities:
                    best_apy = opportunities[0].get('apy', 0)
                    potential_yield = holding.quantity * (best_apy / 100)
                    total_potential_yield += potential_yield
                    
                    holdings_analysis.append({
                        'coin_symbol': holding.coin_symbol,
                        'quantity': holding.quantity,
                        'best_apy': best_apy,
                        'potential_annual_yield': potential_yield,
                        'protocol': opportunities[0].get('protocol', 'N/A')
                    })
        
        return jsonify({
            "total_potential_annual_yield": round(total_potential_yield, 2),
            "holdings_analysis": holdings_analysis,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        app.logger.error(f"Error calculating yield potential: {e}")
        return jsonify({"msg": "Could not calculate yield potential."}), 500

# User Settings / Preferences
@app.route('/api/user/preferences/data_consent', methods=['POST'])
@jwt_required()
def update_data_consent():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    data = request.get_json()
    if 'consent' not in data or not isinstance(data['consent'], bool):
        return jsonify({"msg": "Invalid payload. 'consent' (boolean) is required."}), 400

    user.data_monetization_consent = data['consent']
    try:
        db.session.commit()
        return jsonify({"msg": "Data consent preference updated successfully.", "consent_status": user.data_monetization_consent}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating data consent for user {user.id}: {e}")
        return jsonify({"msg": "Could not update consent preference."}), 500

# --- Main Execution ---
if __name__ == '__main__':
    # Create tables if they don't exist (for development)
    # In production, you'd use Flask-Migrate commands:
    # flask db init (once)
    # flask db migrate -m "Initial migration"
    # flask db upgrade
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000) # Backend runs on port 5000
