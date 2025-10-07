# OMARINO EMS - Demo Data Documentation

## Overview

This document describes the demo data that can be inserted into the OMARINO EMS system for testing and demonstration purposes.

## Contents

The demo data includes:

1. **5 Meters** (Physical and Virtual)
2. **15+ Time Series** (Various measurements)
3. **~10,000 Data Points** (30 days of hourly data)
4. **3 Workflows** (Automated tasks)

---

## 1. Meters (Energy Monitoring Devices)

### 1.1 Main Building - Grid Connection
- **Type**: Electricity Meter
- **Location**: Hauptstraße 123, 10115 Berlin, Germany
- **Purpose**: Monitors grid consumption for main building
- **Sampling**: Every hour (3600 seconds)
- **Timezone**: Europe/Berlin
- **Tags**: building=main, source=grid, category=consumption

### 1.2 Rooftop Solar Array 1
- **Type**: Electricity Meter
- **Location**: Hauptstraße 123, 10115 Berlin, Germany (rooftop)
- **Purpose**: Monitors solar PV production
- **Capacity**: 45 kW peak
- **Sampling**: Every hour
- **Timezone**: Europe/Berlin
- **Tags**: building=main, source=solar, category=production, capacity_kw=45

### 1.3 Building 2 - Consumption
- **Type**: Electricity Meter
- **Location**: Nebenstraße 45, 10115 Berlin, Germany
- **Purpose**: Monitors secondary building consumption
- **Sampling**: Every hour
- **Timezone**: Europe/Berlin
- **Tags**: building=secondary, source=grid, category=consumption

### 1.4 Battery Storage System
- **Type**: Virtual Meter
- **Location**: Hauptstraße 123, 10115 Berlin, Germany
- **Purpose**: Monitors battery state and charging
- **Capacity**: 100 kWh
- **Sampling**: Every 15 minutes (900 seconds)
- **Timezone**: Europe/Berlin
- **Tags**: building=main, type=battery, capacity_kwh=100

### 1.5 Heat Pump
- **Type**: Heat Meter
- **Location**: Hauptstraße 123, 10115 Berlin, Germany
- **Purpose**: Monitors heat pump performance
- **COP**: 3.5 (Coefficient of Performance)
- **Sampling**: Every hour
- **Timezone**: Europe/Berlin
- **Tags**: building=main, type=heatpump, cop=3.5

---

## 2. Time Series Data

### 2.1 Main Building - Grid Connection

#### Active Power (kW)
- **Unit**: kW (Kilowatts)
- **Aggregation**: Mean
- **Pattern**: Realistic consumption pattern
  - Base load: ~20 kW (nighttime)
  - Peak load: ~35 kW (business hours)
  - Daily cycle with noise
- **Data Points**: 720 (30 days × 24 hours)

#### Energy Consumption (kWh)
- **Unit**: kWh (Kilowatt-hours)
- **Aggregation**: Sum
- **Pattern**: Cumulative energy consumption
- **Data Points**: 720

#### Grid Price (EUR/kWh)
- **Unit**: EUR/kWh
- **Aggregation**: Mean
- **Pattern**: Dynamic electricity prices
  - Base: 0.25 EUR/kWh
  - Range: 0.15 - 0.35 EUR/kWh
  - Higher during peak hours
- **Data Points**: 720

### 2.2 Rooftop Solar Array 1

#### Active Power (kW)
- **Unit**: kW
- **Aggregation**: Mean
- **Pattern**: Solar production curve
  - 0 kW during night (18:00-06:00)
  - Peak ~30 kW at noon
  - Realistic solar curve with weather variations
- **Data Points**: 720

#### Energy Production (kWh)
- **Unit**: kWh
- **Aggregation**: Sum
- **Pattern**: Daily production cycle
- **Data Points**: 720

### 2.3 Building 2 - Consumption

#### Active Power (kW)
- **Unit**: kW
- **Aggregation**: Mean
- **Pattern**: 60% of main building consumption
  - Base: ~12 kW
  - Peak: ~21 kW
- **Data Points**: 720

#### Energy Consumption (kWh)
- **Unit**: kWh
- **Aggregation**: Sum
- **Data Points**: 720

### 2.4 Battery Storage System

#### State of Charge (%)
- **Unit**: %
- **Aggregation**: Instant
- **Pattern**: Random between 20-90%
  - Simulates charging/discharging cycles
- **Data Points**: 720

#### Charge Power (kW)
- **Unit**: kW
- **Aggregation**: Mean
- **Pattern**: Positive = charging, Negative = discharging
  - Range: -10 kW to +10 kW
- **Data Points**: 720

### 2.5 Heat Pump

#### Thermal Power (kW)
- **Unit**: kW
- **Aggregation**: Mean
- **Pattern**: Heat output 5-15 kW
- **Data Points**: 720

#### Electric Power (kW)
- **Unit**: kW
- **Aggregation**: Mean
- **Pattern**: Electrical consumption 2-5 kW
- **Data Points**: 720

#### COP (Coefficient of Performance)
- **Unit**: - (dimensionless)
- **Aggregation**: Mean
- **Pattern**: 3.0-4.0 (thermal power / electric power)
- **Data Points**: 720

---

## 3. Workflows (Automated Tasks)

### 3.1 Daily Energy Forecast
- **Schedule**: Daily at midnight (00:00 Europe/Berlin)
- **Status**: Enabled
- **Max Execution Time**: 30 minutes
- **Tasks**:
  1. Fetch Historical Data (last 7 days)
  2. Generate Forecast (next 24 hours using Prophet model)
- **Tags**: forecast, daily, production

### 3.2 Hourly Optimization
- **Schedule**: Every hour (0 * * * *)
- **Status**: Enabled
- **Max Execution Time**: 15 minutes
- **Tasks**:
  1. Fetch Latest Forecast
  2. Fetch Current Prices
  3. Optimize Energy Dispatch (minimize cost, 24-hour horizon)
- **Tags**: optimization, hourly, production

### 3.3 Weekly Report Generation
- **Schedule**: Every Monday at 08:00 (0 8 * * 1)
- **Status**: Disabled (example workflow)
- **Max Execution Time**: 1 hour
- **Tasks**:
  1. Aggregate Weekly Data
  2. Generate Report
- **Tags**: report, weekly

---

## 4. Data Characteristics

### Temporal Coverage
- **Period**: Last 30 days
- **Resolution**: Hourly (3600 seconds)
- **Total Points**: ~10,000 data points across all series

### Realism Features
- **Sine Wave Patterns**: Simulate daily cycles
- **Random Noise**: Add realistic variations (10-20%)
- **Seasonal Patterns**: Solar production follows day/night cycle
- **Non-negative Values**: All power values ≥ 0
- **Coordinated Data**: Battery SOC correlates with charge power

### Data Quality
- All data points marked as "Good" quality
- No missing data gaps
- Consistent timestamps across all series

---

## 5. Usage Instructions

### Insert Demo Data

**Option 1: Using the Shell Script (Recommended)**
```bash
cd scripts
./run-demo-data-insertion.sh
```

**Option 2: Using Python Directly**
```bash
python3 scripts/insert-demo-data.py --host 192.168.75.20 --port 8081
```

**Option 3: Local Development**
```bash
python3 scripts/insert-demo-data.py --host localhost --port 8081
```

### Verify Data Insertion

**Check Meters:**
```bash
curl http://192.168.75.20:8081/api/timeseries/meters | jq .
```

**Check Series:**
```bash
curl http://192.168.75.20:8081/api/timeseries/series | jq .
```

**Query Time Series Data:**
```bash
curl -X POST http://192.168.75.20:8081/api/timeseries/series/query \
  -H "Content-Type: application/json" \
  -d '{"timeRange": "last_7_days"}' | jq .
```

**Check Workflows:**
```bash
curl http://192.168.75.20:8081/api/scheduler/workflows | jq .
```

---

## 6. API Endpoints Reference

### Time Series Service

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/timeseries/meters` | GET | List all meters |
| `/api/timeseries/meters` | POST | Create meter |
| `/api/timeseries/meters/{id}` | GET | Get meter details |
| `/api/timeseries/series` | GET | List all series |
| `/api/timeseries/series` | POST | Create series |
| `/api/timeseries/series/{id}` | GET | Get series details |
| `/api/timeseries/series/{id}/data` | POST | Insert data points |
| `/api/timeseries/series/query` | POST | Query time series data |

### Scheduler Service

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/scheduler/workflows` | GET | List all workflows |
| `/api/scheduler/workflows` | POST | Create workflow |
| `/api/scheduler/workflows/{id}` | GET | Get workflow details |
| `/api/scheduler/workflows/{id}` | PUT | Update workflow |
| `/api/scheduler/workflows/{id}` | DELETE | Delete workflow |
| `/api/scheduler/workflows/{id}/execute` | POST | Trigger workflow execution |
| `/api/scheduler/executions` | GET | List workflow executions |

---

## 7. Visualization Examples

### Expected Patterns

**Main Building Consumption (24-hour cycle):**
```
    35 kW ┤     ╭──╮
          │    ╱    ╲
    20 kW ┤───╯      ╰───
          0   6  12  18  24 (hours)
```

**Solar Production (daily curve):**
```
    30 kW ┤       ╱╲
          │      ╱  ╲
     0 kW ┤─────╯    ╰─────
          0   6  12  18  24 (hours)
```

**Battery State of Charge:**
```
    90% ┤  ╱─╲  ╱─╲
        │ ╱   ╲╱   ╲
    20% ┤╱         ╰─
        0   6  12  18  24 (hours)
```

---

## 8. Troubleshooting

### Common Issues

**Problem**: Script fails with "Connection refused"
- **Solution**: Check if API Gateway is running on port 8081
  ```bash
  curl http://192.168.75.20:8081/health
  ```

**Problem**: "requests module not found"
- **Solution**: Install Python requests library
  ```bash
  python3 -m pip install --user requests
  ```

**Problem**: Workflow creation fails
- **Solution**: Check scheduler service logs
  ```bash
  docker logs omarino-scheduler --tail 50
  ```

**Problem**: Time series data not visible
- **Solution**: Verify database connection and check timeseries service logs
  ```bash
  docker logs omarino-timeseries --tail 50
  ```

---

## 9. Clean Up Demo Data

To remove all demo data:

```bash
# Delete all time series data (keeps meters and series definitions)
curl -X DELETE http://192.168.75.20:8081/api/timeseries/data?all=true

# Delete all workflows
for workflow_id in $(curl -s http://192.168.75.20:8081/api/scheduler/workflows | jq -r '.[] | .id'); do
  curl -X DELETE http://192.168.75.20:8081/api/scheduler/workflows/$workflow_id
done

# Or reset databases completely:
docker exec omarino-postgres psql -U omarino -c "DROP DATABASE omarino_timeseries; CREATE DATABASE omarino_timeseries;"
docker exec omarino-postgres psql -U omarino -c "DROP DATABASE omarino_scheduler; CREATE DATABASE omarino_scheduler;"
docker restart omarino-timeseries omarino-scheduler
```

---

## 10. Next Steps

After inserting demo data:

1. **Explore the Webapp**: http://192.168.75.20:3000
   - View meters and series
   - Query and visualize time series data
   - Monitor workflows

2. **Test Forecasting**:
   ```bash
   curl -X POST http://192.168.75.20:8081/api/forecast/predict \
     -H "Content-Type: application/json" \
     -d '{"seriesId": "<series-id>", "horizon": "24h"}'
   ```

3. **Test Optimization**:
   ```bash
   curl -X POST http://192.168.75.20:8081/api/optimize/solve \
     -H "Content-Type: application/json" \
     -d '{"objective": "minimize_cost", "horizon": "24h"}'
   ```

4. **Trigger Workflows**:
   ```bash
   curl -X POST http://192.168.75.20:8081/api/scheduler/workflows/<workflow-id>/execute
   ```

---

**Last Updated**: October 6, 2025  
**Version**: 1.0  
**Maintainer**: OMARINO Development Team
