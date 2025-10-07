# Webapp UI Fixes Summary

**Date:** October 6, 2025  
**Issues Fixed:** White text visibility + CORS errors

## Problem 1: White Text on White Background

### Root Cause
The `webapp/src/app/globals.css` file had a dark mode media query that set white foreground text when the user's system was in dark mode, but the UI always used light backgrounds (white cards, light gray body).

### Solution
Removed the dark mode CSS that was causing the issue:

**Before:**
```css
@media (prefers-color-scheme: dark) {
  :root {
    --foreground-rgb: 255, 255, 255;  /* White text */
    --background-start-rgb: 0, 0, 0;
    --background-end-rgb: 0, 0, 0;
  }
}
```

**After:**
```css
:root {
  --foreground-rgb: 0, 0, 0;  /* Always black text */
  --background-start-rgb: 249, 250, 251;  /* Always light gray */
  --background-end-rgb: 249, 250, 251;
}
```

## Problem 2: CORS Errors - localhost:8080

### Root Cause
Next.js environment variables (`NEXT_PUBLIC_*`) are baked into the build at **build time**, not runtime. The webapp was built with the default value from `src/lib/api.ts`:
```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8081'
```

Since `NEXT_PUBLIC_API_URL` wasn't set during the build, it defaulted to `localhost:8081`, and the browser couldn't reach the API.

### Solution
Updated the Dockerfile to accept build arguments and rebuilt the image:

**Dockerfile Changes:**
```dockerfile
# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Accept build argument
ARG NEXT_PUBLIC_API_URL=http://localhost:8081

# Set environment variables for build
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# Build Next.js application
RUN npm run build
```

**Build Command:**
```bash
docker build --no-cache --platform linux/amd64 \
  --build-arg NEXT_PUBLIC_API_URL='http://192.168.75.20:8081' \
  -t omarino-webapp:latest .
```

## Verification

### CSS Fix Verification
Check the deployed CSS file contains the correct colors:
```bash
curl -s http://192.168.75.20:3000/_next/static/css/*.css | grep foreground-rgb
# Should show: --foreground-rgb:0,0,0 (black text)
```

### API URL Fix Verification
Check the JavaScript bundles contain the correct API URL:
```bash
sudo docker exec omarino-webapp grep -r '192.168.75.20:8081' /app/.next/
# Should find: baseURL:"http://192.168.75.20:8081"
```

## Deployment

1. **Image pushed to registry:**
   ```bash
   192.168.61.21:32768/omarino-ems/webapp:latest
   Digest: sha256:e38c8ef6cbe4997ccaec5d1a15b13a59b3bc87a5fce7d82869fb7304deabd446
   ```

2. **Container running on server:**
   ```bash
   Container ID: 599a11c090a0
   Port: 3000:3000
   Network: ems_omarino-network
   Status: Running
   ```

## User Action Required

After deployment, users must clear their browser cache to see the fixes:

1. **Hard Refresh:** Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
2. **Clear Browser Cache** for https://ems-demo.omarino.net
3. **Private/Incognito Window** to test without cache

## Results

✅ **Text Visibility:** All text now properly displays as dark text on light backgrounds  
✅ **CORS Errors:** Eliminated - webapp correctly calls http://192.168.75.20:8081  
✅ **API Communication:** All API endpoints now accessible from the frontend  

## Files Modified

1. `webapp/src/app/globals.css` - Removed dark mode CSS
2. `webapp/Dockerfile` - Added ARG for NEXT_PUBLIC_API_URL, fixed ENV syntax

## Related Documentation

- FRONTEND_CORS_FIX.md - Previous CORS configuration fixes
- REGISTRY_PUSH_LOG.md - Image registry operations
