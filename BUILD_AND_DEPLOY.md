# 🚀 Build & Deploy - Complete Guide

## Quick Start (TL;DR)

```bash
# On your server (192.168.75.20)
ssh omar@192.168.75.20
cd ~/OMARINO-EMS-Suite
git pull origin main
./build-and-push.sh    # Build Docker images (10-15 min)
./deploy-all.sh        # Deploy all services (5-7 min)
```

---

## 📋 What You're Deploying

### New Feature: **Database Persistence for Forecasts & Optimizations**

All forecast and optimization results are now automatically saved to PostgreSQL/TimescaleDB and displayed in the webapp UI with beautiful visualizations!

---

## 🎯 Complete Workflow

### Step 1: Build Docker Images

**On Server:**
```bash
ssh omar@192.168.75.20
cd ~/OMARINO-EMS-Suite
git pull origin main
./build-and-push.sh
```

**What it does:**
- Builds `omarino-forecast:latest` with database persistence
- Builds `omarino-optimize:latest` with database persistence  
- Builds `omarino-webapp:latest` with history UI
- Pushes all images to private registry (192.168.61.21:32768)
- Tags each image with timestamp for rollback capability

**Time:** ~10-15 minutes

---

### Step 2: Deploy Services

**On Server:**
```bash
./deploy-all.sh
```

**What it does:**
- Verifies database schema (applies if needed)
- Deploys forecast service with DB connection
- Deploys optimize service with DB connection
- Deploys webapp with new UI
- Runs health checks
- Shows verification commands

**Time:** ~5-7 minutes

---

### Step 3: Verify Deployment

**Check Services:**
```bash
docker ps | grep omarino
```

**Test APIs:**
```bash
# List forecasts
curl https://ems-back.omarino.net/api/forecast/forecasts | jq '.'

# List optimizations
curl https://ems-back.omarino.net/api/optimize/optimizations | jq '.'
```

**Check Database:**
```bash
docker exec omarino-postgres psql -U omarino -d omarino \
  -c "SELECT COUNT(*) FROM forecast_jobs;"
```

**Open Webapp:**
- Forecast page: https://ems-demo.omarino.net/forecasts
- Optimization page: https://ems-demo.omarino.net/optimization

---

## 🎨 New Features

### Forecast Page
- ✅ List of all saved forecasts with metadata
- ✅ Click cards to view detailed forecast
- ✅ Interactive chart with confidence intervals
- ✅ Forecast metrics (MAE, RMSE, MAPE)
- ✅ Auto-refresh every 10 seconds

### Optimization Page
- ✅ List of all saved optimizations
- ✅ Click cards to view detailed results
- ✅ Battery schedule chart (SOC, charge, discharge)
- ✅ Grid schedule chart (import, export)
- ✅ Cost breakdown bar chart
- ✅ Auto-refresh every 10 seconds

---

## 📦 Images Built

All images pushed to: `192.168.61.21:32768`

### Forecast Service
- **Image:** `omarino-forecast:latest`
- **Features:**
  - Database persistence for forecasts
  - GET /api/forecast/forecasts endpoint
  - GET /api/forecast/forecasts/{id} endpoint
  - AsyncPG connection pooling
  - Non-blocking saves

### Optimize Service
- **Image:** `omarino-optimize:latest`
- **Features:**
  - Database persistence for optimizations
  - GET /api/optimize/optimizations endpoint
  - GET /api/optimize/optimizations/{id} endpoint
  - Saves jobs, assets, results, costs
  - Background task integration

### Webapp
- **Image:** `omarino-webapp:latest`
- **Features:**
  - Forecast history page with charts
  - Optimization history page with charts
  - Detailed modal views
  - Auto-refresh functionality
  - Beautiful UI with Recharts

---

## 🗄️ Database Schema

### Tables Created (Already Applied)

**Forecasts:**
- `forecast_jobs` - Metadata (model, horizon, status, metrics)
- `forecast_results` - TimescaleDB hypertable (timestamps, values, confidence)

**Optimizations:**
- `optimization_jobs` - Metadata (type, solver, objective, costs)
- `optimization_assets` - Asset configurations
- `optimization_results` - TimescaleDB hypertable (schedules)
- `optimization_costs` - Cost breakdown by type

---

## 📚 Documentation Files

- **BUILD_INSTRUCTIONS.txt** - This guide (detailed build instructions)
- **DEPLOY.txt** - Simple deployment instructions
- **DEPLOYMENT_GUIDE.md** - Comprehensive deployment guide
- **QUICK_REFERENCE.md** - API reference and quick commands
- **build-and-push.sh** - Automated build script
- **deploy-all.sh** - Automated deployment script

---

## 🔧 Manual Build (If Script Fails)

### Forecast Service
```bash
cd ~/OMARINO-EMS-Suite/forecast-service
docker build -t 192.168.61.21:32768/omarino-forecast:latest .
docker push 192.168.61.21:32768/omarino-forecast:latest
```

### Optimize Service
```bash
cd ~/OMARINO-EMS-Suite/optimize-service
docker build -t 192.168.61.21:32768/omarino-optimize:latest .
docker push 192.168.61.21:32768/omarino-optimize:latest
```

### Webapp
```bash
cd ~/OMARINO-EMS-Suite/webapp
docker build -t 192.168.61.21:32768/omarino-webapp:latest .
docker push 192.168.61.21:32768/omarino-webapp:latest
```

---

## 🆘 Troubleshooting

### Build Issues

**No space left on device:**
```bash
docker system prune -a
docker volume prune
```

**Build is slow:**
```bash
export DOCKER_BUILDKIT=1
```

### Deployment Issues

**Service not connecting to database:**
```bash
# Check logs
docker logs omarino-forecast | grep database
docker logs omarino-optimize | grep database

# Should see:
# forecast_database_connected
# optimization_database_connected
```

**Webapp not showing history:**
```bash
# Check API responses
curl https://ems-back.omarino.net/api/forecast/forecasts
curl https://ems-back.omarino.net/api/optimize/optimizations

# Check browser console (F12) for errors
```

**Database tables missing:**
```bash
# Apply migration manually
docker exec -i omarino-postgres psql -U omarino -d omarino < \
  timeseries-service/Migrations/20251007000000_AddForecastAndOptimizationTables.sql
```

### Service Logs

```bash
# View logs
docker logs omarino-forecast --tail 50
docker logs omarino-optimize --tail 50
docker logs omarino-webapp --tail 50

# Follow logs in real-time
docker logs -f omarino-forecast
```

---

## 🔄 Rollback

If issues occur, rollback to previous version:

### List Available Versions
```bash
curl -X GET http://192.168.61.21:32768/v2/omarino-forecast/tags/list
```

### Deploy Previous Version
```bash
docker stop omarino-forecast
docker rm omarino-forecast
docker run -d --name omarino-forecast \
  --network ems_omarino-network \
  -p 8082:8082 \
  --restart unless-stopped \
  192.168.61.21:32768/omarino-forecast:20251007-120000
```

---

## ✅ Verification Checklist

After deployment, verify:

- [ ] All services running: `docker ps | grep omarino`
- [ ] Forecast API works: `curl https://ems-back.omarino.net/api/forecast/forecasts`
- [ ] Optimize API works: `curl https://ems-back.omarino.net/api/optimize/optimizations`
- [ ] Database has tables: `docker exec omarino-postgres psql -U omarino -d omarino -c "\dt"`
- [ ] Webapp accessible: https://ems-demo.omarino.net
- [ ] Forecast page shows history: https://ems-demo.omarino.net/forecasts
- [ ] Optimization page shows history: https://ems-demo.omarino.net/optimization
- [ ] Can click cards to see details
- [ ] Charts render correctly
- [ ] Auto-refresh works (new items appear)

---

## 📈 Performance Notes

- **Connection Pooling:** 2-10 connections per service
- **Non-blocking Saves:** Services return immediately, DB saves in background
- **Hypertables:** Auto-partitioned time-series data for fast queries
- **Graceful Degradation:** Services work even if DB unavailable
- **Auto-refresh:** UI polls every 10 seconds without blocking

---

## 🎯 Git Commits

Features implemented in these commits:

1. `587c38a` - Forecast service database persistence
2. `15be3ae` - Forecast service deployment script
3. `7f7938b` - Optimize service database persistence
4. `fc30900` - Webapp forecast/optimization history UI
5. `2d99fbc` - Comprehensive deployment guide
6. `2561cc5` - Quick reference guide
7. `5bb017b` - Complete deployment script
8. `650d67f` - Simple deployment instructions
9. `8448b4c` - Build and push script
10. `c929fac` - Build instructions

All code pushed to: https://github.com/OMARINO-DE/omarino-ems-suite

---

## 🚀 Ready to Go!

**Complete workflow:**

```bash
# 1. Connect to server
ssh omar@192.168.75.20

# 2. Navigate to project
cd ~/OMARINO-EMS-Suite

# 3. Pull latest code
git pull origin main

# 4. Build images (10-15 minutes)
./build-and-push.sh

# 5. Deploy services (5-7 minutes)
./deploy-all.sh

# 6. Verify
open https://ems-demo.omarino.net/forecasts
open https://ems-demo.omarino.net/optimization
```

**Total time:** ~15-22 minutes

---

## 💡 Key Benefits

1. **Historical Analysis** - View all past forecasts and optimizations
2. **Model Comparison** - Compare accuracy of different models
3. **Audit Trail** - Track when predictions were made
4. **Reproducibility** - Full results saved for review
5. **Performance Insights** - Analyze solve times and costs

---

## 🎉 You're All Set!

Everything is ready to build and deploy. The scripts handle all the complexity for you. Just follow the workflow above and you'll have the new features live in about 20 minutes!

Good luck! 🚀
