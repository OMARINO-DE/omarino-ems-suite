#!/bin/bash

# OMARINO-EMS: Rebuild and Push AMD64 Images
# This script rebuilds all images for AMD64 platform (x86_64)
# Run this on your ARM64 Mac to build images for the AMD64 server

set -e  # Exit on error

REGISTRY="192.168.61.21:32768"
NAMESPACE="omarino-ems"

echo "=========================================="
echo "OMARINO-EMS: AMD64 Image Builder"
echo "=========================================="
echo "Registry: $REGISTRY"
echo "Platform: linux/amd64"
echo ""
echo "This will rebuild ALL custom services for AMD64"
echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
sleep 5

# Enable buildx for cross-platform builds
docker buildx version || {
    echo "Error: docker buildx not available. Please install it."
    exit 1
}

# Create builder instance with insecure registry support if it doesn't exist
if ! docker buildx inspect omarino-builder >/dev/null 2>&1; then
    echo "Creating buildx builder with insecure registry support..."
    docker buildx create \
        --name omarino-builder \
        --driver docker-container \
        --config <(cat <<EOF
[registry."$REGISTRY"]
  http = true
  insecure = true
EOF
) \
        --use
else
    docker buildx use omarino-builder
fi

echo ""
echo "========================================"
echo "Building Custom Services for AMD64..."
echo "========================================"

# 1. API Gateway
echo ""
echo "[1/6] Building api-gateway for AMD64..."
cd api-gateway
docker buildx build \
    --platform linux/amd64 \
    --tag ${REGISTRY}/${NAMESPACE}/api-gateway:latest \
    --push \
    --progress=plain \
    .
cd ..

# 2. TimeSeries Service
echo ""
echo "[2/6] Building timeseries-service for AMD64..."
cd timeseries-service
docker buildx build \
    --platform linux/amd64 \
    --tag ${REGISTRY}/${NAMESPACE}/timeseries-service:latest \
    --push \
    --progress=plain \
    .
cd ..

# 3. Forecast Service
echo ""
echo "[3/6] Building forecast-service for AMD64..."
cd forecast-service
docker buildx build \
    --platform linux/amd64 \
    --tag ${REGISTRY}/${NAMESPACE}/forecast-service:latest \
    --push \
    --progress=plain \
    .
cd ..

# 4. Optimize Service
echo ""
echo "[4/6] Building optimize-service for AMD64..."
cd optimize-service
docker buildx build \
    --platform linux/amd64 \
    --tag ${REGISTRY}/${NAMESPACE}/optimize-service:latest \
    --push \
    --progress=plain \
    .
cd ..

# 5. Scheduler Service
echo ""
echo "[5/6] Building scheduler-service for AMD64..."
cd scheduler-service
docker buildx build \
    --platform linux/amd64 \
    --tag ${REGISTRY}/${NAMESPACE}/scheduler-service:latest \
    --push \
    --progress=plain \
    .
cd ..

# 6. WebApp
echo ""
echo "[6/6] Building webapp for AMD64..."
cd webapp
docker buildx build \
    --platform linux/amd64 \
    --tag ${REGISTRY}/${NAMESPACE}/webapp:latest \
    --push \
    --progress=plain \
    .
cd ..

echo ""
echo "========================================"
echo "Building Third-Party Images for AMD64..."
echo "========================================"

# Array of third-party images
THIRD_PARTY_IMAGES=(
    "timescale/timescaledb:latest-pg14"
    "redis:7-alpine"
    "prom/prometheus:latest"
    "grafana/grafana:latest"
    "grafana/loki:latest"
    "grafana/promtail:latest"
    "grafana/tempo:latest"
)

for image in "${THIRD_PARTY_IMAGES[@]}"; do
    echo ""
    echo "Processing: $image"
    
    # Pull for AMD64 specifically
    echo "  Pulling AMD64 version from Docker Hub..."
    docker pull --platform linux/amd64 "$image"
    
    # Get the image ID of the AMD64 version
    IMAGE_ID=$(docker images --format "{{.ID}}" "$image" | head -1)
    echo "  Image ID: $IMAGE_ID"
    
    # Tag it for our registry
    TARGET="${REGISTRY}/${image}"
    echo "  Tagging as: $TARGET"
    docker tag "$IMAGE_ID" "$TARGET"
    
    # Push to registry
    echo "  Pushing to registry..."
    docker push "$TARGET"
    
    echo "  ✅ Done: $image"
done

echo ""
echo "========================================"
echo "✅ All images rebuilt for AMD64!"
echo "========================================"
echo ""
echo "Images pushed to registry:"
echo "  Custom Services (6):"
echo "    - ${REGISTRY}/${NAMESPACE}/api-gateway:latest"
echo "    - ${REGISTRY}/${NAMESPACE}/timeseries-service:latest"
echo "    - ${REGISTRY}/${NAMESPACE}/forecast-service:latest"
echo "    - ${REGISTRY}/${NAMESPACE}/optimize-service:latest"
echo "    - ${REGISTRY}/${NAMESPACE}/scheduler-service:latest"
echo "    - ${REGISTRY}/${NAMESPACE}/webapp:latest"
echo ""
echo "  Third-Party Services (7):"
for image in "${THIRD_PARTY_IMAGES[@]}"; do
    echo "    - ${REGISTRY}/${image}"
done
echo ""
echo "Next steps:"
echo "  1. Deploy docker-compose.core-only.yml in Portainer"
echo "  2. Verify all services start successfully"
echo "  3. Deploy full docker-compose.portainer.yml with observability"
echo ""
