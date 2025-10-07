# Forecast Creation Fix

## Issue

When trying to create a new forecast from the webapp at `/forecasts/new`, the user received a "Not Found" error.

## Root Causes

Multiple issues were identified and fixed:

### 1. Incorrect API Endpoint in Frontend

**Problem:** The frontend was calling `/api/forecast/models/{model}/forecast` but the actual endpoint is `/api/forecast/forecast` with the model in the request body.

**File:** `webapp/src/lib/api.ts`

**Before:**
```typescript
runForecast: (model: string, params: any) =>
  apiClient.post<any>(`/api/forecast/models/${model}/forecast`, params),
```

**After:**
```typescript
runForecast: (model: string, params: any) =>
  apiClient.post<any>('/api/forecast/forecast', { ...params, model }),
```

### 2. Incorrect Request Parameters

**Problem:** The frontend was sending `seriesId` and `interval`, but the API expects `series_id` and `granularity` (in ISO 8601 format).

**File:** `webapp/src/app/forecasts/new/page.tsx`

**Before:**
```typescript
await api.forecasts.runForecast(selectedModel, {
  seriesId,
  horizon: parseInt(horizon),
  interval,
})
```

**After:**
```typescript
// Convert interval to ISO 8601 duration format
const granularityMap: Record<string, string> = {
  '15min': 'PT15M',
  '30min': 'PT30M',
  '1H': 'PT1H',
  '1D': 'P1D',
}

await api.forecasts.runForecast(selectedModel, {
  series_id: seriesId,
  horizon: parseInt(horizon),
  granularity: granularityMap[interval] || 'PT1H',
})
```

### 3. Bug in Forecast Service Granularity Parsing

**Problem:** The forecast service was converting 'PT1H' to '1h' (lowercase) but pandas date_range expects '1H' (uppercase) for hours.

**File:** `forecast-service/app/services/forecast_service.py`

**Before:**
```python
mapping = {
    "PT15M": "15min",
    "PT1H": "1h",      # ❌ Wrong - pandas needs uppercase H
    "P1D": "1D",
    "PT30M": "30min",
    "PT5M": "5min"
}
```

**After:**
```python
mapping = {
    "PT15M": "15min",
    "PT1H": "1H",      # ✅ Fixed - uppercase H for hours
    "P1D": "1D",
    "PT30M": "30min",
    "PT5M": "5min"
}
```

This bug was causing the error:
```
Forecast generation failed: unsupported operand type(s) for +: 'Timestamp' and 'str'
```

### 4. Missing Forecast Service Container

**Problem:** The forecast service container wasn't running on the production server.

**Solution:** Started the container manually with proper configuration:
```bash
docker run -d \
  --name omarino-forecast \
  --network ems_omarino-network \
  -e ENVIRONMENT=production \
  -e LOG_LEVEL=info \
  -e TIMESERIES_SERVICE_URL=http://timeseries-service:5001 \
  -p 8009:8001 \
  --restart unless-stopped \
  192.168.61.21:32768/omarino-ems/forecast-service:latest
```

## API Contract

The correct forecast API request format is:

```json
POST /api/forecast/forecast
{
  "series_id": "uuid-string",
  "horizon": 24,
  "granularity": "PT1H",
  "model": "last_value"
}
```

**Required Fields:**
- `series_id` (UUID): ID of the time series to forecast
- `horizon` (int): Number of periods to forecast (1-8760)
- `granularity` (string): ISO 8601 duration (PT15M, PT30M, PT1H, P1D)
- `model` (string): Model to use (auto, arima, ets, xgboost, lightgbm, seasonal_naive, last_value)

**Optional Fields:**
- `start_time` (datetime): Start time for forecast
- `quantiles` (array): Quantiles for probabilistic forecasting (default: [0.1, 0.5, 0.9])
- `external_features` (object): External regressors
- `training_window` (int): Number of historical periods
- `confidence_level` (float): Confidence level (0.0-1.0, default: 0.95)

## Deployment

### Webapp
1. **Built:** Fixed API client and form submission
2. **Image:** `192.168.61.21:32768/omarino-ems/webapp:latest`
3. **Digest:** `sha256:91bfbcd44618648de00bea9cbe83982b03a9f736cbd81b2ddbc4c916af8e8122`
4. **Container:** `79272ea86be5` (running)

### Forecast Service
1. **Built:** Fixed granularity parsing
2. **Image:** `192.168.61.21:32768/omarino-ems/forecast-service:latest`
3. **Digest:** `sha256:42695df0ff5c230a5a059bc343f3747188b5c10f600d5ae4d46b6143d7bcaaf5`
4. **Container:** `b9e30a80c3e8` (running on port 8009:8001)

## Testing

### Test the Forecast API Directly

```bash
# Get a series ID
SERIES_ID=$(curl -s https://ems-back.omarino.net/api/timeseries/series | jq -r '.[0].id')

# Create a forecast
curl -X POST https://ems-back.omarino.net/api/forecast/forecast \
  -H "Content-Type: application/json" \
  -d "{
    \"series_id\": \"$SERIES_ID\",
    \"horizon\": 24,
    \"granularity\": \"PT1H\",
    \"model\": \"last_value\"
  }" | jq '.'
```

Expected response:
```json
{
  "forecast_id": "uuid",
  "series_id": "uuid",
  "model_used": "last_value",
  "created_at": "timestamp",
  "timestamps": [...],
  "point_forecast": [...],
  "quantiles": {...},
  "metrics": null,
  "metadata": {
    "training_samples": 1000,
    "training_time_seconds": 0.123
  }
}
```

### Test via Webapp

1. Go to https://ems-demo.omarino.net/forecasts/new
2. Select a forecast model (e.g., "last_value")
3. Select a time series from the dropdown
4. Set horizon (e.g., 24 hours)
5. Select interval (e.g., 1 hour)
6. Click "Create Forecast"
7. Should redirect to `/forecasts` page
8. Forecast should be created successfully

## Files Modified

1. `webapp/src/lib/api.ts` - Fixed forecast API endpoint
2. `webapp/src/app/forecasts/new/page.tsx` - Fixed request parameters with ISO 8601 conversion
3. `forecast-service/app/services/forecast_service.py` - Fixed granularity parsing (1h → 1H)

## Services Deployed

1. **Webapp** - Container ID: `79272ea86be5`
2. **Forecast Service** - Container ID: `b9e30a80c3e8`

## Verification Checklist

- [ ] Forecast service is running and healthy
- [ ] API endpoint `/api/forecast/forecast` returns 200 (not 404)
- [ ] Webapp form submits without errors
- [ ] Forecast is created and returned with valid data
- [ ] User is redirected to forecasts list page
- [ ] No errors in browser console
- [ ] No errors in forecast service logs

---

**Fixed:** 2025-10-06  
**Status:** ✅ Deployed and Ready for Testing  
**Priority:** 🔴 Critical - Core functionality
