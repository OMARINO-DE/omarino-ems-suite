# Shared Schemas and Contracts

This directory contains canonical JSON Schema definitions and generated client SDKs for the OMARINO EMS Suite.

## Directory Structure

```
shared/
├── schemas/              # JSON Schema definitions
│   ├── time_series_point.json
│   ├── meter.json
│   ├── series.json
│   ├── forecast_request.json
│   ├── forecast_response.json
│   ├── optimize_request.json
│   ├── optimize_response.json
│   └── scheduler_dag.json
├── clients/              # Generated client SDKs
│   ├── typescript/       # TypeScript client (generated)
│   ├── python/           # Python client (generated)
│   └── csharp/           # C# client (generated)
└── openapi/              # OpenAPI specifications
    ├── timeseries-service.yaml
    ├── forecast-service.yaml
    ├── optimize-service.yaml
    └── scheduler-service.yaml
```

## Schema Definitions

### Core Data Models

#### `time_series_point.json`
Represents a single data point in a time series with quality metadata, versioning, and lineage tracking.

**Key Fields:**
- `timestamp` (ISO 8601 UTC)
- `value` (numeric measurement)
- `unit` (e.g., kWh, MW, EUR/MWh)
- `quality` (good, uncertain, bad, estimated, missing)
- `source` (e.g., SCADA, smart_meter, forecast_model)
- `version` (for data lineage)

#### `meter.json`
Physical or virtual metering device metadata with location, tags, and sampling configuration.

**Key Fields:**
- `id` (UUID)
- `meter_type` (electricity, gas, water, heat, virtual)
- `location` (lat/lon, address, site_id)
- `tags` (flexible key-value metadata)
- `sampling_interval` (ISO 8601 duration)
- `timezone` (IANA identifier)

#### `series.json`
Time series metadata linking to a meter, specifying unit, aggregation method, and data type.

**Key Fields:**
- `meter_id` (reference to parent meter)
- `unit` (measurement unit)
- `aggregation` (instant, mean, sum, min, max, count)
- `data_type` (measurement, forecast, schedule, price, weather)

### Forecast Service Contracts

#### `forecast_request.json`
Request for time series forecasting with model selection, quantiles, and external features.

**Example:**
```json
{
  "series_id": "660e8400-e29b-41d4-a716-446655440001",
  "horizon": 96,
  "granularity": "PT15M",
  "model": "auto",
  "quantiles": [0.1, 0.5, 0.9]
}
```

#### `forecast_response.json`
Forecast results with point predictions, quantiles, metrics, and model metadata.

**Contains:**
- Point forecast (median/mean)
- Quantile forecasts (p10, p50, p90)
- Metrics (MAE, MAPE, RMSE, pinball loss)
- Feature importance (if applicable)

### Optimize Service Contracts

#### `optimize_request.json`
Request for energy system optimization (storage dispatch, unit commitment, procurement).

**Key Components:**
- Asset definitions (batteries, generators, flexible loads)
- Constraints (grid limits, reserves, emissions)
- Price signals and forecasts
- Objective function and solver selection

#### `optimize_response.json`
Optimization results with schedule, objective value, sensitivities, and solver statistics.

**Contains:**
- Optimized schedule per interval
- Objective value (e.g., total cost)
- Sensitivities (shadow prices, reduced costs)
- Metrics (total cost, peak power, self-consumption rate)

### Scheduler Service Contract

#### `scheduler_dag.json`
Directed Acyclic Graph definition for workflow orchestration.

**Task Types:**
- `http_call` - Make HTTP request to a service
- `delay` - Wait for a specified duration
- `condition` - Branch based on condition
- `map` - Fan-out parallel tasks
- `foreach_series` - Iterate over series

**Triggers:**
- `cron` - Schedule with cron expression
- `interval` - Repeat every N minutes
- `webhook` - Start via HTTP webhook

## Client SDKs

Client libraries are auto-generated from JSON Schemas and OpenAPI specs.

### TypeScript Client

```typescript
import { ForecastClient } from '@omarino-ems/clients-ts';

const client = new ForecastClient('http://forecast-service:8001');
const forecast = await client.requestForecast({
  series_id: 'uuid',
  horizon: 96,
  granularity: 'PT15M',
  model: 'auto'
});
```

### Python Client

```python
from omarino_ems.clients import ForecastClient

client = ForecastClient('http://forecast-service:8001')
forecast = client.request_forecast(
    series_id='uuid',
    horizon=96,
    granularity='PT15M',
    model='auto'
)
```

### C# Client

```csharp
using OmarinoEMS.Clients;

var client = new ForecastClient("http://forecast-service:8001");
var forecast = await client.RequestForecastAsync(new ForecastRequest
{
    SeriesId = Guid.Parse("..."),
    Horizon = 96,
    Granularity = "PT15M",
    Model = "auto"
});
```

## Schema Validation

### Validate JSON Documents

```bash
# Install ajv-cli
npm install -g ajv-cli

# Validate a forecast request
ajv validate -s schemas/forecast_request.json -d examples/forecast_request.json
```

### Generate TypeScript Types

```bash
cd clients/typescript
npm run generate-types
```

### Generate Python Models

```bash
cd clients/python
poetry run datamodel-codegen \
  --input ../../schemas \
  --output omarino_ems/models \
  --input-file-type jsonschema
```

## Contract Testing

Contract tests ensure services conform to these schemas.

```bash
# Run contract tests
cd ../..
make contract-test
```

## Versioning Strategy

- **Schema Version**: Embedded in `$id` field
- **API Version**: URL path versioning (e.g., `/v1/forecast`)
- **Backward Compatibility**: Additive changes only within major version
- **Breaking Changes**: Require new major version

## Contributing

When adding or modifying schemas:

1. Update JSON Schema definition
2. Add examples in schema file
3. Regenerate client SDKs
4. Update contract tests
5. Update this README

## References

- [JSON Schema Specification](https://json-schema.org/)
- [OpenAPI Specification](https://swagger.io/specification/)
- [ISO 8601 Durations](https://en.wikipedia.org/wiki/ISO_8601#Durations)
- [IANA Time Zones](https://www.iana.org/time-zones)
