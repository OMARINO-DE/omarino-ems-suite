# Forecasts and Optimization Pages Fix

## Issue

The `/forecasts` and `/optimization` pages were showing:
```
Application error: a client-side exception has occurred (see the browser console for more information)
```

## Root Cause

The API endpoints were returning data in wrapped objects:
- `/api/forecast/models` returned `{"models": [...]}`
- `/api/optimize/types` returned `{"types": [...]}`

However, the API client in `webapp/src/lib/api.ts` was returning `response.data` directly without extracting the nested arrays, so the React components received objects instead of arrays.

## Solution

Updated the API client methods to extract the nested data:

### Forecasts API (`webapp/src/lib/api.ts`)

**Before:**
```typescript
forecasts: {
  listModels: () => apiClient.get<any[]>('/api/forecast/models'),
  getForecasts: (params?: { limit?: number }) =>
    apiClient.get<any[]>('/api/forecast/forecasts', { params }),
}
```

**After:**
```typescript
forecasts: {
  listModels: async () => {
    const response = await apiClient.get<{ models: any[] }>('/api/forecast/models')
    return response.models || []
  },
  getForecasts: async (params?: { limit?: number }) => {
    try {
      const response = await apiClient.get<{ forecasts: any[] }>('/api/forecast/forecasts', { params })
      return response.forecasts || []
    } catch (error: any) {
      // Return empty array if 404 (no forecasts yet)
      if (error.response?.status === 404) {
        return []
      }
      throw error
    }
  },
}
```

### Optimization API (`webapp/src/lib/api.ts`)

**Before:**
```typescript
optimization: {
  listTypes: () => apiClient.get<any[]>('/api/optimize/types'),
  listOptimizations: (params?: { status?: string; type?: string; limit?: number }) =>
    apiClient.get<any[]>('/api/optimize', { params }),
}
```

**After:**
```typescript
optimization: {
  listTypes: async () => {
    const response = await apiClient.get<{ types: any[] }>('/api/optimize/types')
    return response.types || []
  },
  listOptimizations: async (params?: { status?: string; type?: string; limit?: number }) => {
    try {
      const response = await apiClient.get<{ optimizations: any[] }>('/api/optimize', { params })
      return response.optimizations || []
    } catch (error: any) {
      // Return empty array if 404 (no optimizations yet)
      if (error.response?.status === 404) {
        return []
      }
      throw error
    }
  },
}
```

## Deployment

1. **Updated file:** `webapp/src/lib/api.ts`
2. **Rebuilt webapp:**
   ```bash
   docker build --no-cache --platform linux/amd64 \
     --build-arg NEXT_PUBLIC_API_URL='https://ems-back.omarino.net' \
     -t 192.168.61.21:32768/omarino-ems/webapp:latest .
   ```
3. **Pushed to registry:**
   ```bash
   docker push 192.168.61.21:32768/omarino-ems/webapp:latest
   ```
4. **Deployed to production:**
   - Image digest: `sha256:02b3f458ec4130befbfe74412dc3607958fca74fb2c685930cb8abeab1ef8e80`
   - Container ID: `13dec3e5ea85`

## Verification

Test the fixed pages:
```bash
# Test forecasts page
curl https://ems-demo.omarino.net/forecasts

# Test optimization page
curl https://ems-demo.omarino.net/optimization

# Test API endpoints directly
curl https://ems-back.omarino.net/api/forecast/models | jq '.models | length'
curl https://ems-back.omarino.net/api/optimize/types | jq '.types | length'
```

Expected results:
- ✅ Pages load without errors
- ✅ "Available Models" section shows 7 forecast models
- ✅ "Optimization Types" section shows 5 optimization types
- ✅ "Recent Forecasts" and "Recent Optimizations" sections show empty state (no data yet)

## Additional Notes

### Error Handling

The fix also includes better error handling:
- Returns empty arrays for 404 responses (no data available yet)
- Properly propagates other errors to the UI
- Provides fallback empty arrays if response properties are undefined

### API Response Structure

The backend services return data in this format:
```json
{
  "models": [...],      // for /api/forecast/models
  "forecasts": [...],   // for /api/forecast/forecasts
  "types": [...],       // for /api/optimize/types
  "optimizations": [...] // for /api/optimize
}
```

### Future Considerations

If other API endpoints follow similar patterns (returning wrapped data), they should be updated using the same approach:
1. Define the response type with the wrapper object
2. Extract the nested data
3. Return empty array as fallback
4. Handle 404 errors gracefully

---

**Fixed:** 2025-10-06  
**Status:** ✅ Deployed and working  
**Pages affected:** `/forecasts`, `/optimization`  
**Files modified:** `webapp/src/lib/api.ts`
