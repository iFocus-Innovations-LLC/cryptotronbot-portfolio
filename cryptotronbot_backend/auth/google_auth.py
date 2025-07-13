"""
Google OAuth authentication for CryptotronBot
"""
import os
import json
from datetime import datetime, timedelta
from flask import request, session, redirect, url_for
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests
from google.auth.exceptions import GoogleAuthError

class GoogleAuth:
    """Google OAuth authentication handler"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the Google Auth with Flask app"""
        self.client_id = app.config.get('GOOGLE_CLIENT_ID')
        self.client_secret = app.config.get('GOOGLE_CLIENT_SECRET')
        self.redirect_uri = app.config.get('GOOGLE_REDIRECT_URI')
        
        # OAuth 2.0 configuration
        self.oauth_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri]
            }
        }
    
    def get_authorization_url(self):
        """
        Get Google OAuth authorization URL
        
        Returns:
            tuple: (authorization_url, state)
        """
        try:
            flow = Flow.from_client_config(
                self.oauth_config,
                scopes=['openid', 'email', 'profile']
            )
            
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            
            return authorization_url, state
            
        except Exception as e:
            print(f"Error creating authorization URL: {e}")
            return None, None
    
    def handle_callback(self, code, state):
        """
        Handle OAuth callback and exchange code for tokens
        
        Args:
            code (str): Authorization code from Google
            state (str): State parameter for CSRF protection
            
        Returns:
            dict: User information or None if error
        """
        try:
            flow = Flow.from_client_config(
                self.oauth_config,
                scopes=['openid', 'email', 'profile']
            )
            flow.redirect_uri = self.redirect_uri
            
            # Exchange authorization code for tokens
            flow.fetch_token(code=code)
            
            # Get user info from ID token
            id_info = id_token.verify_oauth2_token(
                flow.credentials.id_token,
                requests.Request(),
                self.client_id
            )
            
            # Verify issuer
            if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')
            
            return {
                'google_id': id_info['sub'],
                'email': id_info['email'],
                'name': id_info.get('name', ''),
                'picture': id_info.get('picture', ''),
                'access_token': flow.credentials.token,
                'refresh_token': flow.credentials.refresh_token
            }
            
        except Exception as e:
            print(f"Error handling OAuth callback: {e}")
            return None
    
    def verify_token(self, token):
        """
        Verify Google ID token
        
        Args:
            token (str): Google ID token
            
        Returns:
            dict: Token information or None if invalid
        """
        try:
            idinfo = id_token.verify_oauth2_token(
                token, 
                requests.Request(), 
                self.client_id
            )
            
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')
            
            return idinfo
            
        except ValueError as e:
            print(f"Token verification failed: {e}")
            return None
    
    def refresh_access_token(self, refresh_token):
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token (str): Refresh token
            
        Returns:
            dict: New access token information or None if error
        """
        try:
            flow = Flow.from_client_config(
                self.oauth_config,
                scopes=['openid', 'email', 'profile']
            )
            
            # Use refresh token to get new access token
            flow.refresh_token(refresh_token)
            
            return {
                'access_token': flow.credentials.token,
                'expires_at': flow.credentials.expiry.isoformat() if flow.credentials.expiry else None
            }
            
        except Exception as e:
            print(f"Error refreshing token: {e}")
            return None

class GoogleAuthMiddleware:
    """Middleware for Google OAuth authentication"""
    
    def __init__(self, app, auth_handler):
        self.app = app
        self.auth_handler = auth_handler
    
    def __call__(self, environ, start_response):
        """Middleware callable"""
        # Add auth handler to request context
        environ['google_auth'] = self.auth_handler
        return self.app(environ, start_response)

def require_google_auth(f):
    """Decorator to require Google authentication"""
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated with Google
        if 'google_user_id' not in session:
            return redirect(url_for('auth.google_login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def get_google_user_info():
    """Get current Google user information from session"""
    if 'google_user_id' in session:
        return {
            'google_id': session['google_user_id'],
            'email': session.get('google_email'),
            'name': session.get('google_name'),
            'picture': session.get('google_picture')
        }
    return None

def logout_google_user():
    """Logout Google user by clearing session"""
    session.pop('google_user_id', None)
    session.pop('google_email', None)
    session.pop('google_name', None)
    session.pop('google_picture', None)
    session.pop('google_access_token', None)
    session.pop('google_refresh_token', None)

# Flask routes for Google OAuth
def create_google_auth_routes(app, auth_handler, db, User):
    """Create Flask routes for Google OAuth"""
    
    @app.route('/auth/google/login')
    def google_login():
        """Initiate Google OAuth login"""
        authorization_url, state = auth_handler.get_authorization_url()
        if authorization_url:
            session['oauth_state'] = state
            return redirect(authorization_url)
        return "Error: Could not create authorization URL", 500
    
    @app.route('/auth/google/callback')
    def google_callback():
        """Handle Google OAuth callback"""
        # Verify state parameter
        state = request.args.get('state')
        if state != session.get('oauth_state'):
            return "Error: Invalid state parameter", 400
        
        # Get authorization code
        code = request.args.get('code')
        if not code:
            return "Error: No authorization code received", 400
        
        # Handle OAuth callback
        user_info = auth_handler.handle_callback(code, state)
        if not user_info:
            return "Error: Failed to authenticate with Google", 500
        
        # Find or create user
        user = User.query.filter_by(google_id=user_info['google_id']).first()
        if not user:
            # Create new user
            user = User(
                google_id=user_info['google_id'],
                email=user_info['email'],
                name=user_info['name'],
                picture_url=user_info['picture']
            )
            db.session.add(user)
            db.session.commit()
        
        # Update user's last login
        user.last_login = datetime.utcnow()
        user.login_count += 1
        db.session.commit()
        
        # Store user info in session
        session['google_user_id'] = user_info['google_id']
        session['google_email'] = user_info['email']
        session['google_name'] = user_info['name']
        session['google_picture'] = user_info['picture']
        session['google_access_token'] = user_info['access_token']
        if user_info.get('refresh_token'):
            session['google_refresh_token'] = user_info['refresh_token']
        
        # Clear OAuth state
        session.pop('oauth_state', None)
        
        return redirect(url_for('dashboard'))
    
    @app.route('/auth/google/logout')
    def google_logout():
        """Logout Google user"""
        logout_google_user()
        return redirect(url_for('index'))
    
    @app.route('/auth/google/refresh')
    def google_refresh():
        """Refresh Google access token"""
        refresh_token = session.get('google_refresh_token')
        if not refresh_token:
            return "Error: No refresh token available", 400
        
        new_token_info = auth_handler.refresh_access_token(refresh_token)
        if new_token_info:
            session['google_access_token'] = new_token_info['access_token']
            return "Token refreshed successfully", 200
        else:
            return "Error: Failed to refresh token", 500 