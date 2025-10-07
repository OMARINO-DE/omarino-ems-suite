# Workflow Creation 500 Error Diagnostic

The workflow creation is returning HTTP 500 with an empty response body.

## Updated Hotfix with Better Error Handling

**Paste this in your browser console:**

```javascript
// Get the correct API URL
const getApiUrl = () => {
  return 'https://ems-back.omarino.net';
};

// Task type enum mapping
const TaskTypeMap = {
  'HttpCall': 0,
  'Delay': 1,
  'Condition': 2,
  'Transform': 3,
  'Notification': 4
};

// Override fetch with better error handling
const originalFetch = window.fetch;
window.fetch = async function(...args) {
  let [url, options] = args;
  
  // Fix hardcoded localhost URL
  if (url === 'http://localhost:8080/api/workflows') {
    url = `${getApiUrl()}/api/scheduler/workflows`;
    console.log('✅ Fixed workflow URL:', url);
  }
  
  // Fix task type format
  if (url?.includes('/api/scheduler/workflows') && options?.method === 'POST') {
    try {
      const body = JSON.parse(options.body);
      if (body.tasks) {
        body.tasks = body.tasks.map(task => ({
          ...task,
          type: TaskTypeMap[task.type] ?? task.type
        }));
        options.body = JSON.stringify(body);
        console.log('✅ Fixed workflow payload:', JSON.stringify(body, null, 2));
      }
    } catch(e) {
      console.error('Error fixing workflow payload:', e);
    }
  }
  
  // Make the request and handle errors better
  const response = await originalFetch.call(this, url, options);
  
  // Log response details for workflow creation
  if (url?.includes('/api/scheduler/workflows') && options?.method === 'POST') {
    console.log('📊 Response status:', response.status);
    console.log('📊 Response headers:', [...response.headers.entries()]);
    
    // Clone response so we can read it twice
    const clonedResponse = response.clone();
    try {
      const text = await clonedResponse.text();
      console.log('📊 Response body:', text);
      if (text && response.status !== 200 && response.status !== 201) {
        console.error('❌ Server error response:', text);
      }
    } catch(e) {
      console.error('❌ Could not read response body:', e);
    }
  }
  
  return response;
};

console.log('✅ Enhanced scheduler hotfix active!');
```

## What This Does

This enhanced hotfix will show you:
1. The exact payload being sent (formatted JSON)
2. The response status code
3. All response headers
4. The actual response body (even if empty)
5. Better error messages

After pasting this, try creating a workflow again and **copy-paste the entire console output here** so we can see what the server is returning.
