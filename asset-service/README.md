# Asset Management Service

Comprehensive asset management service for OMARINO Energy Management System.

## Overview

The Asset Management Service provides complete lifecycle management for all energy assets in the OMARINO EMS platform, including:

- **Battery Energy Storage Systems (BESS)** - Lithium-ion, LFP, flow batteries, etc.
- **Generators** - Diesel, natural gas, biogas, and other fuel-based generation
- **Grid Connections** - Import/export capabilities and tariff management
- **Solar PV Systems** - Rooftop, ground-mount, and tracking systems
- **Wind Turbines** - Horizontal and vertical axis turbines
- **EV Chargers** - Level 1, Level 2, DC fast charging
- **Load Profiles** - Flexible, critical, and sheddable loads

## Features

### Asset Management
- ✅ Complete CRUD operations for all asset types
- ✅ Detailed specifications for each asset type
- ✅ Multi-site support with geographic information
- ✅ Asset grouping (microgrids, VPPs, portfolios)
- ✅ Asset dependencies and relationships
- ✅ Flexible metadata storage (JSONB)

### Monitoring & Status
- ✅ Real-time asset status tracking
- ✅ Operational status (online, offline, fault, maintenance)
- ✅ Alarm and fault management
- ✅ Communication monitoring
- ✅ Status dashboard with aggregated metrics

### Maintenance Management
- ✅ Preventive maintenance scheduling
- ✅ Corrective maintenance tracking
- ✅ Maintenance history and costs
- ✅ Service provider management
- ✅ Parts tracking
- ✅ Downtime tracking

### Performance Analytics
- ✅ Energy generation and consumption tracking
- ✅ Efficiency and capacity factor metrics
- ✅ Financial metrics (revenue, costs, profit)
- ✅ Environmental metrics (CO2 avoided/emitted)
- ✅ Availability and reliability metrics
- ✅ Aggregated performance summaries

## Architecture

### Technology Stack
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15+ with asyncpg
- **API Documentation**: OpenAPI 3.0 / Swagger UI
- **Logging**: Structured logging with structlog
- **Validation**: Pydantic models
- **Telemetry**: OpenTelemetry for metrics and tracing

### Database Schema

The service uses a comprehensive PostgreSQL schema with the following key tables:

**Core Tables:**
- `assets` - Main asset registry
- `sites` - Site/location management
- `asset_groups` - Asset grouping and organization
- `asset_group_members` - Group membership
- `asset_dependencies` - Asset relationships

**Asset-Specific Tables:**
- `battery_specs` - Battery specifications
- `generator_specs` - Generator specifications
- `grid_connection_specs` - Grid connection specifications
- `solar_pv_specs` - Solar PV specifications
- `wind_turbine_specs` - Wind turbine specifications
- `ev_charger_specs` - EV charger specifications
- `load_specs` - Load profile specifications

**Monitoring & Operations:**
- `asset_status` - Real-time asset status
- `maintenance_records` - Maintenance history
- `asset_performance` - Performance metrics

See [database/schema.sql](./database/schema.sql) for complete schema definition.

## API Endpoints

### General Assets
- `GET /api/assets/assets` - List all assets (with filtering)
- `POST /api/assets/assets` - Create new asset
- `GET /api/assets/assets/{asset_id}` - Get asset details
- `PUT /api/assets/assets/{asset_id}` - Update asset
- `DELETE /api/assets/assets/{asset_id}` - Delete asset

### Asset Type Specific
- `GET /api/assets/batteries` - List battery assets
- `GET /api/assets/generators` - List generator assets
- `GET /api/assets/grid-connections` - List grid connections
- `GET /api/assets/solar` - List solar PV systems
- `POST /api/assets/{type}` - Create asset of specific type

### Status & Monitoring
- `GET /api/assets/assets/{asset_id}/status` - Get real-time status
- `PUT /api/assets/assets/{asset_id}/status` - Update status
- `GET /api/assets/assets/status/dashboard` - Status dashboard

### Sites
- `GET /api/assets/sites` - List sites
- `POST /api/assets/sites` - Create site
- `GET /api/assets/sites/{site_id}/assets` - Get site assets

### Groups
- `GET /api/assets/groups` - List asset groups
- `POST /api/assets/groups` - Create group
- `POST /api/assets/groups/{group_id}/members` - Add asset to group

### Maintenance
- `GET /api/assets/assets/{asset_id}/maintenance` - Get maintenance records
- `POST /api/assets/assets/{asset_id}/maintenance` - Create maintenance record
- `GET /api/assets/maintenance/scheduled` - Get scheduled maintenance

### Performance
- `GET /api/assets/assets/{asset_id}/performance` - Get performance metrics
- `GET /api/assets/performance/summary` - Performance summary

See [api/openapi.yaml](./api/openapi.yaml) for complete API specification.

## Installation

### Prerequisites
- Python 3.11 or higher
- PostgreSQL 15 or higher
- Docker (optional)

### Local Development

1. **Clone repository**
```bash
git clone https://github.com/OMARINO-DE/omarino-ems-suite.git
cd omarino-ems-suite/asset-service
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set environment variables**
```bash
export DATABASE_URL="postgresql://omarino:omarino_dev_pass@localhost:5432/omarino"
export API_PREFIX="/api/assets"
export SERVICE_NAME="asset-service"
```

5. **Initialize database**
```bash
psql -U omarino -d omarino -f database/schema.sql
```

6. **Run service**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

7. **Access API documentation**
Open http://localhost:8003/api/assets/docs

### Docker Deployment

1. **Build Docker image**
```bash
docker build -t omarino-asset-service:latest .
```

2. **Run container**
```bash
docker run -d \
  --name omarino-asset-service \
  --network omarino-network \
  -p 8003:8003 \
  -e DATABASE_URL="postgresql://omarino:omarino_dev_pass@postgres:5432/omarino" \
  -e API_PREFIX="/api/assets" \
  omarino-asset-service:latest
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://omarino:omarino@localhost:5432/omarino` |
| `API_PREFIX` | API route prefix | `/api/assets` |
| `SERVICE_NAME` | Service name for logging | `asset-service` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `CORS_ORIGINS` | Allowed CORS origins | `["*"]` |
| `ENABLE_METRICS` | Enable Prometheus metrics | `true` |
| `METRICS_PORT` | Prometheus metrics port | `9003` |

## Usage Examples

### Create a Battery Asset

```bash
curl -X POST "http://localhost:8003/api/assets/batteries" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Main Storage Battery",
    "description": "Primary BESS for peak shaving",
    "location": "Building A - Rooftop",
    "site_id": "123e4567-e89b-12d3-a456-426614174000",
    "battery": {
      "capacity_kwh": 500.0,
      "max_charge_kw": 250.0,
      "max_discharge_kw": 250.0,
      "round_trip_efficiency": 0.92,
      "min_soc": 0.1,
      "max_soc": 0.95,
      "initial_soc": 0.5,
      "chemistry": "lithium_iron_phosphate",
      "degradation_cost_per_kwh": 0.015,
      "current_health_percentage": 100.0
    }
  }'
```

### Query Assets at a Site

```bash
curl "http://localhost:8003/api/assets/sites/123e4567-e89b-12d3-a456-426614174000/assets"
```

### Update Asset Status

```bash
curl -X PUT "http://localhost:8003/api/assets/assets/{asset_id}/status" \
  -H "Content-Type: application/json" \
  -d '{
    "online": true,
    "operational_status": "online",
    "current_power_kw": 150.5,
    "current_soc": 0.75
  }'
```

### Get Performance Metrics

```bash
curl "http://localhost:8003/api/assets/assets/{asset_id}/performance?from_date=2025-01-01&to_date=2025-01-31&aggregation=daily"
```

## Integration with Other Services

### Scheduler Service
The scheduler service fetches asset specifications when executing optimization workflows:

```csharp
// Fetch battery asset for optimization
var response = await httpClient.GetAsync($"http://asset-service:8003/api/assets/batteries/{batteryId}");
var battery = await response.Content.ReadFromJsonAsync<BatteryAsset>();
```

### Optimization Service
The optimization service retrieves asset specifications for building optimization models:

```python
# Get all batteries for dispatch optimization
async with httpx.AsyncClient() as client:
    response = await client.get("http://asset-service:8003/api/assets/batteries")
    batteries = response.json()["batteries"]
```

### Forecast Service
The forecast service can query asset locations for weather-based forecasting:

```python
# Get solar PV systems for forecast generation
solar_systems = await asset_client.get_solar_systems(site_id=site_id)
```

## Database Schema Design

### Key Design Principles

1. **Separation of Concerns**: Core asset data separate from type-specific specifications
2. **Referential Integrity**: Foreign key constraints ensure data consistency
3. **Flexibility**: JSONB metadata fields for extensibility
4. **Performance**: Indexed columns for common queries
5. **Audit Trail**: Timestamps and user tracking on all tables
6. **Soft Deletes**: Status field allows deactivation without deletion

### Entity Relationships

```
sites (1) ──── (N) assets (1) ──── (1) battery_specs
                 │                  └─── (1) generator_specs
                 │                  └─── (1) grid_connection_specs
                 │                  └─── (1) solar_pv_specs
                 │                  └─── (1) wind_turbine_specs
                 │                  └─── (1) ev_charger_specs
                 │                  └─── (1) load_specs
                 │
                 ├──── (N) asset_status
                 ├──── (N) maintenance_records
                 ├──── (N) asset_performance
                 └──── (N) asset_group_members ──── (1) asset_groups
```

## Development

### Project Structure

```
asset-service/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration
│   ├── models/
│   │   ├── asset.py            # Asset models
│   │   ├── battery.py          # Battery models
│   │   ├── generator.py        # Generator models
│   │   ├── grid.py             # Grid connection models
│   │   ├── solar.py            # Solar PV models
│   │   ├── wind.py             # Wind turbine models
│   │   └── common.py           # Common models
│   ├── routers/
│   │   ├── assets.py           # Asset endpoints
│   │   ├── batteries.py        # Battery endpoints
│   │   ├── generators.py       # Generator endpoints
│   │   ├── grid.py             # Grid endpoints
│   │   ├── solar.py            # Solar endpoints
│   │   ├── wind.py             # Wind endpoints
│   │   ├── sites.py            # Site endpoints
│   │   ├── groups.py           # Group endpoints
│   │   ├── status.py           # Status endpoints
│   │   ├── maintenance.py      # Maintenance endpoints
│   │   ├── performance.py      # Performance endpoints
│   │   └── health.py           # Health check
│   ├── services/
│   │   ├── asset_database.py   # Database operations
│   │   ├── asset_service.py    # Business logic
│   │   └── validation.py       # Validation logic
│   └── utils/
│       ├── logging.py          # Logging utilities
│       └── errors.py           # Error handling
├── database/
│   ├── schema.sql              # Database schema
│   └── seeds/
│       └── sample_assets.sql   # Sample data
├── api/
│   └── openapi.yaml            # API specification
├── tests/
│   ├── test_assets.py
│   ├── test_batteries.py
│   └── test_integration.py
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

### Running Tests

```bash
pytest tests/ -v --cov=app
```

### Code Quality

```bash
# Linting
flake8 app/

# Type checking
mypy app/

# Formatting
black app/
```

## Roadmap

### Phase 1: Core Functionality (Current)
- ✅ Database schema design
- ✅ API specification
- ⏳ Basic CRUD operations
- ⏳ Asset type implementations

### Phase 2: Advanced Features
- ⏳ Real-time status updates via WebSocket
- ⏳ Asset templating and presets
- ⏳ Bulk import/export
- ⏳ Asset validation rules engine

### Phase 3: Integration & Analytics
- ⏳ Integration with optimization service
- ⏳ Integration with scheduler service
- ⏳ Advanced performance analytics
- ⏳ Predictive maintenance
- ⏳ Asset health scoring

### Phase 4: Advanced Capabilities
- ⏳ Multi-tenancy support
- ⏳ Role-based access control
- ⏳ Asset certification and compliance tracking
- ⏳ Digital twin integration
- ⏳ Machine learning for asset optimization

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests.

## License

Copyright © 2025 OMARINO GmbH. All rights reserved.

## Support

For support and questions:
- Email: support@omarino.de
- Documentation: https://docs.omarino.de
- Issues: https://github.com/OMARINO-DE/omarino-ems-suite/issues
