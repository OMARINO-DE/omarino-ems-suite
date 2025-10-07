#!/bin/bash

# OMARINO EMS - Test Data Import Script
# This script imports test data into the OMARINO EMS database

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="omarino-postgres"
DB_USER="omarino"
DB_NAME="omarino"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}OMARINO EMS - Test Data Import${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Check if Docker container is running
echo -e "${YELLOW}Checking database connection...${NC}"
if ! sudo docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${RED}Error: PostgreSQL container '$CONTAINER_NAME' is not running${NC}"
    echo "Please start the container first: sudo docker start $CONTAINER_NAME"
    exit 1
fi

echo -e "${GREEN}✓ Database container is running${NC}"
echo ""

# Test database connection
if ! sudo docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${RED}Error: Cannot connect to database${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Database connection successful${NC}"
echo ""

# Import function
import_sql_file() {
    local file=$1
    local description=$2
    
    echo -e "${YELLOW}$description${NC}"
    if cat "$SCRIPT_DIR/$file" | sudo docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" 2>&1 | grep -E "ERROR|FATAL"; then
        echo -e "${RED}✗ Error importing $file${NC}"
        return 1
    else
        echo -e "${GREEN}✓ $file imported successfully${NC}"
        echo ""
        return 0
    fi
}

# Import all files in sequence
import_sql_file "01-meters.sql" "Step 1/5: Creating test meters..."
import_sql_file "02-series.sql" "Step 2/5: Creating time series definitions..."

echo -e "${YELLOW}Step 3/5: Generating time series data (this may take 1-2 minutes)...${NC}"
cat "$SCRIPT_DIR/03-timeseries-data.sql" | sudo docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" > /tmp/import_output.log 2>&1
if grep -E "ERROR|FATAL" /tmp/import_output.log > /dev/null; then
    echo -e "${RED}✗ Error importing timeseries data${NC}"
    cat /tmp/import_output.log | grep -E "ERROR|FATAL"
    exit 1
else
    echo -e "${GREEN}✓ Time series data generated successfully${NC}"
    echo ""
fi

import_sql_file "04-forecasts.sql" "Step 4/5: Creating sample forecasts..."
import_sql_file "05-optimizations.sql" "Step 5/5: Creating sample optimizations..."

# Display summary
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Import Complete!${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo -e "${GREEN}Summary:${NC}"

sudo docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "
SELECT 
  'Meters' as type,
  COUNT(*)::TEXT as count
FROM meters
WHERE name LIKE 'TEST_%'
UNION ALL
SELECT 
  'Series' as type,
  COUNT(*)::TEXT
FROM meter_series ms
JOIN meters m ON ms.meter_id = m.meter_id
WHERE m.name LIKE 'TEST_%'
UNION ALL
SELECT 
  'Data Points' as type,
  COUNT(*)::TEXT
FROM time_series_data tsd
JOIN meter_series ms ON tsd.series_id = ms.series_id
JOIN meters m ON ms.meter_id = m.meter_id
WHERE m.name LIKE 'TEST_%'
UNION ALL
SELECT 
  'Forecasts' as type,
  COUNT(*)::TEXT
FROM forecast_jobs f
JOIN meter_series ms ON f.series_id = ms.series_id::TEXT
JOIN meters m ON ms.meter_id = m.meter_id
WHERE m.name LIKE 'TEST_%'
UNION ALL
SELECT 
  'Optimizations' as type,
  COUNT(*)::TEXT
FROM optimization_jobs;" -t

echo ""
echo -e "${GREEN}Test data has been imported successfully!${NC}"
echo "You can now access the data through:"
echo "  • Web UI: https://ems-demo.omarino.net"
echo "  • API: https://ems-back.omarino.net/api"
echo ""
echo -e "${YELLOW}Note: All test data is prefixed with 'TEST_' for easy identification${NC}"
echo ""
