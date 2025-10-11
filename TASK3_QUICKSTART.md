# Task 3 Quickstart Guide

**Get started with the Advanced ML Training Pipeline in 5 minutes!**

---

## 🚀 Quick Setup

### 1. Prerequisites

```bash
# Required
- Python 3.11+
- PostgreSQL 14+
- 8GB RAM minimum

# Optional (for distributed training)
- Ray 2.8+
```

### 2. Installation (2 minutes)

```bash
# Clone and navigate
cd ai-hub

# Install dependencies
poetry install

# Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost:5432/ai_hub"
export MLFLOW_TRACKING_URI="http://localhost:5000"

# Run migrations
poetry run alembic upgrade head

# Start service
poetry run uvicorn app.main:app --reload
```

### 3. Verify Installation

```bash
# Check API is running
curl http://localhost:8000/health

# Should return: {"status": "healthy"}
```

---

## 📝 Basic Training Job (3 minutes)

### Create Your First Training Job

```python
import requests

API_URL = "http://localhost:8000"

# Step 1: Create training job
response = requests.post(
    f"{API_URL}/ai/training/jobs",
    json={
        "tenant_id": "demo-tenant",
        "model_type": "forecast",
        "config": {
            "model_type": "forecast",
            "algorithm": "lgbm",
            "hyperparameters": {
                "n_estimators": 100,
                "learning_rate": 0.1,
                "max_depth": 7,
            },
            "training_start": "2024-01-01T00:00:00",
            "training_end": "2024-12-31T23:59:59",
            "features": [
                "temperature",
                "humidity",
                "hour_of_day",
                "day_of_week",
            ],
            "target": "load",
            "validation_split": 0.2,
            "random_seed": 42,
        },
        "priority": "high",
    }
)

job = response.json()
print(f"✓ Job created: {job['job_id']}")

# Step 2: Check status
import time
while True:
    response = requests.get(f"{API_URL}/ai/training/jobs/{job['job_id']}")
    status = response.json()
    
    print(f"Status: {status['status']} | Progress: {status['progress']}%")
    
    if status['status'] in ['COMPLETED', 'FAILED']:
        break
    
    time.sleep(5)

# Step 3: Get results
if status['status'] == 'COMPLETED':
    print(f"\n✓ Training completed!")
    print(f"MAE: {status['metrics']['mae']:.2f}")
    print(f"RMSE: {status['metrics']['rmse']:.2f}")
    print(f"Model: {status['model_path']}")
```

**Expected Output:**
```
✓ Job created: 550e8400-e29b-41d4-a716-446655440000
Status: RUNNING | Progress: 20%
Status: RUNNING | Progress: 60%
Status: RUNNING | Progress: 100%

✓ Training completed!
MAE: 38.45
RMSE: 52.31
Model: /models/demo-tenant/forecast/lgbm/v1.0.0.pkl
```

---

## 🔍 HPO Example (5 minutes)

### Run Hyperparameter Optimization

```python
import requests

API_URL = "http://localhost:8000"

# Step 1: Create HPO study
response = requests.post(
    f"{API_URL}/ai/hpo/studies",
    json={
        "study_name": "my_first_hpo",
        "tenant_id": "demo-tenant",
        "model_type": "forecast",
        "algorithm": "lgbm",
        "objective_metric": "mae",
        "direction": "minimize",
        "sampler": "tpe",
        "pruner": "median",
        "n_trials": 20,
        "timeout": 300,  # 5 minutes
    }
)

study = response.json()
print(f"✓ Study created: {study['study_name']}")

# Step 2: Run optimization
response = requests.post(
    f"{API_URL}/ai/hpo/studies/my_first_hpo/optimize",
    json={
        "n_trials": 20,
        "timeout": 300,
        "n_jobs": 2,  # Run 2 trials in parallel
    }
)

result = response.json()
print(f"\n✓ Optimization complete!")
print(f"Best MAE: {result['best_value']:.2f}")
print(f"\nBest Hyperparameters:")
for param, value in result['best_params'].items():
    print(f"  {param}: {value}")

# Step 3: Get parameter importance
response = requests.get(
    f"{API_URL}/ai/hpo/studies/my_first_hpo/importance"
)
importance = response.json()

print(f"\nParameter Importance:")
for param, score in importance['importances'].items():
    print(f"  {param}: {score:.4f}")
```

**Expected Output:**
```
✓ Study created: my_first_hpo

✓ Optimization complete!
Best MAE: 32.18

Best Hyperparameters:
  n_estimators: 150
  learning_rate: 0.08
  max_depth: 9
  num_leaves: 45

Parameter Importance:
  learning_rate: 0.4523
  max_depth: 0.2891
  n_estimators: 0.1654
  num_leaves: 0.0932
```

---

## 📊 Experiment Tracking (3 minutes)

### Track Your Experiments with MLflow

```python
import requests

API_URL = "http://localhost:8000"

# Step 1: Create experiment
response = requests.post(
    f"{API_URL}/ai/experiments",
    json={
        "name": "load_forecasting_2025",
        "tenant_id": "demo-tenant",
        "model_type": "forecast",
        "description": "My first experiment",
    }
)

experiment = response.json()
print(f"✓ Experiment created: {experiment['experiment_id']}")

# Step 2: Start run
response = requests.post(
    f"{API_URL}/ai/experiments/runs",
    json={
        "experiment_id": experiment['experiment_id'],
        "run_name": "baseline_v1",
        "tags": {"baseline": "true"},
    }
)

run = response.json()
print(f"✓ Run started: {run['run_id']}")

# Step 3: Log parameters
requests.post(
    f"{API_URL}/ai/experiments/runs/params",
    json={
        "run_id": run['run_id'],
        "params": {
            "n_estimators": 100,
            "learning_rate": 0.1,
            "max_depth": 7,
        }
    }
)
print(f"✓ Parameters logged")

# Step 4: Log metrics (can be called multiple times for time-series)
for step in [10, 20, 30]:
    requests.post(
        f"{API_URL}/ai/experiments/runs/metrics",
        json={
            "run_id": run['run_id'],
            "metrics": {
                "mae": 45.0 - step,  # Improving over time
                "rmse": 65.0 - step,
            },
            "step": step,
        }
    )
print(f"✓ Metrics logged")

# Step 5: End run
requests.delete(
    f"{API_URL}/ai/experiments/runs/{run['run_id']}?status=FINISHED"
)
print(f"✓ Run ended")

# Step 6: Get experiment statistics
response = requests.get(
    f"{API_URL}/ai/experiments/{experiment['experiment_id']}/stats"
)
stats = response.json()

print(f"\n✓ Experiment Statistics:")
print(f"Total Runs: {stats['total_runs']}")
print(f"Average MAE: {stats['metric_stats']['mae']['mean']:.2f}")
```

**Expected Output:**
```
✓ Experiment created: 1
✓ Run started: abc123def456
✓ Parameters logged
✓ Metrics logged
✓ Run ended

✓ Experiment Statistics:
Total Runs: 1
Average MAE: 30.00
```

---

## ⚡ Common Use Cases

### 1. Quick Model Training

```bash
# Using curl
curl -X POST "http://localhost:8000/ai/training/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "demo",
    "model_type": "forecast",
    "config": {
      "algorithm": "lgbm",
      "hyperparameters": {"n_estimators": 100}
    }
  }'
```

### 2. List All Training Jobs

```python
response = requests.get(
    f"{API_URL}/ai/training/jobs?tenant_id=demo-tenant"
)
jobs = response.json()

for job in jobs:
    print(f"{job['job_id']}: {job['status']} ({job['progress']}%)")
```

### 3. Get Best HPO Parameters

```bash
curl "http://localhost:8000/ai/hpo/suggest-hyperparameters/forecast"
```

### 4. Compare Multiple Runs

```python
response = requests.post(
    f"{API_URL}/ai/experiments/runs/compare",
    json={
        "run_ids": ["run1", "run2", "run3"],
        "metric_keys": ["mae", "rmse"],
    }
)

comparison = response.json()
for run in comparison['runs']:
    print(f"Run {run['run_id']}: MAE={run['metrics']['mae']:.2f}")
```

---

## 🔧 Troubleshooting

### Service Won't Start

```bash
# Check database connection
psql $DATABASE_URL -c "SELECT 1"

# Check port availability
lsof -i :8000

# Check logs
poetry run uvicorn app.main:app --log-level debug
```

### Job Stuck in PENDING

```python
# Check queue depth
response = requests.get(f"{API_URL}/ai/training/jobs?status=PENDING")
pending_jobs = len(response.json())
print(f"Pending jobs: {pending_jobs}")

# Increase priority
requests.patch(
    f"{API_URL}/ai/training/jobs/{job_id}",
    json={"priority": "high"}
)
```

### Training Fails Immediately

```python
# Check error logs
response = requests.get(f"{API_URL}/ai/training/jobs/{job_id}/logs")
logs = response.json()

for log in logs:
    if log['level'] == 'ERROR':
        print(log['message'])
```

---

## 📚 Next Steps

### Learn More

1. **Training Pipeline**: Read `docs/ai/training-pipeline.md` for advanced features
2. **HPO Guide**: Read `docs/ai/hyperparameter-optimization.md` for optimization strategies
3. **CI/CD Guide**: Read `docs/ai/ci-cd-for-models.md` for automated deployment
4. **Complete Summary**: Read `TASK3_COMPLETE_SUMMARY.md` for full details

### Try Advanced Features

```python
# Distributed training
config = {
    "distributed": True,
    "ray_config": {
        "num_workers": 4,
        "cpus_per_worker": 2,
    }
}

# Custom search space for HPO
search_space = {
    "n_estimators": {
        "type": "int",
        "low": 50,
        "high": 200,
    },
    "learning_rate": {
        "type": "float",
        "low": 0.01,
        "high": 0.3,
        "log": True,
    }
}

# Model validation in CI/CD
from app.services.model_validator import ModelValidator

validator = ModelValidator(model_type=ModelType.FORECAST)
results = validator.validate_model(model_path, validation_data, "target")
```

---

## 🎯 Cheat Sheet

### Most Common Commands

```bash
# Create training job
POST /ai/training/jobs

# Get job status
GET /ai/training/jobs/{job_id}

# Create HPO study
POST /ai/hpo/studies

# Run optimization
POST /ai/hpo/studies/{study_name}/optimize

# Create experiment
POST /ai/experiments

# Start run
POST /ai/experiments/runs

# Log metrics
POST /ai/experiments/runs/metrics
```

### Environment Variables

```bash
# Required
DATABASE_URL=postgresql://user:pass@host:5432/db
MLFLOW_TRACKING_URI=http://mlflow:5000

# Optional
RAY_ADDRESS=ray://ray-head:10001
LOG_LEVEL=INFO
CORS_ORIGINS=["*"]
```

### Useful Queries

```python
# Get all completed jobs
requests.get(f"{API_URL}/ai/training/jobs?status=COMPLETED")

# Get failed jobs
requests.get(f"{API_URL}/ai/training/jobs?status=FAILED")

# Get jobs by tenant
requests.get(f"{API_URL}/ai/training/jobs?tenant_id=acme-corp")

# Get best run in experiment
requests.get(f"{API_URL}/ai/experiments/1/best-run?metric_key=mae")
```

---

## 💡 Tips and Tricks

### Performance Tips

1. **Use distributed training** for datasets > 1M rows
2. **Enable pruning** in HPO to save 50-70% compute
3. **Run parallel trials** with `n_jobs` parameter
4. **Use validation split** 0.2 (20%) for good generalization

### Best Practices

1. **Always set random_seed** for reproducibility
2. **Log to MLflow** for experiment tracking
3. **Use HPO** for baseline models
4. **Validate before deployment** using ModelValidator

### Common Patterns

```python
# Pattern 1: Train → HPO → Train with best params
job1 = create_training_job(default_params)
wait_for_completion(job1)

study = create_hpo_study()
best_params = run_optimization(study)

job2 = create_training_job(best_params)

# Pattern 2: Experiment tracking
experiment = create_experiment()
for config in configs:
    run = start_run(experiment)
    train_and_log(run, config)
    end_run(run)
best = get_best_run(experiment)

# Pattern 3: CI/CD validation
model = train_model()
results = validate_model(model)
if results['passed']:
    deploy_model(model)
else:
    alert_team(results['failures'])
```

---

## 🆘 Getting Help

### Resources
- **Documentation**: `/docs` endpoint or `docs/ai/` folder
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **Examples**: `examples/` folder in repository

### Support
- **GitHub Issues**: https://github.com/omarino/ems-suite/issues
- **Email**: support@omarino.ai
- **Slack**: https://omarino.slack.com

---

## ✅ You're Ready!

You now know how to:
- ✅ Create and monitor training jobs
- ✅ Run hyperparameter optimization
- ✅ Track experiments with MLflow
- ✅ Validate and deploy models

**Start training your models!** 🚀

---

*For complete details, see `TASK3_COMPLETE_SUMMARY.md`*
*Last Updated: 2025-01-15*
