# Check Response Body

The hotfix is running (✅ Fixed 15 points) but still getting 400.

**Paste this in Browser Console to see the EXACT error:**

```javascript
// Get the last failed request details
fetch('https://ems-back.omarino.net/api/series')
  .then(r => r.json())
  .then(series => {
    console.log('Testing with series:', series[0]);
    
    // Send a test request with the FIXED format
    return fetch('https://ems-back.omarino.net/api/ingest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source: 'Test',
        points: [{
          seriesId: series[0].id,
          timestamp: '2025-10-08T00:00:00Z',
          value: 100.5,
          unit: 'kWh',
          quality: 'Good',
          source: 'Test',
          version: 1,
          metadata: null
        }]
      })
    });
  })
  .then(async response => {
    console.log('Status:', response.status);
    const text = await response.text();
    console.log('Raw response:', text);
    
    try {
      const json = JSON.parse(text);
      console.log('Parsed error:', JSON.stringify(json, null, 2));
      
      if (json.errors) {
        console.error('❌ VALIDATION ERRORS:');
        for (const [field, messages] of Object.entries(json.errors)) {
          console.error(`  Field: ${field}`);
          messages.forEach(msg => console.error(`    - ${msg}`));
        }
      }
    } catch(e) {
      console.log('Could not parse as JSON');
    }
  })
  .catch(err => console.error('Error:', err));
```

**This will show us EXACTLY which field is failing validation.**

## What to Look For

The response should show something like:

```json
{
  "errors": {
    "$.points[0].seriesId": ["The series does not exist"],
    "$.points[0].timestamp": ["Invalid timestamp format"],
    etc...
  }
}
```

**Run that code and copy-paste the output here!**
