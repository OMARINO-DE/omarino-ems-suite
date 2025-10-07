#!/bin/bash

# Force Single-Platform Image Push
# This ensures images are pushed without manifest lists

set -e

REGISTRY="192.168.61.21:32768"

echo "════════════════════════════════════════════════════════════"
echo "  Forcing Single-Platform (linux/amd64) Images"
echo "  Registry: $REGISTRY"
echo "════════════════════════════════════════════════════════════"
echo ""

# List of all images to fix
declare -a IMAGES=(
    "timescale/timescaledb:latest-pg14"
    "redis:7-alpine"
    "prom/prometheus:latest"
    "grafana/grafana:latest"
    "grafana/loki:latest"
    "grafana/promtail:latest"
    "grafana/tempo:latest"
)

for image in "${IMAGES[@]}"; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Processing: $image"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    target="${REGISTRY}/${image}"
    
    # Remove any existing local image
    docker rmi -f "$target" 2>/dev/null || true
    docker rmi -f "$image" 2>/dev/null || true
    
    # Pull for linux/amd64 only
    echo "Pulling linux/amd64..."
    docker pull --platform linux/amd64 "$image"
    
    # Get the specific image digest/ID
    IMAGE_ID=$(docker images --format "{{.ID}}" "$image" | head -1)
    echo "Image ID: $IMAGE_ID"
    
    # Tag with registry
    docker tag "$IMAGE_ID" "$target"
    
    # Push using the digest to avoid manifest list
    echo "Pushing..."
    docker push "$target"
    
    echo "✓ Completed: $image"
    echo ""
done

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  All images pushed as single-platform linux/amd64"
echo "════════════════════════════════════════════════════════════"
