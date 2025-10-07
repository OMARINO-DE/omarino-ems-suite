#!/bin/bash
# Health check script for all OMARINO EMS containers

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║        OMARINO EMS Suite - Container Health Check        ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check container status
check_container() {
    local container_name=$1
    local expected_port=$2
    local health_endpoint=$3
    
    echo -e "${BLUE}Checking: ${container_name}${NC}"
    
    # Check if container exists
    if ! docker ps -a --format '{{.Names}}' | grep -q "^${container_name}$"; then
        echo -e "${RED}  ✗ Container does not exist${NC}\n"
        return 1
    fi
    
    # Check if container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
        echo -e "${RED}  ✗ Container is not running${NC}"
        echo -e "    Status: $(docker ps -a --filter name=${container_name} --format '{{.Status}}')"
        echo ""
        return 1
    fi
    
    echo -e "${GREEN}  ✓ Container is running${NC}"
    
    # Get container details
    local status=$(docker inspect --format='{{.State.Status}}' ${container_name})
    local uptime=$(docker inspect --format='{{.State.StartedAt}}' ${container_name})
    local restart_count=$(docker inspect --format='{{.RestartCount}}' ${container_name})
    
    echo "    Status: ${status}"
    echo "    Started: ${uptime}"
    echo "    Restart count: ${restart_count}"
    
    # Check port
    if [ ! -z "$expected_port" ]; then
        local ports=$(docker port ${container_name} 2>/dev/null || echo "none")
        echo "    Ports: ${ports:-none}"
    fi
    
    # Check health endpoint if provided
    if [ ! -z "$health_endpoint" ]; then
        if curl -sf "$health_endpoint" > /dev/null 2>&1; then
            echo -e "${GREEN}    ✓ Health endpoint responding${NC}"
        else
            echo -e "${YELLOW}    ! Health endpoint not responding${NC}"
        fi
    fi
    
    # Check recent logs for errors
    local error_count=$(docker logs ${container_name} --tail 50 2>&1 | grep -i "error\|exception\|fatal" | wc -l | tr -d ' ')
    if [ "$error_count" -gt 0 ]; then
        echo -e "${YELLOW}    ! Found ${error_count} errors in recent logs${NC}"
    else
        echo -e "${GREEN}    ✓ No recent errors in logs${NC}"
    fi
    
    echo ""
}

echo "Container Health Status:"
echo "══════════════════════════════════════════════════════════"
echo ""

# Check all OMARINO containers
check_container "omarino-postgres" "5432" ""
check_container "omarino-forecast" "8082" "http://localhost:8082/api/health"
check_container "omarino-optimize" "8083" "http://localhost:8083/api/health"
check_container "omarino-webapp" "3000" "http://localhost:3000"
check_container "omarino-gateway" "8081" "http://localhost:8081/health"
check_container "omarino-timeseries" "8084" ""

# Summary
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                    Summary                                ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Count running containers
running=$(docker ps --filter name=omarino- --format '{{.Names}}' | wc -l | tr -d ' ')
total=$(docker ps -a --filter name=omarino- --format '{{.Names}}' | wc -l | tr -d ' ')

echo "Running containers: ${running}/${total}"
echo ""

# List all omarino containers
echo "All OMARINO containers:"
docker ps -a --filter name=omarino- --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# Network info
echo "Network connectivity:"
if docker network inspect ems_omarino-network >/dev/null 2>&1; then
    echo -e "${GREEN}✓ ems_omarino-network exists${NC}"
    container_count=$(docker network inspect ems_omarino-network --format '{{len .Containers}}')
    echo "  Containers connected: ${container_count}"
else
    echo -e "${RED}✗ ems_omarino-network not found${NC}"
fi
echo ""

# Database connectivity test
echo "Database connectivity:"
if docker exec omarino-postgres psql -U omarino -d omarino -c "SELECT 1" >/dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL responding${NC}"
    
    # Check for our tables
    if docker exec omarino-postgres psql -U omarino -d omarino -c "SELECT COUNT(*) FROM forecast_jobs" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Database schema exists${NC}"
        
        # Count records
        forecast_count=$(docker exec omarino-postgres psql -U omarino -d omarino -t -c "SELECT COUNT(*) FROM forecast_jobs" 2>/dev/null | tr -d ' ')
        optimization_count=$(docker exec omarino-postgres psql -U omarino -d omarino -t -c "SELECT COUNT(*) FROM optimization_jobs" 2>/dev/null | tr -d ' ')
        
        echo "  Forecasts saved: ${forecast_count:-0}"
        echo "  Optimizations saved: ${optimization_count:-0}"
    else
        echo -e "${YELLOW}! Database schema not found${NC}"
    fi
else
    echo -e "${RED}✗ PostgreSQL not responding${NC}"
fi
echo ""

# Service-specific checks
echo "Service-specific checks:"

# Check forecast service database connection
if docker logs omarino-forecast 2>&1 | tail -100 | grep -q "forecast_database_connected"; then
    echo -e "${GREEN}✓ Forecast service connected to database${NC}"
else
    echo -e "${YELLOW}! Forecast service database connection not confirmed${NC}"
fi

# Check optimize service database connection
if docker logs omarino-optimize 2>&1 | tail -100 | grep -q "optimization_database_connected"; then
    echo -e "${GREEN}✓ Optimize service connected to database${NC}"
else
    echo -e "${YELLOW}! Optimize service database connection not confirmed${NC}"
fi
echo ""

# Resource usage
echo "Resource usage (top 5 containers by memory):"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep omarino | head -6
echo ""

# Recent container restarts
echo "Recent activity:"
for container in $(docker ps --filter name=omarino- --format '{{.Names}}'); do
    last_log=$(docker logs ${container} --tail 1 2>&1 | head -1)
    if [ ! -z "$last_log" ]; then
        echo "  ${container}: ${last_log:0:60}..."
    fi
done
echo ""

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                  Health Check Complete                    ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "To view detailed logs:"
echo "  docker logs omarino-forecast --tail 50"
echo "  docker logs omarino-optimize --tail 50"
echo "  docker logs omarino-webapp --tail 50"
echo ""
echo "To restart a service:"
echo "  docker restart omarino-forecast"
echo ""
