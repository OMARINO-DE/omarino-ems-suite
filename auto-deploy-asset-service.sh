#!/bin/bash

# Automated Deployment Script for Asset Service
# This script will attempt to deploy automatically, or provide instructions if SSH fails

SSH_KEY='/Users/omarzaror/Library/Mobile Documents/com~apple~CloudDocs/Developing/SSH-Key/server.pem'
SERVER_USER="ubuntu"
SERVER_HOST="192.168.75.20"

echo "=========================================="
echo "Automated Asset Service Deployment"
echo "=========================================="
echo ""

# Test SSH connection
echo "Testing SSH connection..."
if ssh -i "$SSH_KEY" -o ConnectTimeout=5 -o BatchMode=yes ${SERVER_USER}@${SERVER_HOST} 'exit' 2>/dev/null; then
    echo "✓ SSH connection successful!"
    echo ""
    
    # Execute deployment
    echo "Starting deployment..."
    ssh -i "$SSH_KEY" ${SERVER_USER}@${SERVER_HOST} 'bash -s' << 'ENDSSH'
set -e

echo "=========================================="
echo "Asset Service Deployment"
echo "=========================================="

cd /home/ubuntu/omarino-ems-suite
echo "Pulling latest code..."
git pull origin main

echo ""
echo "Checking database schema..."
cd asset-service/database
SCHEMA_EXISTS=$(PGPASSWORD=omarino_dev_pass psql -h localhost -U omarino -d omarino -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'assets');")

if [ "$SCHEMA_EXISTS" = "t" ]; then
    echo "✓ Database schema already exists"
else
    echo "Applying database schema..."
    PGPASSWORD=omarino_dev_pass psql -h localhost -U omarino -d omarino -f schema.sql
    echo "✓ Database schema applied"
fi

cd /home/ubuntu/omarino-ems-suite/asset-service

echo ""
echo "Stopping existing container..."
docker stop omarino-asset-service 2>/dev/null || echo "No existing container"
docker rm omarino-asset-service 2>/dev/null || echo "Container removed"

echo ""
echo "Building Docker image..."
docker build -t omarino-asset-service:latest .

echo ""
echo "Starting asset service..."
docker run -d \
  --name omarino-asset-service \
  --network omarino-network \
  --restart unless-stopped \
  -p 8003:8003 \
  -e DATABASE_URL=postgresql://omarino:omarino_dev_pass@postgres:5432/omarino \
  -e API_PREFIX=/api/assets \
  -e LOG_LEVEL=INFO \
  -e CORS_ORIGINS=* \
  omarino-asset-service:latest

echo ""
echo "Waiting for service to start..."
sleep 5

echo ""
echo "Checking service health..."
curl -s http://localhost:8003/api/assets/health | jq '.' || curl -s http://localhost:8003/api/assets/health

echo ""
echo "Container status:"
docker ps | grep omarino-asset-service

echo ""
echo "=========================================="
echo "✓ Deployment Complete!"
echo "=========================================="
echo ""
echo "Service URLs:"
echo "  - Health: http://192.168.75.20:8003/api/assets/health"
echo "  - API Docs: http://192.168.75.20:8003/api/assets/docs"
echo ""
ENDSSH

    if [ $? -eq 0 ]; then
        echo ""
        echo "=========================================="
        echo "✓✓✓ DEPLOYMENT SUCCESSFUL! ✓✓✓"
        echo "=========================================="
        echo ""
        echo "Next steps:"
        echo "1. Test the service: curl http://192.168.75.20:8003/api/assets/health"
        echo "2. View API docs: open http://192.168.75.20:8003/api/assets/docs"
        echo "3. Create test battery (run script below)"
        echo ""
    else
        echo ""
        echo "⚠️  Deployment encountered an error"
        echo "Check logs with: ssh -i '$SSH_KEY' ${SERVER_USER}@${SERVER_HOST} 'docker logs omarino-asset-service'"
    fi
    
else
    echo "❌ SSH connection failed"
    echo ""
    echo "The SSH key needs to be authorized on the server first."
    echo ""
    echo "=========================================="
    echo "MANUAL DEPLOYMENT REQUIRED"
    echo "=========================================="
    echo ""
    echo "Option 1: Add your SSH key to the server"
    echo ""
    echo "1. Get your public key:"
    echo "   ssh-keygen -y -f '$SSH_KEY'"
    echo ""
    echo "2. Log in to the server using password or console:"
    echo "   ssh ${SERVER_USER}@${SERVER_HOST}"
    echo ""
    echo "3. Add the key to authorized_keys:"
    echo "   mkdir -p ~/.ssh"
    echo "   echo 'YOUR_PUBLIC_KEY_HERE' >> ~/.ssh/authorized_keys"
    echo "   chmod 600 ~/.ssh/authorized_keys"
    echo ""
    echo "4. Run this script again"
    echo ""
    echo "=========================================="
    echo "Option 2: Deploy Manually"
    echo "=========================================="
    echo ""
    echo "1. Log in to server (password or console)"
    echo ""
    echo "2. Run these commands:"
    echo ""
    cat << 'COMMANDS'
cd /home/ubuntu/omarino-ems-suite && git pull origin main
cd asset-service/database
PGPASSWORD=omarino_dev_pass psql -h localhost -U omarino -d omarino -f schema.sql
cd /home/ubuntu/omarino-ems-suite/asset-service
docker stop omarino-asset-service 2>/dev/null || true
docker rm omarino-asset-service 2>/dev/null || true
docker build -t omarino-asset-service:latest .
docker run -d --name omarino-asset-service --network omarino-network --restart unless-stopped -p 8003:8003 -e DATABASE_URL=postgresql://omarino:omarino_dev_pass@postgres:5432/omarino -e API_PREFIX=/api/assets -e LOG_LEVEL=INFO -e CORS_ORIGINS=* omarino-asset-service:latest
sleep 5
curl http://localhost:8003/api/assets/health
docker ps | grep omarino-asset-service
COMMANDS
    echo ""
    echo "Full deployment guide: asset-service/DEPLOYMENT.md"
    echo ""
fi
