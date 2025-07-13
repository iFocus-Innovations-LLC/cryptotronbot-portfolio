# CryptoTronBot Kubernetes Deployment Guide

This guide will help you deploy CryptoTronBot to Google Kubernetes Engine (GKE) with full containerization and orchestration.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   Ingress       │    │   Services      │
│   (GKE)         │───▶│   Controller    │───▶│   (ClusterIP)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Database      │
│   (Ruby/Sinatra)│    │   (Flask)       │    │   (SQLite)      │
│   Pods          │    │   Pods          │    │   (Persistent)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📋 Prerequisites

### Required Tools
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Docker](https://docs.docker.com/get-docker/)
- [Git](https://git-scm.com/)

### Required Permissions
- GCP Project Owner or Editor
- Kubernetes Engine Admin
- Storage Admin
- Compute Admin

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone <your-repo-url>
cd cryptotronbot-portfolio
```

### 2. Configure Project
Edit `deploy.sh` and update:
```bash
PROJECT_ID="your-gcp-project-id"
REGION="us-central1"
CLUSTER_NAME="cryptotronbot-cluster"
```

### 3. Run Deployment
```bash
chmod +x deploy.sh
./deploy.sh
```

## 📁 File Structure

```
cryptotronbot-portfolio/
├── Dockerfile.backend          # Backend container definition
├── Dockerfile.frontend         # Frontend container definition
├── docker-compose.yml          # Local development setup
├── nginx.conf                  # Load balancer configuration
├── deploy.sh                   # Deployment script
├── cloudbuild.yaml             # CI/CD pipeline
├── k8s/                        # Kubernetes manifests
│   ├── namespace.yaml          # Namespace definition
│   ├── configmap.yaml          # Configuration
│   ├── secret.yaml             # Secrets
│   ├── backend-deployment.yaml # Backend deployment
│   ├── frontend-deployment.yaml# Frontend deployment
│   ├── services.yaml           # Service definitions
│   ├── ingress.yaml            # Ingress configuration
│   └── hpa.yaml               # Horizontal Pod Autoscaler
└── README-K8S.md              # This file
```

## 🔧 Configuration

### Environment Variables

#### Backend (Flask)
- `FLASK_ENV`: Production environment
- `DATABASE_URL`: SQLite database path
- `JWT_SECRET_KEY`: JWT signing key
- `LOG_LEVEL`: Logging level

#### Frontend (Ruby)
- `RACK_ENV`: Production environment
- `BACKEND_URL`: Backend service URL
- `LOG_LEVEL`: Logging level

### Secrets Management
Update `k8s/secret.yaml` with your actual secrets:
```yaml
data:
  JWT_SECRET_KEY: "base64-encoded-secret"
  DATABASE_PASSWORD: "base64-encoded-password"
  API_KEYS: "base64-encoded-api-keys"
```

## 🐳 Container Images

### Backend Image
- **Base**: Python 3.11-slim
- **Port**: 5000
- **Health Check**: `/api/health`
- **Process**: Gunicorn with 4 workers

### Frontend Image
- **Base**: Ruby 3.2-slim
- **Port**: 4567
- **Health Check**: `/`
- **Process**: Sinatra server

## ⚙️ Kubernetes Resources

### Namespace
- **Name**: `cryptotronbot`
- **Purpose**: Isolate application resources

### Deployments
- **Backend**: 3 replicas with auto-scaling
- **Frontend**: 3 replicas with auto-scaling
- **Resource Limits**: CPU/Memory constraints

### Services
- **Backend Service**: ClusterIP on port 5000
- **Frontend Service**: ClusterIP on port 4567

### Ingress
- **Type**: GCE Load Balancer
- **SSL**: Managed certificates
- **Routing**: Path-based routing

### Autoscaling
- **Backend**: 3-10 replicas (70% CPU, 80% Memory)
- **Frontend**: 3-8 replicas (70% CPU, 80% Memory)

## 🔒 Security Features

### Network Security
- **Ingress**: HTTPS only with TLS 1.2+
- **Services**: ClusterIP (internal only)
- **Pods**: Non-root users

### Application Security
- **Secrets**: Kubernetes secrets for sensitive data
- **ConfigMaps**: Non-sensitive configuration
- **Health Checks**: Liveness and readiness probes

### Rate Limiting
- **API**: 10 requests/second
- **Login**: 5 requests/second

## 📊 Monitoring & Logging

### Health Checks
```bash
# Check pod status
kubectl get pods -n cryptotronbot

# Check service status
kubectl get services -n cryptotronbot

# Check ingress status
kubectl get ingress -n cryptotronbot
```

### Logs
```bash
# Backend logs
kubectl logs -f deployment/cryptotronbot-backend -n cryptotronbot

# Frontend logs
kubectl logs -f deployment/cryptotronbot-frontend -n cryptotronbot
```

### Metrics
```bash
# Resource usage
kubectl top pods -n cryptotronbot

# HPA status
kubectl get hpa -n cryptotronbot
```

## 🔄 CI/CD Pipeline

### Cloud Build Integration
The `cloudbuild.yaml` file defines a complete CI/CD pipeline:

1. **Build**: Docker images for both services
2. **Push**: Images to Google Container Registry
3. **Deploy**: Rolling updates to GKE
4. **Verify**: Health checks and rollout status

### Trigger Setup
```bash
# Create Cloud Build trigger
gcloud builds triggers create github \
  --repo-name=cryptotronbot-portfolio \
  --repo-owner=your-username \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml
```

## 🛠️ Troubleshooting

### Common Issues

#### Pod Not Starting
```bash
# Check pod events
kubectl describe pod <pod-name> -n cryptotronbot

# Check pod logs
kubectl logs <pod-name> -n cryptotronbot
```

#### Service Not Accessible
```bash
# Check service endpoints
kubectl get endpoints -n cryptotronbot

# Test service connectivity
kubectl run test-pod --image=busybox -n cryptotronbot
kubectl exec test-pod -n cryptotronbot -- wget -qO- http://cryptotronbot-backend-service:5000/api/health
```

#### Ingress Issues
```bash
# Check ingress status
kubectl describe ingress cryptotronbot-ingress -n cryptotronbot

# Check load balancer
kubectl get service -n ingress-nginx
```

### Scaling Issues
```bash
# Check HPA status
kubectl describe hpa -n cryptotronbot

# Manual scaling
kubectl scale deployment cryptotronbot-backend --replicas=5 -n cryptotronbot
```

## 🔧 Maintenance

### Updates
```bash
# Update images
kubectl set image deployment/cryptotronbot-backend backend=gcr.io/PROJECT_ID/cryptotronbot-backend:latest -n cryptotronbot
kubectl set image deployment/cryptotronbot-frontend frontend=gcr.io/PROJECT_ID/cryptotronbot-frontend:latest -n cryptotronbot

# Check rollout status
kubectl rollout status deployment/cryptotronbot-backend -n cryptotronbot
```

### Backup
```bash
# Export configurations
kubectl get all -n cryptotronbot -o yaml > backup.yaml

# Backup secrets
kubectl get secret cryptotronbot-secrets -n cryptotronbot -o yaml > secrets-backup.yaml
```

### Cleanup
```bash
# Delete all resources
kubectl delete namespace cryptotronbot

# Delete cluster (optional)
gcloud container clusters delete cryptotronbot-cluster --region=us-central1
```

## 📈 Performance Optimization

### Resource Tuning
- **CPU Requests**: 250m (backend), 100m (frontend)
- **Memory Requests**: 256Mi (backend), 128Mi (frontend)
- **CPU Limits**: 500m (backend), 200m (frontend)
- **Memory Limits**: 512Mi (backend), 256Mi (frontend)

### Scaling Policies
- **Target CPU**: 70%
- **Target Memory**: 80%
- **Min Replicas**: 3
- **Max Replicas**: 10 (backend), 8 (frontend)

## 🔐 Security Best Practices

1. **Rotate Secrets**: Regularly update JWT secrets and API keys
2. **Network Policies**: Implement network policies for pod-to-pod communication
3. **RBAC**: Use role-based access control for cluster access
4. **Pod Security**: Enable pod security standards
5. **Audit Logging**: Enable Kubernetes audit logging

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Kubernetes logs and events
3. Verify configuration and secrets
4. Test connectivity between services

## 🎯 Next Steps

1. **Domain Setup**: Configure your domain in the ingress
2. **SSL Certificates**: Set up managed SSL certificates
3. **Monitoring**: Integrate with Google Cloud Monitoring
4. **Logging**: Set up centralized logging with Cloud Logging
5. **Backup**: Implement automated database backups
6. **Security**: Enable additional security features 