# Docker Image Update Log

This document tracks Docker image rebuilds and pushes to the registry.

## Registry Information
- **Registry URL**: http://192.168.61.21:32768
- **Namespace**: omarino-ems
- **Platform**: linux/amd64

---

## Update: 2025-10-06 (Part 3) - API Gateway Health Check Fix

### Changes
- **Commit**: TBD - Fix health check path for timeseries service
- **File Modified**: `api-gateway/Services/ServiceHealthCheck.cs`
- **Issue**: API Gateway was checking `/api/health` for all services, but timeseries uses `/health`

### What Was Fixed
Updated health check URL logic to handle different service patterns:
```csharp
// Timeseries service uses /health, others use /api/health
var healthPath = serviceName == "Timeseries" ? "/health" : "/api/health";
var healthUrl = $"{serviceEndpoint}{healthPath}";
```

### Docker Image Rebuilt
✅ **api-gateway:latest**
- **Build Command**: `docker buildx build --no-cache --platform linux/amd64 --tag 192.168.61.21:32768/omarino-ems/api-gateway:latest --load .`
- **Build Time**: ~37 seconds
- **New Digest**: `sha256:80a234dcc12c53e7d0a159873eb2cd2c7ca99f4f1ef18233916a06d563e97828`
- **Pushed**: ✅ Successfully pushed to registry
- **Deployed**: ✅ Running on production server
- **Status**: Gateway now reports "All backend services are healthy" ✅

---

## Update: 2025-10-06 (Part 2) - Third-Party Image Architecture Fix

### Issue Discovered
During deployment health check, discovered **redis:7-alpine** image was ARM64, not AMD64.

### Root Cause
Third-party images pulled from Mac (ARM64) were not explicitly pulled for AMD64 platform before pushing to registry.

### Solution
```bash
# On deployment server (has AMD64):
docker pull --platform linux/amd64 redis:7-alpine
docker tag redis:7-alpine 192.168.61.21:32768/omarino-ems/redis:7-alpine
docker push 192.168.61.21:32768/omarino-ems/redis:7-alpine
```

### Docker Image Updated
✅ **redis:7-alpine**
- **Old Digest**: `sha256:a1b2a7c9...` (ARM64 - INCORRECT)
- **New Digest**: `sha256:a1b2a7c905df09bb2d68b0c29a3d2d870a7ba13d58695842492957bc9342eb2d` (AMD64 - CORRECT)
- **Platform**: linux/amd64
- **Status**: Container now starts without "exec format error" ✅

### Lesson Learned
⚠️ **IMPORTANT**: When pushing third-party images to private registry:
1. Always pull with `--platform linux/amd64` flag
2. Pull on the deployment server (AMD64) instead of build machine (ARM64) when possible
3. Verify architecture before pushing: `docker inspect <image> --format='{{.Architecture}}'`

---

## Update: 2025-10-06 (Part 1) - Webapp Scheduler Fix

### Changes
- **Commit**: `6f175dc` - Fix New Workflow button functionality in scheduler page
- **File Modified**: `webapp/src/app/scheduler/page.tsx`
- **Lines Changed**: +209, -3

### What Was Fixed
Added complete "New Workflow" button functionality:
- Modal dialog with workflow creation form
- Fields: name, description, schedule type, cron expression, timezone
- Validation and error handling
- Auto-refresh after creation
- Plus icon from Lucide React

### Docker Image Rebuilt
✅ **webapp:latest**
- **Build Command**: `docker buildx build --platform linux/amd64 --tag 192.168.61.21:32768/omarino-ems/webapp:latest --load .`
- **Build Time**: ~42 seconds
- **New Digest**: `sha256:16db78681784124ba0ba934eb79db6627d981d2483df2b9820d8d7c77b5d5546`
- **Pushed**: ✅ Successfully pushed to registry
- **Verified**: ✅ Pulled successfully on deployment server (192.168.75.20)

### Images NOT Changed (from Part 1)
The following images remained unchanged from the initial build:
- ✅ timeseries-service:latest - No code changes
- ✅ forecast-service:latest - No code changes
- ✅ optimize-service:latest - No code changes
- ✅ scheduler-service:latest - No code changes
- ✅ Third-party images (except redis - see Part 2)

### Deployment Status
🔄 **Ready for Deployment**

The updated webapp image is now available in the registry and ready to deploy via Portainer.

**To deploy the update:**
1. In Portainer, go to Stacks
2. Select the OMARINO-EMS stack
3. Click "Update the stack" or restart the webapp container
4. The new image will be pulled automatically

**To restart just the webapp container:**
```bash
ssh omar@192.168.75.20 -i server.pem
sudo docker restart omarino-webapp
```

Or via docker-compose:
```bash
sudo docker compose -f omarino-ems-core.yml up -d webapp
```

---

## Previous Updates

### 2025-10-06 - Platform Architecture Fix (AMD64 Rebuild)

**All 13 images rebuilt for AMD64 platform:**

**Custom Services:**
1. api-gateway:latest - `sha256:c5a55cf4...`
2. timeseries-service:latest - `sha256:b5e0b5e5...`
3. forecast-service:latest - `sha256:4e579d35...`
4. optimize-service:latest - `sha256:bf15b3f0...`
5. scheduler-service:latest - `sha256:f9bc7ac1...`
6. webapp:latest - `sha256:36b04740...` (superseded by update above)

**Third-Party Images:**
7. timescaledb:latest-pg14 - `sha256:60688ce6...`
8. redis:7-alpine - `sha256:a1b2a7c9...`
9. prometheus:latest - `sha256:d9f75485...`
10. grafana:latest - `sha256:d76d6a64...`
11. loki:latest - `sha256:a67f176f...`
12. promtail:latest - `sha256:a80e3a9c...`
13. tempo:latest - `sha256:2e64b9d7...`

**Issue Resolved**: Platform architecture mismatch (ARM64 vs AMD64)

---

## Rebuild Commands Reference

### Individual Service Rebuild (AMD64)
```bash
cd <service-directory>
docker buildx build \
  --platform linux/amd64 \
  --tag 192.168.61.21:32768/omarino-ems/<service-name>:latest \
  --load \
  .
docker push 192.168.61.21:32768/omarino-ems/<service-name>:latest
```

### All Services Rebuild
```bash
cd "/Users/omarzaror/Library/Mobile Documents/com~apple~CloudDocs/Developing/OMARINO EMS Suite"
bash scripts/rebuild-for-amd64-v2.sh
```

### Verify Image on Server
```bash
ssh omar@192.168.75.20 -i server.pem \
  "sudo docker pull 192.168.61.21:32768/omarino-ems/<service>:latest"
```

### Check Image Architecture
```bash
ssh omar@192.168.75.20 -i server.pem \
  "sudo docker inspect 192.168.61.21:32768/omarino-ems/<service>:latest | grep Architecture"
```

---

## Current Image Status (2025-10-06)

| Image | Version | Digest (first 8 chars) | Platform | Status | Last Updated |
|-------|---------|------------------------|----------|--------|--------------|
| **api-gateway** | **latest** | **80a234dc** | **linux/amd64** | **✅ Updated** | **2025-10-06 (Health check fix)** |
| timeseries-service | latest | b5e0b5e5 | linux/amd64 | ✅ Ready | 2025-10-06 (AMD64 rebuild) |
| forecast-service | latest | 4e579d35 | linux/amd64 | ✅ Ready | 2025-10-06 (AMD64 rebuild) |
| optimize-service | latest | bf15b3f0 | linux/amd64 | ✅ Ready | 2025-10-06 (AMD64 rebuild) |
| scheduler-service | latest | f9bc7ac1 | linux/amd64 | ✅ Ready | 2025-10-06 (AMD64 rebuild) |
| **webapp** | **latest** | **16db7868** | **linux/amd64** | **✅ Updated** | **2025-10-06 (Scheduler fix)** |
| timescaledb | latest-pg14 | 60688ce6 | linux/amd64 | ✅ Ready | 2025-10-06 (AMD64 rebuild) |
| **redis** | **7-alpine** | **a1b2a7c9** | **linux/amd64** | **✅ Fixed** | **2025-10-06 (Architecture fix)** |
| prometheus | latest | d9f75485 | linux/amd64 | ✅ Ready | 2025-10-06 (AMD64 rebuild) |
| grafana | latest | d76d6a64 | linux/amd64 | ✅ Ready | 2025-10-06 (AMD64 rebuild) |
| loki | latest | a67f176f | linux/amd64 | ✅ Ready | 2025-10-06 (AMD64 rebuild) |
| promtail | latest | a80e3a9c | linux/amd64 | ✅ Ready | 2025-10-06 (AMD64 rebuild) |
| tempo | latest | 2e64b9d7 | linux/amd64 | ✅ Ready | 2025-10-06 (AMD64 rebuild) |

### Recent Updates Summary:
- **api-gateway**: Fixed health check path for timeseries service
- **webapp**: Fixed New Workflow button in scheduler page
- **redis**: Fixed ARM64 → AMD64 architecture mismatch

---

## Notes

### When to Rebuild Images

Rebuild an image when:
1. ✅ Code changes in the service directory
2. ✅ Dockerfile modifications
3. ✅ Dependency updates (package.json, requirements.txt, .csproj)
4. ✅ Configuration file changes that are copied into the image
5. ✅ Environment variable defaults in Dockerfile

No rebuild needed when:
1. ❌ Only docker-compose.yml changes
2. ❌ Documentation updates
3. ❌ Script file changes (unless copied into image)
4. ❌ Environment variables passed at runtime

### Build Best Practices

1. **Always specify platform**: `--platform linux/amd64` for deployment server
2. **Use buildx**: For cross-platform builds on ARM64 Mac
3. **Tag correctly**: Use consistent `192.168.61.21:32768/omarino-ems/<service>:latest` format
4. **Verify after push**: Pull on deployment server to confirm
5. **Document changes**: Update this log for tracking

### Troubleshooting

**Build fails with "no matching manifest":**
- Ensure using `--platform linux/amd64`
- Use `docker buildx` instead of regular `docker build`

**Push fails with "http: server gave HTTP response to HTTPS client":**
- Use `--load` flag to load into local Docker first
- Then push separately with `docker push`
- This bypasses buildx's HTTPS requirement

**Old image still running after push:**
- Stop and remove old container
- Pull new image: `docker pull <image>`
- Start container with new image
- Or restart stack in Portainer

---

**Last Updated**: 2025-10-06  
**Maintainer**: GitHub Copilot  
**Registry**: http://192.168.61.21:32768
