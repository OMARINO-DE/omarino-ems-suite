#!/bin/bash

# Deploy script for scheduler service
# Run this script on the server (192.168.75.20)

set -e

echo "===== OMARINO EMS - Scheduler Service Deployment ====="
echo ""

# Navigate to project directory
cd /home/omarino/omarino-ems-suite || cd ~/omarino-ems-suite

# Pull latest changes
echo "Pulling latest changes from GitHub..."
git pull

# Build scheduler service
echo "Building scheduler-service Docker image..."
cd scheduler-service
docker build -t omarino-scheduler:latest .

# Stop and remove old container
echo "Stopping old container..."
docker stop omarino-scheduler || true
docker rm omarino-scheduler || true

# Run new container
echo "Starting new container..."
docker run -d \
  --name omarino-scheduler \
  --network omarino-network \
  -p 8080:8080 \
  -p 5003:5003 \
  -e ASPNETCORE_URLS="http://+:8080" \
  -e ASPNETCORE_ENVIRONMENT=Production \
  omarino-scheduler:latest

# Wait for container to start
echo "Waiting for container to start..."
sleep 5

# Check container status
echo "Container status:"
docker ps | grep omarino-scheduler

# Check health
echo ""
echo "Checking health endpoint..."
sleep 2
curl -s http://localhost:8080/api/scheduler/health | python3 -m json.tool || echo "Health check failed"

echo ""
echo "===== Deployment Complete ====="
echo ""
echo "Recent logs:"
docker logs omarino-scheduler 2>&1 | tail -20
