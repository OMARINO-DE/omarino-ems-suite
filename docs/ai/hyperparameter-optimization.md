# Hyperparameter Optimization Guide

Complete guide to automated hyperparameter optimization using Optuna in the OMARINO AI Hub.

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Study Configuration](#study-configuration)
4. [Hyperparameter Search Spaces](#hyperparameter-search-spaces)
5. [Optimization Algorithms](#optimization-algorithms)
6. [Pruning Strategies](#pruning-strategies)
7. [Running Optimizations](#running-optimizations)
8. [Analyzing Results](#analyzing-results)
9. [Parameter Importance](#parameter-importance)
10. [API Reference](#api-reference)
11. [Best Practices](#best-practices)

---

## Overview

Hyperparameter optimization (HPO) automatically finds the best hyperparameters for your machine learning models. The OMARINO AI Hub uses [Optuna](https://optuna.org/), a state-of-the-art HPO framework.

### Key Features

- **Automated Search**: Intelligent search algorithms (TPE, Random, Grid)
- **Early Stopping**: Pruning strategies to terminate unpromising trials
- **Parallel Execution**: Run multiple trials concurrently
- **Persistence**: Resume interrupted studies
- **Analysis Tools**: Parameter importance, optimization history, visualization
- **Multi-Tenancy**: Tenant isolation and resource management

### When to Use HPO

✅ **Use HPO when:**
- Building baseline models for new use cases
- Model performance is critical
- You have sufficient computational budget
- Need reproducible results

❌ **Skip HPO when:**
- Quick prototyping or experimentation
- Using pre-tuned models
- Limited time/resources
- Default hyperparameters work well

---

## Getting Started

### Quick Start Example

```python
import requests

API_URL = "http://localhost:8000"

# Create HPO study
response = requests.post(
    f"{API_URL}/ai/hpo/studies",
    json={
        "study_name": "load_forecasting_hpo_2025",
        "tenant_id": "acme-corp",
        "model_type": "forecast",
        "algorithm": "lgbm",
        "objective_metric": "mae",
        "direction": "minimize",
        "sampler": "tpe",
        "pruner": "median",
        "n_trials": 100,
        "timeout": 3600,
        "metadata": {
            "description": "HPO for load forecasting baseline",
            "owner": "data-science-team"
        }
    }
)

study = response.json()
print(f"Study created: {study['study_name']}")
```

### Start Optimization

```python
# Run optimization
response = requests.post(
    f"{API_URL}/ai/hpo/studies/{study['study_name']}/optimize",
    json={
        "n_trials": 100,
        "timeout": 3600,
        "n_jobs": 4,  # Parallel trials
    }
)

result = response.json()
print(f"Best trial: {result['best_trial']}")
print(f"Best params: {result['best_params']}")
print(f"Best value: {result['best_value']}")
```

---

## Study Configuration

### StudyCreate Schema

```python
{
  "study_name": "my_hpo_study",
  "tenant_id": "acme-corp",
  "model_type": "forecast",  # or "anomaly"
  "algorithm": "lgbm",       # lgbm, xgboost, rf, mlp
  "objective_metric": "mae", # mae, rmse, mape, r2_score, f1_score, etc.
  "direction": "minimize",   # or "maximize"
  "sampler": "tpe",          # tpe, random, grid
  "pruner": "median",        # median, hyperband, none
  "n_trials": 100,           # Number of trials
  "timeout": 3600,           # Timeout in seconds (1 hour)
  "search_space": {          # Optional custom search space
    "n_estimators": {
      "type": "int",
      "low": 50,
      "high": 200,
      "step": 10
    },
    "learning_rate": {
      "type": "float",
      "low": 0.01,
      "high": 0.3,
      "log": true
    }
  },
  "metadata": {
    "description": "HPO study for...",
    "owner": "data-science-team"
  }
}
```

### Study Naming Conventions

Good study names:
- `{model_type}_{algorithm}_{date}` - e.g., `forecast_lgbm_2025_01`
- `{use_case}_{version}` - e.g., `load_forecasting_v2`
- `{tenant}_{model}_{experiment}` - e.g., `acme_anomaly_baseline`

Bad study names:
- `test` - Too vague
- `study1` - Not descriptive
- `my_study_final_v2_FINAL` - Unclear versioning

---

## Hyperparameter Search Spaces

### Default Search Spaces

The system provides sensible defaults for each algorithm:

#### LightGBM (Forecasting)

```python
{
  "n_estimators": {"type": "int", "low": 50, "high": 500, "step": 10},
  "learning_rate": {"type": "float", "low": 0.01, "high": 0.3, "log": true},
  "max_depth": {"type": "int", "low": 3, "high": 15},
  "num_leaves": {"type": "int", "low": 20, "high": 150},
  "min_data_in_leaf": {"type": "int", "low": 10, "high": 100},
  "feature_fraction": {"type": "float", "low": 0.6, "high": 1.0},
  "bagging_fraction": {"type": "float", "low": 0.6, "high": 1.0},
  "bagging_freq": {"type": "int", "low": 1, "high": 10},
  "lambda_l1": {"type": "float", "low": 0.0, "high": 10.0},
  "lambda_l2": {"type": "float", "low": 0.0, "high": 10.0},
}
```

#### XGBoost

```python
{
  "n_estimators": {"type": "int", "low": 50, "high": 500, "step": 10},
  "learning_rate": {"type": "float", "low": 0.01, "high": 0.3, "log": true},
  "max_depth": {"type": "int", "low": 3, "high": 15},
  "min_child_weight": {"type": "int", "low": 1, "high": 10},
  "gamma": {"type": "float", "low": 0.0, "high": 5.0},
  "subsample": {"type": "float", "low": 0.6, "high": 1.0},
  "colsample_bytree": {"type": "float", "low": 0.6, "high": 1.0},
  "reg_alpha": {"type": "float", "low": 0.0, "high": 10.0},
  "reg_lambda": {"type": "float", "low": 0.0, "high": 10.0},
}
```

### Custom Search Spaces

Define custom search spaces for specific needs:

```python
{
  "search_space": {
    # Integer parameter
    "n_estimators": {
      "type": "int",
      "low": 100,
      "high": 500,
      "step": 50  # Optional: sample in steps
    },
    
    # Float parameter (linear scale)
    "feature_fraction": {
      "type": "float",
      "low": 0.5,
      "high": 1.0
    },
    
    # Float parameter (log scale) - good for learning rates
    "learning_rate": {
      "type": "float",
      "low": 0.001,
      "high": 0.3,
      "log": true
    },
    
    # Categorical parameter
    "booster": {
      "type": "categorical",
      "choices": ["gbtree", "gblinear", "dart"]
    }
  }
}
```

---

## Optimization Algorithms

### TPE (Tree-structured Parzen Estimator)

**Recommended** for most use cases.

```python
{
  "sampler": "tpe",
  "sampler_params": {
    "n_startup_trials": 10,  # Random trials before TPE starts
    "n_ei_candidates": 24,   # Candidates evaluated per trial
    "seed": 42               # For reproducibility
  }
}
```

**When to use:**
- Default choice for HPO
- Medium to large search spaces (5-20 hyperparameters)
- Continuous and categorical parameters
- Limited computational budget

**Pros:**
- Efficient search strategy
- Handles mixed parameter types
- Good balance of exploration/exploitation

**Cons:**
- Requires initial random trials
- Can be slow with very large search spaces

### Random Search

```python
{
  "sampler": "random",
  "sampler_params": {
    "seed": 42
  }
}
```

**When to use:**
- Baseline for comparison
- Very large search spaces
- Highly noisy objective functions
- Simple parallelization

**Pros:**
- Simple and robust
- Easy to parallelize
- No assumptions about search space

**Cons:**
- Less efficient than TPE
- Requires more trials for good results

### Grid Search

```python
{
  "sampler": "grid",
  "sampler_params": {
    "search_space": {
      "n_estimators": [50, 100, 200, 500],
      "learning_rate": [0.01, 0.05, 0.1, 0.3],
      "max_depth": [3, 5, 7, 10]
    }
  }
}
```

**When to use:**
- Small search spaces (< 5 hyperparameters)
- Exhaustive search required
- Reproducible experiments
- Comparing specific configurations

**Pros:**
- Exhaustive coverage
- Reproducible
- Simple to understand

**Cons:**
- Exponential growth with parameters
- Inefficient for large spaces
- No early stopping benefits

---

## Pruning Strategies

Pruning terminates unpromising trials early to save computational resources.

### Median Pruning

**Recommended** for most use cases.

```python
{
  "pruner": "median",
  "pruner_params": {
    "n_startup_trials": 5,      # No pruning for first 5 trials
    "n_warmup_steps": 10,       # No pruning for first 10 steps
    "interval_steps": 1         # Check every step
  }
}
```

**How it works:**
- Compares current trial to median of completed trials
- Prunes if performing worse than median at same step

**When to use:**
- Default choice
- Iterative algorithms (boosting, neural networks)
- Many trials planned

### Hyperband Pruning

```python
{
  "pruner": "hyperband",
  "pruner_params": {
    "min_resource": 10,         # Minimum iterations
    "max_resource": 100,        # Maximum iterations
    "reduction_factor": 3       # Elimination rate
  }
}
```

**How it works:**
- Allocates resources using successive halving
- Promotes promising trials, eliminates poor ones

**When to use:**
- Large number of trials
- Resource-intensive training
- Clear performance trajectory

### No Pruning

```python
{
  "pruner": "none"
}
```

**When to use:**
- Quick training (< 1 minute per trial)
- Non-iterative algorithms
- Small number of trials
- Debugging

---

## Running Optimizations

### Sequential Optimization

```python
# Run 100 trials sequentially
response = requests.post(
    f"{API_URL}/ai/hpo/studies/{study_name}/optimize",
    json={
        "n_trials": 100,
        "timeout": 3600,
    }
)
```

### Parallel Optimization

```python
# Run 100 trials with 4 parallel workers
response = requests.post(
    f"{API_URL}/ai/hpo/studies/{study_name}/optimize",
    json={
        "n_trials": 100,
        "timeout": 3600,
        "n_jobs": 4,  # 4 parallel trials
    }
)
```

**Speedup**: Linear up to number of CPU cores available.

### Time-Limited Optimization

```python
# Run for 1 hour, as many trials as possible
response = requests.post(
    f"{API_URL}/ai/hpo/studies/{study_name}/optimize",
    json={
        "n_trials": 1000,  # Upper limit
        "timeout": 3600,   # 1 hour (will stop early)
    }
)
```

### Resume Interrupted Study

Studies are automatically persisted and can be resumed:

```python
# Resume study with additional trials
response = requests.post(
    f"{API_URL}/ai/hpo/studies/{study_name}/optimize",
    json={
        "n_trials": 50,  # Run 50 more trials
    }
)
```

---

## Analyzing Results

### Get Study Status

```python
response = requests.get(
    f"{API_URL}/ai/hpo/studies/{study_name}"
)
status = response.json()

print(f"Status: {status['state']}")
print(f"Best Trial: {status['best_trial']}")
print(f"Best Value: {status['best_value']:.4f}")
print(f"Completed Trials: {status['n_trials']}")
print(f"\nBest Hyperparameters:")
for param, value in status['best_params'].items():
    print(f"  {param}: {value}")
```

### Get Trial History

```python
response = requests.get(
    f"{API_URL}/ai/hpo/studies/{study_name}/trials"
)
trials = response.json()

# Analyze trial results
for trial in trials:
    print(f"Trial {trial['number']}: {trial['value']:.4f}")
    print(f"  Params: {trial['params']}")
    print(f"  State: {trial['state']}")
```

### Filter Trials

```python
# Get only completed trials
response = requests.get(
    f"{API_URL}/ai/hpo/studies/{study_name}/trials?state=COMPLETE"
)

# Get top 10 trials
response = requests.get(
    f"{API_URL}/ai/hpo/studies/{study_name}/trials?limit=10"
)
```

---

## Parameter Importance

Understand which hyperparameters matter most:

```python
response = requests.get(
    f"{API_URL}/ai/hpo/studies/{study_name}/importance"
)
importance = response.json()

print("Parameter Importance (fANOVA):")
for param, score in importance['importances'].items():
    print(f"  {param}: {score:.4f}")
```

**Example Output:**
```
Parameter Importance (fANOVA):
  learning_rate: 0.45      # Most important
  max_depth: 0.28
  n_estimators: 0.15
  num_leaves: 0.08
  feature_fraction: 0.04   # Least important
```

**How to use:**
- Focus tuning on high-importance parameters
- Fix low-importance parameters to defaults
- Reduce search space in future studies

---

## API Reference

### Create Study

**POST** `/ai/hpo/studies`

```bash
curl -X POST "http://localhost:8000/ai/hpo/studies" \
  -H "Content-Type: application/json" \
  -d '{
    "study_name": "my_study",
    "tenant_id": "acme-corp",
    "model_type": "forecast",
    "algorithm": "lgbm",
    "objective_metric": "mae",
    "direction": "minimize",
    "sampler": "tpe",
    "pruner": "median",
    "n_trials": 100
  }'
```

### Run Optimization

**POST** `/ai/hpo/studies/{study_name}/optimize`

```bash
curl -X POST "http://localhost:8000/ai/hpo/studies/my_study/optimize" \
  -H "Content-Type: application/json" \
  -d '{
    "n_trials": 100,
    "timeout": 3600,
    "n_jobs": 4
  }'
```

### Get Study Status

**GET** `/ai/hpo/studies/{study_name}`

### Get Trial History

**GET** `/ai/hpo/studies/{study_name}/trials`

### Get Parameter Importance

**GET** `/ai/hpo/studies/{study_name}/importance`

### Get Optimization History

**GET** `/ai/hpo/studies/{study_name}/history`

### Delete Study

**DELETE** `/ai/hpo/studies/{study_name}`

### Get Hyperparameter Suggestions

**GET** `/ai/hpo/suggest-hyperparameters/{model_type}`

---

## Best Practices

### 1. Study Design

✅ **Do:**
- Start with default search spaces
- Use meaningful study names
- Document study purpose in metadata
- Plan computational budget

❌ **Don't:**
- Use overly wide search spaces
- Optimize too many parameters at once
- Run without time/trial limits
- Forget to version studies

### 2. Computational Efficiency

✅ **Do:**
- Use pruning for iterative algorithms
- Parallelize when possible
- Set reasonable timeouts
- Resume interrupted studies

❌ **Don't:**
- Run without pruning on slow training
- Over-parallelize (more workers than cores)
- Run indefinitely
- Start new studies for same problem

### 3. Search Space Design

✅ **Do:**
- Use log scale for learning rates
- Set reasonable bounds
- Include important parameters
- Test search space first

❌ **Don't:**
- Use extreme values
- Include too many parameters
- Forget constraints between parameters
- Use same space for different algorithms

### 4. Result Analysis

✅ **Do:**
- Analyze parameter importance
- Compare to baseline
- Validate on holdout set
- Document findings

❌ **Don't:**
- Use best params without validation
- Ignore parameter interactions
- Over-fit to validation set
- Skip statistical significance tests

---

## Advanced Topics

### Multi-Objective Optimization

Optimize multiple metrics simultaneously:

```python
{
  "objective_metrics": ["mae", "training_time"],
  "directions": ["minimize", "minimize"],
  "weights": [0.8, 0.2]  # MAE is more important
}
```

### Conditional Search Spaces

Parameters that depend on other parameters:

```python
{
  "booster": {
    "type": "categorical",
    "choices": ["gbtree", "dart"]
  },
  # Only used when booster="dart"
  "rate_drop": {
    "type": "float",
    "low": 0.0,
    "high": 1.0,
    "condition": {"booster": "dart"}
  }
}
```

### Transfer Learning

Use results from previous studies:

```python
{
  "warm_start_from": "previous_study_name",
  "n_trials": 50  # Additional trials
}
```

---

## Troubleshooting

### All Trials Pruned

**Symptoms**: Most or all trials are pruned early.

**Possible Causes**:
1. Pruning too aggressive
2. Initial trials performing poorly
3. Search space too wide

**Solutions**:
```python
{
  "pruner_params": {
    "n_startup_trials": 10,    # Increase
    "n_warmup_steps": 20,      # Increase
  }
}
```

### No Improvement

**Symptoms**: Best value doesn't improve after many trials.

**Possible Causes**:
1. Search space doesn't contain good parameters
2. Too few trials
3. Local optimum

**Solutions**:
1. Widen search space
2. Run more trials
3. Try different sampler
4. Check data quality

### Study Takes Too Long

**Symptoms**: Optimization running for hours without completion.

**Possible Causes**:
1. Each trial is slow
2. Too many trials requested
3. Sequential execution

**Solutions**:
```python
{
  "n_jobs": 4,           # Parallelize
  "timeout": 3600,       # Set timeout
  "pruner": "median",    # Enable pruning
}
```

---

## Support

For additional help:
- **Documentation**: https://docs.omarino.ai/hpo
- **API Reference**: https://api.omarino.ai/docs
- **Optuna Docs**: https://optuna.readthedocs.io/
- **Support**: support@omarino.ai

---

*Last Updated: 2025-01-15*
