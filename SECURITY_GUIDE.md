# Google IAM Integration for Enhanced Security

## Overview

This guide explains how to integrate Google Identity and Access Management (IAM) with your CryptotronBot application to enhance security for storing end user information. Google IAM provides enterprise-grade security features that can significantly improve your application's security posture.

## Current Security Assessment

Your current application uses:
- SQLite database with local storage
- JWT tokens for authentication
- Basic password hashing with Werkzeug
- Local file-based configuration

## Google IAM Integration Benefits

### 1. **Identity Management**
- **Google OAuth 2.0**: Replace local username/password with Google accounts
- **Single Sign-On (SSO)**: Users can access your app with their Google accounts
- **Multi-Factor Authentication (MFA)**: Leverage Google's built-in MFA
- **Account Recovery**: Google handles password resets and account recovery

### 2. **Access Control**
- **Role-Based Access Control (RBAC)**: Define roles like "free_user", "premium_user", "admin"
- **Fine-grained Permissions**: Control access to specific API endpoints and data
- **Conditional Access**: Implement policies based on location, device, time, etc.

### 3. **Data Security**
- **Google Cloud Storage**: Store user data in encrypted cloud storage
- **Cloud SQL**: Use Google Cloud SQL instead of SQLite
- **Secret Manager**: Store API keys and secrets securely
- **Cloud KMS**: Encrypt sensitive data at rest

## Implementation Plan

### Phase 1: Google OAuth Integration

#### 1.1 Set up Google Cloud Project

```bash
# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
gcloud init

# Create a new project
gcloud projects create cryptotronbot-secure
gcloud config set project cryptotronbot-secure

# Enable required APIs
gcloud services enable iam.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

#### 1.2 Configure OAuth 2.0

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to "APIs & Services" > "Credentials"
3. Create OAuth 2.0 Client ID
4. Add authorized redirect URIs:
   - `http://localhost:5000/auth/google/callback` (development)
   - `https://yourdomain.com/auth/google/callback` (production)

#### 1.3 Update Backend Authentication

```python
# requirements.txt additions
google-auth==2.23.0
google-auth-oauthlib==1.0.0
google-auth-httplib2==0.1.1
google-cloud-storage==2.10.0
google-cloud-secret-manager==2.16.0
google-cloud-sql-connector==1.2.0
```

### Phase 2: Database Migration to Cloud SQL

#### 2.1 Create Cloud SQL Instance

```bash
# Create PostgreSQL instance
gcloud sql instances create cryptotronbot-db \
    --database-version=POSTGRES_14 \
    --tier=db-f1-micro \
    --region=us-central1 \
    --root-password=your-secure-password

# Create database
gcloud sql databases create cryptotronbot_db \
    --instance=cryptotronbot-db

# Create user
gcloud sql users create cryptotronbot_user \
    --instance=cryptotronbot-db \
    --password=your-user-password
```

#### 2.2 Update Database Configuration

```python
# config.py
import os
from google.cloud import secretmanager

def get_secret(secret_id):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{os.getenv('GOOGLE_CLOUD_PROJECT')}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

class Config:
    # Database configuration
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://cryptotronbot_user:{get_secret('db-password')}"
        f"@/cryptotronbot_db?host=/cloudsql/{os.getenv('INSTANCE_CONNECTION_NAME')}"
    )
    
    # JWT configuration
    JWT_SECRET_KEY = get_secret('jwt-secret-key')
    
    # Google OAuth configuration
    GOOGLE_CLIENT_ID = get_secret('google-client-id')
    GOOGLE_CLIENT_SECRET = get_secret('google-client-secret')
```

### Phase 3: Enhanced User Model

```python
# models.py
from google.cloud import storage
import json

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    picture_url = db.Column(db.String(500), nullable=True)
    
    # Security fields
    is_premium_user = db.Column(db.Boolean, default=False)
    data_monetization_consent = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    login_count = db.Column(db.Integer, default=0)
    
    # Google IAM roles
    roles = db.Column(db.JSON, default=list)
    
    # Encrypted sensitive data
    encrypted_api_keys = db.Column(db.Text, nullable=True)  # Encrypted with Cloud KMS
    
    def has_role(self, role):
        return role in self.roles
    
    def add_role(self, role):
        if role not in self.roles:
            self.roles.append(role)
    
    def remove_role(self, role):
        if role in self.roles:
            self.roles.remove(role)
```

### Phase 4: Secure Data Storage

#### 4.1 Cloud Storage for User Data

```python
# utils/secure_storage.py
from google.cloud import storage
from google.cloud import kms_v1
import json

class SecureStorage:
    def __init__(self):
        self.storage_client = storage.Client()
        self.kms_client = kms_v1.KeyManagementServiceClient()
        self.bucket_name = "cryptotronbot-user-data"
        self.key_ring_name = "cryptotronbot-keys"
        
    def store_user_data(self, user_id, data):
        """Store encrypted user data in Cloud Storage"""
        bucket = self.storage_client.bucket(self.bucket_name)
        blob_name = f"users/{user_id}/data.json"
        blob = bucket.blob(blob_name)
        
        # Encrypt data before storing
        encrypted_data = self.encrypt_data(json.dumps(data))
        blob.upload_from_string(encrypted_data)
        
    def get_user_data(self, user_id):
        """Retrieve and decrypt user data"""
        bucket = self.storage_client.bucket(self.bucket_name)
        blob_name = f"users/{user_id}/data.json"
        blob = bucket.blob(blob_name)
        
        if not blob.exists():
            return None
            
        encrypted_data = blob.download_as_string()
        decrypted_data = self.decrypt_data(encrypted_data)
        return json.loads(decrypted_data)
    
    def encrypt_data(self, data):
        """Encrypt data using Cloud KMS"""
        key_name = f"projects/{self.project_id}/locations/global/keyRings/{self.key_ring_name}/cryptoKeys/user-data-key"
        
        request = kms_v1.EncryptRequest(
            name=key_name,
            plaintext=data.encode('utf-8')
        )
        
        response = self.kms_client.encrypt(request=request)
        return response.ciphertext
    
    def decrypt_data(self, encrypted_data):
        """Decrypt data using Cloud KMS"""
        key_name = f"projects/{self.project_id}/locations/global/keyRings/{self.key_ring_name}/cryptoKeys/user-data-key"
        
        request = kms_v1.DecryptRequest(
            name=key_name,
            ciphertext=encrypted_data
        )
        
        response = self.kms_client.decrypt(request=request)
        return response.plaintext.decode('utf-8')
```

#### 4.2 Secret Management

```python
# utils/secrets.py
from google.cloud import secretmanager

class SecretManager:
    def __init__(self):
        self.client = secretmanager.SecretManagerServiceClient()
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    
    def get_secret(self, secret_id):
        """Retrieve a secret from Google Secret Manager"""
        name = f"projects/{self.project_id}/secrets/{secret_id}/versions/latest"
        response = self.client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    
    def create_secret(self, secret_id, secret_value):
        """Create a new secret"""
        parent = f"projects/{self.project_id}"
        
        # Create the secret
        secret = {"replication": {"automatic": {}}}
        secret_name = f"{parent}/secrets/{secret_id}"
        self.client.create_secret(request={"parent": parent, "secret_id": secret_id, "secret": secret})
        
        # Add the secret version
        secret_version = {"data": secret_value.encode("UTF-8")}
        self.client.add_secret_version(request={"parent": secret_name, "payload": secret_version})
```

### Phase 5: IAM Roles and Permissions

#### 5.1 Define Custom Roles

```bash
# Create custom roles
cat > roles/cryptotronbot-user.yaml << EOF
title: "CryptotronBot User"
description: "Basic user permissions for CryptotronBot"
stage: "GA"
includedPermissions:
- storage.objects.get
- storage.objects.create
- storage.objects.update
- storage.objects.delete
- secretmanager.versions.access
EOF

cat > roles/cryptotronbot-premium.yaml << EOF
title: "CryptotronBot Premium User"
description: "Premium user permissions for CryptotronBot"
stage: "GA"
includedPermissions:
- storage.objects.get
- storage.objects.create
- storage.objects.update
- storage.objects.delete
- secretmanager.versions.access
- cloudkms.cryptoKeyVersions.useToDecrypt
- cloudkms.cryptoKeyVersions.useToEncrypt
EOF

# Create the roles
gcloud iam roles create cryptotronbot.user --project=cryptotronbot-secure --file=roles/cryptotronbot-user.yaml
gcloud iam roles create cryptotronbot.premium --project=cryptotronbot-secure --file=roles/cryptotronbot-premium.yaml
```

#### 5.2 Service Account Management

```python
# utils/iam_manager.py
from google.cloud import iam_admin_v1
from google.cloud import resourcemanager_v3

class IAMManager:
    def __init__(self):
        self.iam_client = iam_admin_v1.IAMClient()
        self.resource_client = resourcemanager_v3.ProjectsClient()
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    
    def assign_user_role(self, user_email, role):
        """Assign a role to a user"""
        member = f"user:{user_email}"
        role_name = f"projects/{self.project_id}/roles/{role}"
        
        policy = self.iam_client.get_iam_policy(request={"resource": f"projects/{self.project_id}"})
        
        # Add the binding
        binding = policy.bindings.add()
        binding.role = role_name
        binding.members.append(member)
        
        self.iam_client.set_iam_policy(request={
            "resource": f"projects/{self.project_id}",
            "policy": policy
        })
    
    def create_service_account(self, name, display_name):
        """Create a service account for the application"""
        service_account = self.iam_client.create_service_account(request={
            "name": f"projects/{self.project_id}",
            "account_id": name,
            "service_account": {
                "display_name": display_name,
                "description": f"Service account for {display_name}"
            }
        })
        return service_account
```

### Phase 6: Updated Authentication Flow

```python
# auth/google_auth.py
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests
import os

class GoogleAuth:
    def __init__(self):
        self.client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    
    def get_authorization_url(self):
        """Get Google OAuth authorization URL"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [os.getenv('GOOGLE_REDIRECT_URI')]
                }
            },
            scopes=['openid', 'email', 'profile']
        )
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        return authorization_url, state
    
    def verify_token(self, token):
        """Verify Google ID token"""
        try:
            idinfo = id_token.verify_oauth2_token(
                token, 
                requests.Request(), 
                self.client_id
            )
            
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')
            
            return idinfo
        except ValueError:
            return None
```

### Phase 7: Security Monitoring and Logging

#### 7.1 Cloud Logging Integration

```python
# utils/logging.py
from google.cloud import logging
import logging as python_logging

class SecurityLogger:
    def __init__(self):
        self.client = logging.Client()
        self.logger = self.client.logger('cryptotronbot-security')
    
    def log_login_attempt(self, user_email, success, ip_address, user_agent):
        """Log login attempts for security monitoring"""
        self.logger.log_struct({
            'event': 'login_attempt',
            'user_email': user_email,
            'success': success,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def log_data_access(self, user_id, data_type, action):
        """Log data access for audit trails"""
        self.logger.log_struct({
            'event': 'data_access',
            'user_id': user_id,
            'data_type': data_type,
            'action': action,
            'timestamp': datetime.utcnow().isoformat()
        })
```

#### 7.2 Security Alerts

```python
# utils/security_alerts.py
from google.cloud import monitoring_v3
from google.cloud import error_reporting

class SecurityAlerts:
    def __init__(self):
        self.monitoring_client = monitoring_v3.MetricServiceClient()
        self.error_client = error_reporting.Client()
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    
    def create_alert_policy(self, name, condition, notification_channel):
        """Create alert policy for security events"""
        alert_policy = {
            "display_name": name,
            "conditions": [condition],
            "notification_channels": [notification_channel],
            "documentation": {
                "content": "Security alert for CryptotronBot",
                "mime_type": "text/markdown"
            }
        }
        
        # Create the alert policy
        parent = f"projects/{self.project_id}"
        self.monitoring_client.create_alert_policy(request={
            "name": parent,
            "alert_policy": alert_policy
        })
    
    def report_security_incident(self, error_message, severity='ERROR'):
        """Report security incidents to Error Reporting"""
        self.error_client.report(error_message, severity=severity)
```

## Deployment Configuration

### Environment Variables

```bash
# .env file
GOOGLE_CLOUD_PROJECT=cryptotronbot-secure
GOOGLE_CLIENT_ID=your-oauth-client-id
GOOGLE_CLIENT_SECRET=your-oauth-client-secret
GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/google/callback
INSTANCE_CONNECTION_NAME=cryptotronbot-secure:us-central1:cryptotronbot-db
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

### Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.9-slim

# Install Google Cloud SDK
RUN apt-get update && apt-get install -y curl gnupg
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
RUN apt-get update && apt-get install -y google-cloud-sdk

# Copy application code
COPY . /app
WORKDIR /app

# Install Python dependencies
RUN pip install -r requirements.txt

# Run the application
CMD ["python", "app.py"]
```

## Security Best Practices

### 1. **Principle of Least Privilege**
- Only grant necessary permissions to users and service accounts
- Use custom roles instead of predefined roles when possible
- Regularly review and audit permissions

### 2. **Data Encryption**
- Encrypt data at rest using Cloud KMS
- Encrypt data in transit using TLS
- Use customer-managed encryption keys for sensitive data

### 3. **Access Monitoring**
- Enable Cloud Audit Logs
- Set up alerts for suspicious activities
- Monitor failed authentication attempts

### 4. **Regular Security Updates**
- Keep dependencies updated
- Regularly rotate secrets and keys
- Conduct security assessments

### 5. **Compliance Considerations**
- Implement data retention policies
- Ensure GDPR compliance for EU users
- Document data processing activities

## Migration Checklist

- [ ] Set up Google Cloud Project
- [ ] Enable required APIs
- [ ] Configure OAuth 2.0 credentials
- [ ] Create Cloud SQL instance
- [ ] Set up Secret Manager
- [ ] Create Cloud Storage buckets
- [ ] Configure Cloud KMS
- [ ] Update application code
- [ ] Test authentication flow
- [ ] Migrate existing user data
- [ ] Set up monitoring and alerts
- [ ] Deploy to production
- [ ] Update documentation

## Cost Considerations

- **Cloud SQL**: ~$25-50/month for small instance
- **Cloud Storage**: ~$0.02/GB/month
- **Secret Manager**: ~$0.06/10,000 operations
- **Cloud KMS**: ~$0.03/10,000 operations
- **Cloud Logging**: Free tier available

## Next Steps

1. **Start with Phase 1**: Implement Google OAuth authentication
2. **Test thoroughly**: Ensure all functionality works with new auth system
3. **Gradually migrate**: Move data to cloud services incrementally
4. **Monitor performance**: Track costs and performance metrics
5. **Train team**: Ensure all developers understand the new security model

This integration will significantly improve your application's security posture while providing enterprise-grade features for user management and data protection. 