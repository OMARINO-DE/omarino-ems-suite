# CI/CD for Models Guide

Complete guide to automated model training, validation, and deployment using GitHub Actions and the OMARINO AI Hub.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [GitHub Actions Setup](#github-actions-setup)
4. [Model Validation](#model-validation)
5. [Automated Training](#automated-training)
6. [Deployment Workflow](#deployment-workflow)
7. [Monitoring and Alerts](#monitoring-and-alerts)
8. [Rollback Procedures](#rollback-procedures)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The OMARINO AI Hub provides complete CI/CD infrastructure for machine learning models, ensuring quality, reliability, and automated deployment.

### Key Features

- **Automated Training**: Trigger model training on code changes or schedules
- **Model Validation**: Comprehensive validation suite (performance, drift, stability)
- **Deployment Pipeline**: Automated deployment to production with approval gates
- **Monitoring**: Track model performance and data drift
- **Rollback**: Quick rollback to previous model versions
- **Notifications**: Slack/Email alerts for pipeline events

### CI/CD Pipeline Stages

```
┌──────────────────────────────────────────────────────────┐
│                    CI/CD Pipeline                         │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  1. Lint & Test ──> 2. Train Models ──> 3. Validate     │
│                                             │             │
│                                             ↓             │
│  6. Notify <── 5. Deploy <── 4. Approval                │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                   GitHub Actions Workflow                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌───────────┐    ┌──────────────┐    ┌────────────────┐  │
│  │   Lint &  │───>│    Train     │───>│    Validate    │  │
│  │   Test    │    │   Baseline   │    │    Models      │  │
│  └───────────┘    └──────────────┘    └────────────────┘  │
│                          │                     │            │
│                          ↓                     ↓            │
│                    ┌──────────────────────────────┐         │
│                    │   Model Validator Service    │         │
│                    │  - Performance Checks        │         │
│                    │  - Baseline Comparison       │         │
│                    │  - Data Drift Detection      │         │
│                    │  - Stability Tests           │         │
│                    └──────────────────────────────┘         │
│                               │                             │
│                               ↓                             │
│                    ┌──────────────────┐                     │
│                    │  MLflow Registry │                     │
│                    │  + PostgreSQL DB │                     │
│                    └──────────────────┘                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## GitHub Actions Setup

### Workflow File

Location: `.github/workflows/model-training.yml`

### Trigger Configuration

```yaml
on:
  # Run on push to main/develop
  push:
    branches:
      - main
      - develop
    paths:
      - 'ai-hub/**'
  
  # Run on pull requests
  pull_request:
    branches:
      - main
      - develop
    paths:
      - 'ai-hub/**'
  
  # Weekly scheduled training
  schedule:
    - cron: '0 2 * * 0'  # Sunday 2 AM UTC
  
  # Manual trigger with options
  workflow_dispatch:
    inputs:
      model_type:
        description: 'Model type to train'
        required: true
        default: 'forecast'
        type: choice
        options:
          - forecast
          - anomaly
```

### Environment Variables

Required secrets in GitHub repository:

```yaml
secrets:
  DATABASE_URL_PROD: postgresql://user:pass@host:5432/db
  MLFLOW_TRACKING_URI: http://mlflow-server:5000
  SLACK_WEBHOOK_URL: https://hooks.slack.com/services/...
```

### Setting Up Secrets

```bash
# Navigate to GitHub repository
# Settings > Secrets and variables > Actions > New repository secret

# Add each secret:
DATABASE_URL_PROD=postgresql://...
MLFLOW_TRACKING_URI=http://...
SLACK_WEBHOOK_URL=https://...
```

---

## Model Validation

### Validation Service

The `ModelValidator` service performs comprehensive checks:

#### 1. Performance Validation

```python
# Default thresholds for forecast models
thresholds = {
    "mae": {"max": 50.0},
    "rmse": {"max": 75.0},
    "mape": {"max": 10.0},
    "r2_score": {"min": 0.7},
}

# Validation fails if any threshold is violated
```

#### 2. Baseline Comparison

```python
# Compare to previous model
baseline_metrics = {
    "mae": 45.0,
    "rmse": 65.0,
}

# New model must be within 5% of baseline
tolerance = 0.05  # 5% degradation allowed
```

#### 3. Data Drift Detection

```python
# Statistical tests for distribution shifts
training_stats = {
    "temperature": {"mean": 20.0, "std": 5.0},
    "humidity": {"mean": 60.0, "std": 10.0},
}

# Z-test with p-value < 0.05 indicates drift
```

#### 4. Prediction Stability

```python
# Coefficient of variation check
cv_threshold = 0.5  # Max acceptable variability

# CV = std / mean
# Fails if predictions too variable
```

#### 5. Prediction Range

```python
# Outlier detection
outlier_threshold = 3.0  # Standard deviations

# Predictions should be within reasonable bounds
# Less than 5% outliers acceptable
```

### Using ModelValidator

```python
from app.services.model_validator import ModelValidator

# Create validator
validator = ModelValidator(
    model_type=ModelType.FORECAST,
    thresholds={
        "mae": {"max": 40.0},  # Custom threshold
    }
)

# Run validation
results = validator.validate_model(
    model_path="/path/to/model.pkl",
    validation_data=validation_df,
    target_column="load",
    baseline_metrics={"mae": 45.0},
    training_data_stats=training_stats,
)

# Check results
if not results["passed"]:
    print("Validation failed:")
    for failure in results["failures"]:
        print(f"  - {failure}")
```

### Validation Report

```python
# Generate report
report = validator.generate_validation_report(
    results,
    output_path="/tmp/validation_report.json"
)

print(report)
```

**Example Report:**
```
================================================================================
MODEL VALIDATION REPORT
================================================================================
Model Type: forecast
Timestamp: 2025-01-15T10:30:00Z
Overall Status: ✓ PASSED
Validation Data Size: 2000

────────────────────────────────────────────────────────────────────────────────
PERFORMANCE METRICS
────────────────────────────────────────────────────────────────────────────────
  ✓ mae: 38.5000
  ✓ rmse: 52.3000
  ✓ mape: 7.2000
  ✓ r2_score: 0.8500

────────────────────────────────────────────────────────────────────────────────
BASELINE COMPARISON
────────────────────────────────────────────────────────────────────────────────
  ✓ mae: 38.5000 vs 45.0000 (-14.44%)
  ✓ rmse: 52.3000 vs 65.0000 (-19.54%)

================================================================================
```

---

## Automated Training

### Training Job in GitHub Actions

```yaml
train-baseline:
  name: Train Baseline Models
  runs-on: ubuntu-latest
  
  strategy:
    matrix:
      model_type: [forecast, anomaly]
      algorithm: [lgbm, xgboost]
  
  steps:
    - name: Checkout code
      uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install poetry
        poetry install
    
    - name: Generate training data
      run: |
        poetry run python scripts/generate_training_data.py \
          --model-type ${{ matrix.model_type }} \
          --samples 10000 \
          --output /tmp/training_data.csv
    
    - name: Create training job
      run: |
        poetry run python scripts/create_training_job.py \
          --tenant-id "ci-baseline" \
          --model-type ${{ matrix.model_type }} \
          --algorithm ${{ matrix.algorithm }} \
          --data-path /tmp/training_data.csv \
          --priority high
    
    - name: Upload trained model
      uses: actions/upload-artifact@v4
      with:
        name: model-${{ matrix.model_type }}-${{ matrix.algorithm }}
        path: /tmp/model.pkl
```

### Training Scripts

#### generate_training_data.py

```python
#!/usr/bin/env python
"""Generate synthetic training data for CI/CD."""

import argparse
import pandas as pd
import numpy as np

def generate_forecast_data(samples: int) -> pd.DataFrame:
    """Generate time series data."""
    np.random.seed(42)
    
    dates = pd.date_range('2024-01-01', periods=samples, freq='H')
    
    data = pd.DataFrame({
        'timestamp': dates,
        'temperature': np.random.normal(20, 5, samples),
        'humidity': np.random.normal(60, 10, samples),
        'load': np.random.normal(1000, 200, samples),
    })
    
    return data

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-type', required=True)
    parser.add_argument('--samples', type=int, default=10000)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    
    if args.model_type == 'forecast':
        data = generate_forecast_data(args.samples)
    
    data.to_csv(args.output, index=False)
    print(f"Generated {len(data)} samples")
```

#### create_training_job.py

```python
#!/usr/bin/env python
"""Create training job via API."""

import argparse
import requests
import json

def create_job(tenant_id, model_type, algorithm, data_path, priority):
    """Create training job."""
    
    config = {
        "model_type": model_type,
        "algorithm": algorithm,
        "hyperparameters": {
            "n_estimators": 100,
            "learning_rate": 0.1,
            "max_depth": 7,
        },
        "training_start": "2024-01-01T00:00:00",
        "training_end": "2024-12-31T23:59:59",
        "features": ["temperature", "humidity"],
        "target": "load",
        "validation_split": 0.2,
    }
    
    response = requests.post(
        "http://localhost:8000/ai/training/jobs",
        json={
            "tenant_id": tenant_id,
            "model_type": model_type,
            "config": config,
            "priority": priority,
        }
    )
    
    job = response.json()
    print(f"Job created: {job['job_id']}")
    return job['job_id']

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tenant-id', required=True)
    parser.add_argument('--model-type', required=True)
    parser.add_argument('--algorithm', required=True)
    parser.add_argument('--data-path', required=True)
    parser.add_argument('--priority', default='normal')
    args = parser.parse_args()
    
    job_id = create_job(
        args.tenant_id,
        args.model_type,
        args.algorithm,
        args.data_path,
        args.priority,
    )
```

---

## Deployment Workflow

### Deployment Job

```yaml
deploy-models:
  name: Deploy Models
  runs-on: ubuntu-latest
  needs: validate-models
  if: github.ref == 'refs/heads/main'
  environment: production  # Requires approval
  
  steps:
    - name: Download trained model
      uses: actions/download-artifact@v4
      with:
        name: model-forecast-lgbm
        path: /tmp/
    
    - name: Register model in MLflow
      env:
        MLFLOW_TRACKING_URI: ${{ secrets.MLFLOW_TRACKING_URI }}
      run: |
        poetry run python scripts/register_model.py \
          --model-path /tmp/model.pkl \
          --model-name "forecast_lgbm_baseline" \
          --stage "Production"
    
    - name: Update model registry
      env:
        DATABASE_URL: ${{ secrets.DATABASE_URL_PROD }}
      run: |
        poetry run python scripts/update_registry.py \
          --model-name "forecast_lgbm_baseline" \
          --version ${{ github.sha }} \
          --status "deployed"
```

### Deployment Approval

Configure environment protection in GitHub:

```
Repository Settings > Environments > production
✓ Required reviewers: data-science-team
✓ Wait timer: 0 minutes
✓ Deployment branches: main only
```

---

## Monitoring and Alerts

### Slack Notifications

```yaml
notify:
  name: Send Notifications
  runs-on: ubuntu-latest
  needs: [validate-models, deploy-models]
  if: always()
  
  steps:
    - name: Send Slack notification
      uses: slackapi/slack-github-action@v1
      with:
        payload: |
          {
            "text": "Model Training Pipeline",
            "blocks": [
              {
                "type": "section",
                "text": {
                  "type": "mrkdwn",
                  "text": "*Model Training* - Run #${{ github.run_number }}"
                }
              },
              {
                "type": "section",
                "fields": [
                  {
                    "type": "mrkdwn",
                    "text": "*Status:*\n${{ job.status }}"
                  }
                ]
              }
            ]
          }
      env:
        SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### Performance Monitoring

```python
# scripts/monitor_model_performance.py

import requests
from datetime import datetime, timedelta

def check_model_performance(model_name: str):
    """Check if model performance is degrading."""
    
    # Get recent predictions
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    response = requests.get(
        f"http://api/models/{model_name}/performance",
        params={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
    )
    
    metrics = response.json()
    
    # Check thresholds
    if metrics["mae"] > 50.0:
        send_alert(f"Model {model_name} MAE exceeds threshold: {metrics['mae']}")
    
    if metrics["data_drift_detected"]:
        send_alert(f"Data drift detected for model {model_name}")

def send_alert(message: str):
    """Send alert to Slack."""
    requests.post(
        SLACK_WEBHOOK_URL,
        json={"text": f"⚠️ {message}"}
    )
```

### Scheduled Monitoring

```yaml
# .github/workflows/model-monitoring.yml

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours

jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - name: Check model performance
        run: |
          poetry run python scripts/monitor_model_performance.py
```

---

## Rollback Procedures

### Manual Rollback

```bash
# List model versions
curl "http://api/models/forecast_lgbm_baseline/versions"

# Rollback to previous version
curl -X POST "http://api/models/forecast_lgbm_baseline/rollback" \
  -d '{"target_version": "v1.2.3"}'
```

### Automated Rollback

```python
# scripts/auto_rollback.py

def should_rollback(current_metrics, baseline_metrics):
    """Determine if rollback is needed."""
    
    # Rollback if performance degrades > 20%
    degradation = (current_metrics["mae"] - baseline_metrics["mae"]) / baseline_metrics["mae"]
    
    if degradation > 0.20:
        return True, f"Performance degraded by {degradation*100:.1f}%"
    
    return False, None

def rollback_model(model_name, target_version):
    """Rollback model to previous version."""
    
    response = requests.post(
        f"http://api/models/{model_name}/rollback",
        json={"target_version": target_version}
    )
    
    if response.status_code == 200:
        send_alert(f"✓ Rolled back {model_name} to {target_version}")
    else:
        send_alert(f"✗ Rollback failed for {model_name}")
```

---

## Best Practices

### 1. Testing

✅ **Do:**
- Test validation logic locally
- Use synthetic data for CI
- Run full pipeline before merging
- Keep tests fast (< 10 minutes)

❌ **Don't:**
- Skip validation tests
- Use production data in CI
- Run long-running tests in PR checks
- Deploy untested models

### 2. Versioning

✅ **Do:**
- Version models with semantic versioning
- Tag commits that deploy models
- Track model lineage (data, code, config)
- Document model changes

❌ **Don't:**
- Deploy without version tags
- Lose track of model provenance
- Overwrite production models
- Skip changelog updates

### 3. Security

✅ **Do:**
- Use secrets for credentials
- Rotate secrets regularly
- Limit deployment permissions
- Audit model deployments

❌ **Don't:**
- Commit credentials
- Use shared accounts
- Allow unrestricted deployments
- Skip security scans

### 4. Monitoring

✅ **Do:**
- Monitor model performance
- Set up alerting
- Track data drift
- Review logs regularly

❌ **Don't:**
- Deploy and forget
- Ignore alerts
- Skip drift detection
- Let models degrade silently

---

## Troubleshooting

### Validation Failures

**Problem**: Model fails validation checks.

**Solutions**:
1. Check validation thresholds
2. Compare to baseline
3. Review training data quality
4. Adjust hyperparameters

```bash
# Get validation report
cat validation_report.json | jq '.failures'
```

### Deployment Stuck

**Problem**: Deployment waiting for approval.

**Solutions**:
1. Check GitHub environment settings
2. Verify reviewer availability
3. Review validation results
4. Manual approval in GitHub UI

### Performance Degradation

**Problem**: Model performance declining in production.

**Solutions**:
1. Check for data drift
2. Retrain with recent data
3. Review feature quality
4. Consider rollback

```python
# Check drift
python scripts/check_drift.py --model forecast_lgbm_baseline
```

---

## Support

For additional help:
- **Documentation**: https://docs.omarino.ai/cicd
- **GitHub Actions Docs**: https://docs.github.com/actions
- **Support**: support@omarino.ai

---

*Last Updated: 2025-01-15*
