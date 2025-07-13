import os
from google.cloud import secretmanager
from dotenv import load_dotenv
from datetime import timedelta

# Load environment variables
load_dotenv()

def get_secret(secret_id):
    """Retrieve a secret from Google Secret Manager"""
    try:
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        # Fallback to environment variables for development
        return os.getenv(secret_id.upper().replace('-', '_'))

class SecureConfig:
    """Secure configuration using Google Cloud services"""
    
    # Google Cloud Project
    GOOGLE_CLOUD_PROJECT = os.getenv('GOOGLE_CLOUD_PROJECT')
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://cryptotronbot_user:{get_secret('db-password')}"
        f"@/cryptotronbot_db?host=/cloudsql/{os.getenv('INSTANCE_CONNECTION_NAME')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT configuration
    JWT_SECRET_KEY = get_secret('jwt-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    
    # Google OAuth configuration
    GOOGLE_CLIENT_ID = get_secret('google-client-id')
    GOOGLE_CLIENT_SECRET = get_secret('google-client-secret')
    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI')
    
    # Cloud Storage configuration
    CLOUD_STORAGE_BUCKET = os.getenv('CLOUD_STORAGE_BUCKET', 'cryptotronbot-user-data')
    
    # Cloud KMS configuration
    KMS_KEY_RING = os.getenv('KMS_KEY_RING', 'cryptotronbot-keys')
    KMS_KEY_NAME = os.getenv('KMS_KEY_NAME', 'user-data-key')
    
    # Security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Logging configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = "memory://"
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    
    # CORS settings
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    
    # API rate limits
    FREE_TIER_HOLDING_LIMIT = 5
    PREMIUM_TIER_HOLDING_LIMIT = 100
    
    # Security headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    }

class DevelopmentConfig(SecureConfig):
    """Development configuration with local fallbacks"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///cryptotronbot.db')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-key-change-in-production')
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

class ProductionConfig(SecureConfig):
    """Production configuration with strict security settings"""
    DEBUG = False
    TESTING = False
    
    # Additional production security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    
    # Force HTTPS
    PREFERRED_URL_SCHEME = 'https'
    
    # Strict CORS for production
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '').split(',')
    
    # Enhanced security headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
        'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: https:; font-src 'self' https:; connect-src 'self' https://api.coingecko.com;",
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
    }

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 