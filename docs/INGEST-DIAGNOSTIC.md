# Time Series Import Error - Diagnostic Guide

## 🔴 Current Situation

**Error**: `Import failed: One or more validation errors occurred.`  
**Endpoint**: `POST https://ems-back.omarino.net/api/ingest`  
**Status**: `400 Bad Request`

## 🔍 Diagnostic Steps

### Step 1: Capture Exact Error Details

1. **Open Browser DevTools** (F12)
2. **Go to Network tab**
3. **Try the import again**
4. **Find the failed request** (shows red, 400 status)
5. **Click on it**
6. **Check these tabs**:

#### A. Request Payload
Look for the JSON body being sent. Check:
- Is `quality` a string (`"Good"`) or number (`100`)?
- Does `version` field exist?
- Are all required fields present?

#### B. Response
Look at the error message. Common responses:

**If quality is wrong**:
```json
{
  "type": "https://tools.ietf.org/html/rfc7231#section-6.5.1",
  "title": "One or more validation errors occurred.",
  "status": 400,
  "errors": {
    "$.points[0].quality": [
      "The JSON value could not be converted to OmarinoEMS.TimeSeriesService.Models.DataQuality"
    ]
  }
}
```

**If version is missing**:
```json
{
  "type": "https://tools.ietf.org/html/rfc7231#section-6.5.1",
  "title": "One or more validation errors occurred.",
  "status": 400,
  "errors": {
    "$.points[0].version": [
      "The version field is required."
    ]
  }
}
```

#### C. Headers
Check the response headers for any additional clues.

### Step 2: Test with Known Good Data

Open Browser Console (F12 → Console) and run this test:

```javascript
// Test 1: Check if you have any series
fetch('https://ems-back.omarino.net/api/series')
  .then(r => r.json())
  .then(series => {
    console.log('✅ Available series:', series.length);
    console.log('First series ID:', series[0]?.id);
    
    if (series.length > 0) {
      // Test 2: Try importing ONE point with CORRECT format
      const testPoint = {
        source: 'Diagnostic Test',
        points: [{
          seriesId: series[0].id,  // Use first series
          timestamp: new Date().toISOString(),
          value: 123.45,
          unit: 'kWh',
          quality: 'Good',  // STRING not number!
          source: 'Test',
          version: 1,  // REQUIRED
          metadata: null
        }]
      };
      
      console.log('📤 Testing with payload:', JSON.stringify(testPoint, null, 2));
      
      return fetch('https://ems-back.omarino.net/api/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(testPoint)
      });
    }
  })
  .then(r => {
    console.log('📥 Response status:', r.status);
    return r.json();
  })
  .then(result => {
    if (result.errors) {
      console.error('❌ Validation errors:', result.errors);
      console.log('💡 Fix needed:', JSON.stringify(result.errors, null, 2));
    } else {
      console.log('✅ SUCCESS! Imported:', result.pointsImported, 'points');
    }
  })
  .catch(err => console.error('❌ Error:', err));
```

### Step 3: Compare Payload Formats

#### ❌ WRONG Format (Current Bug)
```json
{
  "source": "file.csv",
  "points": [{
    "seriesId": "guid-here",
    "timestamp": "2025-10-08T12:00:00Z",
    "value": 100,
    "quality": 100  // ❌ NUMBER - WRONG!
    // ❌ version MISSING
  }]
}
```

#### ✅ CORRECT Format (What API Expects)
```json
{
  "source": "file.csv",
  "points": [{
    "seriesId": "guid-here",
    "timestamp": "2025-10-08T12:00:00Z",
    "value": 100,
    "unit": "kWh",
    "quality": "Good",  // ✅ STRING
    "source": "file.csv",
    "version": 1,  // ✅ REQUIRED
    "metadata": null
  }]
}
```

## 🔧 Fixes Available

### Fix 1: Browser Console Hotfix (Immediate)

Use this RIGHT NOW before importing:

```javascript
// Copy-paste into Console before importing
const originalFetch = window.fetch;
window.fetch = function(...args) {
  const [url, options] = args;
  if (url?.includes('/api/ingest') && options?.method === 'POST') {
    try {
      const body = JSON.parse(options.body);
      if (body.points) {
        body.points = body.points.map(p => ({
          ...p,
          quality: typeof p.quality === 'number' ? 'Good' : p.quality,
          version: p.version || 1,
          unit: p.unit || null,
          source: p.source || body.source,
          metadata: p.metadata || null
        }));
        options.body = JSON.stringify(body);
        console.log('🔧 Fixed payload');
      }
    } catch(e) {}
  }
  return originalFetch.apply(this, args);
};
console.log('✅ Hotfix active - try import now');
```

### Fix 2: Wait for Deployment

The permanent fix is in the code but waiting for server restart.

### Fix 3: Use SQL Import Instead

```bash
cd test-data
./import.sh
```

## 📊 Checklist for Successful Import

- [ ] Series exists in database (check with `/api/series`)
- [ ] Meter exists for series (check with `/api/meters`)
- [ ] CSV has valid timestamps (ISO 8601 format)
- [ ] Values are numbers (not strings)
- [ ] Payload includes ALL required fields:
  - [ ] `seriesId` (GUID)
  - [ ] `timestamp` (string)
  - [ ] `value` (number)
  - [ ] `quality` (string: "Good", "Uncertain", "Bad", "Estimated", "Missing")
  - [ ] `version` (number: start with 1)
- [ ] Optional fields are properly formatted:
  - [ ] `unit` (string or null)
  - [ ] `source` (string or null)
  - [ ] `metadata` (object or null)

## 🆘 If Still Failing

### Get Detailed Error

```javascript
fetch('https://ems-back.omarino.net/api/ingest', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    source: 'test',
    points: [{
      seriesId: 'YOUR-SERIES-ID',
      timestamp: '2025-10-08T12:00:00Z',
      value: 100,
      unit: 'kWh',
      quality: 'Good',
      source: 'test',
      version: 1,
      metadata: null
    }]
  })
})
.then(async r => {
  const text = await r.text();
  console.log('Status:', r.status);
  console.log('Response:', text);
  try {
    const json = JSON.parse(text);
    console.log('Parsed:', JSON.stringify(json, null, 2));
  } catch(e) {
    console.log('Could not parse as JSON');
  }
})
.catch(err => console.error('Error:', err));
```

### Check API Endpoint

```bash
# Test if API is responding
curl -I https://ems-back.omarino.net/api/series

# Test ingest with correct payload
curl -X POST https://ems-back.omarino.net/api/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source": "test",
    "points": [{
      "seriesId": "YOUR-SERIES-ID-HERE",
      "timestamp": "2025-10-08T12:00:00Z",
      "value": 100.0,
      "unit": "kWh",
      "quality": "Good",
      "source": "test",
      "version": 1,
      "metadata": null
    }]
  }'
```

## 📋 Report Template

If issue persists, provide:

```
1. Exact error from Response tab:
   [paste JSON error here]

2. Request payload sent:
   [paste JSON payload here]

3. Series ID used:
   [paste GUID here]

4. Browser console errors:
   [paste any console errors]

5. Did browser hotfix work?
   [yes/no]
```

---

**Use the diagnostic test script above to get exact error details!**
