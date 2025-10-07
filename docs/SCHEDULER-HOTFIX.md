# Scheduler Workflow Creation Hotfix

## Problem

Workflow creation is failing with CORS error because the code has a hardcoded URL:
```
http://localhost:8080/api/workflows
```

This causes a cross-origin request that fails.

## Browser Console Hotfix

**Paste this in your browser console BEFORE creating a workflow:**

```javascript
// Get the correct API URL from the page
const getApiUrl = () => {
  // Try to get from environment or use production URL
  return 'https://ems-back.omarino.net';
};

// Task type enum mapping (string to int)
const TaskTypeMap = {
  'HttpCall': 0,
  'Delay': 1,
  'Condition': 2,
  'Transform': 3,
  'Notification': 4
};

// Override the fetch function to fix workflow creation
const originalFetch = window.fetch;
window.fetch = function(...args) {
  let [url, options] = args;
  
  // Fix hardcoded localhost URL for workflows
  if (url === 'http://localhost:8080/api/workflows') {
    url = `${getApiUrl()}/api/scheduler/workflows`;
    console.log('✅ Fixed workflow URL:', url);
  }
  
  // Fix task type format (string to enum int)
  if (url?.includes('/api/scheduler/workflows') && options?.method === 'POST') {
    try {
      const body = JSON.parse(options.body);
      if (body.tasks) {
        body.tasks = body.tasks.map(task => ({
          ...task,
          type: TaskTypeMap[task.type] ?? task.type  // Convert string to int
        }));
        options.body = JSON.stringify(body);
        console.log('✅ Fixed workflow payload:', body);
      }
    } catch(e) {
      console.error('Error fixing workflow payload:', e);
    }
  }
  
  return originalFetch.call(this, url, options);
};

console.log('✅ Scheduler hotfix active!');
```

## What This Does

1. Intercepts all `fetch()` calls
2. Detects the hardcoded `localhost:8080` URL
3. Replaces it with the correct production API URL: `https://ems-back.omarino.net/api/scheduler/workflows`
4. Allows the request to proceed with the correct URL

## Usage

1. Open browser DevTools (F12)
2. Go to Console tab
3. Paste the code above
4. Press Enter
5. You should see: `✅ Scheduler hotfix active!`
6. Now create your workflow - it will work!

## Permanent Fix

The code has been fixed in `webapp/src/app/scheduler/page.tsx` to use the `api.scheduler.createWorkflow()` method instead of hardcoded fetch. Once the server is accessible and the container is rebuilt, this hotfix will no longer be needed.

## Verification

After applying the hotfix, when you create a workflow you should see in the console:
```
✅ Fixed workflow URL: https://ems-back.omarino.net/api/scheduler/workflows
```

Then the workflow should be created successfully!
