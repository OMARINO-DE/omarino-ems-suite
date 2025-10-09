# AI Hub Service Documentation

**Version**: 0.2.0  
**Status**: Feature Store & Model Registry Complete  
**Last Updated**: October 9, 2025

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [API Endpoints](#api-endpoints)
4. [Authentication](#authentication)
5. [Feature Store](#feature-store)
6. [Model Registry](#model-registry)
7. [Model Management](#model-management)
8. [Deployment](#deployment)
9. [Monitoring](#monitoring)
10. [Development](#development)
11. [Troubleshooting](#troubleshooting)

## Overview

The AI Hub Service is the central machine learning microservice for the OMARINO EMS Suite. It provides intelligent forecasting, anomaly detection, and model explainability capabilities for energy management systems.

### Key Capabilities

- **Forecasting**: Generate load, generation, and price forecasts with probabilistic outputs
- **Anomaly Detection**: Identify unusual patterns in energy data streams
- **Explainability**: Understand model predictions with SHAP analysis
- **Feature Store**: Online + Offline + Batch feature engineering and serving
- **Model Registry**: Complete ML model lifecycle management with S3/MinIO storage
- **Model Versioning**: Track model versions, metadata, and performance metrics
- **Feature Export**: Export features to Parquet for training pipelines

### Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | FastAPI | 0.109.0 |
| Runtime | Python | 3.11 |
| ML Libraries | scikit-learn, LightGBM, SHAP | Latest |
| Database | PostgreSQL/TimescaleDB | 15+ |
| Cache | Redis | 7+ |
| Observability | OpenTelemetry | Latest |
| Testing | pytest | 7.4+ |

## Architecture

### System Design

```
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway (YARP)                      │
│                   Routes: /api/ai/* → ai-hub                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     AI Hub Service (FastAPI)                 │
├─────────────────────────────────────────────────────────────┤
│  Routers:                                                    │
│  ├─ /health                  - Health checks                │
│  ├─ /ai/forecast             - Time series forecasting      │
│  ├─ /ai/anomaly              - Anomaly detection            │
│  ├─ /ai/explain              - Model explainability         │
│  ├─ /ai/models/*             - Model registry (5 endpoints) │
│  └─ /ai/features/*           - Feature store (4 endpoints)  │
├─────────────────────────────────────────────────────────────┤
│  Services:                                                   │
│  ├─ ModelCache              - Load & cache ML models        │
│  ├─ ModelStorage            - S3/MinIO artifact storage     │
│  └─ FeatureStore            - Feature engineering/serving   │
└────────┬───────────────┬────────────────┬───────────────────┘
         │               │                │
         ▼               ▼                ▼
┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐
│Redis Cache  │  │ MinIO/S3     │  │  TimescaleDB         │
│- Features   │  │- Model files │  │- Continuous aggr.    │
│- Model meta │  │- Metadata    │  │- Feature views       │
└─────────────┘  │- Metrics     │  │- Training data       │
                 └──────────────┘  └──────────────────────┘
```

### Request Flow

1. **Client Request** → API Gateway validates JWT
2. **Route to AI Hub** → Gateway forwards to ai-hub:8003
3. **Feature Extraction** → FeatureStore gets online/offline features
4. **Model Inference** → ModelCache loads model and predicts
5. **Response** → JSON response with predictions/explanations

### Data Flow

```
Historical Data (TimescaleDB)
    ↓
Feature Engineering
    ↓
Online Cache (Redis, TTL=5min)
    ↓
Model Inference
    ↓
Predictions/Anomalies/Explanations
```

## API Endpoints

### Health & Status

#### GET /health

Health check endpoint (no auth required).

**Response:**
```json
{
  "status": "healthy",
  "service": "ai-hub",
  "version": "0.1.0",
  "timestamp": "2025-10-09T12:00:00Z",
  "environment": "production"
}
```

---

### Forecasting

#### POST /ai/forecast

Generate time series forecasts.

**Request:**
```json
{
  "tenant_id": "tenant-123",
  "asset_id": "meter-001",
  "forecast_type": "load",
  "horizon_hours": 24,
  "interval_minutes": 60,
  "include_quantiles": true,
  "historical_data": [
    {"timestamp": "2025-10-01T00:00:00Z", "value": 42.5},
    {"timestamp": "2025-10-01T01:00:00Z", "value": 38.2}
  ],
  "model_name": "lightgbm_v1",
  "features": {
    "temperature": 22.5,
    "humidity": 65.0
  }
}
```

**Required Fields:**
- `tenant_id` (string): Tenant identifier
- `asset_id` (string): Asset/meter identifier
- `forecast_type` (string): Type: `load`, `generation`, `price`

**Optional Fields:**
- `horizon_hours` (int, 1-168): Forecast horizon, default 24
- `interval_minutes` (int, 15-1440): Interval, default 60
- `include_quantiles` (bool): Include probabilistic quantiles, default true
- `historical_data` (array): Optional historical data
- `model_name` (string): Specific model to use
- `features` (object): Additional features

**Response:**
```json
{
  "forecast_id": "fc-uuid-123",
  "tenant_id": "tenant-123",
  "asset_id": "meter-001",
  "forecasts": [
    {
      "timestamp": "2025-10-02T00:00:00Z",
      "point_forecast": 45.3,
      "quantiles": {
        "p10": 40.1,
        "p50": 45.3,
        "p90": 50.8
      },
      "confidence": 0.85,
      "prediction_interval_lower": 40.77,
      "prediction_interval_upper": 49.83
    }
  ],
  "metadata": {
    "generated_at": "2025-10-01T12:00:00Z",
    "model_name": "lightgbm_v1",
    "model_version": "1.0.0",
    "features_used": ["hour_of_day", "day_of_week", "temperature"],
    "training_samples": 8760,
    "training_date": "2025-09-01T00:00:00Z",
    "mae": 2.5,
    "rmse": 3.8,
    "mape": 0.05
  }
}
```

**Status Codes:**
- `200 OK`: Forecast generated successfully
- `400 Bad Request`: Invalid parameters
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Forecast generation failed

---

### Anomaly Detection

#### POST /ai/anomaly

Detect anomalies in time series data.

**Request:**
```json
{
  "tenant_id": "tenant-123",
  "asset_id": "meter-001",
  "time_series": [
    {"timestamp": "2025-10-01T00:00:00Z", "value": 42.5},
    {"timestamp": "2025-10-01T01:00:00Z", "value": 138.2}
  ],
  "method": "isolation_forest",
  "sensitivity": 3.0,
  "lookback_hours": 168,
  "training_data": [...]
}
```

**Required Fields:**
- `tenant_id` (string): Tenant identifier
- `asset_id` (string): Asset identifier
- `time_series` (array, min 2): Time series data points

**Optional Fields:**
- `method` (string): Detection method, default `isolation_forest`
  - Options: `z_score`, `iqr`, `isolation_forest`, `local_outlier_factor`, `prophet_decomposition`
- `sensitivity` (float, 1.0-5.0): Detection sensitivity, default 3.0
  - Lower = more sensitive (more anomalies detected)
- `lookback_hours` (int): Historical lookback, default 168
- `training_data` (array): Separate training data

**Response:**
```json
{
  "detection_id": "det-uuid-123",
  "tenant_id": "tenant-123",
  "asset_id": "meter-001",
  "anomalies": [
    {
      "timestamp": "2025-10-01T01:00:00Z",
      "value": 138.2,
      "anomaly_score": 4.5,
      "is_anomaly": true,
      "expected_range": {
        "min": 35.0,
        "max": 55.0,
        "mean": 45.0,
        "std": 5.0
      },
      "severity": "high",
      "explanation": "Value deviates 4.50 std devs from expected"
    }
  ],
  "summary": {
    "total_points": 24,
    "anomalies_detected": 1,
    "anomaly_rate": 0.042,
    "mean_anomaly_score": 1.2,
    "max_anomaly_score": 4.5,
    "method_used": "isolation_forest",
    "sensitivity": 3.0
  },
  "generated_at": "2025-10-01T12:00:00Z"
}
```

**Severity Levels:**
- `low`: Anomaly score 2.0-2.5
- `medium`: Anomaly score 2.5-3.5
- `high`: Anomaly score 3.5-4.5
- `critical`: Anomaly score > 4.5

---

### Explainability

#### POST /ai/explain

Generate SHAP-based explanation for a prediction.

**Request:**
```json
{
  "tenant_id": "tenant-123",
  "model_name": "lightgbm_v1",
  "model_version": "1.0.0",
  "prediction_id": "pred-123",
  "input_features": {
    "hour_of_day": 14,
    "day_of_week": 3,
    "temperature": 22.5,
    "humidity": 65.0
  },
  "explanation_type": "shap",
  "max_samples": 100
}
```

**Required Fields:**
- `tenant_id` (string): Tenant identifier
- `model_name` (string): Model to explain

**Optional Fields:**
- `model_version` (string): Model version, default `latest`
- `prediction_id` (string): Specific prediction to explain
- `input_features` (object): Features for ad-hoc explanation
- `explanation_type` (string): Type: `shap`, `lime`, `anchor`, default `shap`
- `max_samples` (int, 10-1000): Max samples for SHAP, default 100

**Response:**
```json
{
  "explanation_id": "exp-uuid-123",
  "tenant_id": "tenant-123",
  "model_name": "lightgbm_v1",
  "model_version": "1.0.0",
  "feature_importances": [
    {
      "feature_name": "hour_of_day",
      "importance": 2.5,
      "value": 14,
      "contribution": 2.5,
      "rank": 1
    },
    {
      "feature_name": "temperature",
      "importance": 1.8,
      "value": 22.5,
      "contribution": -1.8,
      "rank": 2
    }
  ],
  "metadata": {
    "explained_at": "2025-10-01T12:00:00Z",
    "model_name": "lightgbm_v1",
    "model_version": "1.0.0",
    "explanation_method": "shap",
    "base_value": 45.0,
    "prediction_value": 48.5,
    "samples_used": 100
  },
  "waterfall_data": [
    {
      "feature_name": "hour_of_day",
      "contribution": 2.5,
      "cumulative_value": 47.5
    }
  ],
  "force_data": [
    {
      "feature_name": "hour_of_day",
      "feature_value": 14,
      "shap_value": 2.5,
      "is_positive": true
    }
  ],
  "summary": {
    "top_3_features": ["hour_of_day", "temperature", "day_of_week"],
    "total_contribution": 5.2,
    "explanation": "The prediction of 48.50 is driven primarily by hour_of_day"
  }
}
```

#### POST /ai/explain/global

Generate global feature importances for a model.

**Request:**
```json
{
  "tenant_id": "tenant-123",
  "model_name": "lightgbm_v1",
  "model_version": "1.0.0",
  "dataset_sample_size": 100
}
```

**Response:**
```json
{
  "explanation_id": "exp-global-uuid",
  "tenant_id": "tenant-123",
  "model_name": "lightgbm_v1",
  "model_version": "1.0.0",
  "global_importances": [
    {
      "feature_name": "hour_of_day",
      "mean_abs_shap": 2.8,
      "mean_shap": 0.5,
      "importance_rank": 1
    }
  ],
  "samples_analyzed": 100,
  "generated_at": "2025-10-01T12:00:00Z"
}
```

---

### Model Registry

#### POST /ai/models/register

Register a new ML model with metadata and performance metrics.

**Request:**
```json
{
  "tenant_id": "tenant-123",
  "model_name": "forecast-lstm",
  "version": "v1.0.0",
  "model_type": "forecast",
  "stage": "staging",
  "model_file": "<base64_encoded_model>",
  "metadata": {
    "algorithm": "LSTM",
    "framework": "tensorflow",
    "features": ["hour_of_day", "day_of_week", "temperature"],
    "hyperparameters": {
      "units": 128,
      "layers": 2,
      "dropout": 0.2,
      "learning_rate": 0.001
    },
    "training_date": "2025-10-01T00:00:00Z",
    "training_samples": 8760
  },
  "metrics": {
    "mae": 2.5,
    "rmse": 3.8,
    "mape": 0.05,
    "r2_score": 0.92,
    "training_time_seconds": 3600,
    "dataset_size": 100000
  }
}
```

**Required Fields:**
- `tenant_id` (string): Tenant identifier
- `model_name` (string): Model name (alphanumeric, hyphens, underscores)
- `version` (string): Semantic version (e.g., v1.0.0)
- `model_type` (string): Type: `forecast`, `anomaly`, `optimization`, `classification`
- `model_file` (string): Base64-encoded model artifact

**Optional Fields:**
- `stage` (string): Lifecycle stage: `staging`, `production`, `archived`, default `staging`
- `metadata` (object): Model configuration and training details
- `metrics` (object): Performance metrics

**Response (201 Created):**
```json
{
  "model_id": "tenant-123:forecast-lstm:v1.0.0",
  "tenant_id": "tenant-123",
  "model_name": "forecast-lstm",
  "version": "v1.0.0",
  "stage": "staging",
  "storage_path": "s3://models-bucket/tenant-123/forecast-lstm/v1.0.0/",
  "registered_at": "2025-10-09T12:00:00Z",
  "message": "Model registered successfully"
}
```

**Status Codes:**
- `201 Created`: Model registered successfully
- `400 Bad Request`: Invalid model_id format or stage
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Upload failed

---

#### GET /ai/models/{model_id}

Get detailed information about a specific model.

**Path Parameters:**
- `model_id` (string): Format: `{tenant_id}:{model_name}:{version}`

**Response (200 OK):**
```json
{
  "model_id": "tenant-123:forecast-lstm:v1.0.0",
  "tenant_id": "tenant-123",
  "model_name": "forecast-lstm",
  "version": "v1.0.0",
  "model_type": "forecast",
  "stage": "production",
  "registered_at": "2025-10-09T12:00:00Z",
  "storage_path": "s3://models-bucket/tenant-123/forecast-lstm/v1.0.0/",
  "metadata": {
    "algorithm": "LSTM",
    "framework": "tensorflow",
    "features": ["hour_of_day", "day_of_week", "temperature"],
    "hyperparameters": {...},
    "training_date": "2025-10-01T00:00:00Z",
    "training_samples": 8760
  },
  "metrics": {
    "mae": 2.5,
    "rmse": 3.8,
    "mape": 0.05,
    "r2_score": 0.92
  }
}
```

**Status Codes:**
- `200 OK`: Model found
- `400 Bad Request`: Invalid model_id format
- `404 Not Found`: Model not found

---

#### GET /ai/models/

List models with optional filters.

**Query Parameters:**
- `tenant_id` (string, optional): Filter by tenant
- `model_name` (string, optional): Filter by model name
- `stage` (string, optional): Filter by stage
- `limit` (int, optional): Max results, default 100

**Response (200 OK):**
```json
{
  "models": [
    {
      "model_id": "tenant-123:forecast-lstm:v1.0.0",
      "model_name": "forecast-lstm",
      "version": "v1.0.0",
      "stage": "production",
      "registered_at": "2025-10-09T12:00:00Z"
    },
    {
      "model_id": "tenant-123:forecast-lstm:v1.1.0",
      "model_name": "forecast-lstm",
      "version": "v1.1.0",
      "stage": "staging",
      "registered_at": "2025-10-10T12:00:00Z"
    }
  ],
  "total": 2,
  "limit": 100
}
```

---

#### PUT /ai/models/{model_id}/promote

Promote a model to a different lifecycle stage.

**Path Parameters:**
- `model_id` (string): Format: `{tenant_id}:{model_name}:{version}`

**Request:**
```json
{
  "target_stage": "production"
}
```

**Valid Stage Transitions:**
- `staging` → `production`
- `production` → `archived`
- `staging` → `archived`

**Response (200 OK):**
```json
{
  "model_id": "tenant-123:forecast-lstm:v1.0.0",
  "previous_stage": "staging",
  "new_stage": "production",
  "promoted_at": "2025-10-09T12:00:00Z",
  "message": "Model promoted successfully"
}
```

**Status Codes:**
- `200 OK`: Model promoted successfully
- `400 Bad Request`: Invalid stage transition
- `404 Not Found`: Model not found

---

#### DELETE /ai/models/{model_id}

Delete a model from the registry.

**Path Parameters:**
- `model_id` (string): Format: `{tenant_id}:{model_name}:{version}`

**Query Parameters:**
- `force` (bool, optional): Force delete production models, default false

**Response (200 OK):**
```json
{
  "model_id": "tenant-123:forecast-lstm:v1.0.0",
  "deleted_at": "2025-10-09T12:00:00Z",
  "message": "Model deleted successfully"
}
```

**Status Codes:**
- `200 OK`: Model deleted successfully
- `400 Bad Request`: Cannot delete production model without force flag
- `404 Not Found`: Model not found

---

### Features API

#### POST /ai/features/get

Get features for online inference.

**Request:**
```json
{
  "tenant_id": "tenant-123",
  "asset_id": "meter-001",
  "feature_set": "forecast_basic",
  "timestamp": "2025-10-09T14:00:00Z",
  "lookback_hours": 168
}
```

**Required Fields:**
- `tenant_id` (string): Tenant identifier
- `asset_id` (string): Asset identifier

**Optional Fields:**
- `feature_set` (string): Predefined feature set name
- `feature_names` (array): Specific feature names to retrieve
- `timestamp` (string): Target timestamp, default now
- `lookback_hours` (int, 1-8760): Historical lookback, default 168

**Response (200 OK):**
```json
{
  "tenant_id": "tenant-123",
  "asset_id": "meter-001",
  "features": {
    "hour_of_day": 14,
    "day_of_week": 3,
    "day_of_month": 9,
    "is_weekend": 0,
    "is_business_hours": 1,
    "hourly_avg": 45.2,
    "lag_1h": 43.5,
    "lag_24h": 44.8,
    "lag_168h": 42.3,
    "rolling_avg_24h": 44.5,
    "rolling_std_24h": 3.2,
    "temperature": 22.5,
    "humidity": 65.0
  },
  "feature_count": 13,
  "computed_at": "2025-10-09T14:00:00Z",
  "cache_hit": true
}
```

**Available Feature Sets:**
- `forecast_basic`: 6 features, <50ms latency
- `forecast_advanced`: 13 features, <100ms latency
- `anomaly_detection`: 7 features, <50ms latency

**Status Codes:**
- `200 OK`: Features retrieved successfully
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Feature computation failed

---

#### POST /ai/features/export

Export features to Parquet for training pipelines.

**Request:**
```json
{
  "tenant_id": "tenant-123",
  "feature_set": "forecast_basic",
  "start_time": "2024-01-01T00:00:00Z",
  "end_time": "2024-12-31T23:59:59Z",
  "asset_ids": ["meter-001", "meter-002"],
  "output_path": "./exports/features.parquet"
}
```

**Required Fields:**
- `tenant_id` (string): Tenant identifier
- `feature_set` (string): Feature set to export
- `start_time` (string): Start timestamp
- `end_time` (string): End timestamp

**Optional Fields:**
- `asset_ids` (array): Filter specific assets, default all
- `output_path` (string): Custom output path

**Response (202 Accepted):**
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

**Status Codes:**
- `202 Accepted`: Export job created
- `400 Bad Request`: Invalid time range
- `404 Not Found`: No data found for export
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Export failed

---

#### GET /ai/features/exports

List feature export history.

**Query Parameters:**
- `tenant_id` (string, optional): Filter by tenant
- `feature_set` (string, optional): Filter by feature set
- `status_filter` (string, optional): Filter by status
- `limit` (int, optional): Max results, default 100

**Response (200 OK):**
```json
{
  "exports": [
    {
      "export_id": "550e8400-e29b-41d4-a716-446655440000",
      "tenant_id": "tenant-123",
      "feature_set": "forecast_basic",
      "status": "completed",
      "row_count": 876000,
      "file_size_mb": 42.5,
      "started_at": "2025-10-09T14:00:00Z",
      "completed_at": "2025-10-09T14:02:15Z"
    }
  ],
  "total": 1
}
```

---

#### GET /ai/features/sets

List available feature sets with metadata.

**Response (200 OK):**
```json
{
  "feature_sets": {
    "forecast_basic": {
      "name": "forecast_basic",
      "description": "Basic time and statistical features for forecasting",
      "features": [
        "hour_of_day",
        "day_of_week",
        "is_weekend",
        "lag_1h",
        "lag_24h",
        "rolling_avg_24h"
      ],
      "use_cases": ["load_forecasting", "generation_forecasting"],
      "latency": "<50ms",
      "storage": "redis"
    },
    "forecast_advanced": {
      "name": "forecast_advanced",
      "description": "Advanced features including weather and market data",
      "features": [
        "hour_of_day",
        "day_of_week",
        "day_of_month",
        "month",
        "is_weekend",
        "is_business_hours",
        "lag_1h",
        "lag_24h",
        "lag_168h",
        "rolling_avg_24h",
        "rolling_std_24h",
        "temperature",
        "humidity"
      ],
      "use_cases": ["advanced_forecasting", "price_prediction"],
      "latency": "<100ms",
      "storage": "redis+timescaledb"
    },
    "anomaly_detection": {
      "name": "anomaly_detection",
      "description": "Statistical features for anomaly detection",
      "features": [
        "hour_of_day",
        "day_of_week",
        "historical_avg_24h",
        "historical_std_24h",
        "max_24h",
        "min_24h",
        "range_24h"
      ],
      "use_cases": ["anomaly_detection", "outlier_detection"],
      "latency": "<50ms",
      "storage": "timescaledb"
    }
  },
  "total": 3
}
```

---

## Authentication

**Note**: Authentication middleware is not yet implemented in the MVP. All endpoints currently work without authentication.

**Planned Authentication:**
- JWT tokens from Keycloak
- Tenant isolation via `tenant_id` claim
- Role-based access control (RBAC)

**Required JWT Claims:**
```json
{
  "sub": "user-id",
  "tenant_id": "tenant-123",
  "preferred_username": "user@example.com",
  "realm_access": {
    "roles": ["ai_user", "forecaster"]
  }
}
```

**Required Roles:**
- `ai_user`: Basic AI features access
- `forecaster`: Forecast generation
- `anomaly_analyst`: Anomaly detection
- `model_admin`: Model management

---

## Feature Store

### Overview

The Feature Store provides a complete feature engineering platform with online serving, offline storage, and batch export capabilities.

**Key Features:**
- **Online Features**: Redis cache with 5-minute TTL for low-latency serving (<50ms)
- **Offline Features**: TimescaleDB continuous aggregates and materialized views
- **Batch Export**: Export features to Parquet for training pipelines
- **Feature Sets**: Predefined feature collections for different use cases
- **SQL Functions**: Custom TimescaleDB functions for lag and rolling window features
- **Graceful Fallback**: Time features always available even when DB is down

### Architecture

```
┌──────────────────────────────────────────────────────┐
│                   Feature Store                      │
├──────────────────────────────────────────────────────┤
│  Online Layer (Redis, TTL=5min)                      │
│  ├─ Feature cache by tenant_id:asset_id:timestamp    │
│  ├─ <50ms latency for inference                      │
│  └─ Automatic cache warming                          │
├──────────────────────────────────────────────────────┤
│  Offline Layer (TimescaleDB)                         │
│  ├─ Continuous Aggregates:                           │
│  │  ├─ hourly_features (refresh hourly)              │
│  │  └─ daily_features (refresh daily)                │
│  ├─ Materialized Views:                              │
│  │  ├─ forecast_basic_features                       │
│  │  └─ anomaly_detection_features                    │
│  └─ SQL Functions:                                   │
│     ├─ get_lag_features(ARRAY[1,24,168])             │
│     └─ get_rolling_features(window_hours)            │
├──────────────────────────────────────────────────────┤
│  Batch Layer                                         │
│  ├─ Export to Parquet with snappy compression        │
│  ├─ Export metadata tracking in feature_exports      │
│  └─ Support for time range and asset filters         │
└──────────────────────────────────────────────────────┘
```

### Database Objects

**Tables (Hypertables):**
- `timeseries_data`: Raw time series (7-day retention)
- `ai_features`: Computed features (90-day retention)
- `weather_features`: Weather data (1-year retention)
- `feature_exports`: Export job tracking

**Continuous Aggregates:**
- `hourly_features`: Hourly statistics (refresh hourly, 1-year retention)
- `daily_features`: Daily statistics (refresh daily, 2-year retention)

**Materialized Views:**
- `forecast_basic_features`: 6 features for basic forecasting
- `anomaly_detection_features`: 7 features for anomaly detection

**SQL Functions:**
```sql
-- Get lag features
SELECT * FROM get_lag_features(
  'tenant-123', 
  'meter-001', 
  '2025-10-09 14:00:00'::timestamptz,
  ARRAY[1, 24, 168]
);

-- Get rolling window features
SELECT * FROM get_rolling_features(
  'tenant-123', 
  'meter-001', 
  '2025-10-09 14:00:00'::timestamptz,
  24  -- window in hours
);
```

### Feature Sets

Pre-defined collections of features for specific models:

**`forecast_basic`** (6 features, <50ms)
- **Time features**: hour_of_day, day_of_week, is_weekend
- **Statistical**: hourly_avg, lag_1h, lag_24h
- **Use cases**: Basic load/generation forecasting
- **Storage**: Redis + TimescaleDB hourly aggregates

**`forecast_advanced`** (13 features, <100ms)
- **All basic features** plus:
- **Extended time**: day_of_month, month, is_business_hours
- **Extended lags**: lag_168h (1 week)
- **Rolling windows**: rolling_avg_24h, rolling_std_24h
- **Weather**: temperature, humidity, solar_irradiance
- **Use cases**: Advanced forecasting, price prediction
- **Storage**: Redis + TimescaleDB daily aggregates + weather data

**`anomaly_detection`** (7 features, <50ms)
- **Time features**: hour_of_day, day_of_week
- **Historical stats**: historical_avg_24h, historical_std_24h
- **Range features**: max_24h, min_24h, range_24h
- **Use cases**: Anomaly detection, outlier identification
- **Storage**: TimescaleDB materialized views

### Feature Computation Flow

```
1. Check Redis Cache
   ├─ Cache Hit → Return cached features (5ms)
   └─ Cache Miss ↓

2. Compute Time Features (always available)
   ├─ hour_of_day, day_of_week, etc.
   └─ No DB required ↓

3. Query TimescaleDB (if available)
   ├─ Hourly aggregates (hourly_features)
   ├─ Daily aggregates (daily_features)
   ├─ Lag features (get_lag_features)
   ├─ Rolling windows (get_rolling_features)
   └─ Weather features (weather_features) ↓

4. Combine & Cache
   ├─ Merge all feature sources
   ├─ Store in Redis (TTL=5min)
   └─ Return to caller (45-95ms)
```

### Usage Examples

**Get features for inference:**
```python
from app.services import get_feature_store

feature_store = get_feature_store()

# Get predefined feature set
features = await feature_store.compute_feature_set(
    tenant_id="tenant-123",
    asset_id="meter-001",
    feature_set_name="forecast_advanced",
    timestamp=datetime.now(timezone.utc)
)
# Returns: {hour_of_day: 14, lag_1h: 43.5, temperature: 22.5, ...}
```

**Get specific features:**
```python
# Get custom feature selection
features = await feature_store.get_features(
    tenant_id="tenant-123",
    asset_id="meter-001",
    feature_names=["hour_of_day", "lag_24h", "temperature"],
    timestamp=datetime.now(timezone.utc)
)
```

**Export features for training:**
```python
# Export to Parquet
result = await feature_store.export_features_to_parquet(
    tenant_id="tenant-123",
    feature_set="forecast_basic",
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 12, 31),
    asset_ids=["meter-001", "meter-002"],
    output_path="./exports/training_features.parquet"
)
# Returns: {export_id, row_count, file_size_bytes, storage_path}
```

**Batch features for multiple assets:**
```python
# Get features for multiple assets
batch_features = await feature_store.get_batch_features(
    tenant_id="tenant-123",
    asset_ids=["meter-001", "meter-002", "meter-003"],
    feature_set_name="forecast_basic",
    lookback_hours=168
)
```

### Performance Characteristics

| Operation | Latency | Notes |
|-----------|---------|-------|
| **Online features (cached)** | 5-10ms | Redis cache hit |
| **Online features (uncached)** | 45-95ms | DB query + cache |
| **Batch export (1M rows)** | 30-60s | Parquet with snappy compression |
| **Feature set computation** | 20-50ms | Depends on feature count |

### Retention Policies

| Data | Retention | Rationale |
|------|-----------|-----------|
| **Raw time series** | 7 days | Continuous aggregates retain data |
| **AI features** | 90 days | Recent training windows |
| **Hourly aggregates** | 1 year | Historical patterns |
| **Daily aggregates** | 2 years | Long-term trends |
| **Weather features** | 1 year | Seasonal patterns |

### Feature Engineering Best Practices

1. **Use predefined feature sets** for common use cases
2. **Cache warming**: Pre-compute features for known assets
3. **Batch exports**: Use Parquet for training data (10-100x faster than API)
4. **Time zones**: All timestamps in UTC
5. **Missing data**: Features gracefully handle nulls (return 0 or mean)
6. **Feature drift**: Monitor feature distributions over time

---

## Model Registry

### Overview

The Model Registry provides complete ML model lifecycle management with versioning, metadata tracking, and S3/MinIO storage.

**Key Features:**
- **Model Versioning**: Semantic versioning (v1.0.0, v1.1.0, etc.)
- **Lifecycle Management**: staging → production → archived → deleted
- **S3/MinIO Storage**: Artifact storage with automatic bucket creation
- **Metadata Tracking**: Hyperparameters, features, training details
- **Performance Metrics**: Track MAE, RMSE, MAPE, R², etc.
- **Multi-tenant**: Isolated storage by tenant_id

### Model Lifecycle

```
┌─────────────────────────────────────────────────────┐
│            Model Lifecycle Stages                   │
├─────────────────────────────────────────────────────┤
│  1. STAGING                                         │
│     ├─ Initial registration                         │
│     ├─ Testing and validation                       │
│     ├─ A/B testing                                  │
│     └─ Promote to production ↓                      │
│                                                     │
│  2. PRODUCTION                                      │
│     ├─ Active serving                               │
│     ├─ Monitoring performance                       │
│     ├─ Cannot delete without force flag             │
│     └─ Promote to archived ↓                        │
│                                                     │
│  3. ARCHIVED                                        │
│     ├─ No longer serving                            │
│     ├─ Historical reference                         │
│     ├─ Can be restored                              │
│     └─ Delete ↓                                     │
│                                                     │
│  4. DELETED                                         │
│     ├─ Removed from S3/MinIO                        │
│     └─ Cannot be recovered                          │
└─────────────────────────────────────────────────────┘
```

### S3/MinIO Storage Structure

```
models-bucket/
├── tenant-123/
│   ├── forecast-lstm/
│   │   ├── v1.0.0/
│   │   │   ├── model.joblib          # Model artifact
│   │   │   ├── metadata.json         # Hyperparameters, config
│   │   │   └── metrics.json          # Performance metrics
│   │   ├── v1.1.0/
│   │   │   ├── model.joblib
│   │   │   ├── metadata.json
│   │   │   └── metrics.json
│   │   └── v2.0.0/
│   │       └── ...
│   └── anomaly-detector/
│       └── v1.0.0/
│           └── ...
└── tenant-456/
    └── ...
```

### Model ID Format

Model IDs follow the format: `{tenant_id}:{model_name}:{version}`

**Examples:**
- `tenant-123:forecast-lstm:v1.0.0`
- `tenant-456:anomaly-detector:v2.1.3`
- `shared:price-predictor:v1.0.0`

**Rules:**
- `tenant_id`: Alphanumeric, hyphens, underscores
- `model_name`: Alphanumeric, hyphens, underscores
- `version`: Semantic versioning (vX.Y.Z)

### Metadata Structure

**metadata.json:**
```json
{
  "algorithm": "LSTM",
  "framework": "tensorflow",
  "framework_version": "2.14.0",
  "features": ["hour_of_day", "day_of_week", "temperature"],
  "feature_count": 3,
  "target_variable": "load",
  "hyperparameters": {
    "units": 128,
    "layers": 2,
    "dropout": 0.2,
    "learning_rate": 0.001,
    "batch_size": 32,
    "epochs": 100
  },
  "training_date": "2025-10-01T00:00:00Z",
  "training_samples": 8760,
  "training_duration_seconds": 3600,
  "dataset": {
    "source": "timescaledb",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "asset_count": 100
  }
}
```

**metrics.json:**
```json
{
  "mae": 2.5,
  "rmse": 3.8,
  "mape": 0.05,
  "r2_score": 0.92,
  "training_loss": 0.15,
  "validation_loss": 0.18,
  "test_loss": 0.17,
  "training_time_seconds": 3600,
  "inference_time_ms": 45,
  "model_size_mb": 12.5,
  "dataset_size": 100000
}
```

### Usage Examples

**Register a new model:**
```python
from app.services import get_model_storage
import joblib

model_storage = get_model_storage()

# Upload model with metadata
await model_storage.upload_model(
    tenant_id="tenant-123",
    model_name="forecast-lstm",
    version="v1.0.0",
    model=trained_model,
    metadata={
        "algorithm": "LSTM",
        "features": ["hour", "day", "temp"],
        "hyperparameters": {"units": 128}
    },
    metrics={
        "mae": 2.5,
        "rmse": 3.8,
        "r2_score": 0.92
    }
)
```

**Download a model:**
```python
# Download model from S3/MinIO
model = await model_storage.download_model(
    tenant_id="tenant-123",
    model_name="forecast-lstm",
    version="v1.0.0"
)
```

**List model versions:**
```python
# List all versions of a model
versions = await model_storage.list_versions(
    tenant_id="tenant-123",
    model_name="forecast-lstm"
)
# Returns: [{"version": "v1.0.0", "size": 12500000, ...}, ...]
```

**Promote model:**
```python
# Copy model to production (staging → production)
await model_storage.copy_model(
    tenant_id="tenant-123",
    model_name="forecast-lstm",
    source_version="v1.0.0",
    target_version="v1.0.0-prod"
)
```

### REST API Examples

**Register model via API:**
```bash
curl -X POST http://ai-hub:8003/ai/models/register \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-123",
    "model_name": "forecast-lstm",
    "version": "v1.0.0",
    "model_type": "forecast",
    "model_file": "<base64_encoded>",
    "metadata": {...},
    "metrics": {...}
  }'
```

**Get model details:**
```bash
curl http://ai-hub:8003/ai/models/tenant-123:forecast-lstm:v1.0.0
```

**List models:**
```bash
# All models for tenant
curl "http://ai-hub:8003/ai/models/?tenant_id=tenant-123"

# Filter by stage
curl "http://ai-hub:8003/ai/models/?tenant_id=tenant-123&stage=production"

# Filter by model name
curl "http://ai-hub:8003/ai/models/?model_name=forecast-lstm"
```

**Promote model:**
```bash
curl -X PUT http://ai-hub:8003/ai/models/tenant-123:forecast-lstm:v1.0.0/promote \
  -H "Content-Type: application/json" \
  -d '{"target_stage": "production"}'
```

**Delete model:**
```bash
# Delete archived model
curl -X DELETE http://ai-hub:8003/ai/models/tenant-123:forecast-lstm:v1.0.0

# Force delete production model
curl -X DELETE "http://ai-hub:8003/ai/models/tenant-123:forecast-lstm:v1.0.0?force=true"
```

### Model Versioning Best Practices

1. **Semantic Versioning**: Use vMAJOR.MINOR.PATCH
   - MAJOR: Breaking changes (new features, different output format)
   - MINOR: Backward-compatible improvements
   - PATCH: Bug fixes, small tweaks

2. **Staged Rollout**: Always start in `staging`, test thoroughly, then promote to `production`

3. **A/B Testing**: Run multiple versions side-by-side
   - v1.0.0 (production): 80% traffic
   - v1.1.0 (staging): 20% traffic

4. **Model Monitoring**: Track performance metrics in production
   - Monitor MAE, RMSE drift over time
   - Alert on degradation

5. **Archiving**: Keep old versions for:
   - Rollback capability
   - Historical analysis
   - Compliance requirements

6. **Storage Management**: Delete archived models after retention period (e.g., 90 days)

---

## Model Management

### Model Storage Structure

```
./models/
├── tenant-123/
│   ├── forecast/
│   │   ├── lightgbm_v1.0.0.joblib
│   │   ├── lightgbm_v1.0.0_metadata.json
│   │   └── scaler.joblib
│   └── anomaly/
│       └── isolation_forest_v1.0.0.joblib
└── shared/
    └── feature_transformers.joblib
```

### Model Cache

The ModelCache service provides:
- **LRU caching**: Keep N models in memory
- **TTL expiration**: Auto-evict after X seconds
- **Lazy loading**: Load on first use
- **Warmup**: Preload critical models at startup

### Usage

```python
from app.services import get_model_cache

model_cache = get_model_cache()

# Get model (loads if not cached)
model = await model_cache.get_model(
    tenant_id="tenant-123",
    model_name="lightgbm_v1",
    model_version="1.0.0"
)

# Save model
await model_cache.save_model(
    tenant_id="tenant-123",
    model_name="lightgbm_v1",
    model_version="1.0.0",
    model=trained_model,
    metadata={
        "algorithm": "lightgbm",
        "features": ["hour", "day", "temp"],
        "mae": 2.5
    }
)

# List models for tenant
models = await model_cache.list_models(tenant_id="tenant-123")
```

### Model Metadata Format

```json
{
  "model_id": "model-uuid",
  "model_name": "lightgbm_v1",
  "version": "1.0.0",
  "tenant_id": "tenant-123",
  "model_type": "forecast",
  "algorithm": "lightgbm",
  "features": ["hour_of_day", "day_of_week", "temperature"],
  "training_date": "2025-10-01T00:00:00Z",
  "performance_metrics": {
    "mae": 2.5,
    "rmse": 3.8,
    "mape": 0.05
  },
  "hyperparameters": {
    "num_leaves": 31,
    "learning_rate": 0.1,
    "n_estimators": 100
  }
}
```

---

## Deployment

### Docker

**Build:**
```bash
cd ai-hub
docker build -t ai-hub:latest .
```

**Run:**
```bash
docker run -p 8003:8003 \
  -e DATABASE_URL=postgresql://user:pass@postgres:5432/db \
  -e REDIS_HOST=redis \
  -e REDIS_PORT=6379 \
  ai-hub:latest
```

### Docker Compose

Add to `docker-compose.yml`:

```yaml
ai-hub:
  image: 192.168.61.21:32768/omarino-ems/ai-hub:latest
  container_name: omarino-ai-hub
  environment:
    - ENVIRONMENT=production
    - DATABASE_URL=postgresql://omarino:${POSTGRES_PASSWORD}@postgres:5432/omarino_db
    - REDIS_HOST=redis
    - REDIS_PORT=6379
    - REDIS_PASSWORD=${REDIS_PASSWORD}
    - KEYCLOAK_URL=http://keycloak:8080
    - KEYCLOAK_REALM=omarino
    - KEYCLOAK_CLIENT_ID=ai-hub
    - OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4317
  ports:
    - "8003:8003"
  depends_on:
    - postgres
    - redis
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
    interval: 30s
    timeout: 10s
    retries: 3
  networks:
    - omarino-network
  restart: unless-stopped
```

### Environment Variables

**Required:**
```bash
# Application
ENVIRONMENT=production

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Redis Cache
REDIS_HOST=redis
REDIS_PORT=6379

# MinIO/S3 Storage (for Model Registry)
MINIO_ENDPOINT_URL=http://minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MODEL_STORAGE_BUCKET=ai-models
```

**Optional:**
```bash
# Redis
REDIS_PASSWORD=secret

# AWS S3 (alternative to MinIO)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

# Feature Store
EXPORT_STORAGE_PATH=./exports
FEATURE_CACHE_TTL=300  # 5 minutes

# Model Cache
MODEL_STORAGE_PATH=./models
MODEL_CACHE_SIZE=5
MODEL_CACHE_TTL=3600

# Authentication (not yet implemented)
KEYCLOAK_URL=http://keycloak:8080
KEYCLOAK_REALM=omarino
KEYCLOAK_CLIENT_ID=ai-hub

# Observability
OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4317
LOG_LEVEL=INFO
```

---

## Monitoring

### Metrics

- Request rate and latency (OpenTelemetry)
- Model inference time
- Cache hit rate (Redis)
- Anomaly detection rate
- Model accuracy (when ground truth available)

### Structured Logging

All logs are JSON-formatted with structured fields:

```json
{
  "timestamp": "2025-10-01T12:00:00Z",
  "level": "info",
  "event": "forecast_generated",
  "tenant_id": "tenant-123",
  "asset_id": "meter-001",
  "model_name": "lightgbm_v1",
  "horizon_hours": 24,
  "latency_ms": 145
}
```

### OpenTelemetry Tracing

Distributed traces for:
- HTTP requests
- Model inference
- Database queries
- Cache operations
- External service calls

View traces in Grafana Tempo.

---

## Development

### Local Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --port 8003
```

### Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest -m unit

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/test_forecast.py -v
```

See [tests/README.md](../../ai-hub/tests/README.md) for comprehensive testing guide.

### Code Quality

```bash
# Linting
ruff check app/ tests/

# Type checking
mypy app/ --ignore-missing-imports

# Format code
ruff format app/ tests/
```

---

## Troubleshooting

### Common Issues

**Problem**: Model not found  
**Solution**: Check model exists in `./models/{tenant_id}/{model_name}/`

**Problem**: Slow forecast generation  
**Solution**: Increase `MODEL_CACHE_SIZE` or check Redis connection

**Problem**: Features not cached  
**Solution**: Verify Redis is running and `REDIS_HOST` is correct

**Problem**: High memory usage  
**Solution**: Reduce `MODEL_CACHE_SIZE` or use smaller models

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
uvicorn app.main:app --reload
```

### Health Checks

```bash
# Service health
curl http://localhost:8003/health

# Check Redis
redis-cli -h localhost -p 6379 ping

# Check PostgreSQL
psql -h localhost -U omarino -d omarino_db -c "SELECT 1;"
```

---

## API Gateway Integration

Update `api-gateway/appsettings.json`:

```json
{
  "ReverseProxy": {
    "Routes": {
      "ai-route": {
        "ClusterId": "ai-cluster",
        "Match": {
          "Path": "/api/ai/{**catch-all}"
        },
        "Transforms": [
          {
            "PathPattern": "/ai/{**catch-all}"
          }
        ]
      }
    },
    "Clusters": {
      "ai-cluster": {
        "Destinations": {
          "destination1": {
            "Address": "http://ai-hub:8003"
          }
        },
        "HealthCheck": {
          "Active": {
            "Enabled": true,
            "Interval": "00:00:30",
            "Path": "/health"
          }
        }
      }
    }
  }
}
```

---

## Next Steps

### Task 2 Complete ✅ (Feature Store & Model Registry)
- ✅ TimescaleDB continuous aggregates and materialized views
- ✅ Redis online feature caching (5-minute TTL)
- ✅ MinIO/S3 model storage with versioning
- ✅ `/ai/models/*` endpoints (5 endpoints)
- ✅ `/ai/features/*` endpoints (4 endpoints)
- ✅ Parquet export for training pipelines
- ✅ Comprehensive test suite (115 tests, 82%+ coverage)

### Task 3 (Advanced ML Training Pipeline)
- Automated model training workflows
- Distributed training with Ray/Dask
- Hyperparameter optimization (Optuna)
- Model versioning automation
- CI/CD for model deployment

### Task 4 (Real-time Inference at Scale)
- Load balancing for model serving
- Model serving optimization (ONNX)
- Batch prediction API
- Stream processing integration
- GPU acceleration support

### Task 5 (Advanced Features)
- Probabilistic forecasting (quantile regression)
- Scenario engine (Monte Carlo simulations)
- Transfer learning for new assets
- Ensemble models
- AutoML capabilities

---

**For more information, see:**
- [AI Hub README](../../ai-hub/README.md)
- [Feature Engineering Guide](./feature-engineering.md)
- [Testing Guide](../../ai-hub/tests/README.md)
- [Task 2 Complete Summary](../../TASK2_FEATURE_STORE_MODEL_REGISTRY_COMPLETE.md)
- [Task 2 Quickstart](../../TASK2_QUICKSTART.md)
