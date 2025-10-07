# Container Registry Push - October 6, 2025

## Images Pushed to Registry: 192.168.61.21:32768

### 1. API Gateway
**Image**: `192.168.61.21:32768/omarino-ems/api-gateway:latest`
**Digest**: `sha256:b34750ed3cea7d0744303570fbe7538a02c068ef582fd009bec01001de1e84d6`
**Changes**:
- ✅ Updated CORS policy to allow `https://ems-demo.omarino.net`
- ✅ Updated CORS policy to allow `http://192.168.75.20:3000`
- ✅ Maintains existing localhost development origins

**Build Time**: ~35 seconds
**Platform**: linux/amd64

### 2. Time Series Service
**Image**: `192.168.61.21:32768/omarino-ems/timeseries-service:latest`
**Digest**: `sha256:8265ed1d71766063217515283aaa6ed71afc505d8515c94361ae56e054e2555e`
**Changes**:
- ✅ Added Npgsql dynamic JSON support for Dictionary<string, string> fields
- ✅ Configured for JSONB serialization in PostgreSQL
- ✅ Removed auto-migration on startup (tables manually created)

**Build Time**: ~15 seconds
**Platform**: linux/amd64

## Registry Information
- **Registry URL**: http://192.168.61.21:32768
- **Repository**: omarino-ems
- **Access**: Local network only

## Deployment Notes

### To pull and deploy these images on the server:

#### API Gateway:
```bash
ssh omar@192.168.75.20 -i "path/to/server.pem" \
  "sudo docker pull 192.168.61.21:32768/omarino-ems/api-gateway:latest && \
   sudo docker stop omarino-gateway && \
   sudo docker rm omarino-gateway && \
   sudo docker run -d \
     --name omarino-gateway \
     --network ems_omarino-network \
     -p 8081:8080 \
     -e ASPNETCORE_ENVIRONMENT=Production \
     -e ServiceUrls__TimeSeriesService='http://omarino-timeseries:5001' \
     -e ServiceUrls__ForecastService='http://omarino-forecast:5002' \
     -e ServiceUrls__OptimizeService='http://omarino-optimize:5003' \
     -e ServiceUrls__SchedulerService='http://omarino-scheduler:5004' \
     --restart unless-stopped \
     192.168.61.21:32768/omarino-ems/api-gateway:latest"
```

#### Time Series Service:
```bash
ssh omar@192.168.75.20 -i "path/to/server.pem" \
  "sudo docker pull 192.168.61.21:32768/omarino-ems/timeseries-service:latest && \
   sudo docker stop omarino-timeseries && \
   sudo docker rm omarino-timeseries && \
   sudo docker run -d \
     --name omarino-timeseries \
     --network ems_omarino-network \
     -p 5001:5001 \
     -e ASPNETCORE_ENVIRONMENT=Production \
     -e ConnectionStrings__DefaultConnection='Host=omarino-postgres;Port=5432;Database=omarino_timeseries;Username=omarino;Password=omarino_dev_pass' \
     --restart unless-stopped \
     192.168.61.21:32768/omarino-ems/timeseries-service:latest"
```

## Current Deployment Status
- ✅ API Gateway: Running on 192.168.75.20:8081 (healthy)
- ✅ Webapp: Running on 192.168.75.20:3000 → https://ems-demo.omarino.net
- ⚠️ Time Series Service: Image pushed, but service needs database schema (tables created manually)

## Related Files
- FRONTEND_CORS_FIX.md - Details of CORS configuration changes
- timeseries-service/init-schema.sql - Database schema for time series tables

## Next Steps
1. Pull images from registry on any new deployment servers
2. Ensure database schemas are created before starting services
3. Configure environment variables appropriately for each environment
4. Monitor service health after deployment

---
**Date**: October 6, 2025
**Registry**: 192.168.61.21:32768
**Tag**: latest
