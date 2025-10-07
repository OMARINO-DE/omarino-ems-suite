# OMARINO EMS - Docker Deployment Guide

This guide provides instructions for deploying the OMARINO EMS suite using Docker with multi-platform support and private registry integration.

## Overview

The OMARINO EMS stack includes:
- **API Gateway** (ASP.NET Core 8 + YARP)
- **Time Series Service** (ASP.NET Core 8)
- **Forecast Service** (Python FastAPI)
- **Optimize Service** (Python FastAPI) 
- **Scheduler Service** (ASP.NET Core 8 + Quartz.NET)
- **Web Application** (Next.js 14)
- **Observability Stack** (Prometheus, Grafana, Loki, Tempo)
- **Databases** (PostgreSQL with TimescaleDB, Redis)

## Architecture Support

All images are built for **multi-platform support**:
- `linux/amd64` (Intel/AMD 64-bit)
- `linux/arm64` (ARM 64-bit - Apple Silicon, ARM servers)

## Private Registry

All images are configured to use the private registry: `http://192.168.61.21:32768/`

## Quick Start

### Prerequisites

1. **Docker Engine** with buildx support
2. **Docker Compose** v2.0 or later
3. Access to the private registry `192.168.61.21:32768`

### 1. Build and Push Images

Use the provided script to build and push all images:

```bash
# Make the script executable (if not already done)
chmod +x scripts/build-and-push.sh

# Run the build script
./scripts/build-and-push.sh
```

The script will:
- Set up Docker buildx for multi-platform builds
- Pull and push third-party images to private registry
- Build and push custom application images
- Support both ARM64 and AMD64 platforms

### 2. Deploy with Docker Compose

#### Standard Deployment

```bash
# Clone the repository
git clone <repository-url>
cd OMARINO-EMS-Suite

# Start the stack
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

#### Environment Configuration

Create a `.env` file in the root directory:

```env
# Database Configuration
POSTGRES_USER=omarino
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=omarino

# Redis Configuration
REDIS_PASSWORD=your_redis_password

# JWT Configuration
JWT_SECRET_KEY=your_jwt_secret_key_minimum_32_characters_long

# Grafana Configuration
GRAFANA_USER=admin
GRAFANA_PASSWORD=your_grafana_password

# Next.js Configuration
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your_nextauth_secret

# Logging
LOG_LEVEL=Information
ASPNETCORE_ENVIRONMENT=Production
ENVIRONMENT=production
```

### 3. Deploy with Portainer

#### Portainer Stack Deployment

1. **Access Portainer**: Navigate to your Portainer instance
2. **Create Stack**: Go to `Stacks` > `Add stack`
3. **Configure Stack**:
   - **Name**: `OMARINO-EMS`
   - **Repository**: Use Git repository or upload compose file
   - **Compose file**: Use `docker-compose.portainer.yml`

4. **Environment Variables**: Add the following variables in Portainer:

```
POSTGRES_USER=omarino
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=omarino
REDIS_PASSWORD=your_redis_password
JWT_SECRET_KEY=your_jwt_secret_key_minimum_32_characters_long
GRAFANA_USER=admin
GRAFANA_PASSWORD=your_grafana_password
NEXTAUTH_URL=http://your-domain:3000
NEXTAUTH_SECRET=your_nextauth_secret
LOG_LEVEL=Information
ASPNETCORE_ENVIRONMENT=Production
ENVIRONMENT=production
```

5. **Deploy**: Click `Deploy the stack`

#### Portainer Features

The Portainer version includes:
- **Deploy section** with restart policies
- **Resource limits** (can be added as needed)
- **Health checks** for all services
- **Dependency management** with proper startup order
- **Volume management** with named volumes

## Service Endpoints

Once deployed, the following endpoints will be available:

| Service | Port | URL | Description |
|---------|------|-----|-------------|
| Web App | 3000 | http://localhost:3000 | Main application interface |
| API Gateway | 8081 | http://localhost:8081 | API gateway and proxy |
| Time Series | 5001 | http://localhost:5001 | Time series data API |
| Forecast | 8001 | http://localhost:8001 | Forecasting API |
| Optimize | 8002 | http://localhost:8002 | Optimization API |
| Scheduler | 5003 | http://localhost:5003 | Job scheduling API |
| Grafana | 3001 | http://localhost:3001 | Monitoring dashboards |
| Prometheus | 9090 | http://localhost:9090 | Metrics collection |
| Tempo | 3200 | http://localhost:3200 | Distributed tracing |
| PostgreSQL | 5433 | localhost:5433 | Database (external access) |
| Redis | 6380 | localhost:6380 | Cache (external access) |

## Health Checks

All services include health checks:

```bash
# Check overall stack health
docker-compose ps

# Check specific service logs
docker-compose logs <service-name>

# Check service health endpoint (example)
curl http://localhost:8081/health
```

## Scaling Services

### With Docker Compose

```bash
# Scale specific services
docker-compose up -d --scale forecast-service=2
docker-compose up -d --scale optimize-service=2
```

### With Portainer

1. Go to the stack in Portainer
2. Select the service to scale
3. Modify the replica count
4. Apply changes

## Data Persistence

The following volumes are created for data persistence:

- `postgres_data`: PostgreSQL database files
- `redis_data`: Redis persistence
- `prometheus_data`: Prometheus metrics storage
- `grafana_data`: Grafana dashboards and settings
- `loki_data`: Log storage
- `tempo_data`: Trace data storage

## Backup and Recovery

### Database Backup

```bash
# PostgreSQL backup
docker-compose exec postgres pg_dump -U omarino omarino > backup.sql

# Redis backup
docker-compose exec redis redis-cli --rdb /data/backup.rdb
```

### Volume Backup

```bash
# Stop services
docker-compose down

# Backup volumes
docker run --rm -v omarino-ems_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .

# Restart services
docker-compose up -d
```

## Troubleshooting

### Common Issues

1. **Registry Access**: Ensure the private registry `192.168.61.21:32768` is accessible
2. **Platform Issues**: Verify Docker supports the target platform (ARM64/AMD64)
3. **Port Conflicts**: Check that required ports are not in use by other services
4. **Memory**: Ensure sufficient memory is available (recommended: 8GB+)

### Debug Commands

```bash
# Check Docker buildx platforms
docker buildx ls

# Inspect multi-platform image
docker buildx imagetools inspect 192.168.61.21:32768/omarino-ems/api-gateway:latest

# Check service logs
docker-compose logs -f <service-name>

# Execute into container
docker-compose exec <service-name> /bin/bash
```

### Registry Troubleshooting

```bash
# Test registry connectivity
curl -f http://192.168.61.21:32768/v2/

# List repositories
curl http://192.168.61.21:32768/v2/_catalog

# List tags for an image
curl http://192.168.61.21:32768/v2/omarino-ems/api-gateway/tags/list
```

## Security Considerations

1. **Change default passwords** in production
2. **Use strong JWT secrets** (minimum 32 characters)
3. **Configure HTTPS** for production deployments
4. **Secure the private registry** with authentication
5. **Regular security updates** for base images
6. **Network isolation** using Docker networks

## Monitoring

The stack includes comprehensive monitoring:

- **Prometheus**: Metrics collection from all services
- **Grafana**: Visualization and alerting dashboards
- **Loki**: Centralized logging
- **Tempo**: Distributed tracing for request flows

Access Grafana at `http://localhost:3001` with admin credentials to view:
- Application performance metrics
- Infrastructure monitoring
- Custom business dashboards
- Alert configurations

## Updates and Maintenance

### Updating Images

```bash
# Rebuild and push updated images
./scripts/build-and-push.sh

# Pull latest images and restart
docker-compose pull
docker-compose up -d
```

### Version Management

Images are tagged with:
- `latest`: Most recent stable version
- `YYYYMMDD-HHMMSS`: Timestamp-based versions for rollbacks

## Support

For issues and support:
1. Check service logs: `docker-compose logs <service>`
2. Verify health checks: `docker-compose ps`
3. Review this documentation
4. Contact the development team

---

**Note**: This deployment configuration is optimized for both local development and production use with proper security considerations and monitoring capabilities.