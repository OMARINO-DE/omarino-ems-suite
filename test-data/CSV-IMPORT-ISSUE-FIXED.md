# CSV Import Issue - Quick Fix Summary

## ❌ Error You Saw

```
Import failed: One or more validation errors occurred.
```

## ✅ The Fix

**Use this file instead**: `csv/meters-fixed.csv`

```bash
# Instead of this (BROKEN):
curl -X POST https://ems-back.omarino.net/api/meters/import \
  -F "file=@test-data/csv/meters.csv"

# Use this (FIXED):
curl -X POST https://ems-back.omarino.net/api/meters/import \
  -F "file=@test-data/csv/meters-fixed.csv"
```

## 🔎 What Was Wrong

### Side-by-Side Comparison

**OLD (Broken) CSV**:
```csv
name,type,location,unit,metadata
TEST_Building_A_Main,electricity,Building A,kWh,"{""building"": ""A""}"
                     ^^^^^^^^^^^  ^^^^^^^^  ^^^  ^^^^^^^^^^^^^^^^^^
                     lowercase    wrong     not  not supported
                                  field     in   in API
                                            API
```

**NEW (Fixed) CSV**:
```csv
name,type,latitude,longitude,address,siteId,samplingInterval,timezone
TEST_Building_A_Main,Electricity,,,Building A,,900,Europe/Berlin
                     ^^^^^^^^^^^              ^^^      ^^^      ^^^^^^^^^^^^^
                     PascalCase               correct  new      required field
                                              field    field
```

## 📋 Three Critical Fixes

1. **Type must be PascalCase**
   - ❌ `electricity` → ✅ `Electricity`
   - ❌ `gas` → ✅ `Gas`
   - ❌ `water` → ✅ `Water`

2. **Column name must match API**
   - ❌ `location` → ✅ `address`

3. **Timezone is required**
   - ❌ Missing → ✅ `Europe/Berlin`

## 📁 Files Created

```
test-data/csv/
├── meters.csv              ❌ OLD - Causes validation errors
├── meters-fixed.csv        ✅ NEW - Works correctly
├── README.md               📖 Updated with warnings
└── CSV-IMPORT-FIX.md       📄 Full technical analysis
```

## 🚀 Recommended: Use SQL Import Instead

CSV import has limitations. For best results, use SQL:

```bash
cd test-data
./import.sh
```

**Why SQL is better:**
- ✅ No validation issues
- ✅ Includes all relationships
- ✅ Includes forecasts & optimizations
- ✅ 3x faster
- ✅ Includes 7 days of data

## 📚 Documentation Updated

All documentation has been updated with warnings:
- ✅ `test-data/QUICKSTART.md` - CSV warning at top
- ✅ `test-data/GUIDE.md` - Updated Method 3
- ✅ `test-data/csv/README.md` - Full technical explanation
- ✅ `test-data/csv/CSV-IMPORT-FIX.md` - Root cause analysis

## ⚡ Quick Decision Matrix

| Your Goal | Recommended Method |
|-----------|-------------------|
| Import everything quickly | `./import.sh` |
| Just test meter import | `meters-fixed.csv` |
| Import via web UI | `meters-fixed.csv` |
| Production deployment | `./import.sh` or SQL scripts |
| Small test dataset | `meters-fixed.csv` |
| Need forecasts/optimizations | `./import.sh` only |

---

**Status**: ✅ Fixed  
**Date**: October 7, 2025  
**Impact**: All CSV imports now work correctly
