# Asset Service - Manual Deployment Guide

Since automated SSH deployment requires key configuration, here's a step-by-step manual deployment guide.

## Option 1: Deploy on Server (192.168.75.20)

### Step 1: SSH to Server
```bash
ssh -i '/Users/omarzaror/Library/Mobile Documents/com~apple~CloudDocs/Developing/SSH-Key/server.pem' ubuntu@192.168.75.20
```

### Step 2: Pull Latest Code
```bash
cd /home/ubuntu/omarino-ems-suite
git pull origin main
```

### Step 3: Initialize Database Schema
```bash
cd asset-service/database

# Check if schema exists
PGPASSWORD=omarino_dev_pass psql -h localhost -U omarino -d omarino -c "\dt"

# If assets table doesn't exist, apply schema
PGPASSWORD=omarino_dev_pass psql -h localhost -U omarino -d omarino -f schema.sql

# Verify tables were created
PGPASSWORD=omarino_dev_pass psql -h localhost -U omarino -d omarino -c "\dt"
```

Expected output should include:
- assets
- battery_specs
- generator_specs
- grid_connection_specs
- solar_pv_specs
- asset_status
- sites
- asset_groups
- etc.

### Step 4: Build Docker Image
```bash
cd /home/ubuntu/omarino-ems-suite/asset-service
docker build -t omarino-asset-service:latest .
```

### Step 5: Stop Existing Container (if any)
```bash
docker stop omarino-asset-service 2>/dev/null || true
docker rm omarino-asset-service 2>/dev/null || true
```

### Step 6: Run Container
```bash
docker run -d \
  --name omarino-asset-service \
  --network omarino-network \
  --restart unless-stopped \
  -p 8003:8003 \
  -e DATABASE_URL=postgresql://omarino:omarino_dev_pass@postgres:5432/omarino \
  -e API_PREFIX=/api/assets \
  -e LOG_LEVEL=INFO \
  -e CORS_ORIGINS=* \
  omarino-asset-service:latest
```

### Step 7: Verify Deployment
```bash
# Check container is running
docker ps | grep asset-service

# Check logs
docker logs omarino-asset-service

# Test health endpoint
curl http://localhost:8003/api/assets/health

# Expected response:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "database": "connected"
# }
```

### Step 8: Access API Documentation
Open in browser:
```
http://192.168.75.20:8003/api/assets/docs
```

## Option 2: Test Locally First

### Step 1: Set Up Python Environment
```bash
cd asset-service

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment
```bash
# Create .env file
cp .env.example .env

# Edit .env
nano .env
```

Set these values:
```env
DATABASE_URL=postgresql://omarino:omarino_dev_pass@192.168.75.20:5432/omarino
API_PREFIX=/api/assets
LOG_LEVEL=DEBUG
CORS_ORIGINS=*
```

### Step 3: Initialize Database (if not done)
```bash
# Connect to remote database
PGPASSWORD=omarino_dev_pass psql -h 192.168.75.20 -U omarino -d omarino -f database/schema.sql
```

### Step 4: Run Service Locally
```bash
uvicorn app.main:app --reload --port 8003
```

### Step 5: Test Locally
```bash
# Health check
curl http://localhost:8003/api/assets/health

# API docs
open http://localhost:8003/api/assets/docs
```

## Creating Test Data

After deployment, create test assets:

### Method 1: Using curl (from server or local)
```bash
# Set API endpoint
API="http://192.168.75.20:8003/api/assets"

# Create a battery
curl -X POST "${API}/batteries" \
  -H "Content-Type: application/json" \
  -d '{
    "site_id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Demo Battery 1",
    "description": "100 kWh lithium-ion battery",
    "manufacturer": "Tesla",
    "model_number": "Powerpack 2",
    "serial_number": "TP2-001",
    "chemistry": "lithium_ion",
    "capacity": 100.0,
    "usable_capacity": 90.0,
    "voltage": 400.0,
    "max_charge_rate": 50.0,
    "max_discharge_rate": 50.0,
    "efficiency": 0.95,
    "min_soc": 10.0,
    "max_soc": 90.0
  }'
```

### Method 2: Using the test script
```bash
# On your local machine
./test-asset-service.sh
```

### Method 3: Using API Documentation
1. Open http://192.168.75.20:8003/api/assets/docs
2. Click on "POST /api/assets/batteries"
3. Click "Try it out"
4. Fill in the request body
5. Click "Execute"

## Verify Deployment

### Check Service Health
```bash
curl http://192.168.75.20:8003/api/assets/health
```

### List Assets
```bash
curl http://192.168.75.20:8003/api/assets/assets
curl http://192.168.75.20:8003/api/assets/batteries
curl http://192.168.75.20:8003/api/assets/generators
```

### Check Dashboard
```bash
curl http://192.168.75.20:8003/api/assets/status/dashboard/summary
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker logs omarino-asset-service

# Common issues:
# - Database connection: Check DATABASE_URL
# - Port conflict: Check if port 8003 is in use (lsof -i :8003)
# - Network: Check if container is on omarino-network
```

### Database connection fails
```bash
# Test connection from container
docker exec omarino-asset-service ping postgres

# Test from server
PGPASSWORD=omarino_dev_pass psql -h localhost -U omarino -d omarino -c "SELECT 1"
```

### Schema errors
```bash
# Check if tables exist
PGPASSWORD=omarino_dev_pass psql -h localhost -U omarino -d omarino -c "\dt"

# Re-apply schema (safe - uses CREATE TABLE IF NOT EXISTS)
PGPASSWORD=omarino_dev_pass psql -h localhost -U omarino -d omarino -f asset-service/database/schema.sql
```

### Import errors in logs
```bash
# Rebuild image with no cache
docker build --no-cache -t omarino-asset-service:latest .

# Check Python packages in container
docker exec omarino-asset-service pip list
```

## Next Steps After Deployment

1. **Create test assets** via API
2. **Update scheduler service** to fetch assets from asset service
3. **Test optimization workflow** with real assets
4. **Verify results** appear in UI

## Useful Commands

```bash
# View real-time logs
docker logs -f omarino-asset-service

# Restart service
docker restart omarino-asset-service

# Stop service
docker stop omarino-asset-service

# Remove service
docker stop omarino-asset-service
docker rm omarino-asset-service

# Rebuild and redeploy
docker stop omarino-asset-service
docker rm omarino-asset-service
docker build -t omarino-asset-service:latest .
docker run -d --name omarino-asset-service --network omarino-network --restart unless-stopped -p 8003:8003 -e DATABASE_URL=postgresql://omarino:omarino_dev_pass@postgres:5432/omarino omarino-asset-service:latest

# Check resource usage
docker stats omarino-asset-service
```

## Service Endpoints

Once deployed, these endpoints will be available:

- **Health**: http://192.168.75.20:8003/api/assets/health
- **API Docs**: http://192.168.75.20:8003/api/assets/docs
- **OpenAPI JSON**: http://192.168.75.20:8003/api/assets/openapi.json
- **Assets**: http://192.168.75.20:8003/api/assets/assets
- **Batteries**: http://192.168.75.20:8003/api/assets/batteries
- **Generators**: http://192.168.75.20:8003/api/assets/generators
- **Status**: http://192.168.75.20:8003/api/assets/status
- **Dashboard**: http://192.168.75.20:8003/api/assets/status/dashboard/summary
