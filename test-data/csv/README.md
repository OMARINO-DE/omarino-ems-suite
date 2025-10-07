# Test Data - Alternative Formats

This directory contains test data in alternative formats for manual import.

## Available Formats

### 1. SQL Scripts (Recommended)
- Located in parent directory
- Fastest and most reliable
- Includes all relationships and metadata
- Use `import.sh` or `import-all.sql`

### 2. CSV Files (This directory)
- Simple format for spreadsheet tools
- Can be imported via API or web UI
- Suitable for small datasets
- May require additional configuration

## CSV Files

### meters.csv
Basic meter information without UUID dependencies.

### timeseries-sample.csv
Sample time series data (1 day instead of 7 for smaller file size).

## Import Methods

### Via Web UI
1. Navigate to https://ems-demo.omarino.net
2. Go to Settings → Import Data
3. Select CSV file
4. Map columns if needed
5. Click Import

### Via API (curl)
```bash
# Import meters
curl -X POST https://ems-back.omarino.net/api/meters/import \
  -H "Content-Type: multipart/form-data" \
  -F "file=@csv/meters.csv"

# Import time series data
curl -X POST https://ems-back.omarino.net/api/timeseries/import \
  -H "Content-Type: multipart/form-data" \
  -F "file=@csv/timeseries-sample.csv"
```

### Via Python Script
```python
import requests

# Import meters
with open('csv/meters.csv', 'rb') as f:
    response = requests.post(
        'https://ems-back.omarino.net/api/meters/import',
        files={'file': f}
    )
    print(response.json())

# Import time series
with open('csv/timeseries-sample.csv', 'rb') as f:
    response = requests.post(
        'https://ems-back.omarino.net/api/timeseries/import',
        files={'file': f}
    )
    print(response.json())
```

## ⚠️ IMPORTANT: CSV Format Issue Resolved

### Problem
The original `meters.csv` file had a format mismatch causing validation errors:
- **Error**: "One or more validation errors occurred"
- **Cause**: CSV columns didn't match API validation requirements

### Root Cause Analysis
The C# backend expects `CreateMeterRequest` with these fields:
- `name` (required string)
- `type` (required enum: Electricity, Gas, Water, Heat, Virtual - **PascalCase**)
- `timezone` (required string - IANA format like "Europe/Berlin")
- `latitude`, `longitude`, `address`, `siteId`, `samplingInterval`, `tags` (all optional)

The old CSV had:
- ❌ `location` instead of `address`
- ❌ `unit` column (not in meter model)
- ❌ `metadata` JSON (not supported in CSV import)
- ❌ lowercase type values (`electricity` instead of `Electricity`)
- ❌ Missing required `timezone` field

### Solution
**Use `meters-fixed.csv` instead!** ✅

## CSV Format Specifications

### ✅ meters-fixed.csv (CORRECT FORMAT)
```csv
name,type,latitude,longitude,address,siteId,samplingInterval,timezone
TEST_Building_A_Main,Electricity,,,Building A,,900,Europe/Berlin
TEST_Solar_Array_1,Electricity,,,Roof - Building A,,300,Europe/Berlin
TEST_Gas_Meter_A,Gas,,,Building A - Gas Line,,900,Europe/Berlin
TEST_Water_Meter_A,Water,,,Building A - Water Main,,900,Europe/Berlin
```

**Required Fields:**
- `name`: Meter name
- `type`: **Must be PascalCase**: `Electricity`, `Gas`, `Water`, `Heat`, or `Virtual`
- `timezone`: IANA timezone (e.g., `Europe/Berlin`, `UTC`, `America/New_York`)

**Optional Fields (use empty value for null):**
- `latitude`: Decimal degrees
- `longitude`: Decimal degrees
- `address`: Physical location string
- `siteId`: GUID (if you have one)
- `samplingInterval`: Integer seconds (900 = 15 minutes)

### ❌ meters.csv (DEPRECATED - DO NOT USE)
This file will fail validation. Use `meters-fixed.csv` instead.

### timeseries-sample.csv
```csv
meter_name,series_name,timestamp,value,quality
TEST_Building_A_Main,TEST_Building_A_Main_consumption,2025-10-07 00:00:00,45.2,good
```

## Notes

- **Type values MUST be PascalCase**: `Electricity` not `electricity`
- **Timezone is REQUIRED**: Use IANA format like `Europe/Berlin`
- CSV imports are slower than SQL for large datasets
- Relationships between tables must be handled manually
- UUIDs are generated automatically on import
- Empty values in CSV are treated as NULL
- Timestamps must be in ISO 8601 format

## Recommendations

**For full test data import**: Use SQL scripts (`import.sh`)
**For quick testing**: Use CSV files
**For production**: Use API endpoints with proper authentication
