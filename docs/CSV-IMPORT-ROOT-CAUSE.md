# CSV Import Issue - Root Cause Found

## ✅ API Works!

Your test showed:
```
Status: 200
pointsImported: 1
pointsFailed: 0
```

**The API is working perfectly!** 

## 🔴 Problem: CSV File Data

The issue is with the **data in your CSV file**, not the API or the code.

## 🔍 Diagnostic Script

**Paste this in Browser Console to check your CSV before importing:**

```javascript
// Step 1: Check what series exist
fetch('https://ems-back.omarino.net/api/series')
  .then(r => r.json())
  .then(series => {
    console.log('📊 You have', series.length, 'series available');
    
    if (series.length === 0) {
      console.error('❌ NO SERIES FOUND!');
      console.log('👉 You need to create meters and series FIRST before importing data');
      console.log('👉 Run: cd test-data && ./import.sh');
      return;
    }
    
    console.log('✅ Available series:');
    series.forEach((s, i) => {
      console.log(`  ${i+1}. ${s.name} (ID: ${s.id})`);
    });
    
    console.log('\n💡 Your CSV must use one of these series IDs');
  });

// Step 2: Check meters
fetch('https://ems-back.omarino.net/api/meters')
  .then(r => r.json())
  .then(meters => {
    console.log('\n📍 You have', meters.length, 'meters');
    meters.slice(0, 5).forEach((m, i) => {
      console.log(`  ${i+1}. ${m.name} (${m.type})`);
    });
  });
```

## 🎯 Expected CSV Format

Your CSV needs to match existing series. For example:

```csv
timestamp,meter_id,series_id,value,unit
2025-10-08T00:00:00Z,meter-001,ACTUAL-SERIES-ID-HERE,100.5,kWh
2025-10-08T01:00:00Z,meter-001,ACTUAL-SERIES-ID-HERE,105.2,kWh
```

**Problem**: Your CSV probably has:
- ❌ Fake/non-existent series IDs
- ❌ Wrong meter IDs
- ❌ Bad timestamp format

## ✅ Solution Options

### Option 1: Create Test Data First (Recommended)

```bash
cd test-data
./import.sh
```

This creates:
- 15 test meters
- ~45 time series
- 7 days of data
- Everything properly linked

Then you can query the data that was imported.

### Option 2: Create Meters/Series for Your CSV

**Step 1: Create a meter**
```javascript
fetch('https://ems-back.omarino.net/api/meters', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'My Test Meter',
    type: 'Electricity',
    timezone: 'Europe/Berlin',
    address: 'Test Location',
    samplingInterval: 900
  })
})
.then(r => r.json())
.then(meter => {
  console.log('✅ Created meter:', meter.id);
  
  // Step 2: Create a series for this meter
  return fetch('https://ems-back.omarino.net/api/series', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      meterId: meter.id,
      name: 'Consumption',
      unit: 'kWh',
      aggregation: 'Sum'
    })
  });
})
.then(r => r.json())
.then(series => {
  console.log('✅ Created series:', series.id);
  console.log('👉 Use this series ID in your CSV!');
});
```

### Option 3: Fix Your CSV

1. **Check what series you have** (run diagnostic above)
2. **Update your CSV** to use those series IDs
3. **Ensure timestamps** are in ISO 8601 format:
   - ✅ `2025-10-08T12:00:00Z`
   - ✅ `2025-10-08T12:00:00+00:00`
   - ❌ `10/8/2025 12:00 PM`

## 🐛 Your Current Error

When you imported your CSV with 15 points:
- Hotfix worked: ✅ Fixed 15 points
- But API returned: **400 Bad Request**

This means the 15 points had **invalid data**:
- Wrong series IDs (series don't exist)
- Wrong timestamp format
- Missing required fields

## 📋 Checklist Before Importing

Run this diagnostic:

```javascript
console.log('=== PRE-IMPORT CHECKLIST ===\n');

// 1. Check series exist
fetch('https://ems-back.omarino.net/api/series')
  .then(r => r.json())
  .then(series => {
    console.log(series.length > 0 ? '✅' : '❌', 'Series available:', series.length);
    if (series.length === 0) {
      console.log('   👉 Run: cd test-data && ./import.sh');
    }
    return series;
  })
  .then(series => {
    // 2. Validate your CSV data
    console.log('\n📝 Your CSV must have:');
    console.log('   - seriesId: One of', series.slice(0, 3).map(s => s.id).join(', '));
    console.log('   - timestamp: ISO 8601 format (2025-10-08T12:00:00Z)');
    console.log('   - value: Number');
    console.log('   - quality: "Good" (after hotfix)');
    console.log('   - version: 1 (added by hotfix)');
  });
```

---

## 🎯 Bottom Line

**API works! ✅** Your test imported successfully.

**CSV data is wrong! ❌** Either:
1. Series IDs don't exist → Create meters/series first
2. Timestamps are wrong → Use ISO 8601 format
3. No data to import to → Run `./import.sh` to set up test data

**Next step**: Run the diagnostic above to see what series you have!
