# HAProxy API Subdomain Configuration - ems-back.omarino.net

## Overview

Using a separate subdomain for the API backend provides:
- ✅ **Cleaner separation** - Frontend and API on different subdomains
- ✅ **No path conflicts** - No need for path-based routing
- ✅ **Better security** - Can apply different rules per subdomain
- ✅ **Easier debugging** - Clear distinction between webapp and API traffic

## Architecture

### Before (Path-based):
```
https://ems-demo.omarino.net/          → Webapp (port 3000)
https://ems-demo.omarino.net/api/*     → API Gateway (port 8081)
```

### After (Subdomain-based):
```
https://ems-demo.omarino.net/          → Webapp (port 3000)
https://ems-back.omarino.net/*         → API Gateway (port 8081)
```

---

## Step 1: Configure DNS

Add a DNS A record for the API subdomain:

### Option A: Using Your DNS Provider

1. Log into your DNS provider (Cloudflare, GoDaddy, etc.)
2. Add new A record:
   - **Name:** `ems-back` (or `ems-back.omarino.net`)
   - **Type:** `A`
   - **Value:** Your pfSense WAN IP or server public IP
   - **TTL:** Auto or 3600
3. Save the record

### Option B: Using pfSense DNS Resolver

If using pfSense for local DNS:

1. Go to **Services → DNS Resolver**
2. Scroll to **Host Overrides**
3. Click **Add**
   - **Host:** `ems-back`
   - **Domain:** `omarino.net`
   - **IP Address:** Your pfSense LAN IP or `192.168.75.20`
   - **Description:** "EMS Backend API"
4. Click **Save**
5. Click **Apply Changes**

### Verify DNS:
```bash
# Test DNS resolution
nslookup ems-back.omarino.net
dig ems-back.omarino.net

# Should return the same IP as ems-demo.omarino.net
```

---

## Step 2: Configure HAProxy Backend

The backend configuration remains the same (already created):

### Existing Backend:
```
Name: OMARINO_API_Gateway
Server: 192.168.75.20:8081
Health check: /health
```

✅ **No changes needed** - This backend is already configured.

---

## Step 3: Configure HAProxy Frontend for API Subdomain

### Option A: Create New Frontend (Recommended)

1. Go to **Services → HAProxy → Frontend**
2. Click **Add** to create a new frontend
3. Configure:

#### Basic Settings:
- **Name:** `OMARINO_API_Frontend`
- **Status:** Active
- **External address:**
  - **Listen address:** Your WAN interface IP or `*` (any)
  - **Port:** `443`
  - **SSL Offloading:** ✓ Checked
  - **Certificate:** Select your SSL certificate for `*.omarino.net` or `ems-back.omarino.net`

#### Default Backend:
- Select: `OMARINO_API_Gateway`

#### Advanced Settings - ACLs:
- **ACL 1:**
  - Name: `is_api_domain`
  - Expression: `Host matches`
  - Value: `ems-back.omarino.net`

#### Advanced Settings - Actions:
- **Action 1:**
  - Action: `Use Backend`
  - Condition acl names: `is_api_domain`
  - Backend: `OMARINO_API_Gateway`

4. Click **Save**
5. Click **Apply Changes**

### Option B: Manual Configuration

Add to HAProxy configuration:

```haproxy
# Frontend for API subdomain
frontend OMARINO_API_Frontend
    bind <WAN_IP>:443 ssl crt /var/etc/haproxy/omarino.net.pem
    mode http
    
    # ACL to match API subdomain
    acl is_api_domain hdr(host) -i ems-back.omarino.net
    
    # Use API backend
    use_backend OMARINO_API_Gateway if is_api_domain
    default_backend OMARINO_API_Gateway
```

---

## Step 4: Update Existing Webapp Frontend

**Remove API path-based routing** from the webapp frontend:

1. Go to **Services → HAProxy → Frontend**
2. Edit: `OMARINO_EMS_Frontend`
3. Remove these ACLs:
   - ❌ `api_path` (Path starts with `/api/`)
   - ❌ `health_path` (Path starts with `/health`)
4. Remove these Actions:
   - ❌ Route API calls to `OMARINO_API_Gateway`
   - ❌ Route health checks to `OMARINO_API_Gateway`
5. Keep only:
   - **Default backend:** `OMARINO_Webapp`
6. Click **Save**
7. Click **Apply Changes**

---

## Step 5: SSL Certificate

### Option A: Wildcard Certificate (Recommended)

If you have a wildcard certificate (`*.omarino.net`):
- ✅ Use the same certificate for both frontends
- No additional configuration needed

### Option B: Individual Certificates

If using individual certificates:

1. Go to **System → Cert Manager → Certificates**
2. Add new certificate for `ems-back.omarino.net`:
   - **Method:** Import or ACME
   - **Common Name:** `ems-back.omarino.net`
3. In HAProxy Frontend settings:
   - Select the new certificate for `OMARINO_API_Frontend`

### Option C: Let's Encrypt via ACME

1. Go to **Services → Acme Certificates**
2. Add new certificate:
   - **Name:** `ems-back-cert`
   - **Domain:** `ems-back.omarino.net`
   - **Method:** Webroot or DNS
3. Issue certificate
4. Select in HAProxy frontend

---

## Step 6: Firewall Rules

**Verify firewall rules allow HTTPS traffic:**

### WAN → pfSense (Port 443)
- Protocol: TCP
- Source: Any
- Destination: WAN address
- Port: 443
- Action: Pass

### pfSense → Backend Server
- Protocol: TCP
- Source: This Firewall
- Destination: 192.168.75.20
- Ports: 3000, 8081
- Action: Pass

**No changes needed if these rules already exist.**

---

## Step 7: Rebuild Webapp with New API URL

```bash
cd "/Users/omarzaror/Library/Mobile Documents/com~apple~CloudDocs/Developing/OMARINO EMS Suite/webapp"

# Build with API subdomain
docker build --no-cache --platform linux/amd64 \
  --build-arg NEXT_PUBLIC_API_URL='https://ems-back.omarino.net' \
  -t 192.168.61.21:32768/omarino-ems/webapp:latest .

# Push to registry
docker push 192.168.61.21:32768/omarino-ems/webapp:latest
```

---

## Step 8: Deploy Updated Webapp

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

---

## Verification Steps

### Step 1: Test DNS Resolution

```bash
# Check both domains resolve
nslookup ems-demo.omarino.net
nslookup ems-back.omarino.net

# Both should point to the same IP
```

### Step 2: Test API Subdomain

```bash
# Test API health endpoint
curl -k https://ems-back.omarino.net/health

# Test API meters endpoint  
curl -k https://ems-back.omarino.net/api/timeseries/meters

# Test API services health
curl -k https://ems-back.omarino.net/api/health/services

# All should return JSON responses
```

### Step 3: Test Webapp

```bash
# Test webapp
curl -k https://ems-demo.omarino.net/

# Should return HTML
```

### Step 4: Verify in Browser

1. Open `https://ems-demo.omarino.net`
2. Open DevTools (F12) → Network tab
3. Verify API calls go to `https://ems-back.omarino.net/api/*`
4. Check that data loads correctly
5. Verify no CORS errors in console

### Step 5: Check HAProxy Stats

1. Go to **Services → HAProxy → Stats**
2. Verify:
   - ✅ Both frontends are green
   - ✅ Both backends are green
   - ✅ Traffic is being routed correctly
   - ✅ No errors

---

## Troubleshooting

### Issue: DNS not resolving

**Solution:**
```bash
# Clear DNS cache
sudo dscacheutil -flushcache  # macOS
ipconfig /flushdns              # Windows

# Test with explicit DNS server
nslookup ems-back.omarino.net 8.8.8.8
```

### Issue: SSL Certificate Error

**Cause:** Certificate doesn't cover `ems-back.omarino.net`

**Solution:**
- Use wildcard certificate (`*.omarino.net`)
- OR issue separate certificate for `ems-back.omarino.net`

### Issue: 503 Service Unavailable

**Cause:** Backend not reachable from pfSense

**Solution:**
```bash
# From pfSense shell
curl http://192.168.75.20:8081/health

# If fails, check firewall rules
```

### Issue: CORS Error in Browser

**Cause:** API not allowing requests from webapp domain

**Solution:**

Add CORS headers in HAProxy API frontend:

```haproxy
# In OMARINO_API_Frontend, add custom options:
http-response set-header Access-Control-Allow-Origin "https://ems-demo.omarino.net"
http-response set-header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS"
http-response set-header Access-Control-Allow-Headers "Authorization, Content-Type"
http-response set-header Access-Control-Allow-Credentials "true"

# Handle preflight OPTIONS requests
acl is_options method OPTIONS
http-request return status 200 if is_options
```

---

## Benefits of This Setup

### 1. Clear Separation
```
Frontend:  https://ems-demo.omarino.net  → User-facing webapp
Backend:   https://ems-back.omarino.net  → API services only
```

### 2. Independent Scaling
- Can rate-limit API separately
- Can apply different firewall rules
- Can cache webapp and API differently

### 3. Security
- Can restrict API access by IP ranges
- Can add authentication at proxy level for API
- Clear audit trail per subdomain

### 4. Easier Debugging
- HAProxy logs clearly show which service
- Browser network tab shows clear separation
- No confusion between webapp and API routes

### 5. Future-Proof
- Easy to move API to different server
- Easy to add API versioning (v1.ems-back, v2.ems-back)
- Easy to add additional services (mqtt.ems-back, ws.ems-back)

---

## Configuration Summary

### DNS Records:
```
ems-demo.omarino.net  → A → <pfSense WAN IP>
ems-back.omarino.net  → A → <pfSense WAN IP>
```

### HAProxy Frontends:
```
OMARINO_EMS_Frontend:
  - Listen: *:443 (HTTPS)
  - ACL: Host = ems-demo.omarino.net
  - Backend: OMARINO_Webapp (port 3000)

OMARINO_API_Frontend:
  - Listen: *:443 (HTTPS)
  - ACL: Host = ems-back.omarino.net
  - Backend: OMARINO_API_Gateway (port 8081)
```

### HAProxy Backends:
```
OMARINO_Webapp:
  - Server: 192.168.75.20:3000
  - Health: GET /

OMARINO_API_Gateway:
  - Server: 192.168.75.20:8081
  - Health: GET /health
```

### Webapp Configuration:
```bash
NEXT_PUBLIC_API_URL='https://ems-back.omarino.net'
```

---

## Next Steps Checklist

- [ ] Add DNS A record for `ems-back.omarino.net`
- [ ] Verify DNS resolution: `nslookup ems-back.omarino.net`
- [ ] Create HAProxy frontend for API subdomain
- [ ] Remove path-based routing from webapp frontend
- [ ] Verify SSL certificate covers `ems-back.omarino.net`
- [ ] Apply HAProxy configuration
- [ ] Test API subdomain: `curl https://ems-back.omarino.net/health`
- [ ] Rebuild webapp with `NEXT_PUBLIC_API_URL='https://ems-back.omarino.net'`
- [ ] Deploy updated webapp
- [ ] Test in browser: verify API calls go to `ems-back.omarino.net`
- [ ] Monitor HAProxy stats for both frontends

---

**Created:** 2025-10-06  
**Platform:** pfSense with HAProxy  
**Status:** Configuration guide ready  
**Priority:** 🟢 Improvement - Better architecture than path-based routing
