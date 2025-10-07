# Reverse Proxy Setup for OMARINO-EMS

## Current Architecture

```
Internet
    ↓
Firewall/Reverse Proxy (nginx/traefik/caddy)
    ↓
    ├─→ Port 3000 → Webapp (accessible via https://ems-demo.omarino.net)
    └─→ Port 8081 → API Gateway (BLOCKED - behind firewall)
```

## Problem

- Webapp is accessible via `https://ems-demo.omarino.net`
- API Gateway on port 8081 is NOT accessible externally
- Webapp JavaScript tries to call `http://192.168.75.20:8081` which fails from external networks

## Solution

Configure reverse proxy to route API calls to the internal API Gateway:

```
Internet
    ↓
Reverse Proxy
    ↓
    ├─→ https://ems-demo.omarino.net/        → Port 3000 (webapp)
    └─→ https://ems-demo.omarino.net/api/*   → Port 8081 (api-gateway)
```

---

## Configuration by Reverse Proxy Type

### Option A: Nginx Configuration

If using **Nginx**, update your server block:

```nginx
server {
    listen 443 ssl http2;
    server_name ems-demo.omarino.net;

    # SSL certificates (adjust paths)
    ssl_certificate /etc/letsencrypt/live/ems-demo.omarino.net/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ems-demo.omarino.net/privkey.pem;

    # Webapp routes (main app)
    location / {
        proxy_pass http://192.168.75.20:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # API Gateway routes (NEW - add this section)
    location /api/ {
        proxy_pass http://192.168.75.20:8081/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers (if needed)
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type' always;
        
        # Handle OPTIONS requests
        if ($request_method = 'OPTIONS') {
            return 204;
        }
    }

    # Health endpoint (optional)
    location /health {
        proxy_pass http://192.168.75.20:8081/health;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }
}

# HTTP to HTTPS redirect (if not already configured)
server {
    listen 80;
    server_name ems-demo.omarino.net;
    return 301 https://$server_name$request_uri;
}
```

**To apply:**
```bash
# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
# OR
sudo service nginx reload
```

---

### Option B: Traefik Configuration (Docker Labels)

If using **Traefik**, add these labels to your docker-compose.portainer.yml:

```yaml
api-gateway:
  image: 192.168.61.21:32768/omarino-ems/api-gateway:latest
  container_name: omarino-gateway
  labels:
    # Enable Traefik
    - "traefik.enable=true"
    
    # Router for API
    - "traefik.http.routers.api-gateway.rule=Host(`ems-demo.omarino.net`) && PathPrefix(`/api`, `/health`)"
    - "traefik.http.routers.api-gateway.entrypoints=websecure"
    - "traefik.http.routers.api-gateway.tls=true"
    - "traefik.http.routers.api-gateway.tls.certresolver=letsencrypt"
    
    # Service
    - "traefik.http.services.api-gateway.loadbalancer.server.port=8080"
    
    # Middleware for stripping prefix (if needed)
    # - "traefik.http.middlewares.api-strip.stripprefix.prefixes=/api"
    # - "traefik.http.routers.api-gateway.middlewares=api-strip"
  # ... rest of config
```

---

### Option C: Caddy Configuration

If using **Caddy**, add to your Caddyfile:

```caddy
ems-demo.omarino.net {
    # Webapp routes
    handle /* {
        reverse_proxy 192.168.75.20:3000
    }

    # API routes (NEW)
    handle /api/* {
        reverse_proxy 192.168.75.20:8081
    }

    # Health endpoint
    handle /health {
        reverse_proxy 192.168.75.20:8081
    }
}
```

**To apply:**
```bash
# Reload Caddy
sudo systemctl reload caddy
# OR
caddy reload
```

---

## Step-by-Step Implementation

### Step 1: Configure Reverse Proxy

Choose the configuration for your reverse proxy (nginx/traefik/caddy) from above and apply it.

### Step 2: Test API Accessibility

Before rebuilding the webapp, verify the API is accessible:

```bash
# Test from external network (e.g., your laptop NOT on the local network)
curl https://ems-demo.omarino.net/api/health/services

# Expected output: JSON with service statuses
```

### Step 3: Rebuild Webapp with New API URL

Once the API is accessible through the domain, rebuild the webapp:

```bash
cd "/Users/omarzaror/Library/Mobile Documents/com~apple~CloudDocs/Developing/OMARINO EMS Suite/webapp"

# Build with domain as API URL
docker build --no-cache --platform linux/amd64 \
  --build-arg NEXT_PUBLIC_API_URL='https://ems-demo.omarino.net' \
  -t 192.168.61.21:32768/omarino-ems/webapp:latest .

# Push to registry
docker push 192.168.61.21:32768/omarino-ems/webapp:latest
```

### Step 4: Deploy Updated Webapp

Via Portainer:
1. Go to Stacks → OMARINO-EMS
2. Click "Pull and redeploy"
3. Wait for deployment to complete

OR manually via SSH:
```bash
ssh omar@192.168.75.20 -i "/Users/omarzaror/Library/Mobile Documents/com~apple~CloudDocs/Developing/SSH-Key/server.pem" << 'EOF'
  # Pull latest image
  sudo docker pull 192.168.61.21:32768/omarino-ems/webapp:latest
  
  # Recreate container
  sudo docker stop omarino-webapp
  sudo docker rm omarino-webapp
  
  sudo docker run -d \
    --name omarino-webapp \
    --network ems_omarino-network \
    -p 3000:3000 \
    -e NODE_ENV=production \
    -e NEXTAUTH_URL=https://ems-demo.omarino.net \
    -e NEXTAUTH_SECRET=change-this-secret-in-production \
    192.168.61.21:32768/omarino-ems/webapp:latest
EOF
```

### Step 5: Verify

```bash
# Check bundles contain correct URL
ssh omar@192.168.75.20 -i "/Users/omarzaror/Library/Mobile Documents/com~apple~CloudDocs/Developing/SSH-Key/server.pem" \
  "sudo docker exec omarino-webapp grep -r 'baseURL:' /app/.next/static/chunks/ | head -1"

# Expected: baseURL:"https://ems-demo.omarino.net"
```

Test in browser:
1. Open `https://ems-demo.omarino.net`
2. Open browser console (F12)
3. Check Network tab - API calls should go to `https://ems-demo.omarino.net/api/*`
4. Data should load correctly

---

## Verification Checklist

- [ ] Reverse proxy configured to route `/api/*` to port 8081
- [ ] API accessible via `https://ems-demo.omarino.net/api/health/services`
- [ ] Webapp rebuilt with `NEXT_PUBLIC_API_URL='https://ems-demo.omarino.net'`
- [ ] New webapp image pushed to registry
- [ ] Webapp container redeployed with new image
- [ ] Browser shows data when accessing via domain
- [ ] No mixed content warnings in browser console
- [ ] API calls in Network tab show `https://ems-demo.omarino.net/api/*`

---

## Troubleshooting

### Issue: 502 Bad Gateway on /api/* routes

**Cause:** Reverse proxy can't reach API Gateway

**Solution:**
```bash
# Check if API Gateway is running
docker ps | grep api-gateway

# Check API Gateway health
curl http://192.168.75.20:8081/health

# Check reverse proxy logs
sudo tail -f /var/log/nginx/error.log  # nginx
sudo docker logs -f traefik            # traefik
sudo journalctl -u caddy -f            # caddy
```

### Issue: CORS errors in browser console

**Cause:** API Gateway not allowing requests from domain

**Solution:** Add CORS headers in reverse proxy (see nginx config above) OR configure CORS in API Gateway

### Issue: Old data still showing/not showing

**Cause:** Browser caching old version

**Solution:**
```bash
# Clear browser cache
# OR test in incognito mode
# OR hard reload (Cmd+Shift+R / Ctrl+Shift+R)
```

### Issue: Mixed content warning

**Cause:** Some resources loading via HTTP instead of HTTPS

**Solution:** Ensure ALL resources use HTTPS or relative URLs

---

## Architecture Diagram

### Before (NOT WORKING):
```
User Browser
    ↓
https://ems-demo.omarino.net → Reverse Proxy → :3000 Webapp
    ↓ (JavaScript tries to call)
http://192.168.75.20:8081 ❌ BLOCKED (private IP, behind firewall)
```

### After (WORKING):
```
User Browser
    ↓
https://ems-demo.omarino.net/
    ↓
Reverse Proxy
    ├─→ /        → :3000 Webapp
    └─→ /api/*   → :8081 API Gateway ✅
```

---

## Security Considerations

1. **SSL/TLS:** All external traffic uses HTTPS
2. **Firewall:** API Gateway remains behind firewall, only accessible via reverse proxy
3. **Authentication:** API Gateway handles JWT authentication
4. **Rate Limiting:** Configure rate limiting in reverse proxy or API Gateway

---

## Next Steps

1. **Configure reverse proxy** (choose nginx/traefik/caddy config)
2. **Test API accessibility** via domain
3. **Rebuild webapp** with `https://ems-demo.omarino.net` as API URL
4. **Deploy and verify**

---

**Created:** 2025-10-06  
**Status:** Implementation guide ready  
**Priority:** 🔴 Critical - Required for external access
