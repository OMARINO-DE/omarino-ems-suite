# 🚀 OMARINO EMS Suite - Portainer Deployment Guide

## ✅ Pre-Deployment Checklist

All required images are now in your private registry at `192.168.61.21:32768`:

### Custom OMARINO Services (6)
- ✅ api-gateway:latest
- ✅ timeseries-service:latest  
- ✅ forecast-service:latest
- ✅ optimize-service:latest
- ✅ scheduler-service:latest
- ✅ webapp:latest

### Third-Party Services (7)
- ✅ timescale/timescaledb:latest-pg14
- ✅ redis:7-alpine
- ✅ prom/prometheus:latest
- ✅ grafana/grafana:latest
- ✅ grafana/loki:latest
- ✅ grafana/promtail:latest
- ✅ grafana/tempo:latest

**All images are linux/amd64 compatible** ✅

---

## 📋 Step-by-Step Deployment

### Step 1: Access Portainer

Navigate to your Portainer instance in a web browser.

### Step 2: Create New Stack

1. Click on **Stacks** in the left sidebar
2. Click **+ Add stack** button
3. Enter stack name: `OMARINO-EMS` (or your preferred name)

### Step 3: Paste Stack Configuration

Copy the entire contents of `docker-compose.portainer.yml` and paste into the Web editor.

### Step 4: Configure Environment Variables

Click on "Advanced mode" or scroll to "Environment variables" section and add:

#### Required Variables:

```env
POSTGRES_USER=omarino
POSTGRES_PASSWORD=YourSecurePassword123!
POSTGRES_DB=omarino
REDIS_PASSWORD=YourRedisPassword123!
JWT_SECRET_KEY=YourVeryLongSecretKeyAtLeast32CharactersLong!
GRAFANA_USER=admin
GRAFANA_PASSWORD=YourGrafanaPassword123!
```

#### Optional Variables (with defaults):

```env
LOG_LEVEL=Information
ASPNETCORE_ENVIRONMENT=Production
ENVIRONMENT=production
NEXTAUTH_URL=http://your-domain:3000
NEXTAUTH_SECRET=YourNextAuthSecret123!
```

### Step 5: Deploy Stack

1. Review the configuration
2. Click **Deploy the stack** button
3. Wait for Portainer to pull images and start containers

### Step 6: Monitor Deployment

1. Go to **Containers** in Portainer
2. Look for containers prefixed with `omarino-`
3. Wait for all health checks to pass (green status)

Expected containers:
- omarino-postgres (should start first)
- omarino-redis
- omarino-timeseries
- omarino-forecast
- omarino-optimize
- omarino-scheduler
- omarino-gateway
- omarino-webapp
- omarino-prometheus
- omarino-grafana
- omarino-loki
- omarino-promtail
- omarino-tempo

---

## 🔍 Verification Steps

### 1. Check Container Health

All containers should show as "healthy" in Portainer after ~2 minutes.

### 2. Access Services

Once deployed, services will be available at:

| Service | URL | Purpose |
|---------|-----|---------|
| **Web App** | http://your-server:3000 | Main user interface |
| **API Gateway** | http://your-server:8081 | API endpoint |
| **Grafana** | http://your-server:3001 | Monitoring dashboards |
| **Prometheus** | http://your-server:9090 | Metrics |
| **Time Series API** | http://your-server:5001 | Direct time series access |
| **Forecast API** | http://your-server:8001 | Forecasting service |
| **Optimize API** | http://your-server:8002 | Optimization service |
| **Scheduler API** | http://your-server:5003 | Workflow scheduler |

### 3. Health Check Endpoints

Test each service health:

```bash
# API Gateway
curl http://your-server:8081/health

# Time Series Service
curl http://your-server:5001/health

# Forecast Service
curl http://your-server:8001/api/health

# Optimize Service
curl http://your-server:8002/api/health

# Scheduler Service
curl http://your-server:5003/api/health

# Web App
curl http://your-server:3000
```

### 4. Database Connection

Check PostgreSQL is accepting connections:

```bash
# From your deployment machine
docker exec omarino-postgres pg_isready -U omarino
```

Should return: `postgres:5432 - accepting connections`

---

## 🔧 Post-Deployment Configuration

### 1. Initialize Databases

The databases will be automatically created on first run. Check logs:

```bash
# In Portainer, click on omarino-timeseries container
# View logs to see database migration
```

### 2. Configure Grafana

1. Access Grafana: http://your-server:3001
2. Login with configured credentials (default: admin/admin)
3. Add Prometheus as data source:
   - URL: `http://prometheus:9090`
4. Add Loki as data source:
   - URL: `http://loki:3100`
5. Add Tempo as data source:
   - URL: `http://tempo:3200`

### 3. Test API Gateway

Create a test request:

```bash
curl -X POST http://your-server:8081/api/timeseries/meters \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Meter",
    "type": "Electricity",
    "unit": "kWh"
  }'
```

---

## 📊 Monitoring

### View Logs in Portainer

1. Go to **Containers**
2. Click on any container name
3. Click **Logs** tab
4. Enable **Auto-refresh**

### Common Log Locations

- **Application Logs**: View in Portainer or Loki
- **Database Logs**: omarino-postgres container logs
- **Gateway Logs**: omarino-gateway container logs

### Metrics & Dashboards

Access Prometheus: http://your-server:9090

Key metrics to monitor:
- Container CPU/Memory usage
- API request rates
- Database connection pool
- Redis cache hit ratio

---

## 🚨 Troubleshooting

### Container Won't Start

1. Check logs in Portainer
2. Verify environment variables are set correctly
3. Ensure ports are not already in use
4. Check disk space for volumes

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker exec omarino-postgres pg_isready -U omarino

# Check connection from service
docker exec omarino-timeseries curl -f http://postgres:5432
```

### Image Pull Errors

If you see "manifest not found" errors:
1. Verify registry is accessible: `curl http://192.168.61.21:32768/v2/`
2. Re-run the fix script: `bash scripts/fix-multi-arch-images.sh`
3. Redeploy the stack

### Services Not Healthy

Wait 2-3 minutes for initial startup. If still unhealthy:
1. Check container logs
2. Verify dependencies are running (postgres, redis)
3. Check network connectivity between containers

---

## 🔄 Stack Management

### Update Stack

1. Go to **Stacks** → **OMARINO-EMS**
2. Click **Editor** tab
3. Make changes
4. Click **Update the stack**
5. Choose update method:
   - **Pull and redeploy**: Pull latest images
   - **Redeploy**: Use existing images

### Stop Stack

1. Go to **Stacks** → **OMARINO-EMS**
2. Click **Stop this stack**

### Remove Stack

1. Go to **Stacks** → **OMARINO-EMS**
2. Click **Delete this stack**
3. ⚠️ **Warning**: This will remove all containers and volumes (data loss!)

### Backup Data

Before removing the stack, backup volumes:

```bash
# Backup PostgreSQL data
docker run --rm -v omarino_postgres_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres-backup.tar.gz /data

# Backup Grafana data
docker run --rm -v omarino_grafana_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/grafana-backup.tar.gz /data
```

---

## 📈 Scaling

### Scale Individual Services

In Portainer:
1. Go to **Services** (if using Swarm mode)
2. Or manually adjust replicas in stack YAML
3. Update deploy.replicas for each service

### Resource Limits

Add to each service in docker-compose.portainer.yml:

```yaml
deploy:
  resources:
    limits:
      cpus: '1'
      memory: 2G
    reservations:
      cpus: '0.5'
      memory: 512M
```

---

## 🔐 Security Recommendations

### 1. Change Default Passwords

Update all environment variables with strong passwords:
- POSTGRES_PASSWORD
- REDIS_PASSWORD
- JWT_SECRET_KEY
- GRAFANA_PASSWORD
- NEXTAUTH_SECRET

### 2. Enable TLS/SSL

Add reverse proxy (Nginx/Traefik) with SSL certificates.

### 3. Network Isolation

Consider using Portainer's network management to isolate services.

### 4. Regular Updates

```bash
# Rebuild and push new images
./scripts/simple-build-push.sh

# Update stack in Portainer with "Pull and redeploy"
```

---

## 📞 Support

For issues or questions:
- **Email**: omar@omarino.de
- **Website**: https://www.omarino.de/ems-suite

---

**OMARINO IT Services, Inh. Omar Zaror**  
© 2025 All Rights Reserved
