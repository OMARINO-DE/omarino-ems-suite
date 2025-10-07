# Frontend API Endpoint Fixes

## Overview

Fixed incorrect API endpoint paths in the frontend that were preventing demo data from being displayed.

## Problem

The frontend was calling API endpoints that didn't match the actual backend routes, causing the UI to not display any data even though the data was successfully inserted into the database.

---

## Issues Found

### 1. **Time Series Endpoints Mismatch**

**Problem:** Frontend was calling endpoints that don't exist in the backend.

#### Before (Incorrect):
```typescript
timeseries: {
  getSeries: (meterId: string) => 
    apiClient.get<any[]>(`/api/timeseries/meters/${meterId}/series`),
  getSeriesData: (seriesId: string, params?: { start?: string; end?: string; limit?: number }) =>
    apiClient.get<any[]>(`/api/timeseries/series/${seriesId}/data`, { params }),
  ingestData: (data: any) => 
    apiClient.post('/api/timeseries/ingest', data),
}
```

**Issues:**
- `/api/timeseries/meters/{meterId}/series` - This endpoint doesn't exist
- `/api/timeseries/series/{seriesId}/data` - Wrong endpoint (should be `/range`)
- `/api/timeseries/ingest` - Incorrect (should be `/api/ingest`)

#### After (Correct):
```typescript
timeseries: {
  getSeries: (meterId?: string) => 
    apiClient.get<any[]>('/api/timeseries/series', { params: meterId ? { meterId } : undefined }),
  getSeriesData: (seriesId: string, params?: { from?: string; to?: string; agg?: string; interval?: string }) =>
    apiClient.get<any>(`/api/timeseries/series/${seriesId}/range`, { params }),
  ingestData: (data: any) => 
    apiClient.post('/api/ingest', data),
}
```

**Fixes:**
- ✅ Changed to query parameter: `/api/timeseries/series?meterId={id}`
- ✅ Updated endpoint to `/range` with correct parameters (`from`, `to`, `agg`, `interval`)
- ✅ Fixed ingest endpoint to `/api/ingest`

---

### 2. **Scheduler Endpoints Missing Prefix**

**Problem:** Frontend was missing the `/api/scheduler` prefix for workflow and execution endpoints.

#### Before (Incorrect):
```typescript
scheduler: {
  getWorkflows: () => apiClient.get<any[]>('/api/workflows'),
  getWorkflow: (id: string) => apiClient.get<any>(`/api/workflows/${id}`),
  createWorkflow: (workflow: any) => apiClient.post<any>('/api/workflows', workflow),
  // ... more endpoints without /api/scheduler prefix
}
```

#### After (Correct):
```typescript
scheduler: {
  getWorkflows: () => apiClient.get<any[]>('/api/scheduler/workflows'),
  getWorkflow: (id: string) => apiClient.get<any>(`/api/scheduler/workflows/${id}`),
  createWorkflow: (workflow: any) => apiClient.post<any>('/api/scheduler/workflows', workflow),
  // ... all endpoints now have /api/scheduler prefix
}
```

**Fixes:**
- ✅ Added `/scheduler` prefix to all workflow endpoints
- ✅ Added `/scheduler` prefix to all execution endpoints
- ✅ Jobs endpoint already had correct prefix

---

## Backend API Structure

### API Gateway Routes (from `appsettings.json`)

The API Gateway uses YARP reverse proxy with the following route transformations:

```json
{
  "timeseries-route": {
    "Match": { "Path": "/api/timeseries/{**catch-all}" },
    "Transforms": [{ "PathPattern": "/api/{**catch-all}" }]
  }
}
```

**This means:**
- Frontend calls: `/api/timeseries/meters` 
- Gateway transforms to: `/api/meters` 
- Routes to: `http://timeseries-service:5001/api/meters`

### Actual Backend Endpoints

#### TimeSeries Service (`/api/timeseries/*`)
- `GET /api/timeseries/meters` → Get all meters
- `GET /api/timeseries/meters/{id}` → Get specific meter
- `GET /api/timeseries/series?meterId={id}` → Get series for a meter (query param!)
- `GET /api/timeseries/series/{id}` → Get specific series
- `GET /api/timeseries/series/{id}/range?from={}&to={}` → Query time series data
- `POST /api/ingest` → Ingest data points (note: no `/timeseries` prefix!)

#### Scheduler Service (`/api/scheduler/*`)
- `GET /api/scheduler/workflows` → Get all workflows
- `GET /api/scheduler/workflows/{id}` → Get specific workflow
- `POST /api/scheduler/workflows` → Create workflow
- `GET /api/scheduler/executions` → Get executions

---

## Testing & Verification

### 1. **Verify Meters Endpoint**
```bash
curl 'http://192.168.75.20:8081/api/timeseries/meters' | jq 'length'
# Expected: 20 (we have duplicates from multiple runs)
```

### 2. **Verify Series Endpoint with Query Parameter**
```bash
curl 'http://192.168.75.20:8081/api/timeseries/series?meterId=3381b0ab-2b1f-40f6-bd2f-d9191de75539' | jq 'length'
# Expected: 3 (series for that meter)
```

### 3. **Verify Data Query Endpoint**
```bash
curl 'http://192.168.75.20:8081/api/timeseries/series/d5009f63-0d60-4252-b96f-62c308ce7e7b/range?from=2025-09-29T00:00:00Z&to=2025-10-06T23:59:59Z' | jq '.points | length'
# Expected: 168 (7 days × 24 hours)
```

---

## Deployment

### Build and Deploy Steps

1. **Build webapp with correct API URL:**
```bash
cd webapp
docker build --no-cache --platform linux/amd64 \
  --build-arg NEXT_PUBLIC_API_URL='http://192.168.75.20:8081' \
  -t 192.168.61.21:32768/omarino-ems/webapp:latest .
```

2. **Push to registry:**
```bash
docker push 192.168.61.21:32768/omarino-ems/webapp:latest
```

3. **Pull and restart on server:**
```bash
ssh omar@192.168.75.20 << 'EOF'
  sudo docker pull 192.168.61.21:32768/omarino-ems/webapp:latest
  sudo docker stop omarino-webapp
  sudo docker rm omarino-webapp
  sudo docker run -d --name omarino-webapp \
    --network ems_omarino-network \
    -p 3000:3000 \
    -e NODE_ENV=production \
    192.168.61.21:32768/omarino-ems/webapp:latest
EOF
```

---

## Current System Status

### Data Available
- ✅ **20 Meters** (5 unique, with duplicates from multiple demo runs)
- ✅ **24 Series** (linked to latest meter set)
- ✅ **4,032 Data Points** (7 days × 24 hours × 24 series)

### API Endpoints
- ✅ `/api/timeseries/meters` - Working
- ✅ `/api/timeseries/series?meterId={id}` - Working (fixed!)
- ✅ `/api/timeseries/series/{id}/range` - Working (fixed!)
- ✅ `/api/ingest` - Working (fixed!)
- ✅ `/api/scheduler/*` - Fixed with correct prefix

### Frontend
- ✅ **Deployed:** https://ems-demo.omarino.net
- ✅ **Container:** omarino-webapp (57aba22f1e66)
- ✅ **Status:** Running
- ✅ **API URL:** http://192.168.75.20:8081 (baked into build)
- ✅ **API Client:** Fixed endpoints

---

## Files Modified

### `/webapp/src/lib/api.ts`

**Changes:**
1. Updated `getSeries()` to use query parameter instead of path parameter
2. Updated `getSeriesData()` to use `/range` endpoint with correct parameters
3. Fixed `ingestData()` to use `/api/ingest`
4. Added `/scheduler` prefix to all workflow and execution endpoints

**Lines Changed:** 73-122

---

## Known Issues

### Duplicate Meters
Running the demo data script multiple times created duplicate meters. This doesn't affect functionality but clutters the database.

**Solution:** Clean up duplicates or modify demo script to check for existing data before insertion.

### Meter-Series Mismatch
The first 15 meters (from earlier runs) don't have series linked to them. Only the latest 5 meters have series with data.

**Impact:** Frontend will show all 20 meters, but only 5 will have series/data.

**Solution:** Either:
1. Delete old meters: `DELETE FROM "Meters" WHERE "Id" NOT IN (latest_5_ids)`
2. Modify frontend to filter meters without series
3. Clear database and re-run demo data once

---

## Next Steps

1. ✅ Fixed API endpoints in frontend
2. ✅ Rebuilt and deployed webapp
3. ⏭️ Test frontend in browser at https://ems-demo.omarino.net
4. ⏭️ Verify data displays correctly in UI
5. ⏭️ Clean up duplicate meters (optional)
6. ⏭️ Update demo data script to check for existing data

---

**Document Created:** 2025-10-06
**Status:** All API endpoints fixed and deployed
**Frontend URL:** https://ems-demo.omarino.net
