"""
Experiments API Router.

Provides endpoints for experiment tracking and management:
- Create experiments
- Start/end runs
- Log metrics, parameters, artifacts
- Compare runs
- Get experiment statistics
"""

import logging
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.experiment_tracker import ExperimentTracker
from app.models.training import ModelType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/experiments", tags=["Experiments"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ExperimentCreate(BaseModel):
    """Request to create experiment."""
    name: str = Field(..., description="Experiment name")
    tenant_id: str = Field(..., description="Tenant ID")
    model_type: ModelType = Field(..., description="Model type")
    description: Optional[str] = Field(None, description="Experiment description")
    tags: Optional[Dict[str, str]] = Field(None, description="Additional tags")


class ExperimentResponse(BaseModel):
    """Experiment information."""
    experiment_id: str
    name: str
    tenant_id: str
    model_type: str


class RunCreate(BaseModel):
    """Request to start run."""
    experiment_id: str = Field(..., description="Experiment ID")
    run_name: str = Field(..., description="Run name")
    tags: Optional[Dict[str, str]] = Field(None, description="Run tags")


class RunResponse(BaseModel):
    """Run information."""
    run_id: str
    experiment_id: str
    run_name: str
    status: str
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    params: Dict[str, Any]
    metrics: Dict[str, float]
    tags: Dict[str, str]
    artifact_uri: str


class LogMetricsRequest(BaseModel):
    """Request to log metrics."""
    run_id: str = Field(..., description="Run ID")
    metrics: Dict[str, float] = Field(..., description="Metrics to log")
    step: Optional[int] = Field(None, description="Step number")


class LogParamsRequest(BaseModel):
    """Request to log parameters."""
    run_id: str = Field(..., description="Run ID")
    params: Dict[str, Any] = Field(..., description="Parameters to log")


class CompareRunsRequest(BaseModel):
    """Request to compare runs."""
    run_ids: List[str] = Field(..., description="Run IDs to compare")
    metric_keys: Optional[List[str]] = Field(None, description="Specific metrics")


class CompareRunsResponse(BaseModel):
    """Run comparison response."""
    runs: List[Dict[str, Any]]
    comparison_time: str


class ExperimentStatsResponse(BaseModel):
    """Experiment statistics."""
    experiment_id: str
    total_runs: int
    status_counts: Dict[str, int]
    metric_stats: Dict[str, Dict[str, float]]


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

def get_experiment_tracker() -> ExperimentTracker:
    """Get experiment tracker instance."""
    # In production, configure with remote tracking server
    # tracking_uri = "http://mlflow-server:5000"
    return ExperimentTracker(tracking_uri=None)


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/", response_model=ExperimentResponse, status_code=201)
async def create_experiment(
    request: ExperimentCreate,
    tracker: ExperimentTracker = Depends(get_experiment_tracker),
):
    """
    Create new experiment.
    
    Experiments organize related training runs together.
    
    **Example Request:**
    ```bash
    curl -X POST "http://localhost:8000/ai/experiments/" \\
      -H "Content-Type: application/json" \\
      -d '{
        "name": "load_forecasting_2025_q4",
        "tenant_id": "acme-corp",
        "model_type": "forecast",
        "description": "Load forecasting experiments for Q4 2025",
        "tags": {"quarter": "Q4", "year": "2025"}
      }'
    ```
    """
    try:
        experiment_id = tracker.create_experiment(
            name=request.name,
            tenant_id=request.tenant_id,
            model_type=request.model_type,
            description=request.description,
            tags=request.tags,
        )
        
        return ExperimentResponse(
            experiment_id=experiment_id,
            name=request.name,
            tenant_id=request.tenant_id,
            model_type=request.model_type.value,
        )
        
    except Exception as e:
        logger.error(f"Failed to create experiment: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create experiment: {str(e)}"
        )


@router.post("/runs", response_model=Dict[str, str], status_code=201)
async def start_run(
    request: RunCreate,
    tracker: ExperimentTracker = Depends(get_experiment_tracker),
):
    """
    Start new training run.
    
    A run represents a single model training execution.
    
    **Example Request:**
    ```bash
    curl -X POST "http://localhost:8000/ai/experiments/runs" \\
      -H "Content-Type: application/json" \\
      -d '{
        "experiment_id": "1",
        "run_name": "lgbm_baseline_v1",
        "tags": {"baseline": "true", "algorithm": "lgbm"}
      }'
    ```
    """
    try:
        run_id = tracker.start_run(
            experiment_id=request.experiment_id,
            run_name=request.run_name,
            tags=request.tags,
        )
        
        return {"run_id": run_id, "message": "Run started successfully"}
        
    except Exception as e:
        logger.error(f"Failed to start run: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start run: {str(e)}"
        )


@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: str,
    tracker: ExperimentTracker = Depends(get_experiment_tracker),
):
    """
    Get run details.
    
    Returns complete run information including metrics, parameters, and artifacts.
    
    **Example Request:**
    ```bash
    curl "http://localhost:8000/ai/experiments/runs/abc123"
    ```
    """
    try:
        run_data = tracker.get_run(run_id)
        return RunResponse(**run_data)
        
    except Exception as e:
        logger.error(f"Failed to get run: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Run not found: {str(e)}"
        )


@router.post("/runs/metrics")
async def log_metrics(
    request: LogMetricsRequest,
    tracker: ExperimentTracker = Depends(get_experiment_tracker),
):
    """
    Log metrics to run.
    
    Metrics are numerical values tracked over time (e.g., MAE, RMSE, accuracy).
    
    **Example Request:**
    ```bash
    curl -X POST "http://localhost:8000/ai/experiments/runs/metrics" \\
      -H "Content-Type: application/json" \\
      -d '{
        "run_id": "abc123",
        "metrics": {
          "mae": 12.5,
          "rmse": 18.3,
          "mape": 5.6,
          "r2_score": 0.85
        },
        "step": 100
      }'
    ```
    """
    try:
        tracker.log_metrics(
            run_id=request.run_id,
            metrics=request.metrics,
            step=request.step,
        )
        
        return {"message": "Metrics logged successfully"}
        
    except Exception as e:
        logger.error(f"Failed to log metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to log metrics: {str(e)}"
        )


@router.post("/runs/params")
async def log_params(
    request: LogParamsRequest,
    tracker: ExperimentTracker = Depends(get_experiment_tracker),
):
    """
    Log parameters to run.
    
    Parameters are configuration values (e.g., hyperparameters, model config).
    
    **Example Request:**
    ```bash
    curl -X POST "http://localhost:8000/ai/experiments/runs/params" \\
      -H "Content-Type: application/json" \\
      -d '{
        "run_id": "abc123",
        "params": {
          "n_estimators": 100,
          "learning_rate": 0.1,
          "max_depth": 7,
          "random_seed": 42
        }
      }'
    ```
    """
    try:
        tracker.log_params(
            run_id=request.run_id,
            params=request.params,
        )
        
        return {"message": "Parameters logged successfully"}
        
    except Exception as e:
        logger.error(f"Failed to log params: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to log params: {str(e)}"
        )


@router.delete("/runs/{run_id}")
async def end_run(
    run_id: str,
    status: str = Query("FINISHED", description="Final status: FINISHED, FAILED, KILLED"),
    tracker: ExperimentTracker = Depends(get_experiment_tracker),
):
    """
    End training run.
    
    Marks the run as complete with a final status.
    
    **Example Request:**
    ```bash
    curl -X DELETE "http://localhost:8000/ai/experiments/runs/abc123?status=FINISHED"
    ```
    """
    try:
        tracker.end_run(run_id=run_id, status=status)
        return {"message": f"Run ended with status: {status}"}
        
    except Exception as e:
        logger.error(f"Failed to end run: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to end run: {str(e)}"
        )


@router.post("/runs/compare", response_model=CompareRunsResponse)
async def compare_runs(
    request: CompareRunsRequest,
    tracker: ExperimentTracker = Depends(get_experiment_tracker),
):
    """
    Compare multiple runs.
    
    Returns side-by-side comparison of metrics and parameters.
    
    **Example Request:**
    ```bash
    curl -X POST "http://localhost:8000/ai/experiments/runs/compare" \\
      -H "Content-Type: application/json" \\
      -d '{
        "run_ids": ["abc123", "def456", "ghi789"],
        "metric_keys": ["mae", "rmse", "mape"]
      }'
    ```
    """
    try:
        comparison = tracker.compare_runs(
            run_ids=request.run_ids,
            metric_keys=request.metric_keys,
        )
        
        return CompareRunsResponse(**comparison)
        
    except Exception as e:
        logger.error(f"Failed to compare runs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compare runs: {str(e)}"
        )


@router.get("/{experiment_id}/best-run")
async def get_best_run(
    experiment_id: str,
    metric_key: str = Query(..., description="Metric to optimize"),
    maximize: bool = Query(False, description="True to maximize, False to minimize"),
    tracker: ExperimentTracker = Depends(get_experiment_tracker),
):
    """
    Get best run from experiment.
    
    Returns the run with the best value for the specified metric.
    
    **Example Request:**
    ```bash
    curl "http://localhost:8000/ai/experiments/1/best-run?metric_key=mae&maximize=false"
    ```
    """
    try:
        best_run = tracker.get_best_run(
            experiment_id=experiment_id,
            metric_key=metric_key,
            maximize=maximize,
        )
        
        if not best_run:
            raise HTTPException(
                status_code=404,
                detail="No runs found for this experiment"
            )
        
        return best_run
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get best run: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get best run: {str(e)}"
        )


@router.get("/{experiment_id}/stats", response_model=ExperimentStatsResponse)
async def get_experiment_stats(
    experiment_id: str,
    tracker: ExperimentTracker = Depends(get_experiment_tracker),
):
    """
    Get experiment statistics.
    
    Returns summary statistics for all runs in the experiment.
    
    **Example Request:**
    ```bash
    curl "http://localhost:8000/ai/experiments/1/stats"
    ```
    
    **Example Response:**
    ```json
    {
      "experiment_id": "1",
      "total_runs": 25,
      "status_counts": {
        "FINISHED": 20,
        "FAILED": 3,
        "RUNNING": 2
      },
      "metric_stats": {
        "mae": {
          "count": 20,
          "mean": 12.5,
          "std": 2.3,
          "min": 8.2,
          "max": 18.7
        }
      }
    }
    ```
    """
    try:
        stats = tracker.get_experiment_stats(experiment_id)
        return ExperimentStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Failed to get experiment stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get experiment stats: {str(e)}"
        )


@router.get("/{experiment_id}/runs")
async def search_runs(
    experiment_id: str,
    filter_string: Optional[str] = Query(None, description="Filter expression"),
    max_results: int = Query(100, ge=1, le=1000),
    order_by: Optional[str] = Query(None, description="Order by expression"),
    tracker: ExperimentTracker = Depends(get_experiment_tracker),
):
    """
    Search runs in experiment.
    
    Supports filtering and sorting of runs.
    
    **Example Request:**
    ```bash
    # Get all runs
    curl "http://localhost:8000/ai/experiments/1/runs"
    
    # Get runs with MAE < 15
    curl "http://localhost:8000/ai/experiments/1/runs?filter_string=metrics.mae%20%3C%2015"
    
    # Get top 10 runs by MAE
    curl "http://localhost:8000/ai/experiments/1/runs?max_results=10&order_by=metrics.mae%20ASC"
    ```
    """
    try:
        order_by_list = [order_by] if order_by else None
        
        runs = tracker.search_runs(
            experiment_ids=[experiment_id],
            filter_string=filter_string,
            max_results=max_results,
            order_by=order_by_list,
        )
        
        return {"runs": runs, "total": len(runs)}
        
    except Exception as e:
        logger.error(f"Failed to search runs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search runs: {str(e)}"
        )
