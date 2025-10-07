# Database Persistence Feature - Deployment Guide

## Overview
This guide will help you deploy the new database persistence feature that saves forecast and optimization results to PostgreSQL/TimescaleDB and displays them in the webapp UI.

## What's New
1. **Forecast Service**: Now saves all forecasts to database with metadata and results
2. **Optimize Service**: Saves optimization jobs, assets, schedules, and costs
3. **Webapp**: Displays forecast and optimization history with detailed views

## Prerequisites
- SSH access to server: `ssh omar@192.168.75.20`
- GitHub repository access
- Database container running: `omarino-postgres`

## Deployment Steps

### 1. Connect to Server
```bash
ssh omar@192.168.75.20
cd ~/OMARINO-EMS-Suite
```

### 2. Pull Latest Code
```bash
git pull origin main
```

You should see the following new/modified files:
- `timeseries-service/Migrations/20251007000000_AddForecastAndOptimizationTables.sql` (NEW)
- `forecast-service/app/services/forecast_database.py` (NEW)
- `forecast-service/app/main.py` (MODIFIED)
- `forecast-service/app/routers/forecast.py` (MODIFIED)
- `optimize-service/app/services/optimization_database.py` (NEW)
- `optimize-service/app/main.py` (MODIFIED)
- `optimize-service/app/routers/optimize.py` (MODIFIED)
- `webapp/src/app/forecasts/page.tsx` (MODIFIED)
- `webapp/src/app/optimization/page.tsx` (MODIFIED)
- `deploy-forecast-service.sh` (NEW)
- `deploy-optimize-service.sh` (NEW)

### 3. Verify Database Schema
The database schema should already be applied (it was created during development). Verify it:

```bash
docker exec -it omarino-postgres psql -U omarino -d omarino -c "\dt"
```

You should see these new tables:
- `forecast_jobs`
- `forecast_results`
- `optimization_jobs`
- `optimization_assets`
- `optimization_results`
- `optimization_costs`

### 4. Deploy Forecast Service
```bash
chmod +x deploy-forecast-service.sh
./deploy-forecast-service.sh
```

Expected output:
- ✅ `forecast_database_connected` in logs
- ✅ Health check returns status 200

### 5. Deploy Optimize Service
```bash
chmod +x deploy-optimize-service.sh
./deploy-optimize-service.sh
```

Expected output:
- ✅ `optimization_database_connected` in logs
- ✅ Health check returns status 200

### 6. Deploy Webapp
```bash
cd webapp

# Stop old container
docker stop omarino-webapp || true
docker rm omarino-webapp || true

# Build new image
docker build -t 192.168.61.21:32768/omarino-webapp:latest .

# Push to registry
docker push 192.168.61.21:32768/omarino-webapp:latest

# Start new container
docker run -d \
  --name omarino-webapp \
  --network ems_omarino-network \
  -p 3000:3000 \
  --restart unless-stopped \
  192.168.61.21:32768/omarino-webapp:latest

# Wait and check logs
sleep 5
docker logs omarino-webapp --tail 30
```

### 7. Verify Deployment

#### Test Forecast Service
```bash
# Create a forecast
curl -X POST https://ems-back.omarino.net/api/forecast/forecast \
  -H "Content-Type: application/json" \
  -d '{
    "series_id": "test-meter-001",
    "model": "auto",
    "horizon": 24,
    "granularity": "hourly",
    "historical_data": [
      {"timestamp": "2025-01-01T00:00:00Z", "value": 100},
      {"timestamp": "2025-01-01T01:00:00Z", "value": 110},
      {"timestamp": "2025-01-01T02:00:00Z", "value": 105}
    ]
  }'

# List forecasts (should show the one you just created)
curl https://ems-back.omarino.net/api/forecast/forecasts

# Get specific forecast (use forecast_id from above)
curl https://ems-back.omarino.net/api/forecast/forecasts/{forecast_id}
```

#### Test Optimization Service
```bash
# Create an optimization
curl -X POST https://ems-back.omarino.net/api/optimize/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "optimization_type": "battery_dispatch",
    "start_time": "2025-01-01T00:00:00Z",
    "end_time": "2025-01-02T00:00:00Z",
    "time_step_minutes": 60,
    "assets": [
      {
        "asset_id": "battery-001",
        "asset_type": "battery",
        "capacity_kwh": 100,
        "power_kw": 50,
        "efficiency": 0.95,
        "initial_soc": 50
      }
    ],
    "price_forecast": [
      {"timestamp": "2025-01-01T00:00:00Z", "price": 0.10}
    ],
    "demand_forecast": [
      {"timestamp": "2025-01-01T00:00:00Z", "demand": 50}
    ]
  }'

# List optimizations
curl https://ems-back.omarino.net/api/optimize/optimizations

# Get specific optimization (use optimization_id from above)
curl https://ems-back.omarino.net/api/optimize/optimizations/{optimization_id}
```

#### Test Webapp UI
Open in browser: https://ems-demo.omarino.net

**Forecast Page** (https://ems-demo.omarino.net/forecasts):
- ✅ Should show list of saved forecasts
- ✅ Click on a forecast to see detailed view with chart
- ✅ Auto-refreshes every 10 seconds

**Optimization Page** (https://ems-demo.omarino.net/optimization):
- ✅ Should show list of saved optimizations
- ✅ Click on an optimization to see:
  - Battery schedule chart
  - Grid schedule chart
  - Cost breakdown
- ✅ Auto-refreshes every 10 seconds

### 8. Verify Database Storage

Check that data is being saved to database:

```bash
# Check forecast jobs
docker exec -it omarino-postgres psql -U omarino -d omarino -c "SELECT forecast_id, model_name, status, created_at FROM forecast_jobs ORDER BY created_at DESC LIMIT 5;"

# Check forecast results count
docker exec -it omarino-postgres psql -U omarino -d omarino -c "SELECT COUNT(*) as total_forecast_points FROM forecast_results;"

# Check optimization jobs
docker exec -it omarino-postgres psql -U omarino -d omarino -c "SELECT optimization_id, optimization_type, solver, total_cost, created_at FROM optimization_jobs ORDER BY created_at DESC LIMIT 5;"

# Check optimization results count
docker exec -it omarino-postgres psql -U omarino -d omarino -c "SELECT COUNT(*) as total_schedule_points FROM optimization_results;"
```

## Architecture Changes

### Database Schema

**Forecast Tables:**
- `forecast_jobs`: Stores forecast metadata (model, horizon, metrics, status)
- `forecast_results`: TimescaleDB hypertable for forecast data points (timestamp, value, confidence intervals)

**Optimization Tables:**
- `optimization_jobs`: Stores optimization metadata (type, solver, objective, costs)
- `optimization_assets`: Asset configurations used in optimization
- `optimization_results`: TimescaleDB hypertable for optimized schedules (battery SOC, charge/discharge, grid import/export)
- `optimization_costs`: Cost breakdown by type

### New API Endpoints

**Forecast Service:**
- `GET /api/forecast/forecasts?limit={n}&offset={n}` - List saved forecasts
- `GET /api/forecast/forecasts/{id}` - Get specific forecast with full results

**Optimize Service:**
- `GET /api/optimize/optimizations?limit={n}&offset={n}` - List saved optimizations
- `GET /api/optimize/optimizations/{id}` - Get specific optimization with full results

### Service Behavior

Both services now:
1. Execute forecasts/optimizations normally
2. Return results immediately (no wait)
3. Save to database in background (non-blocking)
4. Continue working even if database is unavailable
5. Log database connection status on startup

## Troubleshooting

### Forecast Service Not Saving
Check logs:
```bash
docker logs omarino-forecast --tail 50 | grep -i database
```

Should see: `forecast_database_connected`

If you see connection errors, verify database container:
```bash
docker exec -it omarino-postgres psql -U omarino -d omarino -c "SELECT 1;"
```

### Optimize Service Not Saving
Check logs:
```bash
docker logs omarino-optimize --tail 50 | grep -i database
```

Should see: `optimization_database_connected`

### Webapp Not Showing History
1. Check that services are deployed and connected
2. Open browser console (F12) for errors
3. Check API responses:
   ```bash
   curl https://ems-back.omarino.net/api/forecast/forecasts
   curl https://ems-back.omarino.net/api/optimize/optimizations
   ```

### Database Connection Issues
Check network:
```bash
docker network inspect ems_omarino-network | grep -A 10 omarino-postgres
docker network inspect ems_omarino-network | grep -A 10 omarino-forecast
docker network inspect ems_omarino-network | grep -A 10 omarino-optimize
```

All three containers should be on the same network.

## Rollback Plan

If issues occur, rollback to previous version:

```bash
# Rollback forecast service
docker stop omarino-forecast
docker rm omarino-forecast
docker run -d \
  --name omarino-forecast \
  --network ems_omarino-network \
  -p 8082:8082 \
  --restart unless-stopped \
  192.168.61.21:32768/omarino-forecast:previous

# Similar for optimize-service and webapp
```

The service will continue to work without database persistence.

## Performance Notes

- **TimescaleDB Hypertables**: Optimized for time-series data with automatic partitioning
- **Indexes**: Created on foreign keys and timestamps for fast queries
- **Connection Pooling**: Each service maintains 2-10 database connections
- **Non-blocking Saves**: Services return immediately, database saves happen in background
- **Auto-refresh**: UI polls every 10 seconds for new results

## Git Commits

This feature was implemented in the following commits:
1. `587c38a` - Add database persistence to forecast service
2. `15be3ae` - Add forecast service deployment script
3. `7f7938b` - Add database persistence to optimize service
4. `fc30900` - Add forecast and optimization history UI

## Contact

For issues or questions, contact the development team.
