#!/bin/bash
# Deploy forecast service with database persistence

set -e

echo "=== Deploying Forecast Service with Database Persistence ==="

# Navigate to project directory
cd ~/OMARINO-EMS-Suite

# Pull latest changes
echo "Pulling latest code from GitHub..."
git pull origin main

# Build Docker image
echo "Building forecast service image..."
cd forecast-service
docker build -t 192.168.61.21:32768/omarino-forecast:latest .

# Push to registry
echo "Pushing to registry..."
docker push 192.168.61.21:32768/omarino-forecast:latest

# Stop and remove old container
echo "Stopping old container..."
docker stop omarino-forecast || true
docker rm omarino-forecast || true

# Start new container with database connection
echo "Starting new container..."
docker run -d \
  --name omarino-forecast \
  --network ems_omarino-network \
  -p 8082:8082 \
  -e DATABASE_URL="postgresql://omarino:omarino@omarino-postgres:5432/omarino" \
  --restart unless-stopped \
  192.168.61.21:32768/omarino-forecast:latest

# Wait for startup
echo "Waiting for service to start..."
sleep 5

# Check logs
echo "Checking logs..."
docker logs omarino-forecast --tail 30

# Test API
echo "Testing API..."
curl -s http://localhost:8082/api/health | jq '.'

echo ""
echo "=== Deployment Complete ==="
echo "Service is running at: http://localhost:8082"
echo "Check database connection in logs above for 'forecast_database_connected'"
