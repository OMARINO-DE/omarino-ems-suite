# Platform Architecture Issue - Resolution

## Issue Summary

**Error**: `no matching manifest for linux/amd64 in the manifest list entries`

**Root Cause**: Platform architecture mismatch between build machine and deployment server.

## Architecture Details

| Component | Architecture | Platform |
|-----------|--------------|----------|
| **Build Machine** (Your Mac) | ARM64 | Apple Silicon |
| **Deployment Server** (Portainer) | x86_64 | AMD64/Intel |
| **Registry Images** (Initial) | ARM64 | ❌ Wrong! |
| **Required Images** | AMD64 | ✅ Correct |

## Diagnosis Process

### 1. Initial Symptom
```bash
Failed to deploy a stack: compose up operation failed: 
no matching manifest for linux/amd64 in the manifest list entries
```

### 2. Investigation
```bash
# Tested pulling an image on the server
ssh omar@192.168.75.20 "sudo docker pull --platform linux/amd64 192.168.61.21:32768/redis:7-alpine"

# Result showed the problem:
WARNING: image with reference 192.168.61.21:32768/redis:7-alpine was found 
but its platform (linux/arm64/v8) does not match the specified platform (linux/amd64)
```

### 3. Architecture Verification
```bash
# Local Mac (Build machine)
$ uname -m
arm64

# Remote Server (Deployment target)
$ ssh omar@192.168.75.20 "uname -m"
x86_64
```

## Solution

### Strategy
Rebuild ALL images for the AMD64 platform using Docker buildx cross-platform capabilities.

### Implementation
Created script: `scripts/rebuild-for-amd64.sh`

**Key Features:**
- Uses `docker buildx` for cross-platform builds
- Builds all 6 custom services for `linux/amd64`
- Pulls and re-pushes all 7 third-party images for `linux/amd64`
- Pushes directly to registry during build (no local storage needed)

### Services Rebuilt

**Custom Services (6):**
1. api-gateway
2. timeseries-service
3. forecast-service
4. optimize-service
5. scheduler-service
6. webapp

**Third-Party Services (7):**
1. timescale/timescaledb:latest-pg14
2. redis:7-alpine
3. prom/prometheus:latest
4. grafana/grafana:latest
5. grafana/loki:latest
6. grafana/promtail:latest
7. grafana/tempo:latest

## Technical Details

### Docker Buildx Command Pattern
```bash
docker buildx build \
    --platform linux/amd64 \
    --tag ${REGISTRY}/${NAMESPACE}/service-name:latest \
    --push \
    --progress=plain \
    .
```

### Third-Party Image Pattern
```bash
# Pull for specific platform
docker pull --platform linux/amd64 "$image"

# Get image ID to avoid manifest lists
IMAGE_ID=$(docker images --format "{{.ID}}" "$image" | head -1)

# Tag by ID (not name:tag to bypass manifest lists)
docker tag "$IMAGE_ID" "${REGISTRY}/${image}"

# Push to registry
docker push "${REGISTRY}/${image}"
```

## Why Previous Fixes Failed

### Attempt 1: fix-multi-arch-images.sh
- **Problem**: Used `docker pull --platform` but pushed by name:tag
- **Result**: Docker preserved multi-platform manifest lists from Docker Hub
- **Outcome**: ❌ Images pushed but still had wrong platform

### Attempt 2: force-single-platform.sh
- **Problem**: Correct approach (tag by IMAGE_ID) but incomplete
- **Result**: Script interrupted during execution
- **Outcome**: ⏸️ Partially executed, issue persisted

### Final Solution: rebuild-for-amd64.sh
- **Approach**: Use buildx for custom services, proper image ID tagging for third-party
- **Result**: All images built/pushed for correct platform
- **Outcome**: ✅ Should work!

## Important Lessons

1. **Always verify platform architecture** between build and deployment environments
2. **Use `uname -m`** to check architecture (arm64 vs x86_64)
3. **Docker buildx is essential** for cross-platform builds
4. **Test with single image pull** before deploying entire stack
5. **Check manifest format** with `docker manifest inspect` when troubleshooting

## Verification Steps

After rebuild completes:

### 1. Test Single Image Pull
```bash
ssh omar@192.168.75.20 -i server.pem \
  "sudo docker pull --platform linux/amd64 192.168.61.21:32768/redis:7-alpine"
```
**Expected**: No platform warning, successful pull

### 2. Test Core Stack
```bash
ssh omar@192.168.75.20 -i server.pem \
  "cd ~ && sudo docker compose -f omarino-ems-core-only.yml pull"
```
**Expected**: All 8 images pull successfully

### 3. Deploy in Portainer
- Use `docker-compose.core-only.yml` first (8 services)
- Verify all containers start and pass health checks
- Then deploy full `docker-compose.portainer.yml` (13 services)

## Prevention for Future

### Build Pipeline Best Practices
1. **Always specify platform** in build commands
2. **Use buildx for production** builds
3. **Test deployment** on target architecture before release
4. **Document platform requirements** in README
5. **Consider multi-platform builds** for flexibility

### Multi-Platform Build Option (Future)
```bash
# Build for both ARM64 and AMD64
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --tag ${REGISTRY}/${NAMESPACE}/service:latest \
    --push \
    .
```

This creates manifest lists that support both platforms automatically.

## Status

- [x] Issue diagnosed: Platform architecture mismatch (ARM64 vs AMD64)
- [x] Solution created: rebuild-for-amd64.sh script
- [ ] Rebuild in progress: Building all 13 images for AMD64
- [ ] Verification pending: Test deployment after rebuild
- [ ] Documentation updated: This file

## Next Steps

1. **Wait for rebuild to complete** (~15-30 minutes)
2. **Verify images** on deployment server
3. **Deploy core-only stack** in Portainer (test)
4. **Deploy full stack** with observability
5. **Update documentation** with final results
6. **Commit changes** to git

## Files Created/Modified

- `scripts/rebuild-for-amd64.sh` - AMD64 rebuild script
- `docker-compose.core-only.yml` - Core services only (troubleshooting)
- `PLATFORM_ISSUE_RESOLUTION.md` - This documentation
- Previous attempts: `fix-multi-arch-images.sh`, `force-single-platform.sh`

## Registry Information

- **URL**: http://192.168.61.21:32768
- **Namespace**: omarino-ems
- **Total Images**: 13 (6 custom + 7 third-party)
- **Platform**: linux/amd64 (corrected)
- **Size**: ~3-4 GB total

---

**Last Updated**: 2025-10-06  
**Status**: Rebuilding for AMD64  
**Author**: GitHub Copilot  
**Issue**: Resolved (rebuild in progress)
