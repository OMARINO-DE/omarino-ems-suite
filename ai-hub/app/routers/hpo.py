"""
HPO (Hyperparameter Optimization) API Router.

Provides endpoints for managing Optuna studies and trials:
- Create and start HPO studies
- Get study status and results
- List trials and view history
- Get parameter importance
- Delete studies
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.hpo_optimizer import HPOOptimizer
from app.models.training import ModelType, HyperparameterSpec

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/hpo", tags=["HPO"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class HPOStudyCreate(BaseModel):
    """Request to create HPO study."""
    study_name: str = Field(..., description="Unique study name")
    tenant_id: str = Field(..., description="Tenant ID")
    model_type: ModelType = Field(..., description="Model type")
    optimization_direction: str = Field("minimize", description="minimize or maximize")
    sampler_type: str = Field("tpe", description="tpe, random, or grid")
    pruner_type: str = Field("median", description="median, hyperband, or none")
    n_trials: int = Field(20, ge=1, le=1000, description="Number of trials")
    timeout_seconds: Optional[int] = Field(None, description="Max optimization time")


class HPOStudyResponse(BaseModel):
    """HPO study information."""
    study_id: str
    tenant_id: str
    model_type: str
    direction: str
    sampler: str
    pruner: str
    n_trials: int
    status: str
    trials_completed: Optional[int] = None
    trials_pruned: Optional[int] = None
    trials_failed: Optional[int] = None
    running_trials: Optional[int] = None
    best_value: Optional[float] = None
    best_params: Optional[dict] = None
    best_trial_number: Optional[int] = None
    created_at: Optional[str] = None


class HPOOptimizeRequest(BaseModel):
    """Request to start optimization."""
    hyperparameter_space: dict = Field(..., description="Hyperparameter search space")
    n_trials: int = Field(20, ge=1, le=1000)
    timeout_seconds: Optional[int] = None
    n_jobs: int = Field(1, ge=1, le=16, description="Parallel jobs")


class HPOOptimizeResponse(BaseModel):
    """Optimization results."""
    study_id: str
    best_value: float
    best_params: dict
    best_trial_number: int
    n_trials: int
    completed_trials: int
    pruned_trials: int
    failed_trials: int


class HPOTrialResponse(BaseModel):
    """Single trial result."""
    trial_number: int
    state: str
    value: Optional[float]
    params: dict
    datetime_start: Optional[str]
    datetime_complete: Optional[str]
    duration_seconds: Optional[float]


class HPOHistoryResponse(BaseModel):
    """Optimization history for visualization."""
    trial_numbers: List[int]
    values: List[float]
    best_values: List[float]


class HPOParamImportanceResponse(BaseModel):
    """Parameter importance scores."""
    study_id: str
    importances: dict


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

def get_hpo_optimizer() -> HPOOptimizer:
    """Get HPO optimizer instance."""
    # In production, this would use PostgreSQL storage
    # storage_url = "postgresql://user:pass@host:5432/ai_hub"
    return HPOOptimizer(storage_url=None)


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/studies", response_model=HPOStudyResponse, status_code=201)
async def create_study(
    request: HPOStudyCreate,
    optimizer: HPOOptimizer = Depends(get_hpo_optimizer),
):
    """
    Create new HPO study.
    
    Creates an Optuna study with specified configuration.
    
    **Example Request:**
    ```bash
    curl -X POST "http://localhost:8000/ai/hpo/studies" \\
      -H "Content-Type: application/json" \\
      -d '{
        "study_name": "forecast_optimization_v1",
        "tenant_id": "acme-corp",
        "model_type": "forecast",
        "optimization_direction": "minimize",
        "sampler_type": "tpe",
        "pruner_type": "median",
        "n_trials": 50
      }'
    ```
    
    **Response:**
    ```json
    {
      "study_id": "forecast_optimization_v1",
      "tenant_id": "acme-corp",
      "model_type": "forecast",
      "direction": "minimize",
      "sampler": "tpe",
      "pruner": "median",
      "n_trials": 50,
      "status": "created"
    }
    ```
    """
    try:
        result = await optimizer.create_study(
            study_name=request.study_name,
            tenant_id=request.tenant_id,
            model_type=request.model_type,
            optimization_direction=request.optimization_direction,
            sampler_type=request.sampler_type,
            pruner_type=request.pruner_type,
            n_trials=request.n_trials,
            timeout_seconds=request.timeout_seconds,
        )
        
        return HPOStudyResponse(**result)
        
    except Exception as e:
        logger.error(f"Failed to create study: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create study: {str(e)}")


@router.get("/studies/{study_name}", response_model=HPOStudyResponse)
async def get_study(
    study_name: str,
    optimizer: HPOOptimizer = Depends(get_hpo_optimizer),
):
    """
    Get study status and results.
    
    Returns current status, progress, and best results if available.
    
    **Example Request:**
    ```bash
    curl "http://localhost:8000/ai/hpo/studies/forecast_optimization_v1"
    ```
    """
    try:
        result = await optimizer.get_study_status(study_name)
        return HPOStudyResponse(**result)
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get study: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get study: {str(e)}")


@router.post("/studies/{study_name}/optimize", response_model=HPOOptimizeResponse)
async def optimize_study(
    study_name: str,
    request: HPOOptimizeRequest,
    optimizer: HPOOptimizer = Depends(get_hpo_optimizer),
):
    """
    Start hyperparameter optimization.
    
    Runs the optimization process with specified hyperparameter space.
    This endpoint will block until optimization completes or times out.
    
    **Example Request:**
    ```bash
    curl -X POST "http://localhost:8000/ai/hpo/studies/forecast_optimization_v1/optimize" \\
      -H "Content-Type: application/json" \\
      -d '{
        "hyperparameter_space": {
          "n_estimators": {"type": "int", "low": 50, "high": 500},
          "learning_rate": {"type": "float", "low": 0.01, "high": 0.3, "log": true},
          "max_depth": {"type": "int", "low": 3, "high": 15}
        },
        "n_trials": 50,
        "n_jobs": 4
      }'
    ```
    
    **Note:** For long-running optimizations, consider using a task queue
    and polling the study status instead of waiting for this endpoint to return.
    """
    try:
        # Convert dict to HyperparameterSpec objects
        hp_space = {}
        for param_name, spec_dict in request.hyperparameter_space.items():
            hp_space[param_name] = HyperparameterSpec(**spec_dict)
        
        # Define objective function (placeholder - in production this would
        # call the actual training pipeline)
        def objective_func(params: dict, trial) -> float:
            # TODO: Integrate with actual training pipeline
            # For now, return a dummy score
            import random
            return random.uniform(0.1, 1.0)
        
        result = await optimizer.optimize(
            study_name=study_name,
            objective_func=objective_func,
            hyperparameter_space=hp_space,
            n_trials=request.n_trials,
            timeout_seconds=request.timeout_seconds,
            n_jobs=request.n_jobs,
        )
        
        return HPOOptimizeResponse(**result)
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@router.get("/studies/{study_name}/trials", response_model=List[HPOTrialResponse])
async def get_trials(
    study_name: str,
    include_pruned: bool = Query(False, description="Include pruned trials"),
    optimizer: HPOOptimizer = Depends(get_hpo_optimizer),
):
    """
    Get trial history for study.
    
    Returns list of all trials with their results and parameters.
    
    **Example Request:**
    ```bash
    curl "http://localhost:8000/ai/hpo/studies/forecast_optimization_v1/trials?include_pruned=false"
    ```
    """
    try:
        trials = await optimizer.get_trial_history(
            study_name=study_name,
            include_pruned=include_pruned,
        )
        
        return [HPOTrialResponse(**trial) for trial in trials]
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get trials: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get trials: {str(e)}")


@router.get("/studies/{study_name}/importance", response_model=HPOParamImportanceResponse)
async def get_param_importance(
    study_name: str,
    optimizer: HPOOptimizer = Depends(get_hpo_optimizer),
):
    """
    Get parameter importance scores.
    
    Uses fANOVA to calculate which hyperparameters have the most impact
    on the objective value.
    
    **Example Request:**
    ```bash
    curl "http://localhost:8000/ai/hpo/studies/forecast_optimization_v1/importance"
    ```
    
    **Example Response:**
    ```json
    {
      "study_id": "forecast_optimization_v1",
      "importances": {
        "learning_rate": 0.45,
        "n_estimators": 0.32,
        "max_depth": 0.23
      }
    }
    ```
    """
    try:
        importances = await optimizer.get_param_importances(study_name)
        
        return HPOParamImportanceResponse(
            study_id=study_name,
            importances=importances,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get importances: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get importances: {str(e)}")


@router.get("/studies/{study_name}/history", response_model=HPOHistoryResponse)
async def get_optimization_history(
    study_name: str,
    optimizer: HPOOptimizer = Depends(get_hpo_optimizer),
):
    """
    Get optimization history for visualization.
    
    Returns trial numbers, values, and cumulative best values for plotting
    optimization progress over time.
    
    **Example Request:**
    ```bash
    curl "http://localhost:8000/ai/hpo/studies/forecast_optimization_v1/history"
    ```
    
    **Use Case:**
    Plot optimization progress to see if the study is converging or needs more trials.
    """
    try:
        history = await optimizer.get_optimization_history(study_name)
        return HPOHistoryResponse(**history)
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")


@router.delete("/studies/{study_name}", status_code=200)
async def delete_study(
    study_name: str,
    optimizer: HPOOptimizer = Depends(get_hpo_optimizer),
):
    """
    Delete HPO study.
    
    Removes study and all associated trials from storage.
    
    **Example Request:**
    ```bash
    curl -X DELETE "http://localhost:8000/ai/hpo/studies/forecast_optimization_v1"
    ```
    """
    try:
        await optimizer.delete_study(study_name)
        return {"message": f"Study '{study_name}' deleted successfully"}
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete study: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete study: {str(e)}")


@router.get("/suggest-hyperparameters/{model_type}", response_model=dict)
async def suggest_hyperparameters(
    model_type: ModelType,
    optimizer: HPOOptimizer = Depends(get_hpo_optimizer),
):
    """
    Get suggested hyperparameter search space for model type.
    
    Returns recommended hyperparameter ranges based on model type.
    
    **Example Request:**
    ```bash
    curl "http://localhost:8000/ai/hpo/suggest-hyperparameters/forecast"
    ```
    
    **Example Response:**
    ```json
    {
      "n_estimators": {"type": "int", "low": 50, "high": 500, "step": 50},
      "learning_rate": {"type": "float", "low": 0.01, "high": 0.3, "log": true},
      "max_depth": {"type": "int", "low": 3, "high": 15}
    }
    ```
    """
    try:
        suggestions = optimizer.suggest_hyperparameters(model_type)
        
        # Convert HyperparameterSpec objects to dicts
        result = {}
        for param_name, spec in suggestions.items():
            result[param_name] = spec.model_dump()
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")
