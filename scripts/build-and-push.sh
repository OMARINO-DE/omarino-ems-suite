#!/bin/bash

# OMARINO EMS - Multi-platform Docker Build and Push Script
set -e

# Configuration
REGISTRY="192.168.61.21:32768"
PROJECT_NAME="omarino-ems"
PLATFORMS="linux/amd64,linux/arm64"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker buildx is available
check_buildx() {
    if ! docker buildx version >/dev/null 2>&1; then
        log_error "Docker buildx is not available. Please install Docker Desktop or enable buildx."
        exit 1
    fi
    log_success "Docker buildx is available"
}

# Create buildx builder for multi-platform builds
setup_builder() {
    log_info "Setting up buildx builder for multi-platform builds..."
    
    # Check if builder already exists
    if docker buildx inspect omarino-builder >/dev/null 2>&1; then
        log_info "Builder 'omarino-builder' already exists"
        docker buildx use omarino-builder
    else
        log_info "Creating new builder 'omarino-builder'"
        docker buildx create --name omarino-builder --use --bootstrap
    fi
    
    log_success "Builder setup complete"
}

# Test registry connectivity
test_registry() {
    log_info "Testing registry connectivity to ${REGISTRY}..."
    
    # Try to ping the registry
    if curl -f -s "http://${REGISTRY}/v2/" >/dev/null 2>&1; then
        log_success "Registry is accessible"
    else
        log_warning "Registry might not be accessible or requires authentication"
        log_info "Continuing anyway - docker push will fail if registry is not accessible"
    fi
}

# Pull and push third-party images to private registry
push_third_party_images() {
    log_info "Pulling and pushing third-party images to private registry..."
    
    declare -a images=(
        "timescale/timescaledb:latest-pg14"
        "redis:7-alpine"
        "prom/prometheus:latest"
        "grafana/grafana:latest"
        "grafana/loki:latest"
        "grafana/promtail:latest"
        "grafana/tempo:latest"
    )
    
    for image in "${images[@]}"; do
        log_info "Processing $image..."
        
        # Extract image name without registry
        image_name=$(echo $image | sed 's|.*/||')
        target_image="${REGISTRY}/${image}"
        
        # Pull the image for both platforms
        log_info "Pulling $image for multiple platforms..."
        docker buildx imagetools create --tag "$target_image" "$image"
        
        log_success "Pushed $image to $target_image"
    done
}

# Build and push custom application images
build_and_push_services() {
    log_info "Building and pushing custom services..."
    
    declare -a services=(
        "api-gateway"
        "timeseries-service"
        "forecast-service"
        "optimize-service"
        "scheduler-service"
        "webapp"
    )
    
    for service in "${services[@]}"; do
        log_info "Building and pushing $service..."
        
        if [ -d "$service" ]; then
            cd "$service"
            
            # Build and push for multiple platforms
            docker buildx build \
                --platform "$PLATFORMS" \
                --tag "${REGISTRY}/${PROJECT_NAME}/${service}:latest" \
                --tag "${REGISTRY}/${PROJECT_NAME}/${service}:$(date +%Y%m%d-%H%M%S)" \
                --push \
                .
                
            log_success "Built and pushed $service"
            cd ..
        else
            log_error "Directory $service not found!"
            exit 1
        fi
    done
}

# Verify images in registry
verify_images() {
    log_info "Verifying images in registry..."
    
    # List custom images
    log_info "Custom application images:"
    declare -a services=("api-gateway" "timeseries-service" "forecast-service" "optimize-service" "scheduler-service" "webapp")
    
    for service in "${services[@]}"; do
        image="${REGISTRY}/${PROJECT_NAME}/${service}:latest"
        if docker manifest inspect "$image" >/dev/null 2>&1; then
            log_success "$image - OK"
        else
            log_error "$image - FAILED"
        fi
    done
}

# Main execution
main() {
    log_info "Starting OMARINO EMS multi-platform build and push process..."
    log_info "Registry: $REGISTRY"
    log_info "Platforms: $PLATFORMS"
    echo ""
    
    check_buildx
    setup_builder
    test_registry
    
    # Ask user what to do
    echo ""
    log_info "What would you like to do?"
    echo "1) Push third-party images only"
    echo "2) Build and push custom services only"
    echo "3) Do both (recommended for first-time setup)"
    echo "4) Verify existing images"
    read -p "Enter your choice (1-4): " choice
    
    case $choice in
        1)
            push_third_party_images
            ;;
        2)
            build_and_push_services
            ;;
        3)
            push_third_party_images
            build_and_push_services
            ;;
        4)
            verify_images
            ;;
        *)
            log_error "Invalid choice. Exiting."
            exit 1
            ;;
    esac
    
    echo ""
    log_success "Process completed successfully!"
    log_info "You can now use 'docker-compose up' to start the OMARINO-EMS stack"
    log_info "Or use the Portainer-compatible compose file for stack deployment"
}

# Run main function
main "$@"