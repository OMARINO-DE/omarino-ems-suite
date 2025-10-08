#!/bin/bash

# Asset Service Deployment Script for OMARINO EMS Suite
# This script deploys the asset service to the server

set -e  # Exit on any error

echo "=========================================="
echo "OMARINO Asset Service Deployment"
echo "=========================================="
echo ""

# Configuration
SERVER_USER="ubuntu"
SERVER_HOST="192.168.75.20"
SSH_KEY="/Users/omarzaror/Library/Mobile Documents/com~apple~CloudDocs/Developing/SSH-Key/server.pem"
REMOTE_DIR="/home/ubuntu/omarino-ems-suite"
SERVICE_NAME="asset-service"
CONTAINER_NAME="omarino-asset-service"
IMAGE_NAME="omarino-asset-service:latest"
SERVICE_PORT="8003"
DATABASE_URL="postgresql://omarino:omarino_dev_pass@postgres:5432/omarino"

echo "Step 1: Connecting to server..."
ssh -i "$SSH_KEY" ${SERVER_USER}@${SERVER_HOST} << 'ENDSSH'

cd /home/ubuntu/omarino-ems-suite

echo "Step 2: Pulling latest code from GitHub..."
git pull origin main

echo "Step 3: Initializing database schema..."
cd asset-service/database
# Check if schema is already applied by looking for assets table
SCHEMA_EXISTS=$(PGPASSWORD=omarino_dev_pass psql -h localhost -U omarino -d omarino -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'assets');")

if [ "$SCHEMA_EXISTS" = "t" ]; then
    echo "  ✓ Database schema already exists"
else
    echo "  Applying database schema..."
    PGPASSWORD=omarino_dev_pass psql -h localhost -U omarino -d omarino -f schema.sql
    echo "  ✓ Database schema applied successfully"
fi

cd ../..

echo "Step 4: Stopping existing container (if running)..."
if docker ps -a --format '{{.Names}}' | grep -q "^omarino-asset-service$"; then
    docker stop omarino-asset-service || true
    docker rm omarino-asset-service || true
    echo "  ✓ Existing container stopped and removed"
else
    echo "  ✓ No existing container found"
fi

echo "Step 5: Building Docker image..."
cd asset-service
docker build -t omarino-asset-service:latest .
echo "  ✓ Docker image built successfully"

echo "Step 6: Starting Asset Service container..."
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

echo "  ✓ Container started successfully"

echo ""
echo "Step 7: Waiting for service to be ready..."
sleep 5

echo "Step 8: Checking service health..."
HEALTH_CHECK=$(curl -s http://localhost:8003/api/assets/health || echo "failed")

if echo "$HEALTH_CHECK" | grep -q "healthy"; then
    echo "  ✓ Service is healthy and running!"
else
    echo "  ⚠️  Service may not be fully ready yet"
    echo "  Check logs with: docker logs omarino-asset-service"
fi

echo ""
echo "Step 9: Checking container status..."
docker ps | grep omarino-asset-service

echo ""
echo "=========================================="
echo "✓ Asset Service Deployment Complete!"
echo "=========================================="
echo ""
echo "Service Information:"
echo "  - Container: omarino-asset-service"
echo "  - Port: 8003"
echo "  - Health: http://192.168.75.20:8003/api/assets/health"
echo "  - API Docs: http://192.168.75.20:8003/api/assets/docs"
echo ""
echo "Useful Commands:"
echo "  - View logs: docker logs -f omarino-asset-service"
echo "  - Restart: docker restart omarino-asset-service"
echo "  - Stop: docker stop omarino-asset-service"
echo "  - Check status: docker ps | grep asset-service"
echo ""
echo "Next Steps:"
echo "  1. Test health endpoint: curl http://192.168.75.20:8003/api/assets/health"
echo "  2. View API docs: open http://192.168.75.20:8003/api/assets/docs"
echo "  3. Create test assets via API"
echo ""

ENDSSH

echo "=========================================="
echo "Deployment script completed!"
echo "=========================================="
