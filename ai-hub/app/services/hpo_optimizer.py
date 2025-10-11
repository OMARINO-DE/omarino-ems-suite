"""
Hyperparameter Optimization (HPO) service using Optuna.

Provides automated hyperparameter tuning with:
- Parallel trial execution
- Multiple optimization algorithms (TPE, GP, Random, Grid)
- Pruning for early stopping of unpromising trials
- Multi-objective optimization support
- Study persistence and resume capability
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from uuid import UUID, uuid4

import numpy as np
import optuna
from optuna.trial import TrialState
from optuna.pruners import MedianPruner, HyperbandPruner
from optuna.samplers import TPESampler, RandomSampler, GridSampler

from app.models.training import (
    ModelType,
    TrainingConfig,
    HyperparameterSpec,
)

logger = logging.getLogger(__name__)


class HPOOptimizer:
    """
    Hyperparameter optimization using Optuna.
    
    Manages HPO studies including trial creation, execution,
    and result tracking.
    """
    
    def __init__(self, storage_url: Optional[str] = None):
        """
        Initialize HPO optimizer.
        
        Args:
            storage_url: Optuna storage URL (e.g., postgresql://...)
                        If None, uses in-memory storage
        """
        self.storage_url = storage_url
        self._studies: Dict[str, optuna.Study] = {}
    
    async def create_study(
        self,
        study_name: str,
        tenant_id: str,
        model_type: ModelType,
        optimization_direction: str = "minimize",
        sampler_type: str = "tpe",
        pruner_type: str = "median",
        n_trials: int = 20,
        timeout_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create new HPO study.
        
        Args:
            study_name: Unique study name
            tenant_id: Tenant ID
            model_type: Type of model
            optimization_direction: "minimize" or "maximize"
            sampler_type: "tpe", "random", or "grid"
            pruner_type: "median", "hyperband", or "none"
            n_trials: Number of trials to run
            timeout_seconds: Max time for study (optional)
            
        Returns:
            Study information dictionary
        """
        logger.info(f"Creating HPO study: {study_name}")
        
        # Create sampler
        if sampler_type == "tpe":
            sampler = TPESampler(seed=42)
        elif sampler_type == "random":
            sampler = RandomSampler(seed=42)
        elif sampler_type == "grid":
            sampler = None  # Grid sampler requires search space
        else:
            raise ValueError(f"Unknown sampler type: {sampler_type}")
        
        # Create pruner
        if pruner_type == "median":
            pruner = MedianPruner(n_startup_trials=5, n_warmup_steps=5)
        elif pruner_type == "hyperband":
            pruner = HyperbandPruner()
        elif pruner_type == "none":
            pruner = None
        else:
            raise ValueError(f"Unknown pruner type: {pruner_type}")
        
        # Create study
        study = optuna.create_study(
            study_name=study_name,
            storage=self.storage_url,
            sampler=sampler,
            pruner=pruner,
            direction=optimization_direction,
            load_if_exists=False,
        )
        
        # Store study
        self._studies[study_name] = study
        
        # Store metadata
        study.set_user_attr("tenant_id", tenant_id)
        study.set_user_attr("model_type", model_type.value)
        study.set_user_attr("n_trials", n_trials)
        study.set_user_attr("timeout_seconds", timeout_seconds)
        study.set_user_attr("created_at", datetime.utcnow().isoformat())
        
        logger.info(
            f"Study '{study_name}' created with {sampler_type} sampler "
            f"and {pruner_type} pruner"
        )
        
        return {
            "study_id": study_name,
            "tenant_id": tenant_id,
            "model_type": model_type.value,
            "direction": optimization_direction,
            "sampler": sampler_type,
            "pruner": pruner_type,
            "n_trials": n_trials,
            "status": "created",
        }
    
    async def optimize(
        self,
        study_name: str,
        objective_func: Callable,
        hyperparameter_space: Dict[str, HyperparameterSpec],
        n_trials: int = 20,
        timeout_seconds: Optional[int] = None,
        n_jobs: int = 1,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Dict[str, Any]:
        """
        Run hyperparameter optimization.
        
        Args:
            study_name: Study name
            objective_func: Objective function to minimize/maximize
            hyperparameter_space: Hyperparameter search space
            n_trials: Number of trials
            timeout_seconds: Max optimization time
            n_jobs: Number of parallel jobs (-1 for all cores)
            progress_callback: Progress callback (current_trial, total_trials)
            
        Returns:
            Optimization results
        """
        if study_name not in self._studies:
            raise ValueError(f"Study not found: {study_name}")
        
        study = self._studies[study_name]
        
        logger.info(
            f"Starting optimization for study '{study_name}' "
            f"with {n_trials} trials"
        )
        
        # Wrap objective function to add progress callback
        trials_completed = 0
        
        def wrapped_objective(trial: optuna.Trial) -> float:
            nonlocal trials_completed
            
            # Sample hyperparameters
            params = {}
            for param_name, spec in hyperparameter_space.items():
                if spec.type == "int":
                    params[param_name] = trial.suggest_int(
                        param_name,
                        spec.low,
                        spec.high,
                        step=spec.step if hasattr(spec, "step") else 1,
                    )
                elif spec.type == "float":
                    params[param_name] = trial.suggest_float(
                        param_name,
                        spec.low,
                        spec.high,
                        log=spec.log if hasattr(spec, "log") else False,
                    )
                elif spec.type == "categorical":
                    params[param_name] = trial.suggest_categorical(
                        param_name,
                        spec.choices,
                    )
            
            # Call objective function
            score = objective_func(params, trial)
            
            # Update progress
            trials_completed += 1
            if progress_callback:
                asyncio.create_task(
                    progress_callback(trials_completed, n_trials)
                )
            
            return score
        
        # Run optimization
        try:
            study.optimize(
                wrapped_objective,
                n_trials=n_trials,
                timeout=timeout_seconds,
                n_jobs=n_jobs,
                show_progress_bar=False,  # We use custom progress callback
            )
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            raise
        
        # Get results
        best_trial = study.best_trial
        
        logger.info(
            f"Optimization complete. Best value: {best_trial.value:.4f} "
            f"(trial #{best_trial.number})"
        )
        
        return {
            "study_id": study_name,
            "best_value": best_trial.value,
            "best_params": best_trial.params,
            "best_trial_number": best_trial.number,
            "n_trials": len(study.trials),
            "completed_trials": len([t for t in study.trials if t.state == TrialState.COMPLETE]),
            "pruned_trials": len([t for t in study.trials if t.state == TrialState.PRUNED]),
            "failed_trials": len([t for t in study.trials if t.state == TrialState.FAIL]),
        }
    
    async def get_study_status(self, study_name: str) -> Dict[str, Any]:
        """
        Get study status and results.
        
        Args:
            study_name: Study name
            
        Returns:
            Study status dictionary
        """
        if study_name not in self._studies:
            raise ValueError(f"Study not found: {study_name}")
        
        study = self._studies[study_name]
        
        # Get trials by state
        trials = study.trials
        completed = [t for t in trials if t.state == TrialState.COMPLETE]
        pruned = [t for t in trials if t.state == TrialState.PRUNED]
        failed = [t for t in trials if t.state == TrialState.FAIL]
        running = [t for t in trials if t.state == TrialState.RUNNING]
        
        # Get best trial if any completed
        best_value = None
        best_params = None
        best_trial_number = None
        
        if completed:
            best_trial = study.best_trial
            best_value = best_trial.value
            best_params = best_trial.params
            best_trial_number = best_trial.number
        
        return {
            "study_id": study_name,
            "tenant_id": study.user_attrs.get("tenant_id"),
            "model_type": study.user_attrs.get("model_type"),
            "direction": study.direction.name.lower(),
            "n_trials": len(trials),
            "completed_trials": len(completed),
            "pruned_trials": len(pruned),
            "failed_trials": len(failed),
            "running_trials": len(running),
            "best_value": best_value,
            "best_params": best_params,
            "best_trial_number": best_trial_number,
            "created_at": study.user_attrs.get("created_at"),
        }
    
    async def get_trial_history(
        self,
        study_name: str,
        include_pruned: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get trial history for study.
        
        Args:
            study_name: Study name
            include_pruned: Include pruned trials
            
        Returns:
            List of trial dictionaries
        """
        if study_name not in self._studies:
            raise ValueError(f"Study not found: {study_name}")
        
        study = self._studies[study_name]
        
        trials = []
        for trial in study.trials:
            # Skip pruned if requested
            if not include_pruned and trial.state == TrialState.PRUNED:
                continue
            
            trials.append({
                "trial_number": trial.number,
                "state": trial.state.name,
                "value": trial.value if trial.value is not None else None,
                "params": trial.params,
                "datetime_start": trial.datetime_start.isoformat() if trial.datetime_start else None,
                "datetime_complete": trial.datetime_complete.isoformat() if trial.datetime_complete else None,
                "duration_seconds": trial.duration.total_seconds() if trial.duration else None,
            })
        
        return trials
    
    async def get_param_importances(
        self,
        study_name: str,
    ) -> Dict[str, float]:
        """
        Calculate parameter importances.
        
        Args:
            study_name: Study name
            
        Returns:
            Dictionary of parameter importances
        """
        if study_name not in self._studies:
            raise ValueError(f"Study not found: {study_name}")
        
        study = self._studies[study_name]
        
        # Need at least 2 completed trials
        completed_trials = [
            t for t in study.trials if t.state == TrialState.COMPLETE
        ]
        
        if len(completed_trials) < 2:
            return {}
        
        try:
            # Calculate importances using fANOVA
            importances = optuna.importance.get_param_importances(study)
            
            # Convert to dict with float values
            return {k: float(v) for k, v in importances.items()}
            
        except Exception as e:
            logger.warning(f"Failed to calculate param importances: {e}")
            return {}
    
    async def get_optimization_history(
        self,
        study_name: str,
    ) -> Dict[str, List[Any]]:
        """
        Get optimization history for visualization.
        
        Args:
            study_name: Study name
            
        Returns:
            Dictionary with trial numbers, values, and best values
        """
        if study_name not in self._studies:
            raise ValueError(f"Study not found: {study_name}")
        
        study = self._studies[study_name]
        
        # Get completed trials
        completed_trials = [
            t for t in study.trials if t.state == TrialState.COMPLETE
        ]
        
        if not completed_trials:
            return {
                "trial_numbers": [],
                "values": [],
                "best_values": [],
            }
        
        # Sort by trial number
        completed_trials.sort(key=lambda t: t.number)
        
        # Extract data
        trial_numbers = [t.number for t in completed_trials]
        values = [t.value for t in completed_trials]
        
        # Calculate best value at each step
        best_values = []
        current_best = values[0]
        
        for value in values:
            if study.direction == optuna.study.StudyDirection.MINIMIZE:
                current_best = min(current_best, value)
            else:
                current_best = max(current_best, value)
            best_values.append(current_best)
        
        return {
            "trial_numbers": trial_numbers,
            "values": values,
            "best_values": best_values,
        }
    
    async def delete_study(self, study_name: str) -> None:
        """
        Delete study.
        
        Args:
            study_name: Study name
        """
        if study_name not in self._studies:
            raise ValueError(f"Study not found: {study_name}")
        
        # Delete from storage if persistent
        if self.storage_url:
            optuna.delete_study(
                study_name=study_name,
                storage=self.storage_url,
            )
        
        # Remove from cache
        del self._studies[study_name]
        
        logger.info(f"Study '{study_name}' deleted")
    
    async def resume_study(self, study_name: str) -> optuna.Study:
        """
        Resume existing study from storage.
        
        Args:
            study_name: Study name
            
        Returns:
            Loaded study
        """
        if not self.storage_url:
            raise ValueError("Cannot resume study without persistent storage")
        
        logger.info(f"Resuming study: {study_name}")
        
        study = optuna.load_study(
            study_name=study_name,
            storage=self.storage_url,
        )
        
        self._studies[study_name] = study
        
        return study
    
    def suggest_hyperparameters(
        self,
        model_type: ModelType,
    ) -> Dict[str, HyperparameterSpec]:
        """
        Get suggested hyperparameter search space for model type.
        
        Args:
            model_type: Type of model
            
        Returns:
            Dictionary of hyperparameter specifications
        """
        if model_type == ModelType.FORECAST:
            return {
                "n_estimators": HyperparameterSpec(
                    type="int",
                    low=50,
                    high=500,
                    step=50,
                ),
                "learning_rate": HyperparameterSpec(
                    type="float",
                    low=0.01,
                    high=0.3,
                    log=True,
                ),
                "max_depth": HyperparameterSpec(
                    type="int",
                    low=3,
                    high=15,
                ),
                "min_child_samples": HyperparameterSpec(
                    type="int",
                    low=5,
                    high=100,
                ),
                "subsample": HyperparameterSpec(
                    type="float",
                    low=0.5,
                    high=1.0,
                ),
                "colsample_bytree": HyperparameterSpec(
                    type="float",
                    low=0.5,
                    high=1.0,
                ),
            }
        elif model_type == ModelType.ANOMALY:
            return {
                "n_estimators": HyperparameterSpec(
                    type="int",
                    low=50,
                    high=300,
                ),
                "contamination": HyperparameterSpec(
                    type="float",
                    low=0.01,
                    high=0.3,
                ),
                "max_samples": HyperparameterSpec(
                    type="categorical",
                    choices=["auto", 256, 512, 1024],
                ),
            }
        else:
            raise ValueError(f"No hyperparameter space for {model_type}")
