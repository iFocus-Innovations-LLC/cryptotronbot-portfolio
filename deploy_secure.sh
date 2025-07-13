#!/bin/bash

# CryptotronBot Secure Deployment Script
# This script sets up Google Cloud infrastructure for enhanced security

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="cryptotronbot-secure"
REGION="us-central1"
ZONE="us-central1-a"
INSTANCE_NAME="cryptotronbot-db"
BUCKET_NAME="cryptotronbot-user-data"
KEY_RING_NAME="cryptotronbot-keys"
KEY_NAME="user-data-key"

echo -e "${BLUE}🚀 Starting CryptotronBot Secure Deployment${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ Google Cloud SDK is not installed. Please install it first:${NC}"
    echo "https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${YELLOW}⚠️  You are not authenticated with Google Cloud. Please run:${NC}"
    echo "gcloud auth login"
    exit 1
fi

echo -e "${GREEN}✅ Google Cloud SDK is installed and authenticated${NC}"

# Step 1: Create or select project
echo -e "${BLUE}📋 Step 1: Setting up Google Cloud Project${NC}"

# Check if project exists
if gcloud projects describe $PROJECT_ID &> /dev/null; then
    echo -e "${GREEN}✅ Project $PROJECT_ID already exists${NC}"
else
    echo -e "${YELLOW}📝 Creating new project: $PROJECT_ID${NC}"
    gcloud projects create $PROJECT_ID --name="CryptotronBot Secure"
fi

# Set the project
gcloud config set project $PROJECT_ID
echo -e "${GREEN}✅ Project set to: $PROJECT_ID${NC}"

# Step 2: Enable required APIs
echo -e "${BLUE}🔧 Step 2: Enabling required APIs${NC}"

APIS=(
    "iam.googleapis.com"
    "cloudresourcemanager.googleapis.com"
    "sqladmin.googleapis.com"
    "storage.googleapis.com"
    "secretmanager.googleapis.com"
    "cloudkms.googleapis.com"
    "logging.googleapis.com"
    "monitoring.googleapis.com"
    "errorreporting.googleapis.com"
)

for api in "${APIS[@]}"; do
    echo -e "${YELLOW}📝 Enabling $api${NC}"
    gcloud services enable $api
done

echo -e "${GREEN}✅ All required APIs enabled${NC}"

# Step 3: Create Cloud SQL instance
echo -e "${BLUE}🗄️  Step 3: Setting up Cloud SQL Database${NC}"

# Check if instance exists
if gcloud sql instances describe $INSTANCE_NAME &> /dev/null; then
    echo -e "${GREEN}✅ Cloud SQL instance $INSTANCE_NAME already exists${NC}"
else
    echo -e "${YELLOW}📝 Creating Cloud SQL instance: $INSTANCE_NAME${NC}"
    
    # Generate a secure password
    DB_PASSWORD=$(openssl rand -base64 32)
    
    gcloud sql instances create $INSTANCE_NAME \
        --database-version=POSTGRES_14 \
        --tier=db-f1-micro \
        --region=$REGION \
        --root-password="$DB_PASSWORD" \
        --storage-type=SSD \
        --storage-size=10GB \
        --backup-start-time="02:00" \
        --maintenance-window-day=SUN \
        --maintenance-window-hour=02 \
        --availability-type=zonal \
        --backup-configuration-enabled \
        --backup-configuration-binary-logging-enabled
    
    echo -e "${GREEN}✅ Cloud SQL instance created${NC}"
    echo -e "${YELLOW}📝 Root password: $DB_PASSWORD${NC}"
    echo -e "${YELLOW}⚠️  Please save this password securely!${NC}"
fi

# Create database
echo -e "${YELLOW}📝 Creating database: cryptotronbot_db${NC}"
gcloud sql databases create cryptotronbot_db --instance=$INSTANCE_NAME || echo -e "${GREEN}✅ Database already exists${NC}"

# Create user
echo -e "${YELLOW}📝 Creating database user: cryptotronbot_user${NC}"
USER_PASSWORD=$(openssl rand -base64 32)
gcloud sql users create cryptotronbot_user --instance=$INSTANCE_NAME --password="$USER_PASSWORD" || echo -e "${GREEN}✅ User already exists${NC}"

echo -e "${GREEN}✅ Database setup complete${NC}"
echo -e "${YELLOW}📝 User password: $USER_PASSWORD${NC}"

# Step 4: Create Cloud Storage bucket
echo -e "${BLUE}📦 Step 4: Setting up Cloud Storage${NC}"

if gsutil ls -b gs://$BUCKET_NAME &> /dev/null; then
    echo -e "${GREEN}✅ Storage bucket $BUCKET_NAME already exists${NC}"
else
    echo -e "${YELLOW}📝 Creating storage bucket: $BUCKET_NAME${NC}"
    gsutil mb -l $REGION gs://$BUCKET_NAME
    
    # Set bucket permissions
    gsutil iam ch allUsers:objectViewer gs://$BUCKET_NAME
    gsutil iam ch allUsers:objectCreator gs://$BUCKET_NAME
fi

echo -e "${GREEN}✅ Cloud Storage setup complete${NC}"

# Step 5: Set up Cloud KMS
echo -e "${BLUE}🔐 Step 5: Setting up Cloud KMS${NC}"

# Create key ring
echo -e "${YELLOW}📝 Creating key ring: $KEY_RING_NAME${NC}"
gcloud kms keyrings create $KEY_RING_NAME --location=global || echo -e "${GREEN}✅ Key ring already exists${NC}"

# Create encryption key
echo -e "${YELLOW}📝 Creating encryption key: $KEY_NAME${NC}"
gcloud kms keys create $KEY_NAME \
    --keyring=$KEY_RING_NAME \
    --location=global \
    --purpose=encryption \
    --protection-level=software || echo -e "${GREEN}✅ Key already exists${NC}"

echo -e "${GREEN}✅ Cloud KMS setup complete${NC}"

# Step 6: Set up Secret Manager
echo -e "${BLUE}🔑 Step 6: Setting up Secret Manager${NC}"

# Create secrets
SECRETS=(
    "db-password"
    "jwt-secret-key"
    "google-client-id"
    "google-client-secret"
)

for secret in "${SECRETS[@]}"; do
    echo -e "${YELLOW}📝 Creating secret: $secret${NC}"
    echo "placeholder-value" | gcloud secrets create $secret --data-file=- || echo -e "${GREEN}✅ Secret already exists${NC}"
done

echo -e "${GREEN}✅ Secret Manager setup complete${NC}"

# Step 7: Create service account
echo -e "${BLUE}👤 Step 7: Creating Service Account${NC}"

SERVICE_ACCOUNT_NAME="cryptotronbot-app"
SERVICE_ACCOUNT_EMAIL="$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com"

# Create service account
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
    --display-name="CryptotronBot Application" \
    --description="Service account for CryptotronBot application" || echo -e "${GREEN}✅ Service account already exists${NC}"

# Grant necessary permissions
echo -e "${YELLOW}📝 Granting permissions to service account${NC}"

# Cloud SQL permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/cloudsql.client"

# Storage permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/storage.objectViewer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/storage.objectCreator"

# KMS permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/cloudkms.cryptoKeyEncrypterDecrypter"

# Secret Manager permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/secretmanager.secretAccessor"

# Logging permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/logging.logWriter"

echo -e "${GREEN}✅ Service account setup complete${NC}"

# Step 8: Create service account key
echo -e "${BLUE}🔑 Step 8: Creating Service Account Key${NC}"

KEY_FILE="cryptotronbot-service-account.json"
if [ ! -f "$KEY_FILE" ]; then
    echo -e "${YELLOW}📝 Creating service account key file${NC}"
    gcloud iam service-accounts keys create $KEY_FILE \
        --iam-account=$SERVICE_ACCOUNT_EMAIL
    
    echo -e "${GREEN}✅ Service account key created: $KEY_FILE${NC}"
    echo -e "${YELLOW}⚠️  Keep this file secure and never commit it to version control!${NC}"
else
    echo -e "${GREEN}✅ Service account key already exists: $KEY_FILE${NC}"
fi

# Step 9: Create environment file
echo -e "${BLUE}📝 Step 9: Creating Environment Configuration${NC}"

cat > .env.secure << EOF
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=$PROJECT_ID
GOOGLE_APPLICATION_CREDENTIALS=./$KEY_FILE

# Database Configuration
INSTANCE_CONNECTION_NAME=$PROJECT_ID:$REGION:$INSTANCE_NAME
DATABASE_URL=postgresql://cryptotronbot_user:$USER_PASSWORD@/cryptotronbot_db?host=/cloudsql/$PROJECT_ID:$REGION:$INSTANCE_NAME

# Cloud Storage Configuration
CLOUD_STORAGE_BUCKET=$BUCKET_NAME

# Cloud KMS Configuration
KMS_KEY_RING=$KEY_RING_NAME
KMS_KEY_NAME=$KEY_NAME

# OAuth Configuration (You need to set these manually)
GOOGLE_CLIENT_ID=your-oauth-client-id
GOOGLE_CLIENT_SECRET=your-oauth-client-secret
GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/google/callback

# Security Configuration
JWT_SECRET_KEY=your-jwt-secret-key
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# Application Configuration
FLASK_ENV=production
FLASK_APP=app.py
EOF

echo -e "${GREEN}✅ Environment file created: .env.secure${NC}"

# Step 10: Create deployment script
echo -e "${BLUE}📋 Step 10: Creating Application Deployment Script${NC}"

cat > deploy_app.sh << 'EOF'
#!/bin/bash

# Deploy CryptotronBot application

set -e

echo "🚀 Deploying CryptotronBot application..."

# Install dependencies
pip install -r requirements_secure.txt

# Set up environment
export $(cat .env.secure | xargs)

# Run database migrations
flask db upgrade

# Start the application
python app.py
EOF

chmod +x deploy_app.sh

echo -e "${GREEN}✅ Deployment script created: deploy_app.sh${NC}"

# Step 11: Create monitoring setup
echo -e "${BLUE}📊 Step 11: Setting up Monitoring and Logging${NC}"

# Create log sink
echo -e "${YELLOW}📝 Creating log sink${NC}"
gcloud logging sinks create cryptotronbot-logs \
    storage.googleapis.com/$BUCKET_NAME/logs \
    --log-filter="resource.type=gce_instance" || echo -e "${GREEN}✅ Log sink already exists${NC}"

# Create alert policy
echo -e "${YELLOW}📝 Creating alert policy${NC}"
cat > alert-policy.yaml << EOF
displayName: "CryptotronBot Security Alerts"
conditions:
- displayName: "Failed Authentication Attempts"
  conditionThreshold:
    filter: 'resource.type="gce_instance" AND logName="projects/$PROJECT_ID/logs/cryptotronbot-security"'
    comparison: COMPARISON_GREATER_THAN
    thresholdValue: 10
    duration: 300s
notificationChannels:
- projects/$PROJECT_ID/notificationChannels/CHANNEL_ID
documentation:
  content: "Security alert for CryptotronBot - Multiple failed authentication attempts detected"
  mimeType: "text/markdown"
EOF

echo -e "${GREEN}✅ Monitoring setup complete${NC}"

# Final summary
echo -e "${BLUE}🎉 Deployment Summary${NC}"
echo -e "${GREEN}✅ Google Cloud Project: $PROJECT_ID${NC}"
echo -e "${GREEN}✅ Cloud SQL Instance: $INSTANCE_NAME${NC}"
echo -e "${GREEN}✅ Storage Bucket: $BUCKET_NAME${NC}"
echo -e "${GREEN}✅ KMS Key Ring: $KEY_RING_NAME${NC}"
echo -e "${GREEN}✅ Service Account: $SERVICE_ACCOUNT_EMAIL${NC}"
echo -e "${GREEN}✅ Service Account Key: $KEY_FILE${NC}"
echo -e "${GREEN}✅ Environment File: .env.secure${NC}"
echo -e "${GREEN}✅ Deployment Script: deploy_app.sh${NC}"

echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "1. Set up Google OAuth 2.0 credentials in Google Cloud Console"
echo "2. Update GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env.secure"
echo "3. Update GOOGLE_REDIRECT_URI with your domain"
echo "4. Set up your domain and SSL certificate"
echo "5. Run: ./deploy_app.sh"

echo -e "${YELLOW}⚠️  Important Security Notes:${NC}"
echo "- Keep the service account key file secure"
echo "- Never commit .env.secure or $KEY_FILE to version control"
echo "- Regularly rotate secrets and keys"
echo "- Monitor logs for security events"
echo "- Set up alerts for suspicious activities"

echo -e "${GREEN}🎉 Secure deployment setup complete!${NC}" 