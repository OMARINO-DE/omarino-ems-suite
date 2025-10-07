# HAProxy Configuration for OMARINO-EMS on pfSense

## Current Setup

- **Reverse Proxy:** HAProxy on pfSense
- **Frontend Domain:** `https://ems-demo.omarino.net`
- **Backend Webapp:** `192.168.75.20:3000`
- **Backend API Gateway:** `192.168.75.20:8081` (currently NOT accessible externally)

---

## HAProxy Configuration Guide

### Overview

We need to configure HAProxy to:
1. Route root path (`/`) to webapp on port 3000
2. Route API paths (`/api/*`, `/health`) to API Gateway on port 8081
3. Both accessible via `https://ems-demo.omarino.net`

---

## Step-by-Step Configuration in pfSense

### Step 1: Configure Backend Servers

#### Backend 1: Webapp
1. Go to **Services → HAProxy → Backend**
2. Click **Add** to create a new backend
3. Configure:
   - **Name:** `OMARINO_Webapp`
   - **Forwardto:** Address+Port
   - **Server list:**
     - **Name:** `webapp_server`
     - **Address:** `192.168.75.20`
     - **Port:** `3000`
     - **SSL:** Unchecked (backend uses HTTP)
   - **Health checking:**
     - **Health check method:** HTTP
     - **Check URI:** `/`
     - **Check interval:** `10s`
4. Click **Save**

#### Backend 2: API Gateway
1. Click **Add** to create another backend
2. Configure:
   - **Name:** `OMARINO_API_Gateway`
   - **Forwardto:** Address+Port
   - **Server list:**
     - **Name:** `api_gateway_server`
     - **Address:** `192.168.75.20`
     - **Port:** `8081`
     - **SSL:** Unchecked (backend uses HTTP)
   - **Health checking:**
     - **Health check method:** HTTP
     - **Check URI:** `/health`
     - **Check interval:** `10s`
3. Click **Save**

---

### Step 2: Configure Frontend with ACLs

1. Go to **Services → HAProxy → Frontend**
2. Find or create your frontend for `ems-demo.omarino.net`
3. Edit the frontend:

#### Basic Settings:
- **Name:** `OMARINO_EMS_Frontend`
- **Status:** Active
- **External address:**
  - **Listen address:** Your WAN interface IP or `*` (any)
  - **Port:** `443`
  - **SSL Offloading:** ✓ Checked
  - **Certificate:** Select your SSL certificate for `ems-demo.omarino.net`

#### Advanced Settings - ACLs:
Add these ACLs to match different paths:

**ACL 1: API Paths**
- **Name:** `api_path`
- **Expression:** `Path starts with`
- **Value:** `/api/`
- Click **Add** after each ACL

**ACL 2: Health Path**
- **Name:** `health_path`
- **Expression:** `Path starts with`
- **Value:** `/health`

**ACL 3: Root Path (default)**
- **Name:** `webapp_path`
- **Expression:** `Path starts with`
- **Value:** `/`

#### Advanced Settings - Actions:
Configure the routing based on ACLs:

**Action 1: Route API calls**
- **Action:** `Use Backend`
- **Condition acl names:** `api_path`
- **Backend:** `OMARINO_API_Gateway`

**Action 2: Route health checks**
- **Action:** `Use Backend`
- **Condition acl names:** `health_path`
- **Backend:** `OMARINO_API_Gateway`

**Action 3: Route webapp (default)**
- **Action:** `Use Backend`
- **Condition acl names:** `webapp_path` (or leave empty for default)
- **Backend:** `OMARINO_Webapp`

4. Click **Save**
5. Click **Apply Changes**

---

## Alternative: Manual HAProxy Configuration

If you prefer to edit the HAProxy config directly, add this to your pfSense HAProxy configuration:

### Backend Configuration

```haproxy
# Backend for Webapp
backend OMARINO_Webapp
    mode http
    balance roundrobin
    option forwardfor
    http-request set-header X-Forwarded-Proto https if { ssl_fc }
    http-request set-header X-Forwarded-Host %[req.hdr(Host)]
    
    # Health check
    option httpchk GET /
    http-check expect status 200
    
    # Server
    server webapp_server 192.168.75.20:3000 check inter 10s

# Backend for API Gateway
backend OMARINO_API_Gateway
    mode http
    balance roundrobin
    option forwardfor
    http-request set-header X-Forwarded-Proto https if { ssl_fc }
    http-request set-header X-Forwarded-Host %[req.hdr(Host)]
    
    # Health check
    option httpchk GET /health
    http-check expect status 200
    
    # Server
    server api_gateway_server 192.168.75.20:8081 check inter 10s
```

### Frontend Configuration

```haproxy
# Frontend for ems-demo.omarino.net
frontend OMARINO_EMS_Frontend
    bind <WAN_IP>:443 ssl crt /var/etc/haproxy/ems-demo.omarino.net.pem
    mode http
    
    # Enable HTTP/2
    option http-server-close
    
    # ACLs for path-based routing
    acl api_path path_beg /api/
    acl health_path path_beg /health
    
    # CORS headers (if needed)
    http-response set-header Access-Control-Allow-Origin "*"
    http-response set-header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS"
    http-response set-header Access-Control-Allow-Headers "Authorization, Content-Type"
    
    # Route based on path
    use_backend OMARINO_API_Gateway if api_path
    use_backend OMARINO_API_Gateway if health_path
    default_backend OMARINO_Webapp
```

---

## Configuration via pfSense WebGUI (Detailed)

### Method 1: Using ACLs and Actions (Recommended)

1. **Navigate to HAProxy**
   - Services → HAProxy → Settings
   - Ensure HAProxy is enabled

2. **Create Backends**
   
   **Backend 1: Webapp**
   - Services → HAProxy → Backend → Add
   - **Name:** `OMARINO_Webapp`
   - **Server list → Add:**
     - Mode: `Active`
     - Name: `webapp_server`
     - Forwardto: `Address+Port`
     - Address: `192.168.75.20`
     - Port: `3000`
     - Encrypt(SSL): `no`
   - **Health checking:**
     - Health check method: `HTTP`
     - HTTP check method: `OPTIONS`
   - Click **Save**
   
   **Backend 2: API Gateway**
   - Services → HAProxy → Backend → Add
   - **Name:** `OMARINO_API_Gateway`
   - **Server list → Add:**
     - Mode: `Active`
     - Name: `api_gateway_server`
     - Forwardto: `Address+Port`
     - Address: `192.168.75.20`
     - Port: `8081`
     - Encrypt(SSL): `no`
   - **Health checking:**
     - Health check method: `HTTP`
     - HTTP check method: `OPTIONS`
   - Click **Save**

3. **Configure Frontend**
   - Services → HAProxy → Frontend → Edit (or Add)
   - **Name:** `OMARINO_EMS_Frontend`
   - **Status:** `Active`
   
   **External address:**
   - Listen address: Your WAN IP or `*`
   - Port: `443`
   - Type: `http / https (SSL Offloading)`
   
   **SSL Offloading:**
   - ✓ SSL Offloading
   - Certificate: Select your certificate for `ems-demo.omarino.net`
   
   **Advanced pass thru → ACLs:**
   - **ACL 1:**
     - Name: `api_path`
     - Expression: `Path starts with:`
     - Value: `/api/`
   - **ACL 2:**
     - Name: `health_path`
     - Expression: `Path starts with:`
     - Value: `/health`
   
   **Advanced pass thru → Actions:**
   - **Action 1:**
     - Action: `Use Backend`
     - Condition acl names: `api_path`
     - backend: `OMARINO_API_Gateway`
   - **Action 2:**
     - Action: `Use Backend`
     - Condition acl names: `health_path`
     - backend: `OMARINO_API_Gateway`
   
   **Default backend:**
   - Select: `OMARINO_Webapp`
   
   Click **Save**

4. **Apply Configuration**
   - Services → HAProxy → Settings
   - Click **Apply Changes**

---

## Verification Steps

### Step 1: Test HAProxy Configuration

From a machine that can access pfSense:

```bash
# Test webapp access
curl -k https://ems-demo.omarino.net/

# Test API health endpoint
curl -k https://ems-demo.omarino.net/health

# Test API meters endpoint
curl -k https://ems-demo.omarino.net/api/timeseries/meters

# Expected: JSON responses from API Gateway
```

### Step 2: Check HAProxy Stats

1. Go to **Services → HAProxy → Stats**
2. Verify:
   - Both backends are green (healthy)
   - Traffic is being routed correctly
   - No errors in the logs

### Step 3: View HAProxy Logs

From pfSense shell:
```bash
# View real-time HAProxy logs
tail -f /var/log/haproxy.log

# Search for errors
grep -i error /var/log/haproxy.log
```

---

## After HAProxy Configuration

Once HAProxy is configured and tested, proceed with webapp rebuild:

### Step 1: Verify API is Accessible

From your laptop (external network):
```bash
# Test API through HAProxy
curl https://ems-demo.omarino.net/api/health/services
curl https://ems-demo.omarino.net/api/timeseries/meters
```

### Step 2: Rebuild Webapp

```bash
cd "/Users/omarzaror/Library/Mobile Documents/com~apple~CloudDocs/Developing/OMARINO EMS Suite/webapp"

# Build with domain as API URL
docker build --no-cache --platform linux/amd64 \
  --build-arg NEXT_PUBLIC_API_URL='https://ems-demo.omarino.net' \
  -t 192.168.61.21:32768/omarino-ems/webapp:latest .

# Push to registry
docker push 192.168.61.21:32768/omarino-ems/webapp:latest
```

### Step 3: Deploy Updated Webapp

Via SSH:
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

### Step 4: Test from Browser

1. Open `https://ems-demo.omarino.net`
2. Open browser DevTools (F12) → Network tab
3. Verify API calls go to `https://ems-demo.omarino.net/api/*`
4. Check that data loads correctly

---

## Troubleshooting HAProxy

### Issue: 504 Gateway Timeout on /api/* routes

**Cause:** HAProxy on pfSense cannot reach API Gateway backend at `192.168.75.20:8081`

**Solution:**

1. **Test connectivity from pfSense:**
```bash
# SSH to pfSense
ssh admin@<pfsense-ip>

# Test if backend is reachable
curl -v http://192.168.75.20:8081/health
curl -v http://192.168.75.20:3000/
```

2. **Check firewall rules:**
   - Go to **Firewall → Rules → LAN**
   - Ensure there's a rule allowing:
     - Source: pfSense (this firewall)
     - Destination: 192.168.75.20
     - Ports: 3000, 8081
     - Action: Pass

3. **Add firewall rule if missing:**
   - Firewall → Rules → LAN → Add
   - **Protocol:** TCP
   - **Source:** Single host or alias → `This Firewall (self)`
   - **Destination:** Single host or alias → `192.168.75.20`
   - **Destination Port Range:** From: `3000` To: `3000`, Add another for `8081`
   - **Description:** "HAProxy to EMS Backend"
   - Click **Save** and **Apply Changes**

4. **Verify backend connectivity:**
```bash
# From pfSense shell
curl http://192.168.75.20:8081/health
# Should return: {"status":"Healthy"}

curl http://192.168.75.20:3000/
# Should return: HTML content
```

### Issue: 503 Service Unavailable

**Cause:** Backend server not reachable or down

**Solution:**
```bash
# From pfSense shell, test backend connectivity
curl http://192.168.75.20:3000
curl http://192.168.75.20:8081/health

# Check firewall rules allow pfSense → 192.168.75.20
```

### Issue: ACLs not matching

**Cause:** ACL expression incorrect

**Solution:**
- Verify ACL syntax in HAProxy Stats
- Check HAProxy logs: `tail -f /var/log/haproxy.log`
- Test ACL: `echo "get /api/health" | socat stdio /var/run/haproxy.sock`

### Issue: SSL certificate error

**Cause:** Certificate not trusted or expired

**Solution:**
1. Go to System → Cert Manager
2. Verify certificate is valid for `ems-demo.omarino.net`
3. Ensure certificate chain is complete

### Issue: Backend health checks failing

**Cause:** Health check path returns non-200 status

**Solution:**
- Test health check manually:
  ```bash
  curl -v http://192.168.75.20:3000/
  curl -v http://192.168.75.20:8081/health
  ```
- Adjust health check path in backend configuration

---

## HAProxy Best Practices

### 1. Enable Logging
Services → HAProxy → Settings
- ✓ Enable HAProxy
- ✓ Enable logging
- Syslog facility: `local0`

### 2. Enable Stats Page
Services → HAProxy → Settings → Stats tab
- ✓ Enable HAProxy stats
- Stats URI: `/haproxy?stats`
- Stats username: `admin`
- Stats password: `<secure-password>`

Access at: `https://<pfSense-IP>/haproxy?stats`

### 3. Configure Timeouts
Services → HAProxy → Settings → Tuning
- Client timeout: `30000` (30s)
- Server timeout: `30000` (30s)
- Connect timeout: `5000` (5s)

### 4. Enable HTTP/2
In frontend configuration:
- Advanced → Custom options:
  ```
  http-request set-header X-Forwarded-Proto https if { ssl_fc }
  ```

---

## Architecture Diagram

### Current Flow:
```
Internet
    ↓
pfSense Firewall
    ↓
HAProxy (443)
    ├─→ / (root)      → 192.168.75.20:3000 (webapp)
    └─→ /api/*        → 192.168.75.20:8081 (api-gateway)
        /health       → 192.168.75.20:8081 (api-gateway)
```

### Traffic Flow:
```
User Browser → https://ems-demo.omarino.net/
    ↓
HAProxy matches ACL: path = "/"
    ↓
Routes to: OMARINO_Webapp backend
    ↓
Proxies to: http://192.168.75.20:3000

User Browser → https://ems-demo.omarino.net/api/timeseries/meters
    ↓
HAProxy matches ACL: path starts with "/api/"
    ↓
Routes to: OMARINO_API_Gateway backend
    ↓
Proxies to: http://192.168.75.20:8081/api/timeseries/meters
```

---

## Security Considerations

### 1. Firewall Rules

Ensure these rules are configured:

**WAN → pfSense**
- Protocol: TCP
- Source: Any
- Destination: pfSense WAN address
- Port: 443
- Action: Allow

**pfSense → Backend Servers**
- Protocol: TCP
- Source: pfSense
- Destination: 192.168.75.20
- Ports: 3000, 8081
- Action: Allow

### 2. Rate Limiting

In frontend configuration, add custom options:
```haproxy
# Rate limiting: 100 requests per 10 seconds per IP
stick-table type ip size 100k expire 30s store http_req_rate(10s)
http-request track-sc0 src
http-request deny deny_status 429 if { sc_http_req_rate(0) gt 100 }
```

### 3. DDoS Protection

Enable SYN flood protection in pfSense:
- System → Advanced → Firewall & NAT
- ✓ Enable SYN proxy

---

## Monitoring

### HAProxy Stats Dashboard

Access at: `http://<pfSense-IP>/haproxy_stats.php` (or via Services → HAProxy → Stats)

Monitor:
- Backend status (green = healthy)
- Request rate
- Error rate
- Queue depth
- Response times

### pfSense Logs

View in real-time:
```bash
# SSH to pfSense
tail -f /var/log/haproxy.log | grep -E 'ems-demo|192.168.75.20'
```

---

## Next Steps Checklist

- [ ] Configure HAProxy backends (webapp + API gateway)
- [ ] Configure HAProxy frontend with ACLs and actions
- [ ] Apply HAProxy configuration
- [ ] Test API accessibility via domain: `curl https://ems-demo.omarino.net/api/health/services`
- [ ] Rebuild webapp with `NEXT_PUBLIC_API_URL='https://ems-demo.omarino.net'`
- [ ] Push webapp image to registry
- [ ] Deploy updated webapp to server
- [ ] Test in browser: `https://ems-demo.omarino.net`
- [ ] Verify data loads correctly
- [ ] Monitor HAProxy stats for errors

---

**Created:** 2025-10-06  
**Platform:** pfSense with HAProxy  
**Status:** Configuration guide ready  
**Priority:** 🔴 Critical - Required for external access
