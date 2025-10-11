# Training Pipeline Guide

Complete guide to using the OMARINO AI Hub training pipeline for automated model training, distributed execution, and lifecycle management.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Getting Started](#getting-started)
4. [Training Configuration](#training-configuration)
5. [Job Lifecycle](#job-lifecycle)
6. [Distributed Training](#distributed-training)
7. [Progress Monitoring](#progress-monitoring)
8. [Error Handling](#error-handling)
9. [API Reference](#api-reference)
10. [Best Practices](#best-practices)

---

## Overview

The OMARINO AI Hub training pipeline provides a production-grade infrastructure for training machine learning models at scale. It supports:

- **Automated Training**: Queue-based job management with priority scheduling
- **Distributed Execution**: Leverage Ray for parallel and distributed training
- **Model Lifecycle**: Complete tracking from data preparation to model registration
- **Progress Monitoring**: Real-time status updates and metrics logging
- **Error Handling**: Automatic retry with exponential backoff
- **Multi-Tenancy**: Tenant isolation and resource management

### Supported Model Types

- **Forecast**: Time series forecasting (load forecasting, demand prediction)
- **Anomaly**: Anomaly detection (equipment failures, unusual patterns)

### Supported Algorithms

- **LightGBM**: Fast gradient boosting (recommended for forecasting)
- **XGBoost**: Robust gradient boosting
- **Random Forest**: Ensemble decision trees
- **Neural Networks**: Deep learning models (MLP, LSTM)

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Training Pipeline                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │   Training   │───>│   Training   │───>│  Ray Cluster │ │
│  │ Orchestrator │    │   Pipeline   │    │   Manager    │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│         │                    │                    │         │
│         │                    │                    │         │
│         v                    v                    v         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              PostgreSQL Database                      │  │
│  │  - Training Jobs        - Ray Clusters                │  │
│  │  - Job Metrics          - Worker Nodes                │  │
│  │  - Model Versions                                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Training Pipeline Steps

The training pipeline consists of 5 steps:

1. **Data Loading**: Load and validate training data
2. **Preprocessing**: Clean, transform, and feature engineer
3. **Training**: Train model with configured algorithm
4. **Evaluation**: Calculate performance metrics
5. **Registration**: Save model to registry

---

## Getting Started

### Prerequisites

```bash
# Install dependencies
cd ai-hub
poetry install

# Run database migrations
poetry run alembic upgrade head

# Start the AI Hub service
poetry run uvicorn app.main:app --reload
```

### Quick Start Example

```python
import requests

# API endpoint
API_URL = "http://localhost:8000"

# Create training job
response = requests.post(
    f"{API_URL}/ai/training/jobs",
    json={
        "tenant_id": "acme-corp",
        "model_type": "forecast",
        "config": {
            "model_type": "forecast",
            "algorithm": "lgbm",
            "hyperparameters": {
                "n_estimators": 100,
                "learning_rate": 0.1,
                "max_depth": 7,
                "num_leaves": 31,
            },
            "training_start": "2024-01-01T00:00:00",
            "training_end": "2024-12-31T23:59:59",
            "features": [
                "temperature",
                "humidity",
                "day_of_week",
                "hour_of_day",
                "load_lag_1",
                "load_lag_24",
            ],
            "target": "load",
            "validation_split": 0.2,
            "random_seed": 42,
        },
        "priority": "high",
        "metadata": {
            "description": "Baseline load forecasting model",
            "owner": "data-science-team",
        },
    }
)

job = response.json()
print(f"Job created: {job['job_id']}")
```

### Check Job Status

```python
# Get job status
response = requests.get(f"{API_URL}/ai/training/jobs/{job['job_id']}")
status = response.json()

print(f"Status: {status['status']}")
print(f"Progress: {status['progress']}%")
print(f"Current Step: {status['current_step']}")

# Check for metrics
if status['metrics']:
    print(f"MAE: {status['metrics']['mae']:.2f}")
    print(f"RMSE: {status['metrics']['rmse']:.2f}")
```

---

## Training Configuration

### TrainingConfig Schema

```python
{
  "model_type": "forecast",  # or "anomaly"
  "algorithm": "lgbm",       # lgbm, xgboost, rf, mlp, lstm
  "hyperparameters": {
    # Algorithm-specific hyperparameters
    "n_estimators": 100,
    "learning_rate": 0.1,
    "max_depth": 7,
  },
  "training_start": "2024-01-01T00:00:00",  # ISO 8601 format
  "training_end": "2024-12-31T23:59:59",
  "features": [              # Feature list
    "temperature",
    "humidity",
    "load_lag_1",
  ],
  "target": "load",          # Target variable
  "validation_split": 0.2,   # Validation set size (0.0-1.0)
  "random_seed": 42,         # For reproducibility
  "early_stopping_rounds": 50,  # Optional
  "distributed": false,      # Enable distributed training
  "ray_config": {            # Required if distributed=true
    "num_workers": 4,
    "cpus_per_worker": 2,
    "memory_per_worker": "4GB",
  }
}
```

### Hyperparameters by Algorithm

#### LightGBM (recommended for forecasting)

```python
{
  "n_estimators": 100,        # Number of boosting rounds
  "learning_rate": 0.1,       # Learning rate (0.01-0.3)
  "max_depth": 7,             # Max tree depth (3-15)
  "num_leaves": 31,           # Max leaves per tree
  "min_data_in_leaf": 20,     # Min samples per leaf
  "feature_fraction": 0.8,    # Feature sampling ratio
  "bagging_fraction": 0.8,    # Data sampling ratio
  "bagging_freq": 5,          # Bagging frequency
  "lambda_l1": 0.0,           # L1 regularization
  "lambda_l2": 0.0,           # L2 regularization
}
```

#### XGBoost

```python
{
  "n_estimators": 100,
  "learning_rate": 0.1,
  "max_depth": 7,
  "min_child_weight": 1,
  "gamma": 0.0,
  "subsample": 0.8,
  "colsample_bytree": 0.8,
  "reg_alpha": 0.0,           # L1 regularization
  "reg_lambda": 1.0,          # L2 regularization
}
```

#### Random Forest

```python
{
  "n_estimators": 100,
  "max_depth": None,          # Unlimited depth
  "min_samples_split": 2,
  "min_samples_leaf": 1,
  "max_features": "sqrt",     # or "log2", float, int
  "bootstrap": true,
}
```

---

## Job Lifecycle

### Job States

```
PENDING → RUNNING → COMPLETED
                 ↓
              FAILED
```

1. **PENDING**: Job created, waiting in queue
2. **RUNNING**: Job being executed
3. **COMPLETED**: Job finished successfully
4. **FAILED**: Job encountered error (will retry)

### Job Priority

Jobs are processed by priority:

- **critical**: Highest priority (emergency retraining)
- **high**: High priority (scheduled retraining)
- **normal**: Normal priority (default)
- **low**: Low priority (experimental training)

### Automatic Retry

Failed jobs are automatically retried with exponential backoff:

- Initial retry: 1 minute
- Second retry: 2 minutes
- Third retry: 4 minutes
- Max retries: 3

---

## Distributed Training

### Enabling Distributed Training

```python
config = {
  "model_type": "forecast",
  "algorithm": "lgbm",
  "distributed": True,
  "ray_config": {
    "num_workers": 4,         # Number of worker nodes
    "cpus_per_worker": 2,     # CPUs per worker
    "memory_per_worker": "4GB",  # Memory per worker
    "use_gpu": False,         # Enable GPU support
  },
  # ... rest of config
}
```

### Ray Cluster Management

The system automatically manages Ray clusters:

```python
# Check Ray cluster status
response = requests.get(f"{API_URL}/ai/training/ray/clusters")
clusters = response.json()

for cluster in clusters:
    print(f"Cluster: {cluster['cluster_id']}")
    print(f"Status: {cluster['status']}")
    print(f"Workers: {cluster['num_workers']}")
```

### When to Use Distributed Training

**Use distributed training for:**
- Large datasets (> 1M rows)
- Complex models (deep neural networks)
- Hyperparameter optimization (parallel trials)
- Time-constrained training

**Stick with single-node for:**
- Small datasets (< 100K rows)
- Simple models (linear, tree-based)
- Quick experimentation
- Limited resources

---

## Progress Monitoring

### Real-Time Status Updates

```python
import time

def wait_for_completion(job_id):
    """Poll job status until complete."""
    while True:
        response = requests.get(f"{API_URL}/ai/training/jobs/{job_id}")
        status = response.json()
        
        print(f"Status: {status['status']}")
        print(f"Progress: {status['progress']}%")
        print(f"Step: {status['current_step']}")
        
        if status['status'] in ['COMPLETED', 'FAILED']:
            break
        
        time.sleep(5)  # Poll every 5 seconds

wait_for_completion(job['job_id'])
```

### Streaming Logs

```python
# Get training logs
response = requests.get(
    f"{API_URL}/ai/training/jobs/{job_id}/logs",
    stream=True
)

for line in response.iter_lines():
    print(line.decode('utf-8'))
```

### Metrics Tracking

```python
# Get job metrics
response = requests.get(f"{API_URL}/ai/training/jobs/{job_id}/metrics")
metrics = response.json()

print("Training Metrics:")
print(f"  MAE: {metrics['mae']:.4f}")
print(f"  RMSE: {metrics['rmse']:.4f}")
print(f"  MAPE: {metrics['mape']:.4f}%")
print(f"  R² Score: {metrics['r2_score']:.4f}")

print(f"\nTraining Time: {metrics['training_duration_seconds']}s")
print(f"Data Size: {metrics['training_data_size']} rows")
```

---

## Error Handling

### Common Errors

#### 1. Data Loading Errors

```python
{
  "error": "DataLoadError",
  "message": "Failed to load training data",
  "details": {
    "reason": "Table not found: features.load_forecasting",
    "tenant_id": "acme-corp"
  }
}
```

**Solution**: Ensure feature tables exist and are populated.

#### 2. Configuration Errors

```python
{
  "error": "ConfigValidationError",
  "message": "Invalid training configuration",
  "details": {
    "field": "validation_split",
    "error": "Must be between 0.0 and 1.0"
  }
}
```

**Solution**: Validate configuration before submission.

#### 3. Resource Errors

```python
{
  "error": "ResourceError",
  "message": "Insufficient resources for distributed training",
  "details": {
    "requested_workers": 8,
    "available_workers": 4
  }
}
```

**Solution**: Reduce `num_workers` or scale up Ray cluster.

### Error Recovery

```python
# Retry failed job
response = requests.post(
    f"{API_URL}/ai/training/jobs/{job_id}/retry"
)

# Cancel running job
response = requests.delete(
    f"{API_URL}/ai/training/jobs/{job_id}"
)
```

---

## API Reference

### Create Training Job

**POST** `/ai/training/jobs`

```bash
curl -X POST "http://localhost:8000/ai/training/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "acme-corp",
    "model_type": "forecast",
    "config": { ... },
    "priority": "high"
  }'
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PENDING",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Get Job Status

**GET** `/ai/training/jobs/{job_id}`

```bash
curl "http://localhost:8000/ai/training/jobs/550e8400-..."
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "RUNNING",
  "progress": 65,
  "current_step": "training",
  "metrics": {
    "mae": 12.5,
    "rmse": 18.3
  }
}
```

### List Training Jobs

**GET** `/ai/training/jobs?tenant_id={tenant_id}&status={status}`

```bash
curl "http://localhost:8000/ai/training/jobs?tenant_id=acme-corp&status=COMPLETED"
```

### Get Job Metrics

**GET** `/ai/training/jobs/{job_id}/metrics`

### Get Training Logs

**GET** `/ai/training/jobs/{job_id}/logs`

### Retry Failed Job

**POST** `/ai/training/jobs/{job_id}/retry`

### Cancel Job

**DELETE** `/ai/training/jobs/{job_id}`

---

## Best Practices

### 1. Data Preparation

✅ **Do:**
- Ensure feature tables are up-to-date
- Handle missing values before training
- Normalize/scale features appropriately
- Use meaningful feature names

❌ **Don't:**
- Train on incomplete data
- Include target leakage features
- Use high-cardinality categorical features without encoding

### 2. Hyperparameter Selection

✅ **Do:**
- Start with default hyperparameters
- Use HPO for optimal tuning
- Document hyperparameter choices
- Consider computational budget

❌ **Don't:**
- Over-tune on validation set
- Use extreme values without reason
- Ignore early stopping

### 3. Resource Management

✅ **Do:**
- Monitor resource usage
- Scale workers based on data size
- Use appropriate priority levels
- Clean up old models

❌ **Don't:**
- Over-provision resources
- Run too many concurrent jobs
- Ignore memory limits

### 4. Model Lifecycle

✅ **Do:**
- Version all models
- Track experiment metrics
- Document model changes
- Validate before deployment

❌ **Don't:**
- Deploy untested models
- Skip baseline comparisons
- Ignore model degradation

### 5. Monitoring

✅ **Do:**
- Track training metrics
- Monitor job queues
- Set up alerts for failures
- Review logs regularly

❌ **Don't:**
- Ignore warning signs
- Let queues grow indefinitely
- Skip performance reviews

---

## Advanced Topics

### Custom Training Logic

You can extend the training pipeline with custom logic:

```python
from app.services.training_pipeline import TrainingPipeline

class CustomPipeline(TrainingPipeline):
    async def preprocess_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Custom preprocessing logic."""
        # Your custom transformations
        data = super().preprocess_data(data)
        data['custom_feature'] = data['load'] * data['temperature']
        return data
```

### Integration with MLflow

Track experiments automatically:

```python
config = {
  "model_type": "forecast",
  "algorithm": "lgbm",
  "mlflow_tracking": {
    "experiment_name": "load_forecasting_2025",
    "run_name": "baseline_v1",
    "tags": {
      "team": "data-science",
      "project": "demand-forecasting"
    }
  },
  # ... rest of config
}
```

### Scheduled Training

Use cron expressions for scheduled training:

```python
{
  "tenant_id": "acme-corp",
  "model_type": "forecast",
  "schedule": "0 2 * * 0",  # Weekly on Sunday at 2 AM
  "config": { ... }
}
```

---

## Troubleshooting

### Job Stuck in PENDING

**Symptoms**: Job remains in PENDING status for extended period.

**Possible Causes**:
1. Queue is full with higher priority jobs
2. System resources exhausted
3. Database connection issues

**Solutions**:
```bash
# Check queue depth
curl "http://localhost:8000/ai/training/jobs?status=PENDING"

# Check system resources
curl "http://localhost:8000/health"

# Increase job priority
curl -X PATCH "http://localhost:8000/ai/training/jobs/{job_id}" \
  -d '{"priority": "high"}'
```

### Training Fails Immediately

**Symptoms**: Job transitions from PENDING → RUNNING → FAILED quickly.

**Possible Causes**:
1. Invalid configuration
2. Missing data
3. Dependency errors

**Solutions**:
```bash
# Check error logs
curl "http://localhost:8000/ai/training/jobs/{job_id}/logs"

# Validate configuration
curl -X POST "http://localhost:8000/ai/training/validate" \
  -d '{"config": { ... }}'
```

### Out of Memory Errors

**Symptoms**: Training crashes with memory errors.

**Solutions**:
1. Reduce batch size
2. Enable distributed training
3. Increase worker memory
4. Use data sampling

```python
config = {
  "distributed": True,
  "ray_config": {
    "num_workers": 4,
    "memory_per_worker": "8GB",  # Increase memory
  },
  "training_options": {
    "batch_size": 1000,          # Reduce batch size
    "use_sample": 0.5,           # Use 50% of data
  }
}
```

---

## Support

For additional help:
- **Documentation**: https://docs.omarino.ai/training-pipeline
- **API Reference**: https://api.omarino.ai/docs
- **Support**: support@omarino.ai
- **GitHub**: https://github.com/omarino/ems-suite

---

*Last Updated: 2025-01-15*
