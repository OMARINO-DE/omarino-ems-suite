# Feature Engineering Guide

**AI Hub Feature Store**  
**Version**: 0.2.0  
**Last Updated**: October 9, 2025

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Feature Types](#feature-types)
4. [Feature Sets](#feature-sets)
5. [TimescaleDB Integration](#timescaledb-integration)
6. [Online Features](#online-features)
7. [Batch Export](#batch-export)
8. [Creating Custom Features](#creating-custom-features)
9. [Best Practices](#best-practices)
10. [Performance Optimization](#performance-optimization)
11. [Troubleshooting](#troubleshooting)

---

## Overview

The AI Hub Feature Store is a production-ready feature engineering platform that provides:

- **Online Serving**: Low-latency feature retrieval (<50ms) via Redis cache
- **Offline Storage**: Historical features in TimescaleDB with continuous aggregates
- **Batch Export**: Export features to Parquet for training pipelines
- **Feature Sets**: Predefined collections for common ML use cases
- **Graceful Fallback**: Time features always available even when DB is down

### Key Benefits

✅ **Consistent Features**: Same feature logic for training and serving  
✅ **Low Latency**: Redis caching ensures <50ms response times  
✅ **Scalable**: TimescaleDB handles billions of data points  
✅ **Efficient**: Continuous aggregates precompute expensive operations  
✅ **Reliable**: Fallback mechanisms ensure high availability  

---

## Architecture

### Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Online Layer (Redis)                    │
│  • Cache: tenant_id:asset_id:timestamp                  │
│  • TTL: 5 minutes                                        │
│  • Latency: 5-10ms (cache hit)                          │
│  • Use case: Real-time inference                        │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│               Offline Layer (TimescaleDB)                │
│  • Continuous Aggregates: hourly_features, daily_features│
│  • Materialized Views: forecast_*, anomaly_*            │
│  • SQL Functions: get_lag_features, get_rolling_features│
│  • Latency: 45-95ms (cache miss + DB query)             │
│  • Use case: Historical analysis, training data         │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                 Batch Layer (Parquet)                    │
│  • Format: Parquet with snappy compression              │
│  • Metadata: feature_exports table                      │
│  • Latency: 30-60s per million rows                     │
│  • Use case: Model training, offline analysis           │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

```
Raw Data → TimescaleDB Hypertable
    ↓
Continuous Aggregate (hourly refresh)
    ↓
Materialized View (forecast_basic_features)
    ↓
Feature Computation (FeatureStore)
    ↓
Redis Cache (5-minute TTL)
    ↓
Model Inference
```

---

## Feature Types

### 1. Time Features (Always Available)

Computed from timestamp without requiring any data:

| Feature | Type | Range | Description |
|---------|------|-------|-------------|
| `hour_of_day` | int | 0-23 | Hour of day in UTC |
| `day_of_week` | int | 0-6 | Monday=0, Sunday=6 |
| `day_of_month` | int | 1-31 | Day of month |
| `month` | int | 1-12 | Month of year |
| `is_weekend` | bool | 0-1 | Saturday or Sunday |
| `is_business_hours` | bool | 0-1 | 9am-5pm weekdays |

**Use Cases:**
- Basic forecasting
- Seasonal patterns
- Business rules
- Fallback when DB unavailable

**Example:**
```python
# These features are always available
features = await feature_store.get_features(
    tenant_id="tenant-123",
    asset_id="meter-001",
    timestamp=datetime(2025, 10, 9, 14, 30, 0, tzinfo=timezone.utc)
)
# Returns: {hour_of_day: 14, day_of_week: 3, is_weekend: 0, ...}
```

### 2. Statistical Features (TimescaleDB)

Computed from historical data using continuous aggregates:

| Feature | Type | Window | Description |
|---------|------|--------|-------------|
| `hourly_avg` | float | 1 hour | Average value in hour |
| `hourly_min` | float | 1 hour | Minimum value in hour |
| `hourly_max` | float | 1 hour | Maximum value in hour |
| `hourly_stddev` | float | 1 hour | Standard deviation in hour |
| `hourly_count` | int | 1 hour | Data point count |
| `daily_avg` | float | 1 day | Average value in day |
| `daily_min` | float | 1 day | Minimum value in day |
| `daily_max` | float | 1 day | Maximum value in day |
| `daily_stddev` | float | 1 day | Standard deviation in day |

**Query:**
```sql
SELECT 
    hourly_avg, hourly_min, hourly_max, hourly_stddev, hourly_count
FROM hourly_features
WHERE tenant_id = 'tenant-123'
  AND asset_id = 'meter-001'
  AND bucket = '2025-10-09 14:00:00'::timestamptz;
```

### 3. Lag Features (SQL Functions)

Historical values at specific time lags:

| Feature | Lag | Description |
|---------|-----|-------------|
| `lag_1h` | 1 hour | Value 1 hour ago |
| `lag_24h` | 24 hours | Value 1 day ago |
| `lag_168h` | 168 hours | Value 1 week ago |

**SQL Function:**
```sql
CREATE OR REPLACE FUNCTION get_lag_features(
    p_tenant_id TEXT,
    p_asset_id TEXT,
    p_timestamp TIMESTAMPTZ,
    p_lags INT[]
)
RETURNS TABLE(lag_value NUMERIC) AS $$
BEGIN
    RETURN QUERY
    SELECT avg(value)
    FROM ai_features
    WHERE tenant_id = p_tenant_id
      AND asset_id = p_asset_id
      AND timestamp IN (
          SELECT p_timestamp - (lag_hours * INTERVAL '1 hour')
          FROM unnest(p_lags) AS lag_hours
      )
    GROUP BY timestamp
    ORDER BY timestamp DESC;
END;
$$ LANGUAGE plpgsql;
```

**Usage:**
```python
# Get lag features via FeatureStore
features = await feature_store.get_features(
    tenant_id="tenant-123",
    asset_id="meter-001",
    timestamp=datetime.now(timezone.utc)
)
# Returns: {lag_1h: 43.5, lag_24h: 44.8, lag_168h: 42.3}
```

### 4. Rolling Window Features (SQL Functions)

Statistical aggregates over sliding time windows:

| Feature | Window | Description |
|---------|--------|-------------|
| `rolling_avg_24h` | 24 hours | Average over 24 hours |
| `rolling_std_24h` | 24 hours | Std dev over 24 hours |
| `rolling_min_24h` | 24 hours | Min value over 24 hours |
| `rolling_max_24h` | 24 hours | Max value over 24 hours |
| `rolling_avg_168h` | 168 hours | Average over 1 week |
| `rolling_std_168h` | 168 hours | Std dev over 1 week |

**SQL Function:**
```sql
CREATE OR REPLACE FUNCTION get_rolling_features(
    p_tenant_id TEXT,
    p_asset_id TEXT,
    p_timestamp TIMESTAMPTZ,
    p_window_hours INT
)
RETURNS TABLE(
    rolling_avg NUMERIC,
    rolling_stddev NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        avg(value), 
        stddev(value)
    FROM ai_features
    WHERE tenant_id = p_tenant_id
      AND asset_id = p_asset_id
      AND timestamp BETWEEN 
          (p_timestamp - (p_window_hours * INTERVAL '1 hour')) 
          AND p_timestamp;
END;
$$ LANGUAGE plpgsql;
```

### 5. Weather Features (External Data)

Weather data integrated from weather_features table:

| Feature | Type | Unit | Description |
|---------|------|------|-------------|
| `temperature` | float | °C | Temperature |
| `humidity` | float | % | Relative humidity |
| `solar_irradiance` | float | W/m² | Solar radiation |
| `wind_speed` | float | m/s | Wind speed |
| `cloud_cover` | float | % | Cloud coverage |
| `precipitation` | float | mm | Precipitation |

**Query:**
```sql
SELECT 
    temperature, humidity, solar_irradiance, wind_speed
FROM weather_features
WHERE tenant_id = 'tenant-123'
  AND asset_id = 'meter-001'
  AND timestamp <= '2025-10-09 14:00:00'::timestamptz
ORDER BY timestamp DESC
LIMIT 1;
```

---

## Feature Sets

Pre-configured feature collections for common use cases.

### forecast_basic (6 features)

**Purpose**: Basic load and generation forecasting

**Features:**
- `hour_of_day` (time)
- `day_of_week` (time)
- `is_weekend` (time)
- `lag_1h` (lag)
- `lag_24h` (lag)
- `rolling_avg_24h` (rolling)

**Performance:**
- Latency: <50ms (cache hit), <80ms (cache miss)
- Storage: Redis + hourly_features aggregate

**Use Cases:**
- Short-term load forecasting (1-24 hours)
- Generation forecasting (solar, wind)
- Basic demand prediction

**API Usage:**
```bash
curl -X POST http://ai-hub:8003/ai/features/get \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-123",
    "asset_id": "meter-001",
    "feature_set": "forecast_basic"
  }'
```

**Python Usage:**
```python
features = await feature_store.compute_feature_set(
    tenant_id="tenant-123",
    asset_id="meter-001",
    feature_set_name="forecast_basic"
)
```

### forecast_advanced (13 features)

**Purpose**: Advanced forecasting with weather and market data

**Features:**
- All `forecast_basic` features (6)
- `day_of_month` (time)
- `month` (time)
- `is_business_hours` (time)
- `lag_168h` (lag)
- `rolling_std_24h` (rolling)
- `temperature` (weather)
- `humidity` (weather)

**Performance:**
- Latency: <100ms (cache hit), <150ms (cache miss)
- Storage: Redis + daily_features + weather_features

**Use Cases:**
- Long-term forecasting (1-7 days)
- Price prediction (electricity markets)
- Weather-dependent load forecasting
- Renewable energy forecasting

**API Usage:**
```bash
curl -X POST http://ai-hub:8003/ai/features/get \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-123",
    "asset_id": "meter-001",
    "feature_set": "forecast_advanced"
  }'
```

### anomaly_detection (7 features)

**Purpose**: Identify outliers and anomalies in time series

**Features:**
- `hour_of_day` (time)
- `day_of_week` (time)
- `historical_avg_24h` (statistical)
- `historical_std_24h` (statistical)
- `max_24h` (statistical)
- `min_24h` (statistical)
- `range_24h` (statistical)

**Performance:**
- Latency: <50ms
- Storage: TimescaleDB materialized view

**Use Cases:**
- Real-time anomaly detection
- Outlier identification
- Data quality monitoring
- Fraud detection

**API Usage:**
```bash
curl -X POST http://ai-hub:8003/ai/features/get \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-123",
    "asset_id": "meter-001",
    "feature_set": "anomaly_detection"
  }'
```

---

## TimescaleDB Integration

### Database Objects

#### 1. Hypertables

**timeseries_data** (raw data, 7-day retention):
```sql
CREATE TABLE timeseries_data (
    timestamp TIMESTAMPTZ NOT NULL,
    tenant_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    value NUMERIC NOT NULL,
    quality INTEGER DEFAULT 1
);

SELECT create_hypertable('timeseries_data', 'timestamp');

-- Retention policy: 7 days
SELECT add_retention_policy('timeseries_data', INTERVAL '7 days');
```

**ai_features** (computed features, 90-day retention):
```sql
CREATE TABLE ai_features (
    timestamp TIMESTAMPTZ NOT NULL,
    tenant_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    value NUMERIC NOT NULL,
    feature_type TEXT NOT NULL
);

SELECT create_hypertable('ai_features', 'timestamp');

-- Retention policy: 90 days
SELECT add_retention_policy('ai_features', INTERVAL '90 days');
```

**weather_features** (weather data, 1-year retention):
```sql
CREATE TABLE weather_features (
    timestamp TIMESTAMPTZ NOT NULL,
    tenant_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    temperature NUMERIC,
    humidity NUMERIC,
    solar_irradiance NUMERIC,
    wind_speed NUMERIC
);

SELECT create_hypertable('weather_features', 'timestamp');

-- Retention policy: 1 year
SELECT add_retention_policy('weather_features', INTERVAL '365 days');
```

#### 2. Continuous Aggregates

**hourly_features** (refresh hourly):
```sql
CREATE MATERIALIZED VIEW hourly_features
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', timestamp) AS bucket,
    tenant_id,
    asset_id,
    avg(value) AS hourly_avg,
    min(value) AS hourly_min,
    max(value) AS hourly_max,
    stddev(value) AS hourly_stddev,
    count(*) AS hourly_count
FROM ai_features
GROUP BY bucket, tenant_id, asset_id
WITH NO DATA;

-- Refresh policy: hourly
SELECT add_continuous_aggregate_policy('hourly_features',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);

-- Retention policy: 1 year
SELECT add_retention_policy('hourly_features', INTERVAL '365 days');
```

**daily_features** (refresh daily):
```sql
CREATE MATERIALIZED VIEW daily_features
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', timestamp) AS bucket,
    tenant_id,
    asset_id,
    avg(value) AS daily_avg,
    min(value) AS daily_min,
    max(value) AS daily_max,
    stddev(value) AS daily_stddev,
    count(*) AS daily_count
FROM ai_features
GROUP BY bucket, tenant_id, asset_id
WITH NO DATA;

-- Refresh policy: daily
SELECT add_continuous_aggregate_policy('daily_features',
    start_offset => INTERVAL '2 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day'
);

-- Retention policy: 2 years
SELECT add_retention_policy('daily_features', INTERVAL '730 days');
```

#### 3. Materialized Views

**forecast_basic_features**:
```sql
CREATE MATERIALIZED VIEW forecast_basic_features AS
SELECT 
    af.timestamp,
    af.tenant_id,
    af.asset_id,
    af.value,
    hf.hourly_avg,
    LAG(af.value, 1) OVER (PARTITION BY af.tenant_id, af.asset_id ORDER BY af.timestamp) AS lag_1h,
    LAG(af.value, 24) OVER (PARTITION BY af.tenant_id, af.asset_id ORDER BY af.timestamp) AS lag_24h,
    AVG(af.value) OVER (
        PARTITION BY af.tenant_id, af.asset_id 
        ORDER BY af.timestamp 
        ROWS BETWEEN 24 PRECEDING AND CURRENT ROW
    ) AS rolling_avg_24h
FROM ai_features af
LEFT JOIN hourly_features hf 
    ON time_bucket('1 hour', af.timestamp) = hf.bucket
    AND af.tenant_id = hf.tenant_id
    AND af.asset_id = hf.asset_id;

-- Refresh manually or via cron
REFRESH MATERIALIZED VIEW forecast_basic_features;
```

#### 4. SQL Functions

See [Feature Types](#feature-types) section for `get_lag_features()` and `get_rolling_features()` implementations.

### Migration

Run the migration to create all database objects:

```bash
cd ai-hub
psql -U omarino -d omarino_db -f migrations/001_create_feature_views.sql
```

Verify:
```sql
-- Check hypertables
SELECT * FROM timescaledb_information.hypertables;

-- Check continuous aggregates
SELECT * FROM timescaledb_information.continuous_aggregates;

-- Check functions
\df get_lag_features
\df get_rolling_features
```

---

## Online Features

### Redis Caching Strategy

**Cache Key Format:**
```
features:{tenant_id}:{asset_id}:{timestamp}
```

**Example:**
```
features:tenant-123:meter-001:2025-10-09T14:00:00Z
```

**TTL:** 5 minutes (300 seconds)

**Cache Hit Flow:**
```
1. Client requests features
2. Generate cache key
3. Check Redis
   ├─ Cache Hit → Return cached features (5-10ms)
   └─ Cache Miss ↓
4. Compute features from TimescaleDB (45-95ms)
5. Store in Redis with TTL=300s
6. Return features to client
```

### Python Implementation

```python
import redis
import json
from datetime import datetime, timezone

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    password=os.getenv("REDIS_PASSWORD"),
    decode_responses=True
)

async def get_features_cached(
    tenant_id: str,
    asset_id: str,
    timestamp: datetime
) -> dict:
    """Get features with Redis caching"""
    
    # Generate cache key
    ts_str = timestamp.isoformat()
    cache_key = f"features:{tenant_id}:{asset_id}:{ts_str}"
    
    # Try cache
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Cache miss: compute features
    features = await compute_features(tenant_id, asset_id, timestamp)
    
    # Store in cache (TTL=5 minutes)
    redis_client.setex(
        cache_key,
        300,  # TTL in seconds
        json.dumps(features)
    )
    
    return features
```

### Cache Warming

Pre-load features for known assets:

```python
async def warm_feature_cache(tenant_id: str, asset_ids: list[str]):
    """Warm Redis cache for multiple assets"""
    now = datetime.now(timezone.utc)
    
    for asset_id in asset_ids:
        features = await compute_features(tenant_id, asset_id, now)
        cache_key = f"features:{tenant_id}:{asset_id}:{now.isoformat()}"
        redis_client.setex(cache_key, 300, json.dumps(features))
    
    print(f"Warmed cache for {len(asset_ids)} assets")
```

### Cache Invalidation

Invalidate cache when data changes:

```python
def invalidate_feature_cache(tenant_id: str, asset_id: str):
    """Invalidate all cached features for an asset"""
    pattern = f"features:{tenant_id}:{asset_id}:*"
    
    for key in redis_client.scan_iter(match=pattern):
        redis_client.delete(key)
    
    print(f"Invalidated cache for {tenant_id}:{asset_id}")
```

---

## Batch Export

### Parquet Export

Export features to Parquet for training pipelines:

**API Request:**
```bash
curl -X POST http://ai-hub:8003/ai/features/export \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-123",
    "feature_set": "forecast_basic",
    "start_time": "2024-01-01T00:00:00Z",
    "end_time": "2024-12-31T23:59:59Z",
    "asset_ids": ["meter-001", "meter-002"],
    "output_path": "./exports/training_features.parquet"
  }'
```

**Response:**
```json
{
  "export_id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "tenant-123",
  "feature_set": "forecast_basic",
  "status": "completed",
  "storage_path": "./exports/tenant-123_forecast_basic_550e8400.parquet",
  "row_count": 876000,
  "file_size_mb": 42.5,
  "started_at": "2025-10-09T14:00:00Z",
  "completed_at": "2025-10-09T14:02:15Z"
}
```

### Python Implementation

```python
import pandas as pd
from sqlalchemy import text

async def export_features_to_parquet(
    tenant_id: str,
    feature_set: str,
    start_time: datetime,
    end_time: datetime,
    output_path: str,
    asset_ids: list[str] = None
) -> dict:
    """Export features to Parquet file"""
    
    # Query features from materialized view
    query = f"""
        SELECT 
            timestamp, tenant_id, asset_id,
            hour_of_day, day_of_week, is_weekend,
            lag_1h, lag_24h, rolling_avg_24h
        FROM {feature_set}_features
        WHERE tenant_id = :tenant_id
          AND timestamp BETWEEN :start_time AND :end_time
    """
    
    if asset_ids:
        query += " AND asset_id = ANY(:asset_ids)"
    
    # Execute query
    result = await db_session.execute(
        text(query),
        {
            "tenant_id": tenant_id,
            "start_time": start_time,
            "end_time": end_time,
            "asset_ids": asset_ids
        }
    )
    
    # Convert to DataFrame
    df = pd.DataFrame(result.fetchall(), columns=result.keys())
    
    if df.empty:
        return {"status": "no_data", "row_count": 0}
    
    # Write to Parquet
    df.to_parquet(
        output_path,
        compression="snappy",
        index=False
    )
    
    file_size = os.path.getsize(output_path)
    
    # Track in feature_exports table
    export_id = str(uuid.uuid4())
    await db_session.execute(
        text("""
            INSERT INTO feature_exports 
            (export_id, tenant_id, feature_set, status, row_count, file_size_bytes, storage_path)
            VALUES (:export_id, :tenant_id, :feature_set, 'completed', :row_count, :file_size, :storage_path)
        """),
        {
            "export_id": export_id,
            "tenant_id": tenant_id,
            "feature_set": feature_set,
            "row_count": len(df),
            "file_size": file_size,
            "storage_path": output_path
        }
    )
    
    await db_session.commit()
    
    return {
        "export_id": export_id,
        "status": "completed",
        "row_count": len(df),
        "file_size_bytes": file_size,
        "storage_path": output_path
    }
```

### Reading Parquet Files

```python
import pandas as pd

# Read exported features
df = pd.read_parquet("./exports/training_features.parquet")

print(f"Loaded {len(df)} rows")
print(f"Columns: {df.columns.tolist()}")
print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

# Use for training
X = df[['hour_of_day', 'lag_1h', 'lag_24h', 'rolling_avg_24h']]
y = df['value']
```

---

## Creating Custom Features

### 1. Add to TimescaleDB

Create a new materialized view:

```sql
CREATE MATERIALIZED VIEW my_custom_features AS
SELECT 
    af.timestamp,
    af.tenant_id,
    af.asset_id,
    af.value,
    -- Custom feature logic
    CASE 
        WHEN EXTRACT(DOW FROM af.timestamp) IN (0, 6) THEN 1
        ELSE 0
    END AS is_weekend_custom,
    -- Use window functions
    AVG(af.value) OVER (
        PARTITION BY af.tenant_id, af.asset_id
        ORDER BY af.timestamp
        ROWS BETWEEN 48 PRECEDING AND CURRENT ROW
    ) AS rolling_avg_48h
FROM ai_features af;

-- Refresh schedule
CREATE INDEX idx_custom_features ON my_custom_features(tenant_id, asset_id, timestamp);
```

### 2. Update FeatureStore

Add custom feature set to `app/services/feature_store.py`:

```python
FEATURE_SETS = {
    # Existing feature sets...
    
    "my_custom_set": {
        "name": "my_custom_set",
        "description": "Custom features for specific use case",
        "features": [
            "hour_of_day",
            "is_weekend_custom",
            "rolling_avg_48h"
        ],
        "use_cases": ["custom_forecasting"],
        "latency": "<100ms",
        "storage": "timescaledb"
    }
}

async def _compute_my_custom_features(
    self,
    tenant_id: str,
    asset_id: str,
    timestamp: datetime
) -> dict:
    """Compute custom features"""
    
    query = text("""
        SELECT 
            is_weekend_custom,
            rolling_avg_48h
        FROM my_custom_features
        WHERE tenant_id = :tenant_id
          AND asset_id = :asset_id
          AND timestamp = :timestamp
    """)
    
    result = await self.db_session.execute(
        query,
        {"tenant_id": tenant_id, "asset_id": asset_id, "timestamp": timestamp}
    )
    
    row = result.fetchone()
    if row:
        return {
            "is_weekend_custom": row.is_weekend_custom,
            "rolling_avg_48h": float(row.rolling_avg_48h) if row.rolling_avg_48h else 0.0
        }
    
    return {}
```

### 3. Use Custom Feature Set

```python
features = await feature_store.compute_feature_set(
    tenant_id="tenant-123",
    asset_id="meter-001",
    feature_set_name="my_custom_set"
)
```

---

## Best Practices

### 1. Feature Selection

✅ **DO:**
- Start with `forecast_basic` (6 features) for simple models
- Add features incrementally based on importance
- Monitor feature importance with SHAP values
- Remove low-importance features to reduce latency

❌ **DON'T:**
- Use all features by default (increases latency)
- Add features without validating importance
- Forget to update feature sets when model changes

### 2. Cache Management

✅ **DO:**
- Use Redis caching for online inference
- Set appropriate TTL (5 minutes for features)
- Warm cache for high-traffic assets
- Monitor cache hit rate

❌ **DON'T:**
- Set TTL too high (stale features)
- Set TTL too low (increased DB load)
- Cache features longer than needed

### 3. Performance Optimization

✅ **DO:**
- Use continuous aggregates for expensive queries
- Create indexes on tenant_id, asset_id, timestamp
- Batch export for training (10-100x faster than API)
- Use Parquet with snappy compression

❌ **DON'T:**
- Query raw hypertable for aggregates
- Run expensive computations in API endpoint
- Export features via API for training

### 4. Data Quality

✅ **DO:**
- Handle missing values gracefully (return 0 or mean)
- Validate feature ranges (e.g., hour_of_day: 0-23)
- Monitor feature distributions for drift
- Log feature computation errors

❌ **DON'T:**
- Fail silently when features missing
- Allow null values in production
- Ignore feature drift warnings

### 5. Versioning

✅ **DO:**
- Version feature sets with models
- Document feature changes in metadata
- Test feature changes with A/B tests
- Maintain backward compatibility

❌ **DON'T:**
- Change feature logic without versioning
- Remove features still used by production models
- Deploy feature changes without testing

---

## Performance Optimization

### Query Optimization

**Use Continuous Aggregates:**
```sql
-- GOOD: Query continuous aggregate
SELECT hourly_avg FROM hourly_features
WHERE tenant_id = 'tenant-123' AND asset_id = 'meter-001';

-- BAD: Query raw hypertable
SELECT avg(value) FROM ai_features
WHERE tenant_id = 'tenant-123' AND asset_id = 'meter-001'
GROUP BY time_bucket('1 hour', timestamp);
```

**Use Indexes:**
```sql
-- Create composite index
CREATE INDEX idx_features_composite 
ON ai_features(tenant_id, asset_id, timestamp DESC);

-- Verify index usage
EXPLAIN ANALYZE
SELECT * FROM ai_features
WHERE tenant_id = 'tenant-123' AND asset_id = 'meter-001';
```

### Caching Strategy

**Optimize Cache Keys:**
- Truncate timestamp to nearest minute/hour
- Group similar timestamps together
- Reduce cache key cardinality

**Example:**
```python
# GOOD: Truncate to hour
timestamp_key = timestamp.replace(minute=0, second=0, microsecond=0)

# BAD: Use exact timestamp
timestamp_key = timestamp  # Too many unique keys
```

### Batch Operations

**Bulk Feature Retrieval:**
```python
# GOOD: Batch query
asset_ids = ["meter-001", "meter-002", "meter-003"]
features = await feature_store.get_batch_features(
    tenant_id="tenant-123",
    asset_ids=asset_ids,
    feature_set_name="forecast_basic"
)

# BAD: Individual queries
for asset_id in asset_ids:
    features = await feature_store.get_features(...)  # N queries
```

---

## Troubleshooting

### Issue: Features not caching

**Symptoms:**
- High DB load
- Slow feature retrieval (>100ms)
- Redis shows 0% hit rate

**Solutions:**
1. Check Redis connection:
   ```bash
   redis-cli -h localhost -p 6379 ping
   ```

2. Verify TTL:
   ```bash
   redis-cli -h localhost -p 6379
   > KEYS features:*
   > TTL features:tenant-123:meter-001:2025-10-09T14:00:00Z
   ```

3. Check cache key format:
   - Ensure timestamps are consistent
   - Verify tenant_id and asset_id format

### Issue: Slow feature computation

**Symptoms:**
- Feature retrieval >200ms
- TimescaleDB high CPU
- Query timeouts

**Solutions:**
1. Check continuous aggregate refresh:
   ```sql
   SELECT * FROM timescaledb_information.continuous_aggregates;
   ```

2. Verify indexes:
   ```sql
   \d+ ai_features  -- Check indexes
   ```

3. Analyze query plan:
   ```sql
   EXPLAIN ANALYZE
   SELECT * FROM hourly_features WHERE ...;
   ```

### Issue: Missing features

**Symptoms:**
- Features return null/0
- Incomplete feature dictionaries
- DB queries return empty

**Solutions:**
1. Check data availability:
   ```sql
   SELECT count(*) FROM ai_features
   WHERE tenant_id = 'tenant-123' AND asset_id = 'meter-001';
   ```

2. Verify continuous aggregate data:
   ```sql
   SELECT * FROM hourly_features
   WHERE tenant_id = 'tenant-123'
   ORDER BY bucket DESC LIMIT 10;
   ```

3. Check retention policies:
   ```sql
   SELECT * FROM timescaledb_information.jobs
   WHERE proc_name LIKE '%retention%';
   ```

### Issue: Export fails

**Symptoms:**
- Parquet export returns 500 error
- Export status stuck in "processing"
- File size is 0 bytes

**Solutions:**
1. Check disk space:
   ```bash
   df -h
   ```

2. Verify export permissions:
   ```bash
   ls -la ./exports/
   ```

3. Check export logs:
   ```bash
   docker logs ai-hub | grep "export_features_to_parquet"
   ```

4. Verify time range:
   - start_time < end_time
   - Data exists in time range

---

## Additional Resources

- [AI Hub API Documentation](./ai-hub.md)
- [TimescaleDB Continuous Aggregates](https://docs.timescale.com/use-timescale/latest/continuous-aggregates/)
- [Parquet Format](https://parquet.apache.org/docs/)
- [Redis Caching Patterns](https://redis.io/docs/manual/patterns/)

---

**Questions?** See [AI Hub README](../../ai-hub/README.md) or open an issue.
