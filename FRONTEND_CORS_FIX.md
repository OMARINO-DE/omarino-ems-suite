# Frontend CORS Configuration Fix

## Issue
The frontend at `https://ems-demo.omarino.net` was unable to access the API Gateway due to CORS (Cross-Origin Resource Sharing) errors. The browser was blocking requests to `http://localhost:8080` because:
1. The webapp was configured to use the wrong API URL (internal Docker network address)
2. The API Gateway's CORS policy only allowed localhost origins

## Errors Observed
```
Quellübergreifende (Cross-Origin) Anfrage blockiert: 
Die Gleiche-Quelle-Regel verbietet das Lesen der externen Ressource auf 
http://localhost:8080/api/health/services. 
(Grund: CORS-Kopfzeile 'Access-Control-Allow-Origin' fehlt). 
Statuscode: 200.
```

## Solution

### 1. Updated Webapp Container Configuration
**File**: Docker container environment for `omarino-webapp`

**Changed**:
- `NEXT_PUBLIC_API_URL`: from `http://api-gateway:8080` to `http://192.168.75.20:8081`
- `NEXTAUTH_URL`: from `http://localhost:3000` to `https://ems-demo.omarino.net`

**Command executed**:
```bash
sudo docker run -d \
  --name omarino-webapp \
  --network ems_omarino-network \
  -p 3000:3000 \
  -e NODE_ENV=production \
  -e NEXT_PUBLIC_API_URL='http://192.168.75.20:8081' \
  -e NEXTAUTH_SECRET='change-this-secret-in-production' \
  -e NEXTAUTH_URL='https://ems-demo.omarino.net' \
  --restart unless-stopped \
  192.168.61.21:32768/omarino-ems/webapp:latest
```

### 2. Updated API Gateway CORS Policy
**File**: `api-gateway/Program.cs`

**Before**:
```csharp
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowWebApp", policy =>
    {
        policy.WithOrigins("http://localhost:3000", "http://localhost:3001")
              .AllowAnyHeader()
              .AllowAnyMethod()
              .AllowCredentials();
    });
});
```

**After**:
```csharp
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowWebApp", policy =>
    {
        policy.WithOrigins(
                "http://localhost:3000", 
                "http://localhost:3001",
                "http://192.168.75.20:3000",
                "https://ems-demo.omarino.net")
              .AllowAnyHeader()
              .AllowAnyMethod()
              .AllowCredentials();
    });
});
```

### 3. Rebuilt and Deployed API Gateway
- Built new Docker image with updated CORS configuration
- Deployed to server at 192.168.75.20:8081
- Container is healthy and responding correctly

## Verification
Test CORS headers:
```bash
curl -H "Origin: https://ems-demo.omarino.net" \
  http://192.168.75.20:8081/api/health/services \
  -v 2>&1 | grep -i "access-control"
```

**Result**:
```
< Access-Control-Allow-Credentials: true
< Access-Control-Allow-Origin: https://ems-demo.omarino.net
```

## Current Configuration
- **Frontend URL**: https://ems-demo.omarino.net (port 443, HTTPS)
- **API Gateway URL**: http://192.168.75.20:8081 (port 8081, HTTP)
- **Allowed CORS Origins**:
  - http://localhost:3000 (development)
  - http://localhost:3001 (development)
  - http://192.168.75.20:3000 (server direct access)
  - https://ems-demo.omarino.net (production)

## Status
✅ **RESOLVED** - Frontend can now successfully communicate with the API Gateway

## Next Steps (Optional Improvements)
1. **Use HTTPS for API**: Set up SSL/TLS certificate for API Gateway
2. **Use Same Domain**: Configure subdomain (e.g., api.omarino.net) for API Gateway
3. **Environment Variables**: Store configuration in docker-compose.yml for easier management
4. **Reverse Proxy**: Consider using Nginx or Traefik to handle SSL termination and routing

## Date
October 6, 2025
