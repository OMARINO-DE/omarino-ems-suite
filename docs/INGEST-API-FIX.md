# Time Series Ingest API - Validation Error Fix

## 🔴 Error
```
POST https://ems-back.omarino.net/api/ingest
Status: 400 Bad Request
Import failed: One or more validation errors occurred.
```

## 🔍 Root Cause

The Web UI was sending **incomplete data** to the `/api/ingest` endpoint.

### Required by API (`TimeSeriesPointDto`)

```csharp
public record TimeSeriesPointDto(
    Guid SeriesId,      // ✅ Required
    DateTime Timestamp, // ✅ Required
    double Value,       // ✅ Required
    string? Unit,       // Optional
    DataQuality Quality,// ✅ Required (ENUM, not int!)
    string? Source,     // Optional
    int Version,        // ✅ Required (for conflict resolution)
    Dictionary<string, object>? Metadata  // Optional
);

public enum DataQuality {
    Good,        // Valid data
    Uncertain,   // Data quality uncertain
    Bad,         // Data quality bad
    Estimated,   // Estimated/interpolated
    Missing      // Missing data
}
```

### What UI Was Sending (WRONG ❌)

```javascript
{
  seriesId: "...",
  timestamp: "2025-10-07T...",
  value: 123.45,
  quality: 100  // ❌ WRONG - Integer instead of enum string
  // ❌ MISSING: version (required!)
  // ❌ MISSING: unit, source (optional but good to include)
}
```

**Problems**:
1. ❌ `quality` was `100` (int) instead of `"Good"` (enum string)
2. ❌ `version` field was completely missing (required!)
3. ❌ `unit` and `source` were missing (optional but helpful)

## ✅ Solution

### Fixed Web UI Code

**File**: `webapp/src/app/timeseries/page.tsx`

```typescript
// BEFORE (BROKEN)
allPoints.push({
  seriesId: seriesId,
  timestamp: row.timestamp,
  value: parseFloat(row.value),
  quality: 100  // ❌ Wrong type
})

// AFTER (FIXED)
allPoints.push({
  seriesId: seriesId,
  timestamp: row.timestamp,
  value: parseFloat(row.value),
  unit: row.unit || null,
  quality: 'Good',  // ✅ Enum string
  source: file.name,
  version: 1,  // ✅ Required field
  metadata: null
})
```

## 🧪 Testing

### Test Payload (Correct Format)

```json
{
  "source": "test-data.csv",
  "points": [
    {
      "seriesId": "123e4567-e89b-12d3-a456-426614174000",
      "timestamp": "2025-10-07T12:00:00Z",
      "value": 125.5,
      "unit": "kWh",
      "quality": "Good",
      "source": "CSV Import",
      "version": 1,
      "metadata": null
    }
  ]
}
```

### Test with curl

```bash
curl -X POST https://ems-back.omarino.net/api/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source": "test",
    "points": [
      {
        "seriesId": "YOUR-SERIES-ID-HERE",
        "timestamp": "2025-10-07T12:00:00Z",
        "value": 100.0,
        "unit": "kWh",
        "quality": "Good",
        "source": "test",
        "version": 1,
        "metadata": null
      }
    ]
  }'
```

Expected success response:
```json
{
  "jobId": "...",
  "pointsImported": 1,
  "pointsFailed": 0,
  "errors": null
}
```

## 📋 Field Reference

### Required Fields
- **seriesId** (string/GUID): ID of the time series
- **timestamp** (string/DateTime): ISO 8601 format
- **value** (number/double): Numeric value
- **quality** (string/enum): One of: `Good`, `Uncertain`, `Bad`, `Estimated`, `Missing`
- **version** (number/int): Version for conflict resolution (start with 1)

### Optional Fields
- **unit** (string?): Unit of measurement (e.g., "kWh", "°C")
- **source** (string?): Source of data (e.g., "CSV Import", "API")
- **metadata** (object?): Additional key-value metadata

## 🔄 Next Steps

1. ✅ Fix deployed in webapp code
2. 🔄 Redeploy webapp to production
3. ✅ Test import functionality
4. ✅ Update documentation

## 📝 Deployment

### Deploy Fixed Webapp

```bash
# Navigate to webapp directory
cd webapp

# Build production bundle
npm run build

# Deploy to server
rsync -avz --exclude='node_modules' \
  -e "ssh -i '/path/to/key.pem'" \
  .next/ user@server:/path/to/webapp/.next/
```

Or rebuild Docker container:
```bash
cd webapp
docker build -t omarino-webapp:latest .
docker stop omarino-webapp
docker rm omarino-webapp
docker run -d --name omarino-webapp -p 3000:3000 omarino-webapp:latest
```

## 🐛 Debugging Tips

### Check Request Payload in Browser

1. Open Browser DevTools (F12)
2. Network tab
3. Find POST to `/api/ingest`
4. Click → Payload/Request tab
5. Verify all required fields present
6. Check `quality` is string not number
7. Check `version` field exists

### Common Validation Errors

| Error | Cause | Fix |
|-------|-------|-----|
| "The field SeriesId is required" | Missing or invalid GUID | Check series exists |
| "The field Timestamp is required" | Invalid date format | Use ISO 8601 |
| "The field Value is required" | Missing or NaN | Ensure valid number |
| "The field Quality is required" | Missing quality | Add "Good" |
| "The field Version is required" | Missing version | Add version: 1 |
| "The value '100' is not valid for Quality" | Integer instead of enum | Use "Good" not 100 |

### Check API Logs

```bash
# View timeseries service logs
sudo docker logs omarino-timeseries --tail 100

# Look for validation errors
sudo docker logs omarino-timeseries 2>&1 | grep -i "validation"
```

## 📚 Related Documentation

- `timeseries-service/DTOs/RequestsResponses.cs` - API contracts
- `timeseries-service/Models/TimeSeriesPoint.cs` - Data model
- `timeseries-service/Controllers/IngestController.cs` - Endpoint implementation
- `webapp/src/app/timeseries/page.tsx` - Web UI implementation

---

**Status**: ✅ Fixed  
**Date**: October 7, 2025  
**Issue**: Missing `version` field and wrong `quality` type  
**Solution**: Updated webapp to send complete payload with correct types
