#!/bin/bash

# Asset Service Test Script
# Creates sample assets for testing

set -e

SERVER="http://192.168.75.20:8003"
API_PREFIX="/api/assets"

echo "=========================================="
echo "OMARINO Asset Service - Test Data Creation"
echo "=========================================="
echo ""

# First, create a test site
echo "Step 1: Creating test site..."
SITE_RESPONSE=$(curl -s -X POST "${SERVER}${API_PREFIX}/sites" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Demo Site 1",
    "description": "Test site for development",
    "location": "Test Location",
    "latitude": 52.5200,
    "longitude": 13.4050,
    "timezone": "Europe/Berlin"
  }' || echo '{"error": "Failed to create site"}')

SITE_ID=$(echo "$SITE_RESPONSE" | grep -o '"site_id":"[^"]*"' | cut -d'"' -f4 || echo "")

if [ -z "$SITE_ID" ]; then
    echo "⚠️  Could not create site. Using a dummy UUID for testing."
    SITE_ID="123e4567-e89b-12d3-a456-426614174000"
else
    echo "✓ Site created: $SITE_ID"
fi

echo ""
echo "Step 2: Creating test battery..."
BATTERY_RESPONSE=$(curl -s -X POST "${SERVER}${API_PREFIX}/batteries" \
  -H "Content-Type: application/json" \
  -d "{
    \"site_id\": \"$SITE_ID\",
    \"name\": \"Demo Battery 1\",
    \"description\": \"100 kWh lithium-ion battery for testing\",
    \"manufacturer\": \"Tesla\",
    \"model_number\": \"Powerpack 2\",
    \"serial_number\": \"TP2-DEMO-001\",
    \"installation_date\": \"2024-01-15\",
    \"chemistry\": \"lithium_ion\",
    \"capacity\": 100.0,
    \"usable_capacity\": 90.0,
    \"voltage\": 400.0,
    \"max_charge_rate\": 50.0,
    \"max_discharge_rate\": 50.0,
    \"efficiency\": 0.95,
    \"cycle_life\": 6000,
    \"depth_of_discharge\": 90.0,
    \"min_soc\": 10.0,
    \"max_soc\": 90.0
  }")

BATTERY_ID=$(echo "$BATTERY_RESPONSE" | grep -o '"asset_id":"[^"]*"' | cut -d'"' -f4 || echo "")

if [ -n "$BATTERY_ID" ]; then
    echo "✓ Battery created: $BATTERY_ID"
else
    echo "⚠️  Failed to create battery"
fi

echo ""
echo "Step 3: Creating test generator..."
GENERATOR_RESPONSE=$(curl -s -X POST "${SERVER}${API_PREFIX}/generators" \
  -H "Content-Type: application/json" \
  -d "{
    \"site_id\": \"$SITE_ID\",
    \"name\": \"Demo Generator 1\",
    \"description\": \"50 kW diesel generator for backup power\",
    \"manufacturer\": \"Caterpillar\",
    \"model_number\": \"CAT-D50\",
    \"serial_number\": \"CAT-DEMO-001\",
    \"installation_date\": \"2024-01-20\",
    \"rated_capacity_kw\": 50.0,
    \"max_output_kw\": 55.0,
    \"min_output_kw\": 10.0,
    \"generator_type\": \"diesel\",
    \"fuel_cost_per_kwh\": 0.15,
    \"startup_cost\": 5.0,
    \"shutdown_cost\": 2.0,
    \"min_uptime_hours\": 2.0,
    \"min_downtime_hours\": 1.0,
    \"co2_emissions_kg_per_kwh\": 0.8
  }")

GENERATOR_ID=$(echo "$GENERATOR_RESPONSE" | grep -o '"asset_id":"[^"]*"' | cut -d'"' -f4 || echo "")

if [ -n "$GENERATOR_ID" ]; then
    echo "✓ Generator created: $GENERATOR_ID"
else
    echo "⚠️  Failed to create generator"
fi

echo ""
echo "Step 4: Setting battery status..."
if [ -n "$BATTERY_ID" ]; then
    STATUS_RESPONSE=$(curl -s -X POST "${SERVER}${API_PREFIX}/status/${BATTERY_ID}" \
      -H "Content-Type: application/json" \
      -d '{
        "online": true,
        "operational_status": "running",
        "current_power_kw": 0.0,
        "current_soc": 75.0,
        "current_soh": 98.5,
        "temperature_c": 25.0
      }')
    
    if echo "$STATUS_RESPONSE" | grep -q "online"; then
        echo "✓ Battery status updated"
    else
        echo "⚠️  Failed to update battery status"
    fi
fi

echo ""
echo "Step 5: Testing API endpoints..."
echo ""

echo "5.1: Health Check"
curl -s "${SERVER}${API_PREFIX}/health" | jq '.' || echo "Failed"
echo ""

echo "5.2: List all assets"
curl -s "${SERVER}${API_PREFIX}/assets?limit=10" | jq '.total, .items[].name' || echo "Failed"
echo ""

echo "5.3: List batteries"
curl -s "${SERVER}${API_PREFIX}/batteries?limit=10" | jq '.total, .items[].name' || echo "Failed"
echo ""

echo "5.4: List generators"
curl -s "${SERVER}${API_PREFIX}/generators?limit=10" | jq '.total, .items[].name' || echo "Failed"
echo ""

echo "5.5: Dashboard summary"
curl -s "${SERVER}${API_PREFIX}/status/dashboard/summary" | jq '.' || echo "Failed"
echo ""

echo "=========================================="
echo "✓ Test Data Creation Complete!"
echo "=========================================="
echo ""
echo "Created Assets:"
if [ -n "$SITE_ID" ]; then
    echo "  - Site: $SITE_ID"
fi
if [ -n "$BATTERY_ID" ]; then
    echo "  - Battery: $BATTERY_ID (Demo Battery 1 - 100 kWh)"
fi
if [ -n "$GENERATOR_ID" ]; then
    echo "  - Generator: $GENERATOR_ID (Demo Generator 1 - 50 kW)"
fi
echo ""
echo "API Documentation:"
echo "  http://192.168.75.20:8003/api/assets/docs"
echo ""
echo "Next Steps:"
echo "  1. View assets in API docs"
echo "  2. Update workflow to use battery ID: $BATTERY_ID"
echo "  3. Test optimization workflow"
echo ""
