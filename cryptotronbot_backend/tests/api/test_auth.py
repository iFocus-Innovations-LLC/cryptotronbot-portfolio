import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import app, db, User

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

def test_register_login_and_me(client):
    # Register
    response = client.post('/api/auth/register', json={
        'username': 'apitestuser',
        'email': 'apitestuser@example.com',
        'password': 'testpassword123'
    })
    assert response.status_code in (201, 409)  # 409 if already exists

    # Login
    response = client.post('/api/auth/login', json={
        'username': 'apitestuser',
        'password': 'testpassword123'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert 'access_token' in data
    token = data['access_token']

    # Get current user profile
    response = client.get('/api/auth/me', headers={
        'Authorization': f'Bearer {token}'
    })
    assert response.status_code == 200
    profile = response.get_json()
    assert profile['username'] == 'apitestuser' 