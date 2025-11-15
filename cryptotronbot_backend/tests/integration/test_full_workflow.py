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

def test_full_user_workflow(client):
    """Test complete workflow: register -> login -> portfolio operations."""
    # Register a new user
    response = client.post('/api/auth/register', json={
        'username': 'integrationuser',
        'email': 'integrationuser@example.com',
        'password': 'testpassword123'
    })
    assert response.status_code in (201, 409)  # 201 created or 409 already exists
    
    # Login
    response = client.post('/api/auth/login', json={
        'username': 'integrationuser',
        'password': 'testpassword123'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert 'access_token' in data
    token = data['access_token']
    
    # Get portfolio (should be empty initially)
    response = client.get('/api/portfolio', headers={
        'Authorization': f'Bearer {token}'
    })
    assert response.status_code == 200
    
    # Health check
    response = client.get('/api/health')
    assert response.status_code == 200
    health_data = response.get_json()
    assert health_data['status'] == 'healthy'

