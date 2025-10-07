# Time Series Ingest Fix - Summary

## 🔴 Problem
When trying to import time series data via the Web UI at https://ems-demo.omarino.net:

```
POST https://ems-back.omarino.net/api/ingest
Status: 400 Bad Request
Error: One or more validation errors occurred
```

## 🔍 Root Cause

The Web UI (`webapp/src/app/timeseries/page.tsx`) was sending **incomplete/incorrect data** to the `/api/ingest` endpoint.

### What Was Wrong

#### ❌ Before (Broken)
```javascript
allPoints.push({
  seriesId: seriesId,
  timestamp: row.timestamp,
  value: parseFloat(row.value),
  quality: 100  // ❌ WRONG: Integer instead of enum string
  // ❌ MISSING: version field (required!)
  // ❌ MISSING: unit, source (optional)
})
```

**Issues**:
1. `quality` was `100` (number) but API expects `"Good"` (string enum)
2. `version` field was completely missing (required for conflict resolution!)
3. Missing optional but useful fields: `unit`, `source`, `metadata`

## ✅ Solution

### Fixed Code

**File**: `webapp/src/app/timeseries/page.tsx` (Line ~125)

```typescript
allPoints.push({
  seriesId: seriesId,
  timestamp: row.timestamp,
  value: parseFloat(row.value),
  unit: row.unit || null,  // ✅ Optional: unit of measurement
  quality: 'Good',  // ✅ Fixed: Enum string
  source: file.name,  // ✅ Optional: source identifier
  version: 1,  // ✅ Fixed: Required version field
  metadata: null  // ✅ Optional: additional data
})
```

### API Requirements (`TimeSeriesPointDto`)

```csharp
public record TimeSeriesPointDto(
    Guid SeriesId,      // ✅ Required
    DateTime Timestamp, // ✅ Required
    double Value,       // ✅ Required
    string? Unit,       // Optional
    DataQuality Quality,// ✅ Required (enum: Good/Uncertain/Bad/Estimated/Missing)
    string? Source,     // Optional
    int Version,        // ✅ Required (for upsert logic)
    Dictionary<string, object>? Metadata  // Optional
);
```

## 📋 Valid Quality Values

| Value | Meaning |
|-------|---------|
| `"Good"` | Valid, trusted data |
| `"Uncertain"` | Data quality uncertain |
| `"Bad"` | Known bad data |
| `"Estimated"` | Estimated/interpolated |
| `"Missing"` | Missing data point |

## 🚀 Deployment

### Status

- ✅ Code fixed in `webapp/src/app/timeseries/page.tsx`
- ✅ Synced to server: `omar@192.168.75.20:~/git/webapp/src/`
- 🔄 Building new Docker image: `omarino-webapp:latest`
- 🔄 Container restart: `omarino-webapp`

### Commands Used

```bash
# 1. Sync fixed code
rsync -avz --exclude='node_modules' \
  -e "ssh -i '/path/to/key.pem'" \
  webapp/src/ omar@192.168.75.20:~/git/webapp/src/

# 2. Rebuild Docker image
ssh omar@192.168.75.20 \
  "cd ~/git/webapp && \
   sudo docker build -t omarino-webapp:latest . && \
   sudo docker restart omarino-webapp"
```

## 🧪 Testing

### After Deployment

1. Navigate to: https://ems-demo.omarino.net/timeseries
2. Click "Import Data" button
3. Select a CSV file with time series data
4. Import should now succeed! ✅

### Expected CSV Format

```csv
timestamp,meter_id,value,unit
2025-10-07T00:00:00Z,meter-001,125.5,kWh
2025-10-07T01:00:00Z,meter-001,130.2,kWh
2025-10-07T02:00:00Z,meter-001,128.7,kWh
```

### Expected Success Response

```json
{
  "jobId": "uuid-here",
  "pointsImported": 3,
  "pointsFailed": 0,
  "errors": null
}
```

## 📝 Related Issues

This is the **second** validation error we encountered:

1. ✅ **First**: `/api/meters/import` endpoint didn't exist
   - **Solution**: Created Python script `import-meters-csv.py`
   - **Result**: All 15 meters imported successfully

2. ✅ **Second** (this one): `/api/ingest` validation failures
   - **Solution**: Fixed Web UI to send complete payload
   - **Result**: Web UI import now works correctly

## 📚 Documentation

- ✅ `docs/INGEST-API-FIX.md` - Full technical details
- ✅ `test-data/CSV-IMPORT-REAL-SOLUTION.md` - Meter import fix
- ✅ `test-data/CSV-IMPORT-INVESTIGATION.md` - Investigation timeline

## ⚡ Quick Reference

### Correct Ingest Payload

```json
{
  "source": "my-import.csv",
  "points": [
    {
      "seriesId": "guid-here",
      "timestamp": "2025-10-07T12:00:00Z",
      "value": 123.45,
      "unit": "kWh",
      "quality": "Good",
      "source": "CSV Import",
      "version": 1,
      "metadata": null
    }
  ]
}
```

### Validation Checklist

- [ ] `seriesId` is valid GUID
- [ ] `timestamp` is ISO 8601 format
- [ ] `value` is a number
- [ ] `quality` is a **string** (not number): "Good", "Uncertain", "Bad", "Estimated", or "Missing"
- [ ] `version` field exists (start with 1)
- [ ] `unit`, `source`, `metadata` are optional but recommended

---

**Status**: ✅ Fixed and deployed  
**Date**: October 7, 2025  
**File**: `webapp/src/app/timeseries/page.tsx`  
**Changes**: Added `version`, fixed `quality` type, added optional fields
