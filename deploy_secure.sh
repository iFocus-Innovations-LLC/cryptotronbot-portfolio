#!/bin/bash

# CryptotronBot Secure Deployment Script (Revised)
# This script sets up Google Cloud infrastructure with enhanced security practices.

set -e # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Configuration ---
PROJECT_ID="cryptotronbot-secure"
REGION="us-central1"
ZONE="us-central1-a" # Used for some zonal resources, SQL instance is regional.
INSTANCE_NAME="cryptotronbot-db"
BUCKET_NAME="cryptotronbot-user-data" # Private bucket for application data
KEY_RING_NAME="cryptotronbot-keys"
KEY_NAME="user-data-key"

# Secret Manager secret names (for DB passwords)
DB_ROOT_PASSWORD_SECRET_NAME="cryptotronbot-db-root-password"
DB_USER_PASSWORD_SECRET_NAME="cryptotronbot-db-user-password"

echo -e "${BLUE}🚀 Starting CryptotronBot Secure Deployment (Revised Script)${NC}"

# --- Prerequisites Checks ---
echo -e "${BLUE}🔍 Checking Google Cloud SDK and Authentication...${NC}"
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ Google Cloud SDK is not installed. Please install it first:${NC}"
    echo "https://cloud.google.com/sdk/docs/install"
    exit 1
fi

if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${YELLOW}⚠️  You are not authenticated with Google Cloud. Please run:${NC}"
    echo "gcloud auth login"
    exit 1
fi
echo -e "${GREEN}✅ Google Cloud SDK is installed and authenticated.${NC}"

# --- Step 1: Create or select project ---
echo -e "${BLUE}📋 Step 1: Setting up Google Cloud Project${NC}"
if gcloud projects describe $PROJECT_ID &> /dev/null; then
    echo -e "${GREEN}✅ Project $PROJECT_ID already exists.${NC}"
else
    echo -e "${YELLOW}📝 Creating new project: $PROJECT_ID${NC}"
    gcloud projects create $PROJECT_ID --name="CryptotronBot Secure"
fi

gcloud config set project $PROJECT_ID
echo -e "${GREEN}✅ Project set to: $PROJECT_ID${NC}"

# --- Step 2: Enable required APIs ---
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
    "compute.googleapis.com" # Required for VPC network related commands (e.g., if you were to create a network)
)

for api in "${APIS[@]}"; do
    echo -e "${YELLOW}📝 Enabling $api${NC}"
    gcloud services enable $api
done
echo -e "${GREEN}✅ All required APIs enabled.${NC}"

# --- Step 3: Create Cloud SQL instance ---
echo -e "${BLUE}🗄️  Step 3: Setting up Cloud SQL Database${NC}"

# Generate secure passwords
DB_ROOT_PASSWORD=$(openssl rand -base64 32)
DB_USER_PASSWORD=$(openssl rand -base64 32)

# Check if instance exists
if gcloud sql instances describe $INSTANCE_NAME &> /dev/null; then
    echo -e "${GREEN}✅ Cloud SQL instance $INSTANCE_NAME already exists.${NC}"
else
    echo -e "${YELLOW}📝 Creating Cloud SQL instance: $INSTANCE_NAME${NC}"
    echo -e "${YELLOW}ℹ️  Using 'db-f1-micro' tier for demonstration. Consider a larger tier for production.${NC}"
    echo -e "${YELLOW}ℹ️  Cloud SQL will be deployed with private IP only. Ensure your application is in the same VPC or connected via VPN/Interconnect.${NC}"

    gcloud sql instances create $INSTANCE_NAME \
        --database-version=POSTGRES_14 \
        --tier=db-f1-micro \
        --region=$REGION \
        --root-password="$DB_ROOT_PASSWORD" \
        --storage-type=SSD \
        --storage-size=10GB \
        --backup-start-time="02:00" \
        --maintenance-window-day=SUN \
        --maintenance-window-hour=02 \
        --availability-type=REGIONAL \
        --no-enable-external-ip \
        --backup-configuration-enabled \
        --backup-configuration-binary-logging-enabled

    echo -e "${GREEN}✅ Cloud SQL instance created.${NC}"

    # Store root password in Secret Manager
    echo -e "${YELLOW}📝 Storing Cloud SQL root password in Secret Manager: $DB_ROOT_PASSWORD_SECRET_NAME${NC}"
    echo -n "$DB_ROOT_PASSWORD" | gcloud secrets create $DB_ROOT_PASSWORD_SECRET_NAME \
        --data-file=- \
        --project=$PROJECT_ID || gcloud secrets versions add $DB_ROOT_PASSWORD_SECRET_NAME \
        --data-file=- \
        --project=$PROJECT_ID
    echo -e "${GREEN}✅ Cloud SQL root password securely stored in Secret Manager.${NC}"
fi

# Create database
echo -e "${YELLOW}📝 Creating database: cryptotronbot_db${NC}"
gcloud sql databases create cryptotronbot_db --instance=$INSTANCE_NAME \
    --project=$PROJECT_ID || echo -e "${GREEN}✅ Database already exists.${NC}"

# Create user
echo -e "${YELLOW}📝 Creating database user: cryptotronbot_user${NC}"
gcloud sql users create cryptotronbot_user --instance=$INSTANCE_NAME \
    --password="$DB_USER_PASSWORD" \
    --host="%" \
    --project=$PROJECT_ID || echo -e "${GREEN}✅ User already exists.${NC}"

# Store user password in Secret Manager
echo -e "${YELLOW}📝 Storing Cloud SQL user password in Secret Manager: $DB_USER_PASSWORD_SECRET_NAME${NC}"
echo -n "$DB_USER_PASSWORD" | gcloud secrets create $DB_USER_PASSWORD_SECRET_NAME \
    --data-file=- \
    --project=$PROJECT_ID || gcloud secrets versions add $DB_USER_PASSWORD_SECRET_NAME \
    --data-file=- \
    --project=$PROJECT_ID
echo -e "${GREEN}✅ Cloud SQL user password securely stored in Secret Manager.${NC}"

echo -e "${GREEN}✅ Database setup complete. Passwords are in Secret Manager.${NC}"

# --- Step 4: Create Cloud Storage bucket ---
echo -e "${BLUE}📦 Step 4: Setting up Cloud Storage${NC}"

if gsutil ls -b gs://$BUCKET_NAME &> /dev/null; then
    echo -e "${GREEN}✅ Storage bucket $BUCKET_NAME already exists.${NC}"
else
    echo -e "${YELLOW}📝 Creating storage bucket: $BUCKET_NAME${NC}"
    gsutil mb -l $REGION gs://$BUCKET_NAME
    echo -e "${GREEN}✅ Storage bucket created. By default, it's private.${NC}"
    echo -e "${YELLOW}⚠️  Note: This script DOES NOT make the bucket publicly accessible.${NC}"
    echo -e "${YELLOW}    Access will be controlled via IAM on the bucket for specific service accounts.${NC}"
fi
echo -e "${GREEN}✅ Cloud Storage setup complete.${NC}"

# --- Step 5: Set up Cloud KMS ---
echo -e "${BLUE}🔐 Step 5: Setting up Cloud KMS${NC}"

# Create key ring
echo -e "${YELLOW}📝 Creating key ring: $KEY_RING_NAME${NC}"
gcloud kms keyrings create $KEY_RING_NAME --location=global \
    --project=$PROJECT_ID || echo -e "${GREEN}✅ Key ring already exists.${NC}"

# Create encryption key
echo -e "${YELLOW}📝 Creating encryption key: $KEY_NAME${NC}"
gcloud kms keys create $KEY_NAME \
    --keyring=$KEY_RING_NAME \
    --location=global \
    --purpose=encryption \
    --protection-level=software \
    --project=$PROJECT_ID || echo -e "${GREEN}✅ Key already exists.${NC}"
echo -e "${GREEN}✅ Cloud KMS setup complete.${NC}"

# --- Step 6: Set up Secret Manager for application secrets ---
echo -e "${BLUE}🔑 Step 6: Setting up Secret Manager for application secrets${NC}"

SECRETS=(
    "jwt-secret-key"
    "google-client-id"
    "google-client-secret"
)

for secret in "${SECRETS[@]}"; do
    echo -e "${YELLOW}📝 Initializing secret: $secret${NC}"
    echo "placeholder-value" | gcloud secrets create $secret \
        --data-file=- \
        --project=$PROJECT_ID || echo -e "${GREEN}✅ Secret $secret already exists.${NC}"
    echo -e "${YELLOW}⚠️  Remember to update '$secret' in Secret Manager with a real value!${NC}"
done
echo -e "${GREEN}✅ Secret Manager placeholder secrets initialized.${NC}"

# --- Step 7: Create service account and grant permissions ---
echo -e "${BLUE}👤 Step 7: Creating Service Account and granting permissions${NC}"

SERVICE_ACCOUNT_NAME="cryptotronbot-app"
SERVICE_ACCOUNT_EMAIL="$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com"

# Create service account
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
    --display-name="CryptotronBot Application" \
    --description="Service account for CryptotronBot application" \
    --project=$PROJECT_ID || echo -e "${GREEN}✅ Service account already exists.${NC}"

# Grant necessary permissions (least privilege where possible)
echo -e "${YELLOW}📝 Granting permissions to service account: $SERVICE_ACCOUNT_EMAIL${NC}"

# Cloud SQL permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/cloudsql.client" \
    --project=$PROJECT_ID --quiet # --quiet to avoid interactive prompt if binding exists

# Storage permissions (BUCKET-SPECIFIC)
# Grant access only to the designated bucket, not project-wide
gsutil iam ch serviceAccount:$SERVICE_ACCOUNT_EMAIL:objectViewer gs://$BUCKET_NAME \
    || echo -e "${GREEN}✅ Object viewer on bucket already granted to SA.${NC}"
gsutil iam ch serviceAccount:$SERVICE_ACCOUNT_EMAIL:objectCreator gs://$BUCKET_NAME \
    || echo -e "${GREEN}✅ Object creator on bucket already granted to SA.${NC}"

# KMS permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/cloudkms.cryptoKeyEncrypterDecrypter" \
    --project=$PROJECT_ID --quiet

# Secret Manager permissions (for accessing secrets)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID --quiet

# Logging permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/logging.logWriter" \
    --project=$PROJECT_ID --quiet

echo -e "${GREEN}✅ Service account setup complete with refined permissions.${NC}"

# --- Step 8: Create service account key (Optional & Highly Recommended AGAINST for Production) ---
echo -e "${BLUE}🔑 Step 8: Creating Service Account Key (Optional - for local dev only)${NC}"

KEY_FILE="cryptotronbot-service-account.json"
echo -e "${YELLOW}⚠️  WARNING: For production deployments on GCP (e.g., GKE, Cloud Run, GCE),${NC}"
echo -e "${YELLOW}    it's HIGHLY recommended to use Workload Identity or Application Default Credentials (ADC) without a key file.${NC}"
echo -e "${YELLOW}    Creating a local key file is primarily for local development/testing or specific external integrations.${NC}"
echo -e "${YELLOW}    If you do not need a local key file, you can skip this step.${NC}"

read -p "Do you want to create a local service account key file for development? (y/N): " create_key_file_choice
if [[ "$create_key_file_choice" =~ ^[Yy]$ ]]; then
    if [ ! -f "$KEY_FILE" ]; then
        echo -e "${YELLOW}📝 Creating service account key file: $KEY_FILE${NC}"
        gcloud iam service-accounts keys create $KEY_FILE \
            --iam-account=$SERVICE_ACCOUNT_EMAIL \
            --project=$PROJECT_ID
        echo -e "${GREEN}✅ Service account key created: $KEY_FILE${NC}"
        echo -e "${YELLOW}⚠️  CRITICAL: Keep this file SECURE and NEVER COMMIT IT TO VERSION CONTROL!${NC}"
    else
        echo -e "${GREEN}✅ Service account key already exists: $KEY_FILE${NC}"
    fi
else
    echo -e "${YELLOW}⏩ Skipping local service account key file creation.${NC}"
    KEY_FILE="" # Clear key file variable if not created
fi


# --- Step 9: Create environment file ---
echo -e "${BLUE}📝 Step 9: Creating Environment Configuration (.env.secure)${NC}"

cat > .env.secure << EOF
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=$PROJECT_ID
# GOOGLE_APPLICATION_CREDENTIALS is not needed if running on GCP with a service account
# attached or using Workload Identity. If running locally with a key file, uncomment and set:
# GOOGLE_APPLICATION_CREDENTIALS=./$KEY_FILE

# Database Configuration
# The application should retrieve passwords from Secret Manager at runtime.
INSTANCE_CONNECTION_NAME=$PROJECT_ID:$REGION:$INSTANCE_NAME
DB_HOST=/cloudsql/$PROJECT_ID:$REGION:$INSTANCE_NAME
DB_DATABASE=cryptotronbot_db
DB_USER=cryptotronbot_user
DB_PASSWORD_SECRET_NAME=$DB_USER_PASSWORD_SECRET_NAME

# Cloud Storage Configuration
CLOUD_STORAGE_BUCKET=$BUCKET_NAME

# Cloud KMS Configuration
KMS_KEY_RING=$KEY_RING_NAME
KMS_KEY_NAME=$KEY_NAME

# OAuth Configuration (Retrieve from Secret Manager)
GOOGLE_CLIENT_ID_SECRET_NAME=google-client-id
GOOGLE_CLIENT_SECRET_SECRET_NAME=google-client-secret
GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/google/callback # UPDATE THIS!

# Security Configuration (Retrieve from Secret Manager)
JWT_SECRET_KEY_SECRET_NAME=jwt-secret-key
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com # UPDATE THIS!

# Application Configuration
FLASK_ENV=production
FLASK_APP=app.py
EOF

echo -e "${GREEN}✅ Environment file created: .env.secure${NC}"
echo -e "${YELLOW}⚠️  Remember: Application should fetch sensitive values (like DB passwords, JWT secret, OAuth credentials) from Secret Manager at runtime.${NC}"

# --- Step 10: Create deployment script ---
echo -e "${BLUE}📋 Step 10: Creating Application Deployment Script${NC}"

cat > deploy_app.sh << 'EOF'
#!/bin/bash

# Deploy CryptotronBot application

set -e

echo "🚀 Deploying CryptotronBot application..."

# --- IMPORTANT: Your application must be configured to fetch sensitive environment variables
# from Google Secret Manager at runtime using the service account's permissions. ---
#
# Example (conceptual, your app's actual code will vary):
# export DB_PASSWORD=$(gcloud secrets access cryptotronbot-db-user-password --project=<YOUR_PROJECT_ID> --version=latest)
# export JWT_SECRET_KEY=$(gcloud secrets access jwt-secret-key --project=<YOUR_PROJECT_ID> --version=latest)
# etc.

# Load non-sensitive configurations from .env.secure
# Ensure your application is designed to retrieve sensitive values from Secret Manager.
if [ -f ".env.secure" ]; then
    echo "Loading non-sensitive variables from .env.secure"
    # Filter out lines that refer to secret manager names, which the app will handle
    grep -Ev '(^#|SECRET_NAME=|GOOGLE_CLIENT_ID=|GOOGLE_CLIENT_SECRET=|JWT_SECRET_KEY=)' .env.secure | xargs -I {} bash -c 'export "$@"' _ {}
else
    echo "WARNING: .env.secure not found. Ensure environment variables are set."
fi


# Install dependencies (assuming a secure requirements file)
pip install -r requirements_secure.txt

# Run database migrations (assuming flask-migrate setup)
flask db upgrade

# Start the application
python app.py
EOF

chmod +x deploy_app.sh

echo -e "${GREEN}✅ Deployment script created: deploy_app.sh${NC}"
echo -e "${YELLOW}⚠️  Review 'deploy_app.sh' and your application code to ensure secrets are fetched from Secret Manager.${NC}"

# --- Step 11: Create monitoring setup ---
echo -e "${BLUE}📊 Step 11: Setting up Monitoring and Logging${NC}"

# Create log sink
echo -e "${YELLOW}📝 Creating log sink${NC}"
gcloud logging sinks create cryptotronbot-logs \
    storage.googleapis.com/$BUCKET_NAME/logs \
    --log-filter="resource.type=gce_instance" \
    --project=$PROJECT_ID || echo -e "${GREEN}✅ Log sink already exists.${NC}"

# Create alert policy
echo -e "${YELLOW}📝 Creating alert policy placeholder${NC}"
cat > alert-policy.yaml << EOF
displayName: "CryptotronBot Security Alerts"
conditions:
- displayName: "Failed Authentication Attempts"
  conditionThreshold:
    filter: 'resource.type="gce_instance" AND logName="projects/$PROJECT_ID/logs/cryptotronbot-security"'
    # IMPORTANT: Ensure your application logs failed authentication attempts to 'cryptotronbot-security'
    # logName for this alert to function correctly.
    comparison: COMPARISON_GREATER_THAN
    thresholdValue: 10
    duration: 300s
notificationChannels:
- projects/$PROJECT_ID/notificationChannels/YOUR_NOTIFICATION_CHANNEL_ID # <<<< CRITICAL: REPLACE THIS!
documentation:
  content: "Security alert for CryptotronBot - Multiple failed authentication attempts detected. Check logs for details."
  mimeType: "text/markdown"
EOF
echo -e "${YELLOW}⚠️  The alert policy requires a valid notification channel ID. Please create one in GCP Monitoring and update 'alert-policy.yaml'.${NC}"
echo -e "${GREEN}✅ Monitoring setup placeholder created.${NC}"

# --- Final summary ---
echo -e "${BLUE}🎉 Deployment Summary${NC}"
echo -e "${GREEN}✅ Google Cloud Project: $PROJECT_ID${NC}"
echo -e "${GREEN}✅ Cloud SQL Instance: $INSTANCE_NAME (Regional, Private IP)${NC}"
echo -e "${GREEN}✅ Storage Bucket: $BUCKET_NAME (Private)${NC}"
echo -e "${GREEN}✅ KMS Key Ring: $KEY_RING_NAME${NC}"
echo -e "${GREEN}✅ Service Account: $SERVICE_ACCOUNT_EMAIL (Least privilege applied to Storage)${NC}"
if [[ "$create_key_file_choice" =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}✅ Local Service Account Key: $KEY_FILE (For Dev Only!)${NC}"
else
    echo -e "${YELLOW}⏩ No local service account key file created. Good for production.${NC}"
fi
echo -e "${GREEN}✅ Environment File: .env.secure (References Secret Manager)${NC}"
echo -e "${GREEN}✅ Deployment Script: deploy_app.sh${NC}"
echo -e "${GREEN}✅ Cloud SQL Passwords securely stored in Secret Manager: $DB_ROOT_PASSWORD_SECRET_NAME, $DB_USER_PASSWORD_SECRET_NAME${NC}"

echo -e "${YELLOW}📋 Next Steps and CRITICAL Security Actions:${NC}"
echo "1.  **Review and Update Secrets:** Update 'jwt-secret-key', 'google-client-id', 'google-client-secret' secrets in Secret Manager with real values."
echo "    ${YELLOW}gcloud secrets versions add jwt-secret-key --data-file=/path/to/your/secret.txt --project=$PROJECT_ID${NC}"
echo "2.  **Application Configuration:** Modify your CryptotronBot application code to retrieve sensitive configurations (DB passwords, JWT secret, OAuth credentials) directly from Google Secret Manager at runtime using the assigned service account's permissions."
echo "    (e.g., using Google Cloud Client Libraries for Python, Node.js, etc.)"
echo "3.  **Update .env.secure:** Ensure 'GOOGLE_REDIRECT_URI' and 'CORS_ORIGINS' are correct for your domain."
echo "4.  **Notification Channel:** Create a notification channel in Google Cloud Monitoring (e.g., email, Pub/Sub) and update 'alert-policy.yaml' with its ID."
echo "    ${YELLOW}gcloud monitoring channels create --display-name='My Email Channel' --type=email --labels=email_address='your-email@example.com'${NC}"
echo "    Then get its ID: ${YELLOW}gcloud monitoring channels list --format='value(name)'${NC} and update the YAML."
echo "5.  **Log Source for Alerts:** Verify your application logs to 'projects/$PROJECT_ID/logs/cryptotronbot-security' for the security alert to work."
echo "6.  **Deploy Application:** Run: ${YELLOW}./deploy_app.sh${NC}"
echo "    Ensure the environment where you run 'deploy_app.sh' has the necessary permissions and service account configured if you skipped local key creation."
echo "7.  **Consider Private IP for Instances:** For even higher security, deploy your application on Compute Engine instances within the same VPC network as Cloud SQL and ensure they use private IPs."
echo "8.  **Infrastructure as Code (IaC):** For future scalability and manageability, consider migrating this setup to a declarative IaC tool like Terraform or Pulumi."

echo -e "${YELLOW}⚠️  Important Security Notes REITERATED:${NC}"
echo "- **NEVER commit sensitive files (like local service account keys or plaintext .env files) to version control.**"
echo "- **Regularly rotate secrets and keys in Secret Manager and KMS.**"
echo "- **Continuously monitor logs for security events and ensure alerts are active and reviewed.**"
echo "- **Apply the principle of least privilege rigorously to all IAM roles and resource access.**"
echo "- **Regularly review your Cloud Storage bucket permissions.**"

echo -e "${GREEN}🎉 Secure deployment script setup complete! Please follow the next steps carefully.${NC}"
