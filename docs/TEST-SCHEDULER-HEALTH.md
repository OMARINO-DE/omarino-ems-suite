# Test Scheduler Service Health

**Paste this in your browser console to check if the scheduler service is working:**

```javascript
// Test 1: Check scheduler service health
fetch('https://ems-back.omarino.net/api/scheduler/health')
  .then(r => {
    console.log('Health check status:', r.status);
    return r.json();
  })
  .then(data => console.log('Health check response:', data))
  .catch(err => console.error('Health check failed:', err));

// Test 2: Try to get workflows list (should work even if empty)
fetch('https://ems-back.omarino.net/api/scheduler/workflows')
  .then(r => {
    console.log('Get workflows status:', r.status);
    return r.json();
  })
  .then(data => console.log('Existing workflows:', data))
  .catch(err => console.error('Get workflows failed:', err));
```

## Possible Issues

### 1. Scheduler Service Not Running
If you get network errors, the scheduler service might not be running.

### 2. Database Not Initialized  
If GET works but POST fails with 500, the database tables might not exist.

### 3. Configuration Issue
Check if the gateway is routing `/api/scheduler/*` to the scheduler service.

## Next Steps

1. Run both tests above
2. Share the console output
3. If health check fails: scheduler service is down
4. If GET works but POST fails: database/validation issue
