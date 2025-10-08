# Asset Service - Quick Start Guide

## Overview

The Asset Service is a FastAPI-based microservice for managing energy assets (batteries, generators, grid connections, solar panels) in the OMARINO EMS Suite.

## Current Implementation Status

✅ **Completed**:
- Health check endpoint
- Assets CRUD (general asset management)
- Batteries CRUD (specialized battery operations)
- Status monitoring (real-time asset status and dashboard)
- Database client with connection pooling
- Comprehensive data models with validation
- Docker containerization
- Structured logging

⏳ **Pending**:
- Generators router
- Grid connections router
- Solar PV router
- Sites management router
- Asset groups router
- Maintenance scheduling
- Performance analytics

## Quick Start

### 1. Database Setup

First, initialize the database schema:

```bash
# Connect to PostgreSQL
psql -h postgres -U omarino -d omarino

# Run the schema
\i asset-service/database/schema.sql

# Verify tables created
\dt
```

### 2. Local Development

```bash
cd asset-service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env with your settings
# DATABASE_URL=postgresql://omarino:omarino_dev_pass@localhost:5432/omarino

# Run the service
uvicorn app.main:app --reload --port 8003

# Access API documentation
open http://localhost:8003/api/assets/docs
```

### 3. Docker Deployment

```bash
cd asset-service

# Build image
docker build -t omarino-asset-service:latest .

# Run container
docker run -d \
  --name asset-service \
  --network omarino-network \
  -p 8003:8003 \
  -e DATABASE_URL=postgresql://omarino:omarino_dev_pass@postgres:5432/omarino \
  -e API_PREFIX=/api/assets \
  -e LOG_LEVEL=INFO \
  omarino-asset-service:latest

# Check logs
docker logs -f asset-service

# Test health endpoint
curl http://localhost:8003/api/assets/health
```

### 4. Server Deployment

On the server (192.168.75.20):

```bash
# SSH to server
ssh -i /path/to/key.pem ubuntu@192.168.75.20

# Navigate to project
cd omarino-ems-suite

# Pull latest code
git pull

# Build and run
cd asset-service
docker build -t omarino-asset-service:latest .

docker run -d \
  --name asset-service \
  --network omarino-network \
  --restart unless-stopped \
  -p 8003:8003 \
  -e DATABASE_URL=postgresql://omarino:omarino_dev_pass@postgres:5432/omarino \
  omarino-asset-service:latest

# Verify
docker ps | grep asset-service
curl http://localhost:8003/api/assets/health
```

## API Endpoints

### Health Check
- `GET /api/assets/health` - Service health and database connectivity

### Assets
- `GET /api/assets/assets` - List all assets (with filters)
- `POST /api/assets/assets` - Create new asset
- `GET /api/assets/assets/{id}` - Get asset details
- `PUT /api/assets/assets/{id}` - Update asset
- `DELETE /api/assets/assets/{id}` - Delete asset

### Batteries
- `GET /api/assets/batteries` - List batteries (with filters: chemistry, status, site)
- `POST /api/assets/batteries` - Create battery with specifications
- `GET /api/assets/batteries/{id}` - Get battery details
- `PUT /api/assets/batteries/{id}` - Update battery
- `DELETE /api/assets/batteries/{id}` - Delete battery

### Status
- `GET /api/assets/status/{id}` - Get asset status
- `POST /api/assets/status/{id}` - Update asset status
- `GET /api/assets/status` - List all asset statuses
- `GET /api/assets/status/dashboard/summary` - Dashboard summary with metrics

## Testing Examples

### Create a Battery

```bash
curl -X POST http://localhost:8003/api/assets/batteries \
  -H "Content-Type: application/json" \
  -d '{
    "site_id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Battery Bank 1",
    "description": "Main storage battery",
    "manufacturer": "Tesla",
    "model_number": "Powerpack 2",
    "serial_number": "TP2-001",
    "chemistry": "lithium_ion",
    "capacity": 100.0,
    "usable_capacity": 90.0,
    "voltage": 400.0,
    "max_charge_rate": 50.0,
    "max_discharge_rate": 50.0,
    "efficiency": 0.95,
    "min_soc": 10.0,
    "max_soc": 90.0
  }'
```

### List Batteries

```bash
# All batteries
curl http://localhost:8003/api/assets/batteries

# Filter by chemistry
curl http://localhost:8003/api/assets/batteries?chemistry=lithium_ion

# Filter by site
curl "http://localhost:8003/api/assets/batteries?site_id=123e4567-e89b-12d3-a456-426614174000"

# Search
curl "http://localhost:8003/api/assets/batteries?search=Tesla"
```

### Update Asset Status

```bash
curl -X POST http://localhost:8003/api/assets/status/{asset_id} \
  -H "Content-Type: application/json" \
  -d '{
    "online": true,
    "operational_status": "running",
    "current_power_kw": 45.5,
    "current_soc": 75.0,
    "current_soh": 98.5,
    "temperature_c": 25.0
  }'
```

### Get Dashboard Summary

```bash
# All sites
curl http://localhost:8003/api/assets/status/dashboard/summary

# Specific site
curl "http://localhost:8003/api/assets/status/dashboard/summary?site_id=123e4567-e89b-12d3-a456-426614174000"
```

## Configuration

Environment variables (see `.env.example`):

- `DATABASE_URL` - PostgreSQL connection string
- `DB_MIN_POOL_SIZE` - Minimum connection pool size (default: 2)
- `DB_MAX_POOL_SIZE` - Maximum connection pool size (default: 10)
- `DB_COMMAND_TIMEOUT` - Query timeout in seconds (default: 60)
- `API_PREFIX` - API prefix (default: /api/assets)
- `CORS_ORIGINS` - Allowed CORS origins
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `ENABLE_METRICS` - Enable Prometheus metrics (default: true)
- `METRICS_PORT` - Metrics port (default: 9090)

## Architecture

```
asset-service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── models.py            # Pydantic data models
│   ├── database.py          # AsyncPG database client
│   └── routers/
│       ├── __init__.py
│       ├── health.py        # Health check
│       ├── assets.py        # General assets CRUD
│       ├── batteries.py     # Battery-specific operations
│       └── status.py        # Status monitoring
├── database/
│   └── schema.sql           # Database schema
├── api/
│   └── openapi.yaml         # OpenAPI specification
├── Dockerfile               # Container build
├── requirements.txt         # Python dependencies
└── .env.example            # Configuration template
```

## Development Guidelines

### Adding New Routers

1. Create router file in `app/routers/`:
   ```python
   from fastapi import APIRouter, HTTPException, Request, status
   import structlog
   
   logger = structlog.get_logger()
   router = APIRouter()
   
   @router.get("/endpoint")
   async def handler(request: Request):
       db = request.app.state.db
       # Implementation
   ```

2. Add database methods in `app/database.py`

3. Import and register in `app/main.py`:
   ```python
   from app.routers import new_router
   app.include_router(new_router.router, prefix=settings.api_prefix, tags=["Tag"])
   ```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest

# With coverage
pytest --cov=app --cov-report=html
```

## Troubleshooting

### Database Connection Issues

```bash
# Check database is running
docker ps | grep postgres

# Test connection
psql -h localhost -U omarino -d omarino -c "SELECT 1"

# Check logs
docker logs asset-service
```

### Port Already in Use

```bash
# Find process using port 8003
lsof -i :8003

# Kill process
kill -9 <PID>

# Or use different port
uvicorn app.main:app --port 8004
```

### Import Errors

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

## Next Steps

1. **Complete remaining routers**: Generators, Grid, Solar, Sites
2. **Add authentication**: JWT tokens, role-based access
3. **WebSocket support**: Real-time status updates
4. **Performance metrics**: Track asset performance over time
5. **Maintenance scheduling**: Calendar and work order management
6. **Integration tests**: End-to-end API testing
7. **Load testing**: Performance benchmarking

## Support

For issues or questions:
- Check logs: `docker logs asset-service`
- API docs: http://localhost:8003/api/assets/docs
- GitHub issues: OMARINO-DE/omarino-ems-suite
