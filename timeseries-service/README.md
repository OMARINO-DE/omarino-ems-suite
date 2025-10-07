# Time Series Service

ASP.NET Core service for time-series data ingestion, storage, and querying using PostgreSQL with the Timescale extension.

## Features

- **Meter Management**: Register and configure physical/virtual metering devices
- **Series Management**: Define time series linked to meters with units and aggregation types
- **Data Ingestion**: Bulk import time-series data with versioning and quality flags
- **Querying**: Retrieve time-series data with optional aggregation
- **Timescale Integration**: Leverages hypertables for efficient time-series storage
- **Observability**: OpenTelemetry instrumentation, structured logging, Prometheus metrics
- **Health Checks**: `/health`, `/health/ready`, `/health/live` endpoints

## Tech Stack

- **ASP.NET Core 8**
- **Entity Framework Core 8**
- **PostgreSQL 16 + Timescale**
- **NodaTime** for timezone-aware time handling
- **Serilog** for structured logging
- **OpenTelemetry** for observability
- **Swagger/OpenAPI** for API documentation

## Getting Started

### Prerequisites

- .NET 8 SDK
- PostgreSQL 16 with Timescale extension
- (Optional) Docker for containerized deployment

### Configuration

Create or update `appsettings.json`:

```json
{
  "ConnectionStrings": {
    "DefaultConnection": "Host=localhost;Port=5432;Database=omarino_ems;Username=postgres;Password=yourpassword"
  }
}
```

### Database Setup

```bash
# Apply migrations
dotnet ef database update

# Or use Docker Compose (from project root)
docker-compose up -d postgres
```

### Run Locally

```bash
# Restore dependencies
dotnet restore

# Run the service
dotnet run

# Service will be available at:
# - HTTP: http://localhost:5001
# - Swagger: http://localhost:5001/swagger
# - Metrics: http://localhost:5001/metrics
```

### Run with Docker

```bash
# Build image
docker build -t omarino-ems/timeseries-service:latest .

# Run container
docker run -p 5001:5001 \
  -e ConnectionStrings__DefaultConnection="Host=postgres;Database=omarino_ems;Username=postgres;Password=postgres" \
  omarino-ems/timeseries-service:latest
```

## API Endpoints

### Meters

- `GET /api/meters` - List all meters
- `GET /api/meters/{id}` - Get meter by ID
- `POST /api/meters` - Create new meter
- `PUT /api/meters/{id}` - Update meter
- `DELETE /api/meters/{id}` - Delete meter

### Series

- `GET /api/series?meterId={meterId}` - List series for a meter
- `GET /api/series/{id}` - Get series by ID
- `POST /api/series` - Create new series
- `GET /api/series/{id}/range?from={from}&to={to}` - Query series data
- `DELETE /api/series/{id}` - Delete series

### Ingestion

- `POST /api/ingest` - Bulk ingest time-series data
- `GET /api/ingest/jobs/{jobId}` - Get import job status

## API Examples

### Create a Meter

```bash
curl -X POST http://localhost:5001/api/meters \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Building A Main Feed",
    "type": "Electricity",
    "latitude": 52.520008,
    "longitude": 13.404954,
    "address": "Berlin, Germany",
    "siteId": "SITE001",
    "samplingInterval": "PT15M",
    "timezone": "Europe/Berlin",
    "tags": {
      "building": "A",
      "criticality": "high"
    }
  }'
```

### Create a Series

```bash
curl -X POST http://localhost:5001/api/series \
  -H "Content-Type: application/json" \
  -d '{
    "meterId": "YOUR_METER_ID",
    "name": "active_power",
    "description": "Active power consumption",
    "unit": "kW",
    "aggregation": "Mean",
    "dataType": "Measurement"
  }'
```

### Ingest Data

```bash
curl -X POST http://localhost:5001/api/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source": "manual",
    "points": [
      {
        "seriesId": "YOUR_SERIES_ID",
        "timestamp": "2025-10-02T12:00:00Z",
        "value": 125.5,
        "quality": "Good",
        "source": "SCADA",
        "version": 1
      },
      {
        "seriesId": "YOUR_SERIES_ID",
        "timestamp": "2025-10-02T12:15:00Z",
        "value": 130.2,
        "quality": "Good",
        "source": "SCADA",
        "version": 1
      }
    ]
  }'
```

### Query Series Data

```bash
curl "http://localhost:5001/api/series/YOUR_SERIES_ID/range?from=2025-10-02T00:00:00Z&to=2025-10-03T00:00:00Z"
```

## Database Schema

### Tables

- **Meters**: Metering device metadata
- **Series**: Time series definitions
- **TimeSeriesPoints**: Data points (Timescale hypertable)
- **ImportJobs**: Ingestion job tracking

### Indexes

- Composite index on `(series_id, timestamp, version)` for efficient lookups
- Indexes on `series_id`, `timestamp`, `quality` for query performance
- Timescale hypertable partitioned by time (7-day chunks)

## Development

### Run Tests

```bash
cd TimeSeriesService.Tests
dotnet test
```

### Generate Migration

```bash
dotnet ef migrations add MigrationName
```

### Apply Migrations

```bash
dotnet ef database update
```

### Format Code

```bash
dotnet format
```

## Observability

### Structured Logging

Logs are emitted in JSON format (Compact JSON) suitable for log aggregation systems like Elasticsearch, Loki, or CloudWatch.

### Metrics

Prometheus metrics exposed at `/metrics`:
- HTTP request duration
- Database query duration
- Import job statistics

### Health Checks

- `/health` - Overall health status
- `/health/ready` - Readiness probe (includes DB check)
- `/health/live` - Liveness probe

## Configuration

Environment variables:

- `ConnectionStrings__DefaultConnection` - PostgreSQL connection string
- `ASPNETCORE_ENVIRONMENT` - Environment (Development, Staging, Production)
- `ASPNETCORE_URLS` - Listening URLs (default: http://+:5001)

## Performance Considerations

### Timescale Hypertables

- Data partitioned into 7-day chunks by default
- Automatic data retention policies can be configured
- Continuous aggregates for pre-computed rollups

### Bulk Ingestion

- Use batch inserts for large imports
- Consider using COPY for very large datasets
- Version-based upsert prevents duplicate data

### Query Optimization

- Add indexes on commonly queried tags (JSONB GIN index)
- Use time-bucket aggregations for downsampling
- Consider materialized views for frequent queries

## Troubleshooting

### Database Connection Issues

```bash
# Test connection
psql -h localhost -p 5432 -U postgres -d omarino_ems

# Check if Timescale extension is enabled
SELECT * FROM pg_extension WHERE extname = 'timescaledb';
```

### Migration Errors

```bash
# Reset database (development only!)
dotnet ef database drop
dotnet ef database update
```

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for development guidelines.

## License

MIT License - see [LICENSE](../LICENSE)
