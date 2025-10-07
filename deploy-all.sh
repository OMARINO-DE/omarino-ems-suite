#!/bin/bash
# Complete deployment script for database persistence feature
# Run this on the server: ssh omar@192.168.75.20

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  OMARINO EMS Suite - Database Persistence Deployment     ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Navigate to project directory
cd ~/OMARINO-EMS-Suite

# 1. Pull latest code
echo -e "${BLUE}[1/5] Pulling latest code from GitHub...${NC}"
git pull origin main
echo -e "${GREEN}✓ Code updated${NC}\n"

# 2. Verify database schema
echo -e "${BLUE}[2/5] Verifying database schema...${NC}"
if docker exec omarino-postgres psql -U omarino -d omarino -c "SELECT COUNT(*) FROM forecast_jobs;" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Database schema already exists${NC}"
else
    echo -e "${YELLOW}! Database schema not found, applying migration...${NC}"
    docker exec -i omarino-postgres psql -U omarino -d omarino < timeseries-service/Migrations/20251007000000_AddForecastAndOptimizationTables.sql
    echo -e "${GREEN}✓ Database schema applied${NC}"
fi
echo ""

# 3. Deploy Forecast Service
echo -e "${BLUE}[3/5] Deploying Forecast Service...${NC}"
cd forecast-service

# Build image
echo "  Building Docker image..."
docker build -t 192.168.61.21:32768/omarino-forecast:latest . > /dev/null 2>&1
echo -e "${GREEN}  ✓ Image built${NC}"

# Push to registry
echo "  Pushing to registry..."
docker push 192.168.61.21:32768/omarino-forecast:latest > /dev/null 2>&1
echo -e "${GREEN}  ✓ Image pushed${NC}"

# Stop old container
echo "  Stopping old container..."
docker stop omarino-forecast 2>/dev/null || true
docker rm omarino-forecast 2>/dev/null || true

# Start new container
echo "  Starting new container..."
docker run -d \
  --name omarino-forecast \
  --network ems_omarino-network \
  -p 8082:8082 \
  -e DATABASE_URL="postgresql://omarino:omarino@omarino-postgres:5432/omarino" \
  --restart unless-stopped \
  192.168.61.21:32768/omarino-forecast:latest > /dev/null 2>&1

# Wait for startup
sleep 5

# Check health
if curl -s http://localhost:8082/api/health | grep -q "ok"; then
    echo -e "${GREEN}  ✓ Forecast service healthy${NC}"
    
    # Check database connection
    if docker logs omarino-forecast 2>&1 | grep -q "forecast_database_connected"; then
        echo -e "${GREEN}  ✓ Database connected${NC}"
    else
        echo -e "${YELLOW}  ! Database connection not confirmed in logs${NC}"
    fi
else
    echo -e "${RED}  ✗ Forecast service health check failed${NC}"
    docker logs omarino-forecast --tail 20
fi

cd ..
echo ""

# 4. Deploy Optimize Service
echo -e "${BLUE}[4/5] Deploying Optimize Service...${NC}"
cd optimize-service

# Build image
echo "  Building Docker image..."
docker build -t 192.168.61.21:32768/omarino-optimize:latest . > /dev/null 2>&1
echo -e "${GREEN}  ✓ Image built${NC}"

# Push to registry
echo "  Pushing to registry..."
docker push 192.168.61.21:32768/omarino-optimize:latest > /dev/null 2>&1
echo -e "${GREEN}  ✓ Image pushed${NC}"

# Stop old container
echo "  Stopping old container..."
docker stop omarino-optimize 2>/dev/null || true
docker rm omarino-optimize 2>/dev/null || true

# Start new container
echo "  Starting new container..."
docker run -d \
  --name omarino-optimize \
  --network ems_omarino-network \
  -p 8083:8083 \
  -e DATABASE_URL="postgresql://omarino:omarino@omarino-postgres:5432/omarino" \
  --restart unless-stopped \
  192.168.61.21:32768/omarino-optimize:latest > /dev/null 2>&1

# Wait for startup
sleep 5

# Check health
if curl -s http://localhost:8083/api/health | grep -q "ok"; then
    echo -e "${GREEN}  ✓ Optimize service healthy${NC}"
    
    # Check database connection
    if docker logs omarino-optimize 2>&1 | grep -q "optimization_database_connected"; then
        echo -e "${GREEN}  ✓ Database connected${NC}"
    else
        echo -e "${YELLOW}  ! Database connection not confirmed in logs${NC}"
    fi
else
    echo -e "${RED}  ✗ Optimize service health check failed${NC}"
    docker logs omarino-optimize --tail 20
fi

cd ..
echo ""

# 5. Deploy Webapp
echo -e "${BLUE}[5/5] Deploying Webapp...${NC}"
cd webapp

# Build image
echo "  Building Docker image..."
docker build -t 192.168.61.21:32768/omarino-webapp:latest . > /dev/null 2>&1
echo -e "${GREEN}  ✓ Image built${NC}"

# Push to registry
echo "  Pushing to registry..."
docker push 192.168.61.21:32768/omarino-webapp:latest > /dev/null 2>&1
echo -e "${GREEN}  ✓ Image pushed${NC}"

# Stop old container
echo "  Stopping old container..."
docker stop omarino-webapp 2>/dev/null || true
docker rm omarino-webapp 2>/dev/null || true

# Start new container
echo "  Starting new container..."
docker run -d \
  --name omarino-webapp \
  --network ems_omarino-network \
  -p 3000:3000 \
  --restart unless-stopped \
  192.168.61.21:32768/omarino-webapp:latest > /dev/null 2>&1

# Wait for startup
sleep 8

# Check health
if curl -s http://localhost:3000 | grep -q "OMARINO" || curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}  ✓ Webapp running${NC}"
else
    echo -e "${YELLOW}  ! Webapp may still be starting...${NC}"
fi

cd ..
echo ""

# Summary
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                   Deployment Summary                      ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}✓ All services deployed successfully!${NC}"
echo ""
echo "Services:"
echo "  • Forecast Service:     http://localhost:8082"
echo "  • Optimize Service:     http://localhost:8083"
echo "  • Webapp:              http://localhost:3000"
echo ""
echo "Public URLs:"
echo "  • API Gateway:         https://ems-back.omarino.net"
echo "  • Webapp:              https://ems-demo.omarino.net"
echo ""
echo "Verification Commands:"
echo "  # List forecasts"
echo "  curl https://ems-back.omarino.net/api/forecast/forecasts | jq '.'"
echo ""
echo "  # List optimizations"
echo "  curl https://ems-back.omarino.net/api/optimize/optimizations | jq '.'"
echo ""
echo "  # Check database"
echo "  docker exec omarino-postgres psql -U omarino -d omarino -c 'SELECT COUNT(*) FROM forecast_jobs;'"
echo ""
echo -e "${BLUE}Open webapp in browser: https://ems-demo.omarino.net${NC}"
echo ""
