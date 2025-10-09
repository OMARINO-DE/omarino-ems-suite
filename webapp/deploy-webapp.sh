#!/bin/bash

# Deploy OMARINO EMS WebApp to Production Server
# This script builds and deploys the Next.js webapp with the new asset management features

set -e  # Exit on error

SERVER_USER="omar"
SERVER_HOST="192.168.75.20"
SERVER_PATH="/home/omar/OMARINO-EMS-Suite/webapp"

# Check if we can connect via SSH (will use SSH agent or default keys)
if ! ssh -o BatchMode=yes -o ConnectTimeout=5 ${SERVER_USER}@${SERVER_HOST} exit 2>/dev/null; then
    echo "❌ Error: Cannot connect to ${SERVER_HOST}"
    echo "Please ensure:"
    echo "  1. SSH key is configured (ssh-add <key>)"
    echo "  2. Server is reachable"
    echo "  3. User has access to the server"
    exit 1
fi

echo "🚀 Starting OMARINO EMS WebApp Deployment"
echo "=========================================="
echo ""

echo "📦 Step 1: Building Next.js application..."
npm run build

if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi

echo "✅ Build successful!"
echo ""

echo "🔄 Step 2: Syncing files to server..."
rsync -avz --progress \
    -e "ssh -o StrictHostKeyChecking=no" \
    --exclude 'node_modules' \
    --exclude '.next/cache' \
    --exclude '.git' \
    --exclude '.env.local' \
    ./ ${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/

if [ $? -ne 0 ]; then
    echo "❌ File sync failed!"
    exit 1
fi

echo "✅ Files synced successfully!"
echo ""

echo "🔧 Step 3: Installing dependencies on server..."
ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_HOST} << 'ENDSSH'
cd /home/omar/OMARINO-EMS-Suite/webapp
npm ci --production

if [ $? -ne 0 ]; then
    echo "❌ Dependency installation failed!"
    exit 1
fi

echo "✅ Dependencies installed!"
ENDSSH

echo ""

echo "🐳 Step 4: Rebuilding and restarting Docker container..."
ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_HOST} << 'ENDSSH'
cd /home/omar/OMARINO-EMS-Suite/webapp

# Stop and remove existing container if it exists
if [ "$(docker ps -aq -f name=omarino-webapp)" ]; then
    echo "Stopping existing webapp container..."
    docker stop omarino-webapp 2>/dev/null || true
    docker rm omarino-webapp 2>/dev/null || true
fi

# Build new image
echo "Building new Docker image..."
docker build --no-cache -t omarino-webapp:latest .

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed!"
    exit 1
fi

# Start new container
echo "Starting new webapp container..."
docker run -d \
    --name omarino-webapp \
    --network omarino-network \
    -p 3000:3000 \
    -e NEXT_PUBLIC_API_URL=https://ems-back.omarino.net \
    --restart unless-stopped \
    omarino-webapp:latest

if [ $? -ne 0 ]; then
    echo "❌ Failed to start Docker container!"
    exit 1
fi

echo "✅ Docker container started!"

# Wait for container to be healthy
echo "Waiting for webapp to be ready..."
sleep 5

# Check if container is running
if [ "$(docker ps -q -f name=omarino-webapp)" ]; then
    echo "✅ WebApp container is running!"
else
    echo "❌ WebApp container failed to start!"
    docker logs omarino-webapp
    exit 1
fi

ENDSSH

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "📊 Deployment Summary:"
echo "  • Server: ${SERVER_HOST}"
echo "  • Application: OMARINO EMS WebApp"
echo "  • Port: 3000"
echo "  • API URL: https://ems-back.omarino.net"
echo "  • Asset Service: Available at /api/assets"
echo ""
echo "🌐 Access the application at: http://${SERVER_HOST}:3000"
echo ""
echo "New Features Deployed:"
echo "  ✓ Asset Management Dashboard (/assets)"
echo "  ✓ Battery Management (list, create, view)"
echo "  ✓ Generator Management (list, create, view)"
echo "  ✓ Asset Status Dashboard (/assets/status)"
echo "  ✓ Real Asset Integration in Optimization"
echo ""
echo "🔍 To check logs:"
echo "  ssh ${SERVER_USER}@${SERVER_HOST} 'docker logs -f omarino-webapp'"
