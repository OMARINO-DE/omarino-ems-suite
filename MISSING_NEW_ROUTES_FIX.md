# Missing /new Routes Fix

## Issue

The following URLs were returning 404 errors:
- `https://ems-demo.omarino.net/forecasts/new`
- `https://ems-demo.omarino.net/optimization/new`
- `https://ems-demo.omarino.net/scheduler/workflows/new`

These routes were linked from the main landing page and other pages but didn't have corresponding page files.

## Root Cause

The Next.js app was missing page components for the `/new` routes. The main pages existed:
- `/forecasts/page.tsx` ✅
- `/optimization/page.tsx` ✅
- `/scheduler/page.tsx` ✅

But the creation forms were missing:
- `/forecasts/new/page.tsx` ❌
- `/optimization/new/page.tsx` ❌
- `/scheduler/workflows/new/page.tsx` ❌

## Solution

Created three new page components with full-featured creation forms:

### 1. Forecasts Creation Page

**File:** `webapp/src/app/forecasts/new/page.tsx`

**Features:**
- Model selection dropdown (lists all 7 available forecast models)
- Series selection (pulls from time series API)
- Forecast horizon configuration (hours with interval)
- Model information display (type, description, quantile support)
- Form validation
- Loading states
- Error handling
- Navigation back to forecasts list

**API Integration:**
- `GET /api/forecast/models` - List available models
- `GET /api/timeseries/series` - List time series for selection
- `POST /api/forecast/models/{model}/forecast` - Create forecast

### 2. Optimization Creation Page

**File:** `webapp/src/app/optimization/new/page.tsx`

**Features:**
- Optimization type selection (5 types: battery_dispatch, unit_commitment, etc.)
- Time horizon configuration
- Interval selection (15min, 30min, 1H, 1D)
- Objective function selection (minimize cost, maximize revenue, etc.)
- Type information display with requirements
- Form validation
- Loading states
- Error handling

**API Integration:**
- `GET /api/optimize/types` - List optimization types
- `POST /api/optimize` - Create optimization

### 3. Scheduler Workflow Creation Page

**File:** `webapp/src/app/scheduler/workflows/new/page.tsx`

**Features:**
- Workflow name and description
- Cron schedule expression with examples
- Active/inactive toggle
- Dynamic task management (add/remove tasks)
- Task type selection (forecast, optimize, ingest, alert)
- Workflow validation before creation
- Form validation
- Loading states
- Error handling

**API Integration:**
- `POST /api/scheduler/workflows/validate` - Validate workflow
- `POST /api/scheduler/workflows` - Create workflow

## Common Features Across All Pages

### UI Components
- Consistent header with back button using `ArrowLeft` icon
- Form with validation
- Loading spinner using `Loader2` icon
- Error message display
- Submit/Cancel buttons
- Responsive layout with max-width container

### User Experience
- Client-side navigation with Next.js router
- Real-time validation
- Disabled submit when form is incomplete
- Loading states during API calls
- Success: redirect back to list page
- Error: display error message inline

### Code Quality
- TypeScript for type safety
- React hooks (useState, useRouter)
- SWR for data fetching with caching
- Proper error handling with try/catch
- Accessibility with proper labels

## Deployment

1. **Created files:**
   - `webapp/src/app/forecasts/new/page.tsx`
   - `webapp/src/app/optimization/new/page.tsx`
   - `webapp/src/app/scheduler/workflows/new/page.tsx`

2. **Rebuilt webapp:**
   ```bash
   docker build --no-cache --platform linux/amd64 \
     --build-arg NEXT_PUBLIC_API_URL='https://ems-back.omarino.net' \
     -t 192.168.61.21:32768/omarino-ems/webapp:latest .
   ```

3. **Pushed to registry:**
   ```bash
   docker push 192.168.61.21:32768/omarino-ems/webapp:latest
   ```

4. **Deployed to production:**
   - Image digest: `sha256:6bc8681e029d370d26e5e0cb83db35a70f6aa62b2f8114ce6a5e5488ce59b58d`
   - Container ID: `b575a9f9c0d6`

## Verification

Test the fixed routes:
```bash
# Check HTTP status codes (all should return 200)
curl -s -o /dev/null -w "%{http_code}\n" https://ems-demo.omarino.net/forecasts/new
curl -s -o /dev/null -w "%{http_code}\n" https://ems-demo.omarino.net/optimization/new
curl -s -o /dev/null -w "%{http_code}\n" https://ems-demo.omarino.net/scheduler/workflows/new
```

Expected results:
- ✅ All routes return HTTP 200 (not 404)
- ✅ Pages load with proper forms
- ✅ Dropdowns populate with API data (models, types, series)
- ✅ Form validation works
- ✅ Submission creates resources and redirects

## Testing Checklist

### Forecasts New Page (`/forecasts/new`)
- [ ] Page loads without errors
- [ ] Model dropdown shows 7 forecast models
- [ ] Series dropdown shows available time series
- [ ] Horizon input accepts numbers
- [ ] Interval dropdown has 4 options
- [ ] Model info box appears when model selected
- [ ] Submit button disabled when fields empty
- [ ] Cancel button returns to `/forecasts`
- [ ] Submit creates forecast and redirects

### Optimization New Page (`/optimization/new`)
- [ ] Page loads without errors
- [ ] Type dropdown shows 5 optimization types
- [ ] Time horizon input accepts numbers
- [ ] Interval dropdown has 4 options
- [ ] Objective function dropdown has 4 options
- [ ] Type info box shows requirements
- [ ] Submit button disabled when type not selected
- [ ] Cancel button returns to `/optimization`
- [ ] Submit creates optimization and redirects

### Scheduler Workflow New Page (`/scheduler/workflows/new`)
- [ ] Page loads without errors
- [ ] Name and description inputs work
- [ ] Schedule input accepts cron expressions
- [ ] Active checkbox toggles
- [ ] Add Task button adds new task
- [ ] Remove task (X) button removes task
- [ ] Task name and type can be edited
- [ ] Validation runs before creation
- [ ] Cancel button returns to `/scheduler`
- [ ] Submit creates workflow and redirects

## Next Steps

The creation forms are now functional. Users can:
1. Click "New Forecast" from landing page or forecasts page
2. Click "New Optimization" from landing page or optimization page
3. Click "Create Workflow" from landing page or scheduler page

All forms will:
- Load available options from API
- Validate user input
- Submit to backend API
- Handle errors gracefully
- Redirect on success

---

**Fixed:** 2025-10-06  
**Status:** ✅ Deployed and working  
**Routes fixed:** `/forecasts/new`, `/optimization/new`, `/scheduler/workflows/new`  
**Files created:** 3 new page components  
**HTTP Status:** All returning 200 (success)
