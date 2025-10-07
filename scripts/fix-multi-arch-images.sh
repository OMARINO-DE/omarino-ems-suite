#!/bin/bash

# Fix Multi-Architecture Images in Private Registry
# This script properly handles multi-arch images for linux/amd64

set -e

REGISTRY="192.168.61.21:32768"

echo "════════════════════════════════════════════════════════════"
echo "  Fixing Multi-Architecture Images for Private Registry"
echo "  Registry: $REGISTRY"
echo "  Target Platform: linux/amd64"
echo "════════════════════════════════════════════════════════════"
echo ""

# Array of third-party images
declare -a IMAGES=(
    "timescale/timescaledb:latest-pg14"
    "redis:7-alpine"
    "prom/prometheus:latest"
    "grafana/grafana:latest"
    "grafana/loki:latest"
    "grafana/promtail:latest"
    "grafana/tempo:latest"
)

pull_and_push_for_amd64() {
    local source_image=$1
    local target_image="${REGISTRY}/${source_image}"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Processing: $source_image"
    echo "Target: $target_image"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Pull for linux/amd64 specifically
    echo "Pulling for linux/amd64..."
    docker pull --platform linux/amd64 "$source_image"
    
    # Tag for registry
    echo "Tagging for registry..."
    docker tag "$source_image" "$target_image"
    
    # Push to registry
    echo "Pushing to registry..."
    docker push "$target_image"
    
    echo "✓ Completed: $source_image"
    echo ""
}

# Process each image
for source_image in "${IMAGES[@]}"; do
    if pull_and_push_for_amd64 "$source_image"; then
        echo "✅ Successfully processed: $source_image"
    else
        echo "❌ Failed: $source_image"
        exit 1
    fi
done

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  All images successfully pulled and pushed for linux/amd64"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Images available in registry:"
for source_image in "${IMAGES[@]}"; do
    echo "  - ${REGISTRY}/${source_image}"
done
echo ""
