#!/bin/bash
# Build and push all Docker images to private registry
# Registry: 192.168.61.21:32768

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║   Building and Pushing Docker Images to Private Registry ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

REGISTRY="192.168.61.21:32768"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Check if we're on the server or need to use buildx
if command -v docker &> /dev/null; then
    echo -e "${BLUE}Docker found, proceeding with build...${NC}\n"
else
    echo -e "${YELLOW}Docker not found! Please ensure Docker is running.${NC}"
    exit 1
fi

# Function to build and push image
build_and_push() {
    local service_name=$1
    local service_dir=$2
    local port=$3
    
    echo -e "${BLUE}[Building] ${service_name}${NC}"
    echo "  Directory: ${service_dir}"
    echo "  Image: ${REGISTRY}/omarino-${service_name}:latest"
    echo ""
    
    # Build image
    echo "  Building Docker image..."
    if docker build -t ${REGISTRY}/omarino-${service_name}:latest \
                    -t ${REGISTRY}/omarino-${service_name}:${TIMESTAMP} \
                    ${service_dir}; then
        echo -e "${GREEN}  ✓ Build successful${NC}"
    else
        echo -e "${YELLOW}  ✗ Build failed${NC}"
        return 1
    fi
    
    # Push latest tag
    echo "  Pushing latest tag..."
    if docker push ${REGISTRY}/omarino-${service_name}:latest; then
        echo -e "${GREEN}  ✓ Pushed latest tag${NC}"
    else
        echo -e "${YELLOW}  ✗ Push failed${NC}"
        return 1
    fi
    
    # Push timestamp tag
    echo "  Pushing timestamp tag..."
    if docker push ${REGISTRY}/omarino-${service_name}:${TIMESTAMP}; then
        echo -e "${GREEN}  ✓ Pushed ${TIMESTAMP} tag${NC}"
    else
        echo -e "${YELLOW}  ✗ Push failed${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✓ ${service_name} complete${NC}\n"
}

# Get project root
cd "$(dirname "$0")"

# 1. Build and push forecast service
echo "═══════════════════════════════════════════════════════════"
build_and_push "forecast" "forecast-service" "8082"

# 2. Build and push optimize service
echo "═══════════════════════════════════════════════════════════"
build_and_push "optimize" "optimize-service" "8083"

# 3. Build and push webapp
echo "═══════════════════════════════════════════════════════════"
build_and_push "webapp" "webapp" "3000"

# 4. Build and push gateway (if exists)
if [ -d "gateway" ]; then
    echo "═══════════════════════════════════════════════════════════"
    build_and_push "gateway" "gateway" "8081"
fi

# 5. Build and push timeseries service (if exists)
if [ -d "timeseries-service" ]; then
    echo "═══════════════════════════════════════════════════════════"
    build_and_push "timeseries" "timeseries-service" "8084"
fi

# Summary
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                    Build Summary                          ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}✓ All images built and pushed successfully!${NC}"
echo ""
echo "Images pushed to registry: ${REGISTRY}"
echo ""
echo "Images available:"
echo "  • ${REGISTRY}/omarino-forecast:latest (and :${TIMESTAMP})"
echo "  • ${REGISTRY}/omarino-optimize:latest (and :${TIMESTAMP})"
echo "  • ${REGISTRY}/omarino-webapp:latest (and :${TIMESTAMP})"
if [ -d "gateway" ]; then
    echo "  • ${REGISTRY}/omarino-gateway:latest (and :${TIMESTAMP})"
fi
if [ -d "timeseries-service" ]; then
    echo "  • ${REGISTRY}/omarino-timeseries:latest (and :${TIMESTAMP})"
fi
echo ""
echo "Features included in these images:"
echo "  ✓ Database persistence for forecasts"
echo "  ✓ Database persistence for optimizations"
echo "  ✓ New API endpoints for history retrieval"
echo "  ✓ Updated webapp UI with forecast/optimization history"
echo "  ✓ Auto-refresh every 10 seconds"
echo "  ✓ Detailed modal views with charts"
echo ""
echo "Next steps:"
echo "  1. SSH to server: ssh omar@192.168.75.20"
echo "  2. Pull images: docker pull ${REGISTRY}/omarino-forecast:latest"
echo "  3. Or run: ./deploy-all.sh (pulls and deploys automatically)"
echo ""
