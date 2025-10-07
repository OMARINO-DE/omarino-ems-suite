#!/bin/bash
set -e

# OMARINO EMS - End-to-End Test Script
# Tests the complete system flow from data ingestion to visualization

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_BASE_URL="http://localhost:8080"
RETRY_COUNT=30
RETRY_INTERVAL=2

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

print_header() {
    echo -e "\n${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}\n"
}

print_test() {
    echo -e "${YELLOW}TEST: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
    ((TESTS_PASSED++))
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    ((TESTS_FAILED++))
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Wait for services to be ready
wait_for_services() {
    print_header "Waiting for Services"
    
    for i in $(seq 1 $RETRY_COUNT); do
        if curl -s -f "$API_BASE_URL/health" > /dev/null 2>&1; then
            print_success "All services are ready!"
            return 0
        fi
        echo -ne "  Retry $i/$RETRY_COUNT...\r"
        sleep $RETRY_INTERVAL
    done
    
    print_error "Services did not become ready in time"
    return 1
}

# Test 1: Authentication
test_authentication() {
    print_header "Test 1: Authentication"
    
    print_test "Logging in with demo credentials"
    RESPONSE=$(curl -s -X POST "$API_BASE_URL/api/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"username":"demo","password":"demo123"}')
    
    TOKEN=$(echo $RESPONSE | jq -r '.token')
    
    if [ "$TOKEN" != "null" ] && [ ! -z "$TOKEN" ]; then
        print_success "Authentication successful, token received"
        export AUTH_TOKEN="Bearer $TOKEN"
    else
        print_error "Authentication failed"
        return 1
    fi
}

# Test 2: Health Checks
test_health_checks() {
    print_header "Test 2: Health Checks"
    
    print_test "Checking API Gateway health"
    if curl -s -f "$API_BASE_URL/health" > /dev/null; then
        print_success "API Gateway is healthy"
    else
        print_error "API Gateway health check failed"
    fi
    
    print_test "Checking all services health"
    HEALTH_RESPONSE=$(curl -s "$API_BASE_URL/api/health/services")
    HEALTHY_SERVICES=$(echo $HEALTH_RESPONSE | jq -r '.services[] | select(.status=="Healthy") | .name' | wc -l)
    
    if [ $HEALTHY_SERVICES -ge 4 ]; then
        print_success "All critical services are healthy ($HEALTHY_SERVICES services)"
    else
        print_error "Some services are unhealthy"
    fi
}

# Test 3: Create Meter
test_create_meter() {
    print_header "Test 3: Create Meter"
    
    print_test "Creating a test meter"
    METER_DATA='{
        "id": "test-meter-001",
        "name": "Test Building Load",
        "location": "Test Building",
        "type": "Electric",
        "unit": "kW",
        "metadata": {
            "description": "Test meter for E2E testing"
        }
    }'
    
    RESPONSE=$(curl -s -X POST "$API_BASE_URL/api/timeseries/meters" \
        -H "Content-Type: application/json" \
        -H "Authorization: $AUTH_TOKEN" \
        -d "$METER_DATA" \
        -w "\n%{http_code}")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
    
    if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "201" ] || [ "$HTTP_CODE" == "409" ]; then
        print_success "Meter created or already exists"
    else
        print_error "Failed to create meter (HTTP $HTTP_CODE)"
    fi
}

# Test 4: Ingest Time Series Data
test_ingest_data() {
    print_header "Test 4: Ingest Time Series Data"
    
    print_test "Ingesting time series data"
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    INGEST_DATA='{
        "meterId": "test-meter-001",
        "seriesId": "test-meter-001-load",
        "dataPoints": [
            {"timestamp": "'$TIMESTAMP'", "value": 123.45, "quality": "Good"}
        ]
    }'
    
    RESPONSE=$(curl -s -X POST "$API_BASE_URL/api/timeseries/ingest" \
        -H "Content-Type: application/json" \
        -H "Authorization: $AUTH_TOKEN" \
        -d "$INGEST_DATA" \
        -w "\n%{http_code}")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
    
    if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "201" ]; then
        print_success "Data ingested successfully"
    else
        print_error "Failed to ingest data (HTTP $HTTP_CODE)"
    fi
}

# Test 5: Query Time Series Data
test_query_data() {
    print_header "Test 5: Query Time Series Data"
    
    print_test "Querying time series data"
    RESPONSE=$(curl -s "$API_BASE_URL/api/timeseries/series/test-meter-001-load/data?limit=10" \
        -H "Authorization: $AUTH_TOKEN")
    
    DATA_COUNT=$(echo $RESPONSE | jq '. | length')
    
    if [ "$DATA_COUNT" -gt 0 ]; then
        print_success "Retrieved $DATA_COUNT data points"
    else
        print_error "Failed to retrieve data"
    fi
}

# Test 6: List Forecast Models
test_forecast_models() {
    print_header "Test 6: List Forecast Models"
    
    print_test "Listing available forecast models"
    RESPONSE=$(curl -s "$API_BASE_URL/api/forecast/models" \
        -H "Authorization: $AUTH_TOKEN")
    
    MODEL_COUNT=$(echo $RESPONSE | jq '. | length')
    
    if [ "$MODEL_COUNT" -gt 0 ]; then
        print_success "Found $MODEL_COUNT forecast models"
    else
        print_error "Failed to retrieve forecast models"
    fi
}

# Test 7: Run Forecast (if enough data)
test_run_forecast() {
    print_header "Test 7: Run Forecast"
    
    print_test "Running ARIMA forecast"
    FORECAST_REQUEST='{
        "seriesId": "meter-001-load",
        "model": "arima",
        "horizon": 24,
        "frequency": "15min"
    }'
    
    RESPONSE=$(curl -s -X POST "$API_BASE_URL/api/forecast/models/arima/forecast" \
        -H "Content-Type: application/json" \
        -H "Authorization: $AUTH_TOKEN" \
        -d "$FORECAST_REQUEST" \
        -w "\n%{http_code}")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
    BODY=$(echo "$RESPONSE" | head -n -1)
    
    if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "201" ]; then
        FORECAST_ID=$(echo $BODY | jq -r '.id')
        print_success "Forecast created (ID: $FORECAST_ID)"
        export FORECAST_ID
    else
        print_error "Failed to run forecast (HTTP $HTTP_CODE)"
    fi
}

# Test 8: List Optimization Types
test_optimization_types() {
    print_header "Test 8: List Optimization Types"
    
    print_test "Listing optimization types"
    RESPONSE=$(curl -s "$API_BASE_URL/api/optimize/types" \
        -H "Authorization: $AUTH_TOKEN")
    
    TYPE_COUNT=$(echo $RESPONSE | jq '. | length')
    
    if [ "$TYPE_COUNT" -gt 0 ]; then
        print_success "Found $TYPE_COUNT optimization types"
    else
        print_error "Failed to retrieve optimization types"
    fi
}

# Test 9: Create Optimization
test_create_optimization() {
    print_header "Test 9: Create Optimization"
    
    print_test "Creating battery dispatch optimization"
    OPTIMIZATION_REQUEST='{
        "type": "battery_dispatch",
        "parameters": {
            "batteryCapacity": 100,
            "batteryPower": 50,
            "initialSoc": 50,
            "minSoc": 20,
            "maxSoc": 90,
            "efficiency": 0.95,
            "horizon": 24,
            "timeStep": 1,
            "demandForecast": [50, 52, 54, 56, 58, 60, 62, 64, 66, 68, 70, 72, 74, 76, 78, 80, 75, 70, 65, 60, 55, 50, 48, 46],
            "electricityPrices": [0.10, 0.10, 0.10, 0.10, 0.12, 0.15, 0.20, 0.25, 0.22, 0.20, 0.18, 0.18, 0.18, 0.18, 0.20, 0.25, 0.30, 0.28, 0.25, 0.20, 0.15, 0.12, 0.10, 0.10]
        }
    }'
    
    RESPONSE=$(curl -s -X POST "$API_BASE_URL/api/optimize" \
        -H "Content-Type: application/json" \
        -H "Authorization: $AUTH_TOKEN" \
        -d "$OPTIMIZATION_REQUEST" \
        -w "\n%{http_code}")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
    BODY=$(echo "$RESPONSE" | head -n -1)
    
    if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "201" ] || [ "$HTTP_CODE" == "202" ]; then
        OPTIMIZATION_ID=$(echo $BODY | jq -r '.id')
        print_success "Optimization created (ID: $OPTIMIZATION_ID)"
        export OPTIMIZATION_ID
    else
        print_error "Failed to create optimization (HTTP $HTTP_CODE)"
    fi
}

# Test 10: Create Workflow
test_create_workflow() {
    print_header "Test 10: Create Workflow"
    
    print_test "Creating automated workflow"
    WORKFLOW_DATA='{
        "name": "Daily Forecast and Optimization",
        "description": "Automated daily workflow for forecasting and optimization",
        "schedule": {
            "type": "Manual"
        },
        "tasks": [
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "name": "Run Forecast",
                "type": "HttpCall",
                "dependsOn": [],
                "config": {
                    "method": "POST",
                    "url": "http://forecast-service:8001/forecast",
                    "headers": {"Content-Type": "application/json"},
                    "body": "{\"seriesId\":\"meter-001-load\",\"model\":\"arima\",\"horizon\":24}"
                }
            }
        ]
    }'
    
    RESPONSE=$(curl -s -X POST "$API_BASE_URL/api/workflows" \
        -H "Content-Type: application/json" \
        -H "Authorization: $AUTH_TOKEN" \
        -d "$WORKFLOW_DATA" \
        -w "\n%{http_code}")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
    BODY=$(echo "$RESPONSE" | head -n -1)
    
    if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "201" ]; then
        WORKFLOW_ID=$(echo $BODY | jq -r '.id')
        print_success "Workflow created (ID: $WORKFLOW_ID)"
        export WORKFLOW_ID
    else
        print_error "Failed to create workflow (HTTP $HTTP_CODE)"
    fi
}

# Test 11: Prometheus Metrics
test_prometheus_metrics() {
    print_header "Test 11: Prometheus Metrics"
    
    print_test "Checking Prometheus endpoint"
    if curl -s -f "http://localhost:9090/-/healthy" > /dev/null; then
        print_success "Prometheus is accessible"
    else
        print_error "Prometheus is not accessible"
    fi
}

# Test 12: Grafana
test_grafana() {
    print_header "Test 12: Grafana"
    
    print_test "Checking Grafana endpoint"
    if curl -s -f "http://localhost:3001/api/health" > /dev/null; then
        print_success "Grafana is accessible"
    else
        print_error "Grafana is not accessible"
    fi
}

# Print summary
print_summary() {
    print_header "Test Summary"
    
    TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
    
    echo -e "Total Tests: $TOTAL_TESTS"
    echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"
    echo ""
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}✅ All tests passed!${NC}"
        return 0
    else
        echo -e "${RED}❌ Some tests failed${NC}"
        return 1
    fi
}

# Main execution
main() {
    print_header "OMARINO EMS - End-to-End Test Suite"
    
    wait_for_services || exit 1
    
    test_authentication || exit 1
    test_health_checks
    test_create_meter
    test_ingest_data
    test_query_data
    test_forecast_models
    test_run_forecast
    test_optimization_types
    test_create_optimization
    test_create_workflow
    test_prometheus_metrics
    test_grafana
    
    print_summary
}

# Run main function
main
exit $?
