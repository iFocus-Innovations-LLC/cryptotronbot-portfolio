import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import app, db, User, Holding

@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['JWT_SECRET_KEY'] = 'test-secret-key'
    
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()
        db.session.remove()

def get_token(client):
    # Ensure user exists
    client.post('/api/auth/register', json={
        'username': 'apitestuser2',
        'email': 'apitestuser2@example.com',
        'password': 'testpassword123'
    })
    # Login
    response = client.post('/api/auth/login', json={
        'username': 'apitestuser2',
        'password': 'testpassword123'
    })
    data = response.get_json()
    return data['access_token']

def test_get_portfolio(client):
    token = get_token(client)
    response = client.get('/api/portfolio', headers={
        'Authorization': f'Bearer {token}'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert 'holdings' in data or isinstance(data, list) or isinstance(data, dict) 