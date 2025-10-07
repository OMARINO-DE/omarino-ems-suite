# Database Persistence - Quick Reference

## 🎯 What's New

Forecast and optimization results are now automatically saved to PostgreSQL/TimescaleDB and can be viewed in the webapp!

## 📊 Database Tables

### Forecasts
- **forecast_jobs**: Metadata (model, horizon, status, metrics)
- **forecast_results**: Time-series data (timestamps, values, confidence intervals)

### Optimizations
- **optimization_jobs**: Metadata (type, solver, objective, costs)
- **optimization_assets**: Asset configurations
- **optimization_results**: Optimized schedules (battery, grid)
- **optimization_costs**: Cost breakdown

## 🔌 New API Endpoints

### Forecast Service (Port 8082)
```bash
# List saved forecasts
GET /api/forecast/forecasts?limit=20&offset=0

# Get specific forecast with full results
GET /api/forecast/forecasts/{forecast_id}
```

### Optimize Service (Port 8083)
```bash
# List saved optimizations
GET /api/optimize/optimizations?limit=20&offset=0

# Get specific optimization with full results
GET /api/optimize/optimizations/{optimization_id}
```

## 🖥️ Webapp UI

### Forecast Page
- **URL**: https://ems-demo.omarino.net/forecasts
- **Features**:
  - List of all saved forecasts
  - Click to view detailed forecast with chart
  - Shows metrics (MAE, RMSE, MAPE)
  - Confidence intervals (5th and 95th percentile)
  - Auto-refresh every 10 seconds

### Optimization Page
- **URL**: https://ems-demo.omarino.net/optimization
- **Features**:
  - List of all saved optimizations
  - Click to view detailed optimization
  - Battery schedule chart (SOC, charge, discharge)
  - Grid schedule chart (import, export)
  - Cost breakdown bar chart
  - Auto-refresh every 10 seconds

## ⚡ Quick Deploy

```bash
# On server
ssh omar@192.168.75.20
cd ~/OMARINO-EMS-Suite
git pull origin main

# Deploy forecast service
./deploy-forecast-service.sh

# Deploy optimize service
./deploy-optimize-service.sh

# Deploy webapp
cd webapp
docker build -t 192.168.61.21:32768/omarino-webapp:latest .
docker push 192.168.61.21:32768/omarino-webapp:latest
docker stop omarino-webapp && docker rm omarino-webapp
docker run -d --name omarino-webapp --network ems_omarino-network \
  -p 3000:3000 --restart unless-stopped \
  192.168.61.21:32768/omarino-webapp:latest
```

## 🔍 Quick Checks

### Check Database Connection
```bash
# Forecast service
docker logs omarino-forecast | grep forecast_database_connected

# Optimize service
docker logs omarino-optimize | grep optimization_database_connected
```

### Query Database
```bash
# Count saved forecasts
docker exec omarino-postgres psql -U omarino -d omarino \
  -c "SELECT COUNT(*) FROM forecast_jobs;"

# Count saved optimizations
docker exec omarino-postgres psql -U omarino -d omarino \
  -c "SELECT COUNT(*) FROM optimization_jobs;"

# View recent forecasts
docker exec omarino-postgres psql -U omarino -d omarino \
  -c "SELECT forecast_id, model_name, horizon, created_at FROM forecast_jobs ORDER BY created_at DESC LIMIT 5;"

# View recent optimizations
docker exec omarino-postgres psql -U omarino -d omarino \
  -c "SELECT optimization_id, optimization_type, total_cost, created_at FROM optimization_jobs ORDER BY created_at DESC LIMIT 5;"
```

### Test APIs
```bash
# List forecasts
curl https://ems-back.omarino.net/api/forecast/forecasts | jq '.'

# List optimizations
curl https://ems-back.omarino.net/api/optimize/optimizations | jq '.'
```

## 🛠️ Troubleshooting

### Service won't connect to database
```bash
# Check database is running
docker ps | grep omarino-postgres

# Check network
docker network inspect ems_omarino-network

# Check environment variable
docker exec omarino-forecast env | grep DATABASE_URL
```

### Webapp not showing history
```bash
# Check browser console (F12) for errors

# Test API directly
curl https://ems-back.omarino.net/api/forecast/forecasts
curl https://ems-back.omarino.net/api/optimize/optimizations

# Check webapp logs
docker logs omarino-webapp --tail 50
```

### Data not being saved
```bash
# Check service logs for errors
docker logs omarino-forecast --tail 100 | grep -i error
docker logs omarino-optimize --tail 100 | grep -i error

# Verify database tables exist
docker exec omarino-postgres psql -U omarino -d omarino -c "\dt"
```

## 📈 Performance

- **Connection Pooling**: 2-10 connections per service
- **Non-blocking**: Services return immediately, DB saves in background
- **Hypertables**: Auto-partitioned time-series data for fast queries
- **Indexes**: Optimized for timestamp and foreign key lookups
- **Graceful Degradation**: Services work even if DB is unavailable

## 📝 Key Benefits

1. **Historical Analysis**: View all past forecasts and optimizations
2. **Comparison**: Compare different models and strategies
3. **Audit Trail**: Track when and how predictions were made
4. **Performance Metrics**: Evaluate forecast accuracy over time
5. **Reproducibility**: Full results saved for later review

## 🔗 Related Files

- `DEPLOYMENT_GUIDE.md` - Full deployment instructions
- `deploy-forecast-service.sh` - Forecast service deployment script
- `deploy-optimize-service.sh` - Optimize service deployment script
- `timeseries-service/Migrations/20251007000000_AddForecastAndOptimizationTables.sql` - Database schema

## 📚 Git Commits

- `587c38a` - Forecast service database persistence
- `7f7938b` - Optimize service database persistence
- `fc30900` - Webapp forecast/optimization history UI
- `2d99fbc` - Deployment guide

## ✅ Verification Checklist

- [ ] Database migration applied (check with `\dt` in psql)
- [ ] Forecast service shows `forecast_database_connected` in logs
- [ ] Optimize service shows `optimization_database_connected` in logs
- [ ] Webapp builds and starts successfully
- [ ] Can create a forecast via API
- [ ] Forecast appears in database
- [ ] Forecast appears in webapp UI
- [ ] Can create an optimization via API
- [ ] Optimization appears in database
- [ ] Optimization appears in webapp UI
- [ ] Detail modals work (click on cards)
- [ ] Charts render correctly
- [ ] Auto-refresh works (new items appear after 10 seconds)
