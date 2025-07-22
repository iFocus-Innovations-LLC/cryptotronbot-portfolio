import pytest
from cryptotronbot_backend.app import app as flask_app

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client

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