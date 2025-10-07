# OMARINO EMS - Operational Runbook

Complete guide for running, testing, and operating the OMARINO Energy Management System.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [System Startup](#system-startup)
- [Sample Data Import](#sample-data-import)
- [End-to-End Testing](#end-to-end-testing)
- [Manual Testing Procedures](#manual-testing-procedures)
- [Common Operations](#common-operations)
- [Troubleshooting](#troubleshooting)
- [Monitoring and Observability](#monitoring-and-observability)
- [Backup and Recovery](#backup-and-recovery)
- [System Shutdown](#system-shutdown)

---

## 🚀 Quick Start

### Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- 8GB RAM minimum
- 20GB free disk space
- Ports available: 3000, 3001, 5001, 5432, 6379, 8001, 8002, 8003, 8080, 9090

### 5-Minute Setup

```bash
# 1. Navigate to project directory
cd "OMARINO EMS Suite"

# 2. Copy environment configuration
cp .env.example .env

# 3. Start all services
make up

# 4. Wait for services (takes ~2 minutes)
# Watch logs: make logs

# 5. Import sample data
./scripts/import-sample-data.py

# 6. Open web UI
open http://localhost:3000
# Or: make open-webapp
```

---

## 🔧 System Startup

### Step 1: Environment Configuration

Create `.env` file from template:

```bash
cp .env.example .env
```

**Important:** Change these values in production:

```bash
# Security (MUST CHANGE)
POSTGRES_PASSWORD=your-strong-password
REDIS_PASSWORD=your-redis-password
JWT_SECRET_KEY=$(openssl rand -base64 32)
NEXTAUTH_SECRET=$(openssl rand -base64 32)
```

### Step 2: Start Infrastructure

Start all services with Docker Compose:

```bash
# Using Make (recommended)
make up

# Or using docker-compose directly
docker-compose up -d
```

Services will start in this order:
1. PostgreSQL + Redis (databases)
2. Core services (timeseries, forecast, optimize, scheduler)
3. API Gateway
4. Web Application
5. Observability stack (Prometheus, Grafana, Loki, Tempo)

### Step 3: Verify Services

Check that all services are running:

```bash
# Using Make
make ps

# Or docker-compose
docker-compose ps
```

Expected output: All services should show status "Up" or "Up (healthy)".

Check service health:

```bash
# Using Make
make health

# Or manually
curl http://localhost:8080/health | jq
```

### Step 4: Wait for Initialization

Services need time to initialize:
- **PostgreSQL**: ~10 seconds (database initialization)
- **Backend Services**: ~30 seconds (EF Core migrations, model loading)
- **Web Application**: ~20 seconds (Next.js build)
- **Observability**: ~15 seconds (Prometheus scraping)

**Total startup time: ~2 minutes**

Monitor startup:

```bash
# Watch all logs
make logs

# Watch specific service
make logs-timeseries
make logs-forecast
```

---

## 📊 Sample Data Import

### Overview

Sample data includes:
- **6 meters**: Building loads, solar generation, battery, HVAC, chiller, EV charging
- **200+ data points**: 24 hours of data at 15-minute intervals
- **2 series**: Building load and solar generation

### Automated Import

Run the import script:

```bash
# Make script executable (first time only)
chmod +x scripts/import-sample-data.py

# Run import
./scripts/import-sample-data.py

# Or using Python directly
python3 scripts/import-sample-data.py
```

Script will:
1. Wait for services to be ready (up to 60 seconds)
2. Authenticate with API Gateway
3. Import 6 meters
4. Import 200+ time series data points in batches
5. Verify successful import

Expected output:
```
============================================================
OMARINO EMS - Sample Data Import
============================================================

ℹ️  Waiting for services to be ready...
✅ All services are ready!
ℹ️  Authenticating with API Gateway...
✅ Authentication successful!

ℹ️  Importing meters from sample-data/meters.csv...
  ✓ Imported meter: meter-001 - Building A Main Feed
  ✓ Imported meter: meter-002 - Building A Solar
  ...
✅ Imported 6 meters

ℹ️  Importing time series data from sample-data/time_series.csv...
ℹ️  Found 200 data points to import
  ✓ Imported batch for meter-001-load: 96 points (96/200)
  ✓ Imported batch for meter-002-generation: 96 points (192/200)
  ...
✅ Imported 200/200 data points

ℹ️  Verifying imported data...
✅ Found 6 meters in database
✅ Found 2 time series for meter meter-001
✅ Found 96 data points for series meter-001-load

============================================================
✅ Sample data import complete!
============================================================
```

### Manual Import (API)

#### 1. Authenticate

```bash
TOKEN=$(curl -s -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo123"}' | jq -r '.token')

echo "Token: $TOKEN"
```

#### 2. Create Meter

```bash
curl -X POST http://localhost:8080/api/timeseries/meters \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "id": "meter-001",
    "name": "Building A Main Feed",
    "location": "Building A - Ground Floor",
    "type": "Electric",
    "unit": "kW",
    "metadata": {
      "description": "Main electrical feed"
    }
  }'
```

#### 3. Ingest Data

```bash
curl -X POST http://localhost:8080/api/timeseries/ingest \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "meterId": "meter-001",
    "seriesId": "meter-001-load",
    "dataPoints": [
      {
        "timestamp": "2024-10-01T12:00:00Z",
        "value": 245.5,
        "quality": "Good"
      }
    ]
  }'
```

---

## 🧪 End-to-End Testing

### Automated E2E Test Suite

Run comprehensive test suite:

```bash
# Make script executable (first time only)
chmod +x scripts/e2e-test.sh

# Run tests
./scripts/e2e-test.sh
```

Tests performed:
1. ✅ Authentication (JWT login)
2. ✅ Health checks (all services)
3. ✅ Create meter
4. ✅ Ingest time series data
5. ✅ Query time series data
6. ✅ List forecast models
7. ✅ Run forecast
8. ✅ List optimization types
9. ✅ Create optimization
10. ✅ Create workflow
11. ✅ Prometheus metrics
12. ✅ Grafana dashboard

Expected output:
```
============================================================
OMARINO EMS - End-to-End Test Suite
============================================================

============================================================
Waiting for Services
============================================================

✅ All services are ready!

============================================================
Test 1: Authentication
============================================================

TEST: Logging in with demo credentials
✅ Authentication successful, token received

...

============================================================
Test Summary
============================================================

Total Tests: 12
Passed: 12
Failed: 0

✅ All tests passed!
```

---

## 🔬 Manual Testing Procedures

### Test 1: Time Series Ingestion and Query

#### 1.1 Create Meter via Web UI

1. Open http://localhost:3000
2. Navigate to **Time Series** page
3. Click **Import Data**
4. Upload `sample-data/meters.csv`

#### 1.2 Ingest Data via API

```bash
# Get auth token
TOKEN=$(curl -s -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo123"}' | jq -r '.token')

# Ingest data
curl -X POST http://localhost:8080/api/timeseries/ingest \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "meterId": "meter-001",
    "seriesId": "meter-001-load",
    "dataPoints": [
      {"timestamp": "2024-10-01T12:00:00Z", "value": 245.5, "quality": "Good"},
      {"timestamp": "2024-10-01T12:15:00Z", "value": 248.2, "quality": "Good"},
      {"timestamp": "2024-10-01T12:30:00Z", "value": 251.7, "quality": "Good"}
    ]
  }'
```

#### 1.3 Query Data

```bash
# Query latest data
curl "http://localhost:8080/api/timeseries/series/meter-001-load/data?limit=10" \
  -H "Authorization: Bearer $TOKEN" | jq

# Query with time range
curl "http://localhost:8080/api/timeseries/series/meter-001-load/data?start=2024-10-01T00:00:00Z&end=2024-10-01T23:59:59Z" \
  -H "Authorization: Bearer $TOKEN" | jq
```

#### 1.4 Verify in Database

```bash
# Open PostgreSQL shell
make db-shell

# Query meters
SELECT * FROM meters;

# Query time series
SELECT * FROM time_series LIMIT 10;

# Exit
\q
```

### Test 2: Forecasting

#### 2.1 List Available Models

```bash
curl http://localhost:8080/api/forecast/models \
  -H "Authorization: Bearer $TOKEN" | jq
```

Expected models: `arima`, `ets`, `naive`, `seasonal_naive`

#### 2.2 Run ARIMA Forecast

```bash
curl -X POST http://localhost:8080/api/forecast/models/arima/forecast \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "seriesId": "meter-001-load",
    "horizon": 24,
    "frequency": "15min"
  }' | jq
```

#### 2.3 Get Forecast Results

```bash
# Get forecast by ID
FORECAST_ID="<id-from-previous-step>"
curl "http://localhost:8080/api/forecast/forecasts/$FORECAST_ID" \
  -H "Authorization: Bearer $TOKEN" | jq
```

#### 2.4 Verify in Web UI

1. Open http://localhost:3000/forecasts
2. View recent forecasts
3. Click on forecast to see details and chart

### Test 3: Optimization

#### 3.1 List Optimization Types

```bash
curl http://localhost:8080/api/optimize/types \
  -H "Authorization: Bearer $TOKEN" | jq
```

Expected types: `battery_dispatch`, `demand_response`, `cost_optimization`

#### 3.2 Create Battery Dispatch Optimization

```bash
curl -X POST http://localhost:8080/api/optimize \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
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
      "demandForecast": [50,52,54,56,58,60,62,64,66,68,70,72,74,76,78,80,75,70,65,60,55,50,48,46],
      "electricityPrices": [0.10,0.10,0.10,0.10,0.12,0.15,0.20,0.25,0.22,0.20,0.18,0.18,0.18,0.18,0.20,0.25,0.30,0.28,0.25,0.20,0.15,0.12,0.10,0.10]
    }
  }' | jq
```

#### 3.3 Check Optimization Status

```bash
OPTIMIZATION_ID="<id-from-previous-step>"
curl "http://localhost:8080/api/optimize/$OPTIMIZATION_ID" \
  -H "Authorization: Bearer $TOKEN" | jq
```

#### 3.4 View Results in Web UI

1. Open http://localhost:3000/optimization
2. Find your optimization
3. View dispatch schedule and cost savings

### Test 4: Scheduler Workflows

#### 4.1 Create Workflow

```bash
curl -X POST http://localhost:8080/api/workflows \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Daily Forecast and Optimization",
    "description": "Automated workflow",
    "schedule": {
      "type": "Cron",
      "cronExpression": "0 6 * * *",
      "timezone": "UTC"
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
      },
      {
        "id": "00000000-0000-0000-0000-000000000002",
        "name": "Run Optimization",
        "type": "HttpCall",
        "dependsOn": ["00000000-0000-0000-0000-000000000001"],
        "config": {
          "method": "POST",
          "url": "http://optimize-service:8002/optimize",
          "headers": {"Content-Type": "application/json"},
          "body": "{\"type\":\"battery_dispatch\",\"parameters\":{}}"
        }
      }
    ]
  }' | jq
```

#### 4.2 Trigger Workflow Manually

```bash
WORKFLOW_ID="<id-from-previous-step>"
curl -X POST "http://localhost:8080/api/workflows/$WORKFLOW_ID/trigger" \
  -H "Authorization: Bearer $TOKEN" | jq
```

#### 4.3 Check Execution Status

```bash
curl "http://localhost:8080/api/executions?workflowId=$WORKFLOW_ID" \
  -H "Authorization: Bearer $TOKEN" | jq
```

#### 4.4 View in Web UI

1. Open http://localhost:3000/scheduler
2. View active workflows
3. Check execution history

---

## ⚙️ Common Operations

### View Logs

```bash
# All services
make logs

# Specific service
make logs-timeseries
make logs-forecast
make logs-optimize
make logs-scheduler
make logs-gateway
make logs-webapp
```

### Check Service Health

```bash
# Automated health check
make health

# Manual checks
curl http://localhost:8080/health | jq
curl http://localhost:5001/health | jq
curl http://localhost:8001/health | jq
curl http://localhost:8002/health | jq
curl http://localhost:5003/health | jq
```

### Database Operations

```bash
# Open PostgreSQL shell
make db-shell

# Backup database
make db-backup

# Restore database
make db-restore FILE=backup_20241001_120000.sql

# Query specific database
docker-compose exec postgres psql -U omarino -d omarino_timeseries
```

### Redis Operations

```bash
# Open Redis CLI
make redis-cli

# Check cache keys
KEYS *

# Get value
GET optimization:abc123

# Clear cache
FLUSHDB

# Exit
EXIT
```

### Restart Services

```bash
# Restart all services
make restart

# Restart specific service
docker-compose restart timeseries-service
docker-compose restart forecast-service
```

### Rebuild Services

```bash
# Rebuild all
make rebuild

# Rebuild specific service
docker-compose build --no-cache timeseries-service
docker-compose up -d timeseries-service
```

---

## 🔍 Monitoring and Observability

### Grafana Dashboards

Access: http://localhost:3001 (admin/admin)

**Pre-configured Dashboards:**
1. **System Overview** - Service health, request rates, latencies
2. **Request Metrics** - Detailed request analytics
3. **Error Tracking** - Error rates and types
4. **Resource Usage** - CPU, memory, disk

**Create Custom Dashboard:**
1. Go to Dashboards → New Dashboard
2. Add panel → Select Prometheus data source
3. Enter PromQL query (e.g., `rate(http_requests_total[5m])`)
4. Configure visualization
5. Save dashboard

### Prometheus Metrics

Access: http://localhost:9090

**Useful Queries:**

```promql
# Request rate per service
rate(http_requests_total[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# Service uptime
up{job=~".*-service|api-gateway"}

# Database connections
pg_stat_database_numbackends

# Redis memory usage
redis_memory_used_bytes
```

### Loki Logs

Access via Grafana → Explore → Select Loki

**LogQL Queries:**

```logql
# All logs from timeseries service
{service="timeseries"}

# Error logs from all services
{job="omarino-ems"} |= "error" or "Error" or "ERROR"

# Logs for specific request ID
{service="api-gateway"} |= "request_id=abc123"

# HTTP 500 errors
{service="api-gateway"} |= "500"

# Logs from last 5 minutes with level=error
{service="forecast"} | json | level="error" | line_format "{{.timestamp}} {{.message}}"
```

### Tempo Traces

Access via Grafana → Explore → Select Tempo

**Features:**
- View end-to-end request traces across services
- Identify performance bottlenecks
- Correlate traces with logs
- Service dependency graph

---

## 💾 Backup and Recovery

### Database Backup

#### Automated Backup

```bash
# Backup all databases
make db-backup
```

Creates file: `backup_YYYYMMDD_HHMMSS.sql`

#### Manual Backup

```bash
# Backup specific database
docker-compose exec -T postgres pg_dump -U omarino omarino_timeseries > timeseries_backup.sql
docker-compose exec -T postgres pg_dump -U omarino omarino_scheduler > scheduler_backup.sql
```

### Database Restore

```bash
# Restore from backup
make db-restore FILE=backup_20241001_120000.sql

# Or manually
docker-compose exec -T postgres psql -U omarino omarino_timeseries < timeseries_backup.sql
```

### Export Configuration

```bash
# Export environment variables
cp .env .env.backup

# Export Grafana dashboards
docker-compose exec grafana grafana-cli admin export-dashboard
```

### Volume Backup

```bash
# Backup PostgreSQL volume
docker run --rm -v omarino_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_data.tar.gz /data

# Backup Grafana volume
docker run --rm -v omarino_grafana_data:/data -v $(pwd):/backup alpine tar czf /backup/grafana_data.tar.gz /data
```

---

## 🛑 System Shutdown

### Graceful Shutdown

```bash
# Stop all services (keeps data)
make down

# Or
docker-compose down
```

### Complete Cleanup

```bash
# Stop and remove volumes (deletes all data!)
make clean

# Or
docker-compose down -v
```

### Emergency Shutdown

```bash
# Force stop all containers
docker stop $(docker ps -q)

# Remove all containers
docker rm $(docker ps -a -q)
```

---

## 🐛 Troubleshooting

### Service Won't Start

**Symptoms:** Container exits immediately or restarts repeatedly

**Diagnosis:**
```bash
# Check service logs
make logs-{service-name}

# Check container status
docker-compose ps

# Inspect container
docker inspect omarino-{service-name}
```

**Common Solutions:**
1. **Port conflict:** Change port in `docker-compose.yml`
2. **Missing environment variable:** Check `.env` file
3. **Database not ready:** Wait longer, check PostgreSQL logs
4. **Build error:** Rebuild: `docker-compose build {service}`

### Database Connection Failed

**Symptoms:** Services can't connect to PostgreSQL

**Diagnosis:**
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres pg_isready -U omarino
```

**Solutions:**
1. Verify `POSTGRES_USER` and `POSTGRES_PASSWORD` in `.env`
2. Wait for database initialization (check logs)
3. Restart database: `docker-compose restart postgres`

### Out of Memory

**Symptoms:** Containers being killed, slow performance

**Diagnosis:**
```bash
# Check resource usage
make stats

# Check Docker memory limit
docker info | grep Memory
```

**Solutions:**
1. Increase Docker memory limit (Docker Desktop → Settings → Resources)
2. Add resource limits to `docker-compose.yml`:
   ```yaml
   deploy:
     resources:
       limits:
         memory: 2G
   ```
3. Reduce number of running services

### Web UI Not Loading

**Symptoms:** http://localhost:3000 not accessible

**Diagnosis:**
```bash
# Check webapp container
docker-compose ps webapp

# Check webapp logs
make logs-webapp

# Test directly
curl http://localhost:3000
```

**Solutions:**
1. Wait for Next.js build (~20 seconds)
2. Check API Gateway is running: `curl http://localhost:8080/health`
3. Rebuild webapp: `docker-compose build webapp && docker-compose up -d webapp`

### Forecast Service Errors

**Symptoms:** Forecasts fail with errors

**Diagnosis:**
```bash
# Check forecast service logs
make logs-forecast

# Test health
curl http://localhost:8001/health
```

**Common Issues:**
1. **Not enough data:** Need at least 10 data points for ARIMA
2. **Invalid frequency:** Use "15min", "1H", "1D", etc.
3. **Model not loaded:** Check logs for model loading errors

### Optimization Times Out

**Symptoms:** Optimization stuck in "pending" or "running"

**Diagnosis:**
```bash
# Check optimize service logs
make logs-optimize

# Check Redis
make redis-cli
GET optimization:{id}
```

**Solutions:**
1. Check solver installation: Logs should show HiGHS or CBC
2. Reduce horizon or time steps
3. Increase timeout in optimization parameters
4. Check for infeasible problem (no solution exists)

---

## 📞 Support and Maintenance

### Regular Maintenance

**Daily:**
- Check service health: `make health`
- Review error logs: `make logs | grep ERROR`
- Monitor disk usage: `df -h`

**Weekly:**
- Backup database: `make db-backup`
- Review Grafana dashboards
- Check for Docker image updates

**Monthly:**
- Clean unused Docker resources: `make prune`
- Review and archive old logs
- Update dependencies

### Performance Tuning

**Database:**
```sql
-- Check database size
SELECT pg_size_pretty(pg_database_size('omarino_timeseries'));

-- Vacuum tables
VACUUM ANALYZE;

-- Check slow queries
SELECT * FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;
```

**Redis:**
```bash
# Check memory usage
redis-cli INFO memory

# Check slow log
redis-cli SLOWLOG GET 10
```

### Getting Help

1. Check this runbook
2. Review service logs: `make logs`
3. Check [ARCHITECTURE.md](ARCHITECTURE.md) for design details
4. Review service README files
5. Open GitHub issue with:
   - Service logs
   - Steps to reproduce
   - Environment details

---

## 📝 Appendix

### Environment Variables Reference

See [.env.example](.env.example) for all available variables.

### API Endpoints

See [API.md](docs/API.md) for complete API documentation.

### Port Reference

| Port | Service | Purpose |
|------|---------|---------|
| 3000 | webapp | Web UI |
| 3001 | grafana | Monitoring dashboards |
| 3100 | loki | Log aggregation |
| 3200 | tempo | Distributed tracing |
| 5001 | timeseries-service | Time series API |
| 5003 | scheduler-service | Scheduler API |
| 5432 | postgres | PostgreSQL database |
| 6379 | redis | Redis cache |
| 8001 | forecast-service | Forecast API |
| 8002 | optimize-service | Optimization API |
| 8080 | api-gateway | API Gateway |
| 9090 | prometheus | Metrics collection |

### File Locations

- **Configuration:** `.env`
- **Sample Data:** `sample-data/`
- **Scripts:** `scripts/`
- **Logs:** Docker container logs (view with `make logs`)
- **Database:** Docker volume `omarino_postgres_data`
- **Redis:** Docker volume `omarino_redis_data`

---

**Document Version:** 1.0  
**Last Updated:** October 2024  
**Maintainer:** OMARINO EMS Team
