# OMARINO EMS Infrastructure

Complete infrastructure setup for the OMARINO Energy Management System with Docker Compose and observability stack.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         OMARINO EMS Suite                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐      ┌─────────────────────────────────────────┐ │
│  │  WebApp  │─────▶│          API Gateway (YARP)             │ │
│  │ Next.js  │      │     JWT Auth + Rate Limiting            │ │
│  └──────────┘      └─────────────────────────────────────────┘ │
│    :3000                         │  :8080                       │
│                                  │                              │
│         ┌────────────────────────┼────────────────────────┐    │
│         │                        │                        │    │
│    ┌────▼─────┐  ┌──────────▼────────┐  ┌──────────▼──────┐  │
│    │TimeSeries│  │   Forecast        │  │  Optimize       │  │
│    │ Service  │  │   Service         │  │  Service        │  │
│    │ ASP.NET  │  │   FastAPI/Python  │  │  FastAPI/Pyomo  │  │
│    └────┬─────┘  └───────────────────┘  └──────┬──────────┘  │
│    :5001│                                       │ :8002        │
│         │                                       │              │
│    ┌────▼──────────────┐          ┌───────────▼──────┐       │
│    │   PostgreSQL      │          │      Redis        │       │
│    │ + TimescaleDB     │          │      Cache        │       │
│    └───────────────────┘          └───────────────────┘       │
│                                                                 │
│    ┌──────────────────┐                                        │
│    │   Scheduler      │                                        │
│    │   Service        │                                        │
│    │ ASP.NET+Quartz   │                                        │
│    └──────────────────┘                                        │
│         :5003                                                   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                     Observability Stack                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │Prometheus│  │ Grafana  │  │   Loki   │  │  Tempo   │      │
│  │ Metrics  │  │Dashboard │  │   Logs   │  │ Traces   │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
│    :9090         :3001         :3100         :3200            │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Make (optional, for convenience commands)
- 8GB RAM minimum
- 20GB free disk space

### 1. Clone and Configure

```bash
# Navigate to project directory
cd "OMARINO EMS Suite"

# Copy environment variables template
cp .env.example .env

# Edit .env with your configuration
# IMPORTANT: Change default passwords in production!
nano .env
```

### 2. Start the System

```bash
# Using Make (recommended)
make up

# Or using docker-compose directly
docker-compose up -d
```

### 3. Verify Services

```bash
# Check service status
make ps

# Check health
make health

# View logs
make logs
```

### 4. Access Services

- **Web UI**: http://localhost:3000
- **API Gateway**: http://localhost:8080
- **Swagger API Docs**: http://localhost:8080/swagger
- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090
- **PostgreSQL**: localhost:5432 (omarino/omarino_dev_pass)
- **Redis**: localhost:6379

## 📦 Services

### Application Services

| Service | Port | Technology | Description |
|---------|------|------------|-------------|
| webapp | 3000 | Next.js 14 | Web user interface |
| api-gateway | 8080 | ASP.NET Core 8 + YARP | Reverse proxy with auth |
| timeseries-service | 5001 | ASP.NET Core 8 | Time series data management |
| forecast-service | 8001 | Python FastAPI | Energy forecasting models |
| optimize-service | 8002 | Python FastAPI | Battery optimization |
| scheduler-service | 5003 | ASP.NET Core 8 | Workflow automation |

### Infrastructure Services

| Service | Port | Purpose |
|---------|------|---------|
| postgres | 5432 | Primary database (TimescaleDB) |
| redis | 6379 | Caching and rate limiting |
| prometheus | 9090 | Metrics collection |
| grafana | 3001 | Visualization dashboards |
| loki | 3100 | Log aggregation |
| promtail | - | Log collector |
| tempo | 3200 | Distributed tracing |

## 🎯 Make Commands

### Development

```bash
make up              # Start all services
make down            # Stop all services
make restart         # Restart all services
make build           # Build all Docker images
make rebuild         # Rebuild from scratch (no cache)
make logs            # Show all logs
make logs-timeseries # Show specific service logs
make ps              # Show running services
make health          # Check service health
```

### Database

```bash
make db-shell        # Open PostgreSQL shell
make db-migrate      # Run database migrations
make db-backup       # Backup database
make db-restore      # Restore database
```

### Testing

```bash
make test            # Run all tests
make test-timeseries # Test specific service
make test-e2e        # Run end-to-end tests
```

### Monitoring

```bash
make open-grafana    # Open Grafana in browser
make open-prometheus # Open Prometheus in browser
make open-webapp     # Open web UI in browser
make open-swagger    # Open API docs in browser
```

### Cleanup

```bash
make clean           # Stop and remove volumes
make clean-all       # Remove all Docker resources
make prune           # Remove unused Docker resources
```

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Database
POSTGRES_USER=omarino
POSTGRES_PASSWORD=change_in_production
POSTGRES_DB=omarino

# Redis
REDIS_PASSWORD=change_in_production

# Security (IMPORTANT: Change in production!)
JWT_SECRET_KEY=your-secret-key-min-32-chars
NEXTAUTH_SECRET=generate-with-openssl-rand-base64-32

# Logging
LOG_LEVEL=Information  # Debug, Information, Warning, Error

# Environment
ASPNETCORE_ENVIRONMENT=Production  # Development, Production
ENVIRONMENT=production              # development, production
```

### Service URLs

Internal service communication:
- Time Series: `http://timeseries-service:5001`
- Forecast: `http://forecast-service:8001`
- Optimize: `http://optimize-service:8002`
- Scheduler: `http://scheduler-service:5003`

External access:
- All services accessible via API Gateway: `http://localhost:8080/api/{service}`
- Direct service access available on published ports

## 📊 Observability

### Prometheus Metrics

Access Prometheus at http://localhost:9090

**Key Metrics:**
- `up` - Service health (1 = up, 0 = down)
- `http_requests_total` - Request count by service
- `http_request_duration_seconds` - Request latency
- `http_requests_errors_total` - Error count

**Example Queries:**
```promql
# Request rate per service
rate(http_requests_total[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status=~"5.."}[5m])
```

### Grafana Dashboards

Access Grafana at http://localhost:3001 (admin/admin)

**Pre-configured Dashboards:**
- System Overview - Service health and performance
- Request Metrics - Request rates and latencies
- Error Tracking - Error rates and types
- Resource Usage - CPU, memory, disk

**Data Sources:**
- Prometheus - Metrics
- Loki - Logs
- Tempo - Traces
- PostgreSQL - Direct database queries

### Loki Logs

Access logs via Grafana's Explore tab.

**Example LogQL Queries:**
```logql
# All logs from timeseries-service
{service="timeseries"}

# Error logs from all services
{job="omarino-ems"} |= "error" or "Error" or "ERROR"

# Logs for specific request
{service="api-gateway"} |= "request_id=abc123"
```

### Tempo Tracing

Distributed tracing for request flow across services.

**Features:**
- End-to-end request tracing
- Service dependency mapping
- Performance bottleneck identification
- Correlation with logs

## 🗄️ Database

### PostgreSQL + TimescaleDB

Two separate databases:
- `omarino_timeseries` - Time series data with hypertables
- `omarino_scheduler` - Workflow definitions and Quartz.NET tables

**Connection:**
```bash
# Using Make
make db-shell

# Or directly
docker-compose exec postgres psql -U omarino -d omarino_timeseries
```

**Backup:**
```bash
# Automated backup
make db-backup

# Manual backup
docker-compose exec -T postgres pg_dump -U omarino omarino_timeseries > backup.sql
```

**Restore:**
```bash
make db-restore FILE=backup.sql
```

### Redis

Used for:
- Optimization result caching (optimize-service)
- Rate limiting (api-gateway)
- Session storage (future use)

**Access:**
```bash
# Using Make
make redis-cli

# Or directly
docker-compose exec redis redis-cli -a omarino_redis_pass
```

## 🔒 Security

### Production Checklist

- [ ] Change all default passwords in `.env`
- [ ] Generate strong JWT secret: `openssl rand -base64 32`
- [ ] Generate NextAuth secret: `openssl rand -base64 32`
- [ ] Enable HTTPS (add reverse proxy with SSL)
- [ ] Configure firewall rules
- [ ] Enable database encryption at rest
- [ ] Set up automated backups
- [ ] Configure log rotation
- [ ] Enable container security scanning
- [ ] Set resource limits on containers

### JWT Configuration

The API Gateway uses JWT for authentication:

```bash
# Generate secure secret
openssl rand -base64 32

# Add to .env
JWT_SECRET_KEY=your-generated-secret
```

**Login:**
```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "password": "demo123"}'
```

## 📈 Scaling

### Horizontal Scaling

Scale individual services:

```bash
# Scale forecast service to 3 instances
docker-compose up -d --scale forecast-service=3

# Scale optimize service to 2 instances
docker-compose up -d --scale optimize-service=2
```

### Resource Limits

Add to `docker-compose.yml`:

```yaml
services:
  forecast-service:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check service logs
make logs-{service-name}

# Check service status
docker-compose ps

# Rebuild service
docker-compose build {service-name}
docker-compose up -d {service-name}
```

### Database Connection Issues

```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Verify database exists
make db-shell
\l  # List databases

# Check connection string in .env
# Ensure POSTGRES_USER, POSTGRES_PASSWORD match
```

### Out of Memory

```bash
# Check resource usage
make stats

# Increase Docker memory limit (Docker Desktop settings)
# Or add resource limits to docker-compose.yml
```

### Port Already in Use

```bash
# Find process using port
lsof -i :3000  # or :8080, :5432, etc.

# Kill process or change port in docker-compose.yml
ports:
  - "3001:3000"  # Map to different host port
```

### Services Can't Communicate

```bash
# Verify all services on same network
docker network inspect omarino_omarino-network

# Check DNS resolution
docker-compose exec api-gateway ping timeseries-service

# Verify service URLs in environment variables
```

## 📝 Development Workflow

### Local Development

```bash
# 1. Start infrastructure
make up

# 2. Watch logs
make logs

# 3. Make code changes
# (services will rebuild on next up)

# 4. Rebuild specific service
docker-compose build timeseries-service
docker-compose up -d timeseries-service

# 5. Run tests
make test

# 6. Stop services
make down
```

### Hot Reload

For development with hot reload:

```bash
# Mount code as volume in docker-compose.override.yml
version: '3.8'
services:
  timeseries-service:
    volumes:
      - ./timeseries-service:/app
    environment:
      - ASPNETCORE_ENVIRONMENT=Development
```

## 🚢 Deployment

### Production Deployment

1. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with production values
   ```

2. **Build images:**
   ```bash
   make build
   ```

3. **Start services:**
   ```bash
   make up
   ```

4. **Verify health:**
   ```bash
   make health
   ```

5. **Load initial data:**
   ```bash
   make load-sample-data
   ```

### Kubernetes Deployment

See `/deployment/kubernetes/` for Helm charts and manifests (coming in CI/CD step).

## 📚 Additional Resources

- [Architecture Documentation](../docs/ARCHITECTURE.md)
- [API Documentation](../docs/API.md)
- [Deployment Guide](../docs/DEPLOYMENT.md)
- [Service READMEs](../)
  - [Time Series Service](../timeseries-service/README.md)
  - [Forecast Service](../forecast-service/README.md)
  - [Optimize Service](../optimize-service/README.md)
  - [Scheduler Service](../scheduler-service/README.md)
  - [API Gateway](../api-gateway/README.md)
  - [WebApp](../webapp/README.md)

## 🤝 Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for development guidelines.

## 📞 Support

For issues and questions:
1. Check service logs: `make logs`
2. Review troubleshooting section above
3. Check GitHub issues
4. Contact development team

## 📄 License

Part of the OMARINO EMS Suite. See main repository for license information.
