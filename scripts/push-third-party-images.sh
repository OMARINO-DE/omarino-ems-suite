#!/bin/bash

# Push Third-Party Images to Private Registry
# This script pulls public images and pushes them to your private registry

set -e

REGISTRY="192.168.61.21:32768"

echo "════════════════════════════════════════════════════════════"
echo "  Pulling and Pushing Third-Party Images"
echo "  Registry: $REGISTRY"
echo "════════════════════════════════════════════════════════════"
echo ""

# Array of third-party images used in docker-compose.yml
declare -a IMAGES=(
    "timescale/timescaledb:latest-pg14"
    "redis:7-alpine"
    "prom/prometheus:latest"
    "grafana/grafana:latest"
    "grafana/loki:latest"
    "grafana/promtail:latest"
    "grafana/tempo:latest"
)

pull_and_push() {
    local source_image=$1
    local target_image="${REGISTRY}/${source_image}"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Processing: $source_image"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Pull the image
    echo "Pulling from Docker Hub..."
    if docker pull "$source_image"; then
        echo "✓ Pull successful"
        
        # Tag for private registry
        echo "Tagging for private registry..."
        docker tag "$source_image" "$target_image"
        
        # Push to private registry
        echo "Pushing to private registry..."
        if docker push "$target_image"; then
            echo "✓ Push successful: $target_image"
            echo ""
            return 0
        else
            echo "✗ Push failed: $source_image"
            echo ""
            return 1
        fi
    else
        echo "✗ Pull failed: $source_image"
        echo ""
        return 1
    fi
}

# Track successes and failures
declare -a SUCCESSFUL=()
declare -a FAILED=()

# Process each image
for source_image in "${IMAGES[@]}"; do
    if pull_and_push "$source_image"; then
        SUCCESSFUL+=("$source_image")
    else
        FAILED+=("$source_image")
    fi
done

# Summary
echo ""
echo "════════════════════════════════════════════════════════════"
echo "  SUMMARY"
echo "════════════════════════════════════════════════════════════"
echo ""

if [ ${#SUCCESSFUL[@]} -gt 0 ]; then
    echo "✓ Successful (${#SUCCESSFUL[@]}):"
    for image in "${SUCCESSFUL[@]}"; do
        echo "  ✓ ${image}"
    done
    echo ""
fi

if [ ${#FAILED[@]} -gt 0 ]; then
    echo "✗ Failed (${#FAILED[@]}):"
    for image in "${FAILED[@]}"; do
        echo "  ✗ ${image}"
    done
    echo ""
    exit 1
fi

echo "All third-party images pushed successfully!"
echo ""
echo "Images available at: ${REGISTRY}/"
echo "  - timescale/timescaledb:latest-pg14"
echo "  - redis:7-alpine"
echo "  - prom/prometheus:latest"
echo "  - grafana/grafana:latest"
echo "  - grafana/loki:latest"
echo "  - grafana/promtail:latest"
echo "  - grafana/tempo:latest"
echo ""
