#!/bin/bash

# OMARINO EMS - Simple Docker Build and Push Script
# Registry: http://192.168.61.21:32768

set -e

REGISTRY="192.168.61.21:32768"
PROJECT_NAME="omarino-ems"

echo "════════════════════════════════════════════════════════════"
echo "  OMARINO EMS Suite - Docker Build & Push"
echo "  Registry: $REGISTRY"
echo "════════════════════════════════════════════════════════════"
echo ""

cd "/Users/omarzaror/Library/Mobile Documents/com~apple~CloudDocs/Developing/OMARINO EMS Suite"

# Build and push each service
services=("api-gateway" "timeseries-service" "forecast-service" "optimize-service" "scheduler-service" "webapp")

for service in "${services[@]}"; do
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Building: $service"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    docker build -t "${REGISTRY}/${PROJECT_NAME}/${service}:latest" "./${service}"
    
    echo "Pushing: $service"
    docker push "${REGISTRY}/${PROJECT_NAME}/${service}:latest"
    
    echo "✓ Completed: $service"
done

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  All images built and pushed successfully!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Images available at:"
for service in "${services[@]}"; do
    echo "  - ${REGISTRY}/${PROJECT_NAME}/${service}:latest"
done
echo ""
