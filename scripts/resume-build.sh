#!/bin/bash

# Resume build for remaining services
REGISTRY="192.168.61.21:32768"
PROJECT_NAME="omarino-ems"

cd "/Users/omarzaror/Library/Mobile Documents/com~apple~CloudDocs/Developing/OMARINO EMS Suite"

echo "Building remaining services..."
echo ""

# Services left to build
services=("optimize-service" "scheduler-service" "webapp")

for service in "${services[@]}"; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Building: $service"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    docker build -t "${REGISTRY}/${PROJECT_NAME}/${service}:latest" "./${service}"
    
    echo "Pushing: $service"
    docker push "${REGISTRY}/${PROJECT_NAME}/${service}:latest"
    
    echo "✓ Completed: $service"
    echo ""
done

echo "════════════════════════════════════════════════════════════"
echo "  All remaining images built and pushed successfully!"
echo "════════════════════════════════════════════════════════════"
