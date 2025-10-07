# API Gateway - OMARINO EMS Suite

The API Gateway provides a unified entry point for all OMARINO Energy Management System microservices. It implements authentication, authorization, rate limiting, request routing, and health aggregation using ASP.NET Core 8 and YARP (Yet Another Reverse Proxy).

## Features

- **Reverse Proxy**: YARP-based routing to backend microservices
- **Authentication**: JWT token-based authentication
- **Authorization**: Role-based access control
- **Rate Limiting**: IP-based rate limiting to prevent abuse
- **Health Aggregation**: Unified health checks for all backend services
- **API Documentation**: Swagger/OpenAPI integration
- **Observability**: OpenTelemetry tracing and Prometheus metrics
- **CORS Support**: Configurable cross-origin resource sharing
- **Error Handling**: Centralized error handling and logging

## Architecture

```
┌─────────────┐
│   Web App   │
│ (Next.js)   │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│   API Gateway       │
│  (ASP.NET Core 8)   │
│                     │
│  - Authentication   │
│  - Rate Limiting    │
│  - YARP Proxy       │
│  - Health Checks    │
└──────┬──────────────┘
       │
       ├────────────────┬──────────────┬─────────────┐
       ▼                ▼              ▼             ▼
┌──────────────┐ ┌────────────┐ ┌───────────┐ ┌────────────┐
│  Timeseries  │ │  Forecast  │ │ Optimize  │ │ Scheduler  │
│   Service    │ │  Service   │ │  Service  │ │  Service   │
│   :5001      │ │   :8001    │ │   :8002   │ │   :5003    │
└──────────────┘ └────────────┘ └───────────┘ └────────────┘
```

## Quick Start

### Prerequisites

- .NET 8.0 SDK
- Docker (optional, for containerized deployment)

### Run Locally

```bash
# Navigate to the api-gateway directory
cd api-gateway

# Restore dependencies
dotnet restore

# Run the service
dotnet run

# Or use dotnet watch for development
dotnet watch run
```

The API Gateway will start on:
- **HTTP**: http://localhost:8080
- **Swagger UI**: http://localhost:8080
- **Metrics**: http://localhost:9090/metrics

### Run with Docker

```bash
# Build the Docker image
docker build -t omarino-ems/api-gateway:latest .

# Run the container
docker run -d \
  -p 8080:8080 \
  -p 9090:9090 \
  -e JWT_SECRET_KEY="your-secret-key-at-least-32-characters" \
  -e TIMESERIES_SERVICE_URL="http://timeseries-service:5001" \
  -e FORECAST_SERVICE_URL="http://forecast-service:8001" \
  -e OPTIMIZE_SERVICE_URL="http://optimize-service:8002" \
  -e SCHEDULER_SERVICE_URL="http://scheduler-service:5003" \
  --name api-gateway \
  omarino-ems/api-gateway:latest
```

## API Endpoints

### Authentication

#### POST /api/auth/login
Authenticate and receive a JWT token.

**Request:**
```json
{
  "username": "demo",
  "password": "demo123"
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "tokenType": "Bearer",
  "expiresAt": "2025-10-02T12:00:00Z",
  "expiresIn": 3600
}
```

**Example:**
```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo123"}'
```

#### GET /api/auth/validate
Validate the current JWT token.

**Example:**
```bash
curl -X GET http://localhost:8080/api/auth/validate \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### POST /api/auth/refresh
Refresh an existing JWT token.

**Example:**
```bash
curl -X POST http://localhost:8080/api/auth/refresh \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Health Checks

#### GET /health
Gateway health check.

**Response:**
```json
{
  "status": "Healthy",
  "checks": [
    {
      "name": "services-health",
      "status": "Healthy",
      "duration": 123.45
    }
  ],
  "totalDuration": 123.45
}
```

#### GET /api/health/services
Check health of all backend services.

**Response:**
```json
{
  "services": [
    {
      "name": "Timeseries",
      "status": "Healthy",
      "url": "http://timeseries-service:5001/api/health",
      "responseTime": 45
    },
    {
      "name": "Forecast",
      "status": "Healthy",
      "url": "http://forecast-service:8001/api/health",
      "responseTime": 32
    }
  ],
  "overallStatus": "Healthy",
  "checkedAt": "2025-10-02T10:30:00Z"
}
```

#### GET /api/health/services/{serviceName}
Check health of a specific service.

**Example:**
```bash
curl http://localhost:8080/api/health/services/Timeseries
```

#### GET /api/health/info
Get gateway information.

**Response:**
```json
{
  "service": "api-gateway",
  "version": "1.0.0",
  "environment": "Development",
  "timestamp": "2025-10-02T10:30:00Z"
}
```

### Proxied Service Routes

All requests to backend services are proxied through the gateway:

| Route | Backend Service | Example |
|-------|-----------------|---------|
| `/api/timeseries/*` | Timeseries Service | `GET /api/timeseries/meters` |
| `/api/forecast/*` | Forecast Service | `POST /api/forecast/models/arima/forecast` |
| `/api/optimize/*` | Optimize Service | `POST /api/optimize` |
| `/api/scheduler/*` | Scheduler Service | `GET /api/scheduler/jobs` |

**Example (Proxied Request):**
```bash
# Request to gateway
curl http://localhost:8080/api/timeseries/meters \
  -H "Authorization: Bearer YOUR_TOKEN"

# Gateway forwards to timeseries-service:5001/api/meters
```

## Configuration

### Environment Variables

```bash
# ASP.NET Core
ASPNETCORE_ENVIRONMENT=Production
ASPNETCORE_URLS=http://+:8080

# JWT Authentication
JWT_SECRET_KEY=your-secret-key-at-least-32-characters-long
JWT_ISSUER=https://omarino-ems.local
JWT_AUDIENCE=omarino-ems-api
JWT_EXPIRATION_MINUTES=60

# Backend Services
TIMESERIES_SERVICE_URL=http://timeseries-service:5001
FORECAST_SERVICE_URL=http://forecast-service:8001
OPTIMIZE_SERVICE_URL=http://optimize-service:8002
SCHEDULER_SERVICE_URL=http://scheduler-service:5003

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_15_MINUTES=1000
RATE_LIMIT_PER_HOUR=5000

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Observability
PROMETHEUS_PORT=9090
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
```

### appsettings.json

See `appsettings.json` for detailed configuration options including:
- YARP reverse proxy routes and clusters
- Rate limiting rules
- JWT settings
- Service endpoints

## Rate Limiting

The gateway implements IP-based rate limiting to prevent abuse:

- **Per Minute**: 100 requests
- **Per 15 Minutes**: 1,000 requests
- **Per Hour**: 5,000 requests

When rate limits are exceeded, the gateway returns HTTP 429 (Too Many Requests).

**Custom Rate Limits:**

You can configure endpoint-specific rate limits in `appsettings.json`:

```json
{
  "IpRateLimiting": {
    "GeneralRules": [
      {
        "Endpoint": "POST:/api/optimize",
        "Period": "1m",
        "Limit": 10
      }
    ]
  }
}
```

## Authentication & Authorization

### JWT Token Structure

The gateway generates JWT tokens with the following claims:
- `sub`: Username
- `name`: User's display name
- `role`: User roles (e.g., "Admin", "User")
- `iat`: Issued at timestamp
- `exp`: Expiration timestamp

### Protecting Routes

Routes can be protected by adding the `[Authorize]` attribute:

```csharp
[Authorize(Roles = "Admin")]
[HttpDelete("/api/timeseries/meters/{id}")]
public async Task<IActionResult> DeleteMeter(string id) { ... }
```

## Health Checks

The gateway provides multiple health check endpoints:

1. **Gateway Health** (`/health`): Checks the gateway itself and all backend services
2. **Service Health** (`/api/health/services`): Aggregates health from all microservices
3. **Individual Service Health** (`/api/health/services/{serviceName}`): Check a specific service

Health checks are used by:
- Docker/Kubernetes for container orchestration
- Load balancers for traffic routing
- Monitoring systems for alerting

## Observability

### Logging

The gateway uses **Serilog** for structured logging:
- All requests are logged with timing information
- Errors include stack traces in development mode
- Logs are written to console in JSON format

**Log Levels:**
- `Information`: Normal operations, request routing
- `Warning`: Rate limiting, validation errors
- `Error`: Unexpected errors, service failures

### Metrics

Prometheus metrics are exposed at `/metrics` (port 9090):
- `http_requests_total`: Total HTTP requests
- `http_request_duration_seconds`: Request duration histogram
- `yarp_proxy_requests_total`: Proxied requests by route
- `dotnet_*`: .NET runtime metrics

**Grafana Dashboard:**

Import the provided dashboard (`/observability/dashboards/api-gateway.json`) to visualize:
- Request rate and latency
- Error rates by endpoint
- Backend service health
- Rate limiting statistics

### Tracing

OpenTelemetry tracing is enabled for distributed tracing:
- Trace IDs are propagated to backend services
- Each request is assigned a unique trace ID (included in `X-Request-Id` header)
- Traces can be viewed in Jaeger or similar tools

## Development

### Project Structure

```
api-gateway/
├── Controllers/          # API controllers
│   ├── AuthController.cs
│   └── HealthController.cs
├── Middleware/           # Custom middleware
│   ├── RequestLoggingMiddleware.cs
│   └── ErrorHandlingMiddleware.cs
├── Models/               # Data models
│   ├── LoginRequest.cs
│   ├── TokenResponse.cs
│   └── ServiceHealthResponse.cs
├── Services/             # Business logic services
│   ├── ITokenService.cs
│   ├── TokenService.cs
│   ├── IServiceHealthCheck.cs
│   └── ServiceHealthCheck.cs
├── tests/                # Unit and integration tests
│   ├── Controllers/
│   └── Services/
├── Program.cs            # Application entry point
├── appsettings.json      # Configuration
├── Dockerfile            # Container image
└── README.md             # This file
```

### Running Tests

```bash
# Run all tests
dotnet test

# Run with coverage
dotnet test --collect:"XPlat Code Coverage"

# Run specific test
dotnet test --filter "FullyQualifiedName~TokenServiceTests"
```

### Code Quality

```bash
# Format code
dotnet format

# Run code analysis
dotnet build /p:TreatWarningsAsErrors=true
```

## Deployment

### Docker Compose

```yaml
version: '3.8'
services:
  api-gateway:
    image: omarino-ems/api-gateway:latest
    ports:
      - "8080:8080"
      - "9090:9090"
    environment:
      - ASPNETCORE_ENVIRONMENT=Production
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - TIMESERIES_SERVICE_URL=http://timeseries-service:5001
      - FORECAST_SERVICE_URL=http://forecast-service:8001
      - OPTIMIZE_SERVICE_URL=http://optimize-service:8002
      - SCHEDULER_SERVICE_URL=http://scheduler-service:5003
    depends_on:
      - timeseries-service
      - forecast-service
      - optimize-service
      - scheduler-service
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
    spec:
      containers:
      - name: api-gateway
        image: omarino-ems/api-gateway:latest
        ports:
        - containerPort: 8080
        - containerPort: 9090
        env:
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: api-gateway-secrets
              key: jwt-secret
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: api-gateway
spec:
  selector:
    app: api-gateway
  ports:
  - name: http
    port: 80
    targetPort: 8080
  - name: metrics
    port: 9090
    targetPort: 9090
  type: LoadBalancer
```

## Security Considerations

1. **JWT Secret Key**: Use a strong, random secret key (at least 32 characters)
2. **HTTPS**: Always use HTTPS in production (configure with reverse proxy like Nginx)
3. **Rate Limiting**: Adjust limits based on your use case
4. **CORS**: Restrict to specific origins in production
5. **Token Expiration**: Set appropriate expiration times (default: 60 minutes)
6. **User Authentication**: Replace demo authentication with real user store (ASP.NET Core Identity, Auth0, etc.)

## Troubleshooting

### Gateway Returns 502 Bad Gateway

**Cause**: Backend service is not available or not responding.

**Solution**:
1. Check service health: `GET /api/health/services`
2. Verify service URLs in configuration
3. Ensure backend services are running
4. Check network connectivity between containers/services

### Rate Limiting Too Aggressive

**Cause**: Default rate limits are too low for your use case.

**Solution**: Adjust rate limits in `appsettings.json`:

```json
{
  "IpRateLimiting": {
    "GeneralRules": [
      {
        "Endpoint": "*",
        "Period": "1m",
        "Limit": 500
      }
    ]
  }
}
```

### JWT Token Invalid or Expired

**Cause**: Token has expired or secret key doesn't match.

**Solution**:
1. Generate a new token: `POST /api/auth/login`
2. Verify JWT secret key is consistent across environments
3. Check token expiration time in configuration

### CORS Errors

**Cause**: Web app origin is not allowed.

**Solution**: Add your webapp URL to CORS configuration:

```json
{
  "CORS_ORIGINS": "http://localhost:3000,https://webapp.example.com"
}
```

## License

Part of the OMARINO EMS Suite. See main repository for license information.

## Support

For issues and questions:
- Create an issue in the main repository
- Check the [architecture documentation](../docs/architecture.md)
- Review YARP documentation: https://microsoft.github.io/reverse-proxy/
