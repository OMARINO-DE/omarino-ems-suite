# Time Series Import - Browser Console Hotfix

## 🔴 Problem
Still getting validation error when importing time series data, and server is unreachable to deploy fix.

## ✅ Temporary Solution: Browser Console Hotfix

### Option 1: Override Function in Browser Console

1. **Open the page**: https://ems-demo.omarino.net/timeseries
2. **Open Developer Console**: Press `F12` or `Cmd+Option+I` (Mac)
3. **Go to Console tab**
4. **Paste this code** to override the broken function:

```javascript
// Hotfix: Override the handleFileUpload function
(function() {
  console.log('🔧 Applying time series import hotfix...');
  
  // Store original fetch
  const originalFetch = window.fetch;
  
  // Intercept fetch calls to /api/ingest
  window.fetch = function(...args) {
    const [url, options] = args;
    
    // Check if this is an ingest API call
    if (url && url.includes('/api/ingest') && options && options.method === 'POST') {
      try {
        const body = JSON.parse(options.body);
        
        // Fix the points array
        if (body.points && Array.isArray(body.points)) {
          console.log('🔧 Fixing', body.points.length, 'data points...');
          
          body.points = body.points.map(point => ({
            seriesId: point.seriesId,
            timestamp: point.timestamp,
            value: point.value,
            unit: point.unit || null,
            quality: 'Good',  // ✅ Fix: String instead of number
            source: body.source || 'Web Import',
            version: 1,  // ✅ Fix: Add required version field
            metadata: null
          }));
          
          // Update the request body
          options.body = JSON.stringify(body);
          console.log('✅ Fixed payload:', body);
        }
      } catch (e) {
        console.warn('Could not fix payload:', e);
      }
    }
    
    // Call original fetch
    return originalFetch.apply(this, args);
  };
  
  console.log('✅ Hotfix applied! Try importing now.');
})();
```

5. **Press Enter**
6. **Try importing your CSV file again**

### Option 2: Manual API Call

If you have a CSV file ready, you can import directly via console:

```javascript
// 1. First, get your series IDs
fetch('https://ems-back.omarino.net/api/series')
  .then(r => r.json())
  .then(series => {
    console.log('Available series:', series);
    // Note the seriesId you want to use
  });

// 2. Then import data (replace SERIES_ID_HERE)
fetch('https://ems-back.omarino.net/api/ingest', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    source: 'Manual Import',
    points: [
      {
        seriesId: 'SERIES_ID_HERE',  // Replace with actual ID
        timestamp: '2025-10-08T00:00:00Z',
        value: 100.0,
        unit: 'kWh',
        quality: 'Good',  // String, not number!
        source: 'Manual',
        version: 1,
        metadata: null
      },
      {
        seriesId: 'SERIES_ID_HERE',  // Same series
        timestamp: '2025-10-08T01:00:00Z',
        value: 105.5,
        unit: 'kWh',
        quality: 'Good',
        source: 'Manual',
        version: 1,
        metadata: null
      }
    ]
  })
})
.then(r => r.json())
.then(result => console.log('✅ Import result:', result))
.catch(err => console.error('❌ Error:', err));
```

## 🔧 Permanent Fix Status

The permanent fix has been applied to the code but server deployment is pending:

### What Was Fixed

**File**: `webapp/src/app/timeseries/page.tsx`

```typescript
// FIXED CODE (deployed when server comes back)
allPoints.push({
  seriesId: seriesId,
  timestamp: row.timestamp,
  value: parseFloat(row.value),
  unit: row.unit || null,  // ✅ Added
  quality: 'Good',  // ✅ Fixed: was 100 (number)
  source: file.name,  // ✅ Added
  version: 1,  // ✅ Added: required field!
  metadata: null  // ✅ Added
})
```

### Deployment Checklist

Once server is back online:

```bash
# 1. Check if code was synced
ssh omar@server "ls -la ~/git/webapp/src/app/timeseries/page.tsx"

# 2. Rebuild container
ssh omar@server "cd ~/git/webapp && sudo docker build -t omarino-webapp:latest ."

# 3. Restart container
ssh omar@server "sudo docker restart omarino-webapp"

# 4. Verify restart
ssh omar@server "sudo docker logs omarino-webapp --tail 20"

# 5. Clear browser cache
# In browser: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
```

## 📋 Validation Checklist

Before importing, verify your data has:

- [ ] **seriesId**: Valid GUID from your series
- [ ] **timestamp**: ISO 8601 format (e.g., `2025-10-08T12:00:00Z`)
- [ ] **value**: Number (not string)
- [ ] **quality**: String enum - `"Good"`, `"Uncertain"`, `"Bad"`, `"Estimated"`, or `"Missing"` (NOT a number!)
- [ ] **version**: Integer (use `1` for new data)
- [ ] **unit**: String (optional) - e.g., `"kWh"`, `"°C"`
- [ ] **source**: String (optional) - e.g., `"CSV Import"`
- [ ] **metadata**: Object or null (optional)

## 🐛 Debugging

### Check Current Request Payload

1. Open DevTools (F12)
2. Go to **Network** tab
3. Try to import
4. Find the POST request to `/api/ingest`
5. Click on it
6. Go to **Payload** or **Request** tab
7. Look at the `points` array
8. Verify:
   - `quality` is a **string** like `"Good"` (not number `100`)
   - `version` field **exists** (not missing!)

### Example of CORRECT Payload

```json
{
  "source": "my-file.csv",
  "points": [
    {
      "seriesId": "123e4567-e89b-12d3-a456-426614174000",
      "timestamp": "2025-10-08T12:00:00Z",
      "value": 125.5,
      "unit": "kWh",
      "quality": "Good",  // ✅ STRING
      "source": "CSV Import",
      "version": 1,  // ✅ EXISTS
      "metadata": null
    }
  ]
}
```

### Example of WRONG Payload (Current Bug)

```json
{
  "source": "my-file.csv",
  "points": [
    {
      "seriesId": "123e4567-e89b-12d3-a456-426614174000",
      "timestamp": "2025-10-08T12:00:00Z",
      "value": 125.5,
      "quality": 100  // ❌ NUMBER (should be string)
      // ❌ version MISSING
      // ❌ unit MISSING
      // ❌ source MISSING
    }
  ]
}
```

## 💡 Alternative: Use SQL Import

While waiting for webapp fix, you can import via SQL:

```bash
cd test-data
./import.sh
```

This bypasses the webapp entirely and imports directly to database.

---

**Status**: 🔄 Permanent fix ready, awaiting server deployment  
**Workaround**: ✅ Browser console hotfix (use now)  
**Alternative**: ✅ SQL import (recommended for large datasets)

## 📞 Next Steps

1. **Try browser console hotfix** (above) immediately
2. **Wait for server to come back online**
3. **Verify webapp container was rebuilt** with fix
4. **Hard refresh browser** (Ctrl+Shift+R or Cmd+Shift+R)
5. **Test import again**

If still having issues after all this, the API itself might need investigation.
