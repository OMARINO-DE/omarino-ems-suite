# ✅ CSV Import Issue - REAL SOLUTION

## 🔴 The Problem

You were getting:
```
Import failed: One or more validation errors occurred.
```

## 🔍 Root Cause Discovery

**The `/api/meters/import` endpoint DOES NOT EXIST!**

The backend only has these endpoints:
- ✅ `POST /api/meters` - Create meter with JSON body
- ✅ `GET /api/meters` - List all meters
- ✅ `GET /api/meters/{id}` - Get one meter
- ✅ `PUT /api/meters/{id}` - Update meter
- ✅ `DELETE /api/meters/{id}` - Delete meter

❌ **Missing**: `POST /api/meters/import` for CSV file upload

The documentation mentioned CSV import, but the C# backend controller never implemented it!

## ✅ The Real Solution

**Use the Python script that reads CSV and posts via JSON API:**

```bash
cd test-data
python3 import-meters-csv.py
```

**Result**: ✅ All 15 meters imported successfully!

```
✅ Imported: TEST_Building_A_Main (ID: 9d511082-e0ed-49f8-8c08-46a244c2ffb1)
✅ Imported: TEST_Building_A_HVAC (ID: 7f43e150-06a9-4b2e-9a3b-e2f2ac0f6eaf)
✅ Imported: TEST_Building_A_Lighting (ID: 07e3f51e-a984-491d-8453-8f7f6cd10cf4)
✅ Imported: TEST_Building_B_Main (ID: 183a1501-3c52-46b0-a7eb-d5e8b90af625)
✅ Imported: TEST_Building_B_HVAC (ID: 7c773012-f118-4f64-9da5-bc798f9f2532)
✅ Imported: TEST_Solar_Array_1 (ID: e6894a7a-84a2-488f-97d1-b5177dc38905)
✅ Imported: TEST_Solar_Array_2 (ID: 14f9e4fb-7b34-4e83-9dc5-4f2f956e55de)
✅ Imported: TEST_Battery_Storage (ID: 1dc1959f-98ab-4979-bb20-42e19aefd851)
✅ Imported: TEST_Gas_Meter_A (ID: 1ba42440-354e-44e5-b7eb-32098ea4276d)
✅ Imported: TEST_Gas_Meter_B (ID: 8b6eff58-a48a-42c6-9608-79c8bb6615ce)
✅ Imported: TEST_Water_Meter_A (ID: 2127baa1-a7d7-4d2c-bd35-b15e59ee0077)
✅ Imported: TEST_Water_Meter_B (ID: c52c76ac-ab52-45f9-a97e-bb408e9918fa)
✅ Imported: TEST_Temp_Outdoor (ID: 49ba3b64-44d5-49b9-9458-040d0c96ebe1)
✅ Imported: TEST_Temp_Building_A (ID: 293b1770-4c97-4c25-ade2-0bd76279680d)
✅ Imported: TEST_Temp_Building_B (ID: e05794f3-9b00-4bae-814a-786554cd0cb4)
```

## 📁 Files

### ✅ `import-meters-csv.py` (THE SOLUTION)

New Python script that:
1. Reads `csv/meters-fixed.csv`
2. Converts each row to JSON
3. Posts to the **actual working** `POST /api/meters` endpoint
4. Shows progress with colored output
5. Provides detailed error messages

### ❌ CSV Direct Upload (Doesn't Work)

This does NOT work because the endpoint doesn't exist:
```bash
# This FAILS - endpoint not implemented
curl -X POST https://ems-back.omarino.net/api/meters/import \
  -F "file=@csv/meters-fixed.csv"
```

### ✅ Python Script (Works)

This WORKS - uses actual JSON API:
```bash
# This SUCCEEDS
cd test-data
python3 import-meters-csv.py
```

## 🔧 How It Works

The script reads CSV and makes individual API calls:

```python
# For each row in CSV:
payload = {
    "name": "TEST_Building_A_Main",
    "type": "Electricity",  # PascalCase from fixed CSV
    "timezone": "Europe/Berlin",
    "address": "Building A",
    "samplingInterval": 900
}

response = requests.post(
    "https://ems-back.omarino.net/api/meters",
    json=payload
)
```

## 📊 Verification

```bash
# Check imported meters
curl -s https://ems-back.omarino.net/api/meters | \
  python3 -c "import json, sys; \
    meters = json.load(sys.stdin); \
    test = [m for m in meters if m['name'].startswith('TEST_')]; \
    print(f'{len(test)} TEST_ meters found')"
```

Result: **16 TEST_ meters found** ✅ (15 from CSV + 1 from earlier test)

## 🎯 Complete Import Process

### Method 1: Python Script (CSV to JSON API)
```bash
cd test-data
python3 import-meters-csv.py
```

### Method 2: SQL Import (Complete with Data)
```bash
cd test-data
./import.sh
```

### Method 3: Manual JSON API
```bash
curl -X POST https://ems-back.omarino.net/api/meters \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Meter",
    "type": "Electricity",
    "timezone": "Europe/Berlin",
    "address": "Building A"
  }'
```

## 🔮 Future: Implement CSV Upload Endpoint

To make CSV upload work directly, the backend needs this implementation:

```csharp
// Add to MetersController.cs

[HttpPost("import")]
[ProducesResponseType(StatusCodes.Status200OK)]
[ProducesResponseType(StatusCodes.Status400BadRequest)]
public async Task<ActionResult> ImportMeters(
    [FromForm] IFormFile file,
    CancellationToken cancellationToken)
{
    // Read CSV file
    // Parse rows
    // Create meters
    // Return summary
}
```

**Until then**: Use `import-meters-csv.py` ✅

## 📋 Summary

| Method | Status | Notes |
|--------|--------|-------|
| `POST /api/meters/import` with CSV | ❌ | Endpoint doesn't exist |
| `import-meters-csv.py` | ✅ | **USE THIS** - Works perfectly |
| `./import.sh` (SQL) | ✅ | Best for complete data |
| `POST /api/meters` with JSON | ✅ | Direct API, one at a time |

---

**Date**: October 7, 2025  
**Status**: ✅ SOLVED - Use Python script  
**Imported**: 15 meters successfully  
**Script**: `test-data/import-meters-csv.py`
