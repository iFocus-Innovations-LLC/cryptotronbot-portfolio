#!/bin/bash

# Test Local Docker Setup
set -e

echo "🐳 Testing CryptoTronBot Local Docker Setup"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Build images
echo "📦 Building Docker images..."
docker build -f Dockerfile.backend -t cryptotronbot-backend:test .
docker build -f Dockerfile.frontend -t cryptotronbot-frontend:test .

# Test backend
echo "🧪 Testing backend..."
docker run --rm -d --name test-backend -p 5000:5000 cryptotronbot-backend:test
sleep 10

# Test health endpoint
if curl -f http://localhost:5009/api/health > /dev/null 2>&1; then
    echo "✅ Backend health check passed"
else
    echo "❌ Backend health check failed"
    docker logs test-backend
    docker stop test-backend
    exit 1
fi

# Test frontend
echo "🧪 Testing frontend..."
docker run --rm -d --name test-frontend -p 4567:4567 cryptotronbot-frontend:test
sleep 10

# Test frontend endpoint
if curl -f http://localhost:4567/ > /dev/null 2>&1; then
    echo "✅ Frontend health check passed"
else
    echo "❌ Frontend health check failed"
    docker logs test-frontend
    docker stop test-frontend
    exit 1
fi

# Cleanup
echo "🧹 Cleaning up test containers..."
docker stop test-backend test-frontend 2>/dev/null || true

echo "🎉 Local Docker test completed successfully!"
echo "💡 You can now run: docker-compose up" 
