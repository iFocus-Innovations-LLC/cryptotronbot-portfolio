import pytest
from flask import Flask
from cryptotronbot_backend.app import app as flask_app

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client

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