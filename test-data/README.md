# Test Data for OMARINO EMS

This directory contains test data that can be manually imported into the OMARINO EMS system.

## Contents

1. **meters.sql** - Sample meters (sensors/measurement points)
2. **series.sql** - Time series definitions
3. **timeseries-data.sql** - Historical time series data points
4. **forecasts.sql** - Sample forecast results
5. **optimizations.sql** - Sample optimization runs
6. **workflows.sql** - Sample scheduler workflows

## Import Instructions

### Using Docker

```bash
# Import SQL files into PostgreSQL
cat test-data/meters.sql | sudo docker exec -i omarino-postgres psql -U omarino -d omarino

# Or all files at once
for file in test-data/*.sql; do
    echo "Importing $file..."
    cat "$file" | sudo docker exec -i omarino-postgres psql -U omarino -d omarino
done
```

### Using Remote Server (SSH)

```bash
# Copy files to remote server
scp -i "/path/to/server.pem" test-data/*.sql omar@192.168.75.20:~/test-data/

# SSH to server and import
ssh -i "/path/to/server.pem" omar@192.168.75.20
cd ~/test-data
for file in *.sql; do
    echo "Importing $file..."
    cat "$file" | sudo docker exec -i omarino-postgres psql -U omarino -d omarino
done
```

### Using API (CSV Files)

For CSV files, use the web UI or API endpoints to import:

```bash
# Import meters
curl -X POST https://ems-back.omarino.net/api/meters/import \
  -F "file=@test-data/meters.csv"

# Import time series data
curl -X POST https://ems-back.omarino.net/api/timeseries/import \
  -F "file=@test-data/timeseries-data.csv"
```

## Test Data Overview

### Meters
- **Building A - Main** - Main electrical meter (building_a_main)
- **Building A - HVAC** - HVAC system meter (building_a_hvac)
- **Building A - Lighting** - Lighting system meter (building_a_lighting)
- **Building B - Main** - Main electrical meter (building_b_main)
- **Solar Array 1** - Solar panel array (solar_array_1)
- **Battery Storage** - Battery storage system (battery_storage)

### Time Series
- Energy consumption (kWh)
- Power demand (kW)
- Solar generation (kW)
- Battery state of charge (%)
- Temperature readings (°C)
- Cost data (€)

### Time Range
- Historical data: Last 30 days
- Granularity: 15-minute intervals
- Total data points: ~17,280 per series

### Forecasts
- 3 sample forecasts for different series
- 24-hour horizon
- Multiple quantiles (p10, p50, p90)

### Optimizations
- 2 sample optimization runs
- Cost optimization
- Load balancing scenarios

## Data Characteristics

- **Realistic patterns**: Daily and weekly seasonality
- **Peak hours**: 8-10 AM and 6-8 PM
- **Solar generation**: Following sun patterns
- **Random noise**: ±5% variation for realism
- **Special events**: Some weekend and holiday patterns
