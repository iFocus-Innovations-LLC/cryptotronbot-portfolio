#!/bin/bash

# CryptoTronBot GKE Deployment Script
set -e

# Configuration
PROJECT_ID="your-gcp-project-id"
REGION="us-central1"
CLUSTER_NAME="cryptotronbot-cluster"
NAMESPACE="cryptotronbot"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting CryptoTronBot GKE Deployment${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl is not installed. Please install it first.${NC}"
    exit 1
fi

# Authenticate with Google Cloud
echo -e "${YELLOW}🔐 Authenticating with Google Cloud...${NC}"
gcloud auth login
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${YELLOW}🔧 Enabling required APIs...${NC}"
gcloud services enable container.googleapis.com
gcloud services enable compute.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# Create GKE cluster if it doesn't exist
echo -e "${YELLOW}🏗️  Creating GKE cluster...${NC}"
if ! gcloud container clusters describe $CLUSTER_NAME --region=$REGION &> /dev/null; then
    gcloud container clusters create $CLUSTER_NAME \
        --region=$REGION \
        --num-nodes=3 \
        --min-nodes=1 \
        --max-nodes=10 \
        --machine-type=e2-standard-2 \
        --enable-autoscaling \
        --enable-autorepair \
        --enable-autoupgrade \
        --enable-ip-alias \
        --create-subnetwork="" \
        --network=default
else
    echo -e "${GREEN}✅ Cluster already exists${NC}"
fi

# Get cluster credentials
echo -e "${YELLOW}🔑 Getting cluster credentials...${NC}"
gcloud container clusters get-credentials $CLUSTER_NAME --region=$REGION

# Create namespace
echo -e "${YELLOW}📁 Creating namespace...${NC}"
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Configure Docker to use gcloud as a credential helper
echo -e "${YELLOW}🐳 Configuring Docker authentication...${NC}"
gcloud auth configure-docker

# Build and push Docker images
echo -e "${YELLOW}🏗️  Building and pushing Docker images...${NC}"

# Build backend image
echo -e "${YELLOW}📦 Building backend image...${NC}"
docker build -f Dockerfile.backend -t gcr.io/$PROJECT_ID/cryptotronbot-backend:latest .
docker push gcr.io/$PROJECT_ID/cryptotronbot-backend:latest

# Build frontend image
echo -e "${YELLOW}📦 Building frontend image...${NC}"
docker build -f Dockerfile.frontend -t gcr.io/$PROJECT_ID/cryptotronbot-frontend:latest .
docker push gcr.io/$PROJECT_ID/cryptotronbot-frontend:latest

# Create image pull secret
echo -e "${YELLOW}🔐 Creating image pull secret...${NC}"
kubectl create secret docker-registry gcr-secret \
    --docker-server=gcr.io \
    --docker-username=_json_key \
    --docker-password="$(gcloud auth print-access-token)" \
    --docker-email="$(gcloud config get-value account)" \
    --namespace=$NAMESPACE \
    --dry-run=client -o yaml | kubectl apply -f -

# Apply Kubernetes manifests
echo -e "${YELLOW}📋 Applying Kubernetes manifests...${NC}"

# Update image references in deployment files
sed -i.bak "s/YOUR_PROJECT_ID/$PROJECT_ID/g" k8s/*-deployment.yaml

# Apply all manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/services.yaml
kubectl apply -f k8s/hpa.yaml

# Wait for deployments to be ready
echo -e "${YELLOW}⏳ Waiting for deployments to be ready...${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/cryptotronbot-backend -n $NAMESPACE
kubectl wait --for=condition=available --timeout=300s deployment/cryptotronbot-frontend -n $NAMESPACE

# Apply ingress (optional - requires domain setup)
echo -e "${YELLOW}🌐 Setting up ingress...${NC}"
echo -e "${YELLOW}⚠️  Note: You need to update the host in k8s/ingress.yaml with your domain${NC}"
kubectl apply -f k8s/ingress.yaml

# Get service information
echo -e "${GREEN}✅ Deployment completed!${NC}"
echo -e "${YELLOW}📊 Getting service information...${NC}"
kubectl get services -n $NAMESPACE
kubectl get pods -n $NAMESPACE

echo -e "${GREEN}🎉 CryptoTronBot is now deployed on GKE!${NC}"
echo -e "${YELLOW}📝 Next steps:${NC}"
echo -e "   1. Update the host in k8s/ingress.yaml with your domain"
echo -e "   2. Set up SSL certificates"
echo -e "   3. Configure monitoring and logging"
echo -e "   4. Set up CI/CD pipeline"

# Clean up backup files
rm -f k8s/*-deployment.yaml.bak 