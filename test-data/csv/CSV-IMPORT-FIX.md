# CSV Import Validation Error - Root Cause Analysis & Fix

## 🔴 Error Message
```
Import failed: One or more validation errors occurred.
```

## 🔍 Root Cause

The CSV file format did not match the backend API validation requirements.

### API Validation Requirements (C# Backend)

The backend expects `CreateMeterRequest` with these **exact** specifications:

```csharp
public record CreateMeterRequest(
    [Required] string Name,
    [Required] MeterType Type,  // Enum: Electricity, Gas, Water, Heat, Virtual
    double? Latitude,
    double? Longitude,
    string? Address,
    Guid? SiteId,
    int? SamplingInterval,
    [Required] string Timezone,  // IANA timezone format
    Dictionary<string, string>? Tags
);

public enum MeterType {
    Electricity,  // PascalCase required!
    Gas,
    Water,
    Heat,
    Virtual
}
```

### What Was Wrong in Original CSV

**File**: `test-data/csv/meters.csv` ❌

```csv
name,type,location,unit,metadata
TEST_Building_A_Main,electricity,Building A,kWh,"{""building"": ""A""}"
```

**Problems**:
1. ❌ **Type in lowercase**: `electricity` instead of `Electricity`
   - C# enum requires PascalCase
   - Validation fails on case mismatch

2. ❌ **Wrong column name**: `location` instead of `address`
   - Model expects `Address` property
   - CSV header must match property name (case-insensitive, but name must match)

3. ❌ **Extra columns**: `unit` and `metadata`
   - These fields don't exist in `CreateMeterRequest`
   - May be ignored or cause validation errors

4. ❌ **Missing required field**: `timezone`
   - Backend requires IANA timezone (e.g., "Europe/Berlin")
   - Validation fails when required field is missing

## ✅ Solution

### Fixed CSV Format

**File**: `test-data/csv/meters-fixed.csv` ✅

```csv
name,type,latitude,longitude,address,siteId,samplingInterval,timezone
TEST_Building_A_Main,Electricity,,,Building A,,900,Europe/Berlin
TEST_Solar_Array_1,Electricity,,,Roof - Building A,,300,Europe/Berlin
TEST_Gas_Meter_A,Gas,,,Building A - Gas Line,,900,Europe/Berlin
TEST_Water_Meter_A,Water,,,Building A - Water Main,,900,Europe/Berlin
```

**Key Changes**:
1. ✅ **Type in PascalCase**: `Electricity`, `Gas`, `Water`, `Heat`
2. ✅ **Correct column**: `address` instead of `location`
3. ✅ **Required field added**: `timezone` with IANA format
4. ✅ **Removed unsupported columns**: `unit` and `metadata`
5. ✅ **Empty values for nulls**: Comma with no value = NULL

## 📋 Field Requirements

### Required Fields
- **name**: Meter name (string)
- **type**: Must be exact enum value (PascalCase):
  - `Electricity`
  - `Gas`
  - `Water`
  - `Heat`
  - `Virtual`
- **timezone**: IANA timezone string
  - Examples: `Europe/Berlin`, `UTC`, `America/New_York`
  - Full list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

### Optional Fields (use empty value for NULL)
- **latitude**: Decimal degrees (e.g., `52.5200`)
- **longitude**: Decimal degrees (e.g., `13.4050`)
- **address**: Free-text location string
- **siteId**: GUID if you have site grouping
- **samplingInterval**: Integer seconds (900 = 15 minutes, 3600 = 1 hour)
- **tags**: Not supported in CSV import (use JSON API instead)

## 🧪 Testing

### Test Import with Fixed CSV

```bash
# Test locally
curl -X POST http://localhost:8081/api/meters/import \
  -F "file=@test-data/csv/meters-fixed.csv"

# Test on server
curl -X POST https://ems-back.omarino.net/api/meters/import \
  -F "file=@test-data/csv/meters-fixed.csv"
```

### Expected Success Response

```json
{
  "imported": 15,
  "failed": 0,
  "errors": []
}
```

### Verify Import

```bash
# Check meters in database
sudo docker exec omarino-postgres psql -U omarino -d omarino -c \
  "SELECT name, type, timezone FROM meters WHERE name LIKE 'TEST_%';"
```

Expected output:
```
         name          |    type     |   timezone
-----------------------+-------------+--------------
 TEST_Building_A_Main  | Electricity | Europe/Berlin
 TEST_Solar_Array_1    | Electricity | Europe/Berlin
 TEST_Gas_Meter_A      | Gas         | Europe/Berlin
 TEST_Water_Meter_A    | Water       | Europe/Berlin
 ...
```

## 🔧 Troubleshooting

### Still Getting Validation Errors?

1. **Check type values are PascalCase**
   ```bash
   # This will FAIL
   type: electricity
   
   # This will SUCCEED
   type: Electricity
   ```

2. **Verify timezone is valid IANA format**
   ```bash
   # Valid
   Europe/Berlin, America/New_York, UTC, Asia/Tokyo
   
   # Invalid
   CET, EST, PST, GMT+1
   ```

3. **Ensure CSV has correct headers**
   ```bash
   name,type,latitude,longitude,address,siteId,samplingInterval,timezone
   ```

4. **Check for extra commas or quotes**
   - Empty fields: `,,` (correct)
   - Not: `,null,` or `,"",`

### Check Backend Logs

```bash
# View API logs for detailed validation errors
sudo docker logs omarino-timeseries --tail 50

# Look for:
# - "Invalid timezone: ..."
# - "The value 'electricity' is not valid for MeterType"
# - "The field 'Timezone' is required"
```

## 📚 Alternative: Use SQL Import Instead

If CSV import continues to have issues, use SQL import which is more reliable:

```bash
cd test-data
./import.sh
```

SQL import:
- ✅ No validation issues (direct database insert)
- ✅ Includes all relationships
- ✅ Faster for large datasets
- ✅ Includes forecasts and optimizations

## 📝 Summary

| Aspect | Old CSV ❌ | Fixed CSV ✅ |
|--------|-----------|-------------|
| Type format | `electricity` | `Electricity` |
| Location field | `location` | `address` |
| Timezone | Missing | `Europe/Berlin` |
| Extra columns | `unit`, `metadata` | Removed |
| Validation | Fails | Passes |

**Bottom line**: Always use `meters-fixed.csv` for CSV imports, or better yet, use the SQL import scripts!

---

**Updated**: October 7, 2025  
**Status**: ✅ Issue resolved with meters-fixed.csv
