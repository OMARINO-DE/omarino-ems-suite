# Task 2: Feature Store + Model Registry - Quick Start

This guide covers the new features added in Task 2: production-ready feature engineering and ML model lifecycle management.

---

## 🎯 What's New

### Feature Store
- **TimescaleDB Integration**: Continuous aggregates for high-performance feature computation
- **Online Features**: Redis-cached features with <100ms latency
- **Offline Features**: Historical data from TimescaleDB for training
- **Parquet Export**: Batch export for offline training jobs
- **Predefined Feature Sets**: `forecast_basic`, `forecast_advanced`, `anomaly_detection`

### Model Registry
- **S3/MinIO Storage**: Scalable model artifact storage
- **Version Management**: Semantic versioning with metadata
- **Lifecycle Management**: staging → production → archived workflow
- **Metrics Tracking**: Performance metrics (RMSE, MAE, accuracy, etc.)
- **Model Discovery**: List and filter models by tenant, name, stage

---

## 🚀 Quick Start

### 1. Start MinIO (Object Storage)

Add to `docker-compose.yml`:

```yaml
minio:
  image: minio/minio:latest
  container_name: omarino-minio
  command: server /data --console-address ":9001"
  environment:
    - MINIO_ROOT_USER=minioadmin
    - MINIO_ROOT_PASSWORD=minioadmin
  ports:
    - "9000:9000"   # API
    - "9001:9001"   # Console
  volumes:
    - minio-data:/data
  networks:
    - omarino-network
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
    interval: 30s
    timeout: 10s
    retries: 3

volumes:
  minio-data:
```

Start MinIO:
```bash
docker-compose up -d minio
```

Access MinIO Console: http://localhost:9001 (minioadmin/minioadmin)

### 2. Run Database Migration

Apply TimescaleDB feature views:

```bash
docker exec -i omarino-postgres psql -U omarino -d omarino_db < ai-hub/migrations/001_create_feature_views.sql
```

Verify installation:
```sql
-- Check tables
\dt ai_features
\dt weather_features
\dt feature_exports

-- Check materialized views
\d hourly_features
\d daily_features
\d forecast_basic_features
\d anomaly_detection_features

-- Check functions
\df get_lag_features
\df get_rolling_features
```

### 3. Update Environment Variables

Update your `.env`:

```bash
# MinIO Configuration
MINIO_ENDPOINT_URL=http://minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MODEL_STORAGE_BUCKET=ml-models

# Feature Store
FEATURE_CACHE_TTL=300
EXPORT_STORAGE_PATH=/app/exports

# Model Configuration
MODEL_CACHE_SIZE=5
MODEL_CACHE_TTL=3600
```

### 4. Restart AI Hub Service

```bash
docker-compose restart ai-hub

# Check logs
docker-compose logs -f ai-hub
```

---

## 📚 API Examples

### Feature Store

#### 1. Get Features for Online Inference

```bash
curl -X POST http://localhost:8003/ai/features/get \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-123",
    "asset_id": "meter-001",
    "feature_set": "forecast_basic",
    "lookback_hours": 168
  }'
```

Response:
```json
{
  "tenant_id": "tenant-123",
  "asset_id": "meter-001",
  "timestamp": "2025-10-09T12:00:00Z",
  "features": {
    "hour_of_day": 12,
    "day_of_week": 2,
    "is_weekend": 0,
    "hourly_avg": 45.2,
    "hourly_std": 5.8,
    "lag_1h": 43.5,
    "lag_24h": 44.8,
    "lag_168h": 45.1,
    "rolling_24h_avg": 44.9,
    "rolling_24h_std": 6.1
  },
  "feature_count": 10,
  "computed_at": "2025-10-09T12:00:01Z"
}
```

#### 2. Export Features to Parquet

```bash
curl -X POST http://localhost:8003/ai/features/export \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-123",
    "feature_set": "forecast_basic",
    "start_time": "2024-01-01T00:00:00Z",
    "end_time": "2024-12-31T23:59:59Z",
    "asset_ids": ["meter-001", "meter-002", "meter-003"]
  }'
```

Response:
```json
{
  "export_id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "tenant-123",
  "feature_set": "forecast_basic",
  "status": "completed",
  "storage_path": "./exports/tenant-123_forecast_basic_550e8400.parquet",
  "row_count": 876000,
  "file_size_bytes": 44564480,
  "file_size_mb": 42.5,
  "message": "Exported 876000 rows to ./exports/..."
}
```

#### 3. List Available Feature Sets

```bash
curl http://localhost:8003/ai/features/sets
```

Response:
```json
{
  "feature_sets": {
    "forecast_basic": {
      "name": "forecast_basic",
      "description": "Basic features for time series forecasting",
      "features": [
        "hour_of_day", "day_of_week", "is_weekend",
        "historical_avg_24h", "lag_1h", "lag_24h"
      ],
      "use_cases": ["Load forecasting", "Generation forecasting"],
      "latency": "< 50ms (online cache)",
      "storage": "TimescaleDB + Redis"
    },
    "forecast_advanced": {
      "features": [...13 features...],
      "latency": "< 100ms"
    },
    "anomaly_detection": {
      "features": [...7 features...],
      "latency": "< 50ms"
    }
  }
}
```

### Model Registry

#### 1. Register a New Model

```bash
curl -X POST http://localhost:8003/ai/models/register \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-123",
    "model_name": "forecast_lgb",
    "version": "v1.0.0",
    "metadata": {
      "model_type": "LightGBM",
      "framework": "lightgbm",
      "hyperparameters": {
        "num_leaves": 31,
        "learning_rate": 0.05,
        "n_estimators": 100
      },
      "feature_names": ["hour", "temp", "humidity", "lag_24h"],
      "description": "Production load forecasting model"
    },
    "metrics": {
      "rmse": 2.5,
      "mae": 1.8,
      "r2_score": 0.92,
      "mape": 4.2
    },
    "stage": "staging"
  }'
```

Response:
```json
{
  "model_id": "tenant-123:forecast_lgb:v1.0.0",
  "model_name": "forecast_lgb",
  "version": "v1.0.0",
  "stage": "staging",
  "status": "registered",
  "message": "Model forecast_lgb vv1.0.0 registered successfully",
  "uploaded_at": "2025-10-09T12:00:00Z"
}
```

#### 2. Get Model Details

```bash
curl http://localhost:8003/ai/models/tenant-123:forecast_lgb:v1.0.0
```

Response:
```json
{
  "model_id": "tenant-123:forecast_lgb:v1.0.0",
  "tenant_id": "tenant-123",
  "model_name": "forecast_lgb",
  "version": "v1.0.0",
  "stage": "staging",
  "metadata": {
    "model_type": "LightGBM",
    "hyperparameters": {...},
    "feature_names": [...],
    "registered_at": "2025-10-09T12:00:00Z"
  },
  "metrics": {
    "rmse": 2.5,
    "mae": 1.8,
    "r2_score": 0.92
  },
  "uploaded_at": "2025-10-09T12:00:00Z",
  "model_size_bytes": 1048576,
  "model_type": "LightGBM"
}
```

#### 3. List Models

```bash
# List all models for a tenant
curl "http://localhost:8003/ai/models/?tenant_id=tenant-123"

# List production models only
curl "http://localhost:8003/ai/models/?stage=production"

# List specific model versions
curl "http://localhost:8003/ai/models/?tenant_id=tenant-123&model_name=forecast_lgb"
```

#### 4. Promote Model to Production

```bash
curl -X PUT http://localhost:8003/ai/models/tenant-123:forecast_lgb:v1.0.0/promote \
  -H "Content-Type: application/json" \
  -d '{
    "target_stage": "production",
    "reason": "Passed validation tests, 5% improvement in RMSE over v0.9.0"
  }'
```

Response:
```json
{
  "model_id": "tenant-123:forecast_lgb:v1.0.0",
  "model_name": "forecast_lgb",
  "version": "v1.0.0",
  "previous_stage": "staging",
  "current_stage": "production",
  "promoted_at": "2025-10-09T12:05:00Z",
  "message": "Model promoted from staging to production"
}
```

#### 5. Delete Model

```bash
# Delete archived model (safe)
curl -X DELETE http://localhost:8003/ai/models/tenant-123:forecast_lgb:v0.9.0

# Force delete any model (use with caution!)
curl -X DELETE "http://localhost:8003/ai/models/tenant-123:forecast_lgb:v1.0.0?force=true"
```

---

## 🔧 Integration with Training Pipeline

### Example: Train and Register Model

```python
import lightgbm as lgb
import requests
import joblib
from datetime import datetime

# 1. Export training data
export_response = requests.post(
    "http://localhost:8003/ai/features/export",
    json={
        "tenant_id": "tenant-123",
        "feature_set": "forecast_advanced",
        "start_time": "2024-01-01T00:00:00Z",
        "end_time": "2024-11-30T23:59:59Z"
    }
)
export_data = export_response.json()
parquet_path = export_data["storage_path"]

# 2. Load features
import pandas as pd
df = pd.read_parquet(parquet_path)

# 3. Train model
X = df[["hour_of_day", "temperature", "lag_24h", "rolling_24h_avg"]]
y = df["target"]

model = lgb.LGBMRegressor(num_leaves=31, learning_rate=0.05)
model.fit(X, y)

# 4. Evaluate
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
y_pred = model.predict(X)
rmse = mean_squared_error(y, y_pred, squared=False)
mae = mean_absolute_error(y, y_pred)
r2 = r2_score(y, y_pred)

# 5. Register model
version = datetime.now().strftime("v%Y%m%d-%H%M%S")

register_response = requests.post(
    "http://localhost:8003/ai/models/register",
    json={
        "tenant_id": "tenant-123",
        "model_name": "forecast_lgb",
        "version": version,
        "metadata": {
            "model_type": "LightGBM",
            "framework": "lightgbm",
            "hyperparameters": model.get_params(),
            "feature_names": X.columns.tolist(),
            "training_samples": len(X),
            "training_date_range": {
                "start": "2024-01-01",
                "end": "2024-11-30"
            }
        },
        "metrics": {
            "rmse": float(rmse),
            "mae": float(mae),
            "r2_score": float(r2)
        },
        "stage": "staging"
    }
)

print(f"Model registered: {register_response.json()['model_id']}")

# 6. Upload model artifact to MinIO
# (In production, this would be automated by the training pipeline)
```

---

## 📊 Monitoring

### Check Feature Store Health

```bash
# Check continuous aggregate refresh
docker exec omarino-postgres psql -U omarino -d omarino_db -c "
SELECT view_name, last_run_started_at, last_run_status
FROM timescaledb_information.continuous_aggregates
WHERE view_name IN ('hourly_features', 'daily_features');
"

# Check feature export history
docker exec omarino-postgres psql -U omarino -d omarino_db -c "
SELECT export_id, tenant_id, feature_set, status, row_count, 
       file_size_bytes / (1024*1024) as size_mb, created_at
FROM feature_exports
ORDER BY created_at DESC
LIMIT 10;
"
```

### Check Model Registry

```bash
# List models in MinIO bucket
docker exec omarino-minio mc ls minio/ml-models/

# Check model count by stage
curl "http://localhost:8003/ai/models/?stage=production" | jq '.total'
curl "http://localhost:8003/ai/models/?stage=staging" | jq '.total'
```

---

## 🐛 Troubleshooting

### Issue: "Feature export returns no data"

**Solution:** Ensure TimescaleDB migration ran successfully and continuous aggregates are populated:

```sql
-- Check if views exist
\d hourly_features
\d forecast_basic_features

-- Check if data exists
SELECT COUNT(*) FROM hourly_features;
SELECT COUNT(*) FROM forecast_basic_features;

-- Manually refresh materialized views
REFRESH MATERIALIZED VIEW hourly_features;
REFRESH MATERIALIZED VIEW forecast_basic_features;
```

### Issue: "Model upload fails with S3 error"

**Solution:** Check MinIO connection:

```bash
# Test MinIO connectivity
curl http://localhost:9000/minio/health/live

# Check AI Hub logs
docker-compose logs ai-hub | grep -i minio

# Verify environment variables
docker exec omarino-ai-hub env | grep MINIO
```

### Issue: "Features not found in cache"

**Solution:** Check Redis connection and cache TTL:

```bash
# Connect to Redis
docker exec -it omarino-redis redis-cli -a omarino_redis_pass

# Check cached features
KEYS features:*

# Check TTL
TTL features:tenant-123:meter-001:latest

# If no keys, cache is empty (expected on first request)
# Features will be computed from DB and cached
```

---

## 📖 Additional Resources

- **API Documentation**: http://localhost:8003/docs
- **Task 2 Completion Summary**: `TASK2_FEATURE_STORE_MODEL_REGISTRY_COMPLETE.md`
- **Database Migration**: `ai-hub/migrations/001_create_feature_views.sql`
- **Architecture Docs**: `docs/ai/ai-hub.md` (to be updated)

---

## ✅ Verification Checklist

- [ ] MinIO is running and accessible
- [ ] Database migration applied successfully
- [ ] AI Hub service restarted with new env vars
- [ ] Can export features to Parquet
- [ ] Can register a model
- [ ] Can retrieve model metadata
- [ ] Can promote model to production
- [ ] Continuous aggregates are refreshing

---

**Questions?** Check the AI Hub logs: `docker-compose logs -f ai-hub`
