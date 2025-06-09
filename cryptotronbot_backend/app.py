Python


from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, JWTManager
from werkzeug.security import generate_password_hash, check_password_hash
# from models import db, User, Holding # Assuming models.py is setup
# from utils.crypto_api import get_current_prices # Assuming utils/crypto_api.py is setup

# --- Placeholder for models and utils if not using separate files for simplicity ---
# This section would typically be in models.py and utils/crypto_api.py

db = SQLAlchemy() # Define db here if not imported

class User(db.Model): # Simplified for this snippet
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256)) # Increased length
    is_premium_user = db.Column(db.Boolean, default=False)
    # holdings relationship would be here

class Holding(db.Model): # Simplified for this snippet
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    coin_id = db.Column(db.String(50), nullable=False)
    coin_symbol = db.Column(db.String(10), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    # ... other fields

# Placeholder for crypto price function
def get_current_prices(coin_ids_list):
    print(f"Fetching prices for: {coin_ids_list} (mock implementation)")
    # In a real app, call an external API
    mock_prices = {
        'bitcoin': {'usd': 60000.00},
        'ethereum': {'usd': 3000.00},
        'dogecoin': {'usd': 0.15}
    }
    return {coin: data.get('usd') for coin, data in mock_prices.items() if coin in coin_ids_list}
# --- End Placeholder ---


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cryptotronbot.db' # Use PostgreSQL/MySQL in production
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'your-super-secret-key' # Change this!
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False # For simplicity; set an expiration in production

db.init_app(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "Username already exists"}), 409

    hashed_password = generate_password_hash(password)
    new_user = User(username=username, password_hash=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"msg": "User created successfully"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password_hash, password):
        access_token = create_access_token(identity=user.id)
        return jsonify(access_token=access_token, user_id=user.id, is_premium=user.is_premium_user)
    return jsonify({"msg": "Bad username or password"}), 401

@app.route('/api/portfolio', methods=['GET'])
@jwt_required()
def get_portfolio():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    holdings = Holding.query.filter_by(user_id=current_user_id).all()
    portfolio_data = []
    coin_ids_to_fetch = list(set([h.coin_id for h in holdings])) # Get unique coin_ids

    current_prices = {}
    if coin_ids_to_fetch:
        current_prices = get_current_prices(coin_ids_to_fetch)

    total_portfolio_value = 0.0

    for holding in holdings:
        current_price = current_prices.get(holding.coin_id)
        value = (holding.quantity * current_price) if current_price is not None else None
        if value is not None:
            total_portfolio_value += value

        portfolio_data.append({
            "id": holding.id,
            "coin_id": holding.coin_id,
            "coin_symbol": holding.coin_symbol,
            "quantity": holding.quantity,
            "average_buy_price": getattr(holding, 'average_buy_price', None), # if field exists
            "exchange_wallet": getattr(holding, 'exchange_wallet', None), # if field exists
            "current_price": current_price,
            "current_value": value
        })

    # Premium feature example
    analytics = {}
    if user.is_premium_user:
        # Perform advanced analytics (e.g., diversification, risk score)
        analytics = {"diversification_score": 0.75, "risk_level": "medium"} # Mock data

    return jsonify({
        "holdings": portfolio_data,
        "total_value_usd": total_portfolio_value,
        "is_premium": user.is_premium_user,
        "premium_analytics": analytics if user.is_premium_user else "Upgrade to premium for advanced analytics."
    })

@app.route('/api/portfolio/add_holding', methods=['POST'])
@jwt_required()
def add_holding():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    data = request.get_json()

    # Freemium check: Limit number of coins for non-premium users
    if not user.is_premium_user:
        current_holdings_count = Holding.query.filter_by(user_id=current_user_id).count()
        if current_holdings_count >= 5: # Example limit
            return jsonify({"msg": "Free plan limit reached. Upgrade to add more holdings."}), 403

    try:
        new_holding = Holding(
            user_id=current_user_id,
            coin_id=data['coin_id'].lower(), # Store consistently
            coin_symbol=data['coin_symbol'].upper(),
            quantity=float(data['quantity']),
            average_buy_price=float(data.get('average_buy_price', 0)),
            exchange_wallet=data.get('exchange_wallet')
        )
        db.session.add(new_holding)
        db.session.commit()
        return jsonify({"msg": "Holding added", "holding_id": new_holding.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Error adding holding", "error": str(e)}), 400

# Add routes for updating and deleting holdings (PUT /api/portfolio/holding/<id>, DELETE /api/portfolio/holding/<id>)

@app.route('/api/crypto_prices_available', methods=['GET'])
# @jwt_required() # Optional: decide if this needs auth
def get_available_crypto_prices():
    # This could fetch a list of supported coins from your price provider or a predefined list
    # For demonstration, using keys from the mock price function
    # In a real scenario, query an API like CoinGecko's /coins/list
    supported_coins = [
        {"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin"},
        {"id": "ethereum", "symbol": "ETH", "name": "Ethereum"},
        {"id": "dogecoin", "symbol": "DOGE", "name": "Dogecoin"},
        # ... add more or fetch dynamically
    ]
    return jsonify(supported_coins)


if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Create tables if they don't exist
    app.run(debug=True, port=5000) # Backend runs on port 5000
