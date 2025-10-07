# Public Access Issue - Domain vs IP Address

## Problem

Demo data is visible when accessing via IP (`http://192.168.75.20`) but NOT when accessing via domain (`https://ems-demo.omarino.net`).

### Root Cause

The webapp is built with `NEXT_PUBLIC_API_URL=http://192.168.75.20:8081`, which is a **private IP address**. This works when:
- ✅ Accessing from within the same network
- ✅ Accessing via `http://192.168.75.20:3000` (same network)

But fails when:
- ❌ Accessing via public domain `https://ems-demo.omarino.net`
- ❌ User's browser is outside the private network

### Why?

1. User opens `https://ems-demo.omarino.net` in their browser
2. Browser loads the webapp JavaScript
3. JavaScript tries to connect to API at `http://192.168.75.20:8081`
4. **192.168.75.20 is a private IP** - browser cannot reach it from outside the network
5. API calls fail, no data displays

---

## Current Configuration

### Webapp Build
```dockerfile
# Built with private IP
docker build --build-arg NEXT_PUBLIC_API_URL='http://192.168.75.20:8081'
```

### Domain Setup
- **Frontend Domain:** `ems-demo.omarino.net` → Points to `192.168.75.20:3000`
- **API Endpoint:** `http://192.168.75.20:8081` → **Private IP, not accessible externally**

### Browser Behavior
```
User -> https://ems-demo.omarino.net (✅ works, resolves to server)
   ↓
Webapp JS -> http://192.168.75.20:8081 (❌ fails, private IP unreachable)
```

---

## Solutions

### Option 1: Use API Gateway via Subdomain (RECOMMENDED)

**Best Practice:** Set up a subdomain for the API Gateway.

#### Setup:
1. Add DNS record: `api.ems-demo.omarino.net` → `192.168.75.20`
2. Configure reverse proxy (nginx/traefik) on port 443
3. Add SSL certificate
4. Rebuild webapp with new API URL

#### Commands:
```bash
# 1. Rebuild webapp with subdomain
cd webapp
docker build --no-cache --platform linux/amd64 \
  --build-arg NEXT_PUBLIC_API_URL='https://api.ems-demo.omarino.net' \
  -t 192.168.61.21:32768/omarino-ems/webapp:latest .

# 2. Push to registry
docker push 192.168.61.21:32768/omarino-ems/webapp:latest

# 3. Update on server
ssh omar@192.168.75.20 << 'EOF'
  sudo docker pull 192.168.61.21:32768/omarino-ems/webapp:latest
  sudo docker stop omarino-webapp && sudo docker rm omarino-webapp
  sudo docker run -d --name omarino-webapp \
    --network ems_omarino-network \
    -p 3000:3000 \
    -e NODE_ENV=production \
    192.168.61.21:32768/omarino-ems/webapp:latest
EOF
```

#### Nginx Configuration:
```nginx
# /etc/nginx/sites-available/api.ems-demo.omarino.net
server {
    listen 443 ssl http2;
    server_name api.ems-demo.omarino.net;

    ssl_certificate /etc/letsencrypt/live/ems-demo.omarino.net/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ems-demo.omarino.net/privkey.pem;

    location / {
        proxy_pass http://localhost:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Pros:**
- ✅ Clean separation of concerns
- ✅ HTTPS for API calls
- ✅ Professional setup
- ✅ Works from anywhere

**Cons:**
- Requires DNS configuration
- Requires SSL certificate
- Requires reverse proxy setup

---

### Option 2: Use Same Domain with Path Prefix (SIMPLE)

**Quick Fix:** Use nginx to proxy API calls on the same domain.

#### Setup:
Update nginx config for `ems-demo.omarino.net`:

```nginx
server {
    listen 443 ssl http2;
    server_name ems-demo.omarino.net;

    # Existing webapp config
    location / {
        proxy_pass http://localhost:3000;
        # ... existing settings
    }

    # NEW: API proxy
    location /api/ {
        proxy_pass http://localhost:8081/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # NEW: Health endpoint proxy
    location /health {
        proxy_pass http://localhost:8081/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Then rebuild webapp with relative URL:

```bash
cd webapp
docker build --no-cache --platform linux/amd64 \
  --build-arg NEXT_PUBLIC_API_URL='https://ems-demo.omarino.net' \
  -t 192.168.61.21:32768/omarino-ems/webapp:latest .
```

**Pros:**
- ✅ No new DNS record needed
- ✅ Uses existing SSL certificate
- ✅ Simple configuration
- ✅ Works from anywhere

**Cons:**
- API and webapp share same domain
- Path-based routing can be confusing

---

### Option 3: Expose Port 8081 Publicly (NOT RECOMMENDED)

**Quick but insecure:** Expose API Gateway directly on public IP.

```bash
# Rebuild webapp with public IP
docker build --build-arg NEXT_PUBLIC_API_URL='http://<PUBLIC_IP>:8081'
```

**Pros:**
- ✅ Quickest solution
- ✅ No nginx config needed

**Cons:**
- ❌ **INSECURE** - No HTTPS for API
- ❌ Exposes port 8081 publicly
- ❌ No authentication on API calls
- ❌ Not production-ready

---

### Option 4: Use Public IP with Port 8081 (TEMPORARY)

If you have a static public IP for the server:

```bash
cd webapp
docker build --no-cache --platform linux/amd64 \
  --build-arg NEXT_PUBLIC_API_URL='http://<PUBLIC_IP>:8081' \
  -t 192.168.61.21:32768/omarino-ems/webapp:latest .
```

Replace `<PUBLIC_IP>` with your actual public IP address.

**Pros:**
- ✅ Works from anywhere
- ✅ No DNS/nginx config needed

**Cons:**
- ❌ No HTTPS (insecure)
- ❌ Requires firewall rule for port 8081
- ❌ Breaks if IP changes
- ❌ Not professional

---

## Recommended Implementation Plan

### Phase 1: Quick Fix (Same Domain with Path)
1. Update nginx config for `ems-demo.omarino.net` to proxy `/api/*` to `localhost:8081`
2. Rebuild webapp with `NEXT_PUBLIC_API_URL='https://ems-demo.omarino.net'`
3. Deploy updated webapp
4. Test from external network

**Time:** 15 minutes
**Downtime:** ~2 minutes

### Phase 2: Professional Setup (API Subdomain)
1. Add DNS A record: `api.ems-demo.omarino.net` → server IP
2. Obtain SSL certificate for subdomain
3. Configure nginx for API subdomain
4. Rebuild webapp with `NEXT_PUBLIC_API_URL='https://api.ems-demo.omarino.net'`
5. Deploy updated webapp

**Time:** 30-45 minutes
**Downtime:** ~2 minutes

---

## Verification Commands

### Check DNS Resolution
```bash
# Should resolve to server IP
dig ems-demo.omarino.net
dig api.ems-demo.omarino.net  # (if using subdomain)
```

### Check API Accessibility
```bash
# From external network (e.g., your laptop)
curl https://ems-demo.omarino.net/api/health/services
# OR
curl https://api.ems-demo.omarino.net/api/health/services
```

### Check Webapp API URL
```bash
# SSH to server
ssh omar@192.168.75.20

# Check baked-in API URL
sudo docker exec omarino-webapp grep -r 'baseURL:' /app/.next/static/chunks/ | head -1
```

### Test from Browser Console
```javascript
// Open https://ems-demo.omarino.net
// Open browser console (F12)
fetch('/api/timeseries/meters')
  .then(r => r.json())
  .then(d => console.log('Meters:', d.length))
```

---

## Current Nginx Configuration

### Check Current Setup
```bash
ssh omar@192.168.75.20
sudo cat /etc/nginx/sites-enabled/ems-demo.omarino.net
# OR
sudo nginx -T | grep -A 30 'ems-demo.omarino.net'
```

### Expected Output
Should show if API proxying is configured or not.

---

## Next Steps

1. **Decide on approach:**
   - Quick: Option 2 (same domain with path)
   - Best: Option 1 (API subdomain)

2. **Update nginx configuration**
3. **Rebuild webapp with new API URL**
4. **Deploy and test**

---

## Important Notes

### Next.js Environment Variables
- `NEXT_PUBLIC_*` variables are **baked into the build** at build-time
- They become part of the JavaScript bundles
- Cannot be changed with runtime environment variables
- Must rebuild image to change these values

### Docker Compose Limitation
The current `docker-compose.portainer.yml` sets:
```yaml
environment:
  - NEXT_PUBLIC_API_URL=http://api-gateway:8080
```

This **does nothing** because:
1. It's a runtime environment variable
2. `NEXT_PUBLIC_*` vars must be set at **build time**
3. The value is already compiled into the image

### Solution
Either:
- Build different images for different environments (dev/staging/prod)
- Use server-side API proxying (recommended)
- Use runtime configuration (requires code changes)

---

**Document Created:** 2025-10-06  
**Status:** Issue identified, solutions documented  
**Action Required:** Choose and implement solution
