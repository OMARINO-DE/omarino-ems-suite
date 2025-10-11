"""
Experiment Tracking service using MLflow.

Provides experiment management and tracking capabilities:
- Experiment creation and organization
- Metrics logging (MAE, RMSE, MAPE, etc.)
- Parameter logging (hyperparameters, config)
- Artifact storage (models, plots, data)
- Run comparison and analysis
- Model versioning and lineage
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pathlib import Path
import json

try:
    import mlflow
    from mlflow.tracking import MlflowClient
    from mlflow.entities import RunStatus, ViewType
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    MlflowClient = None
    RunStatus = None
    ViewType = None

from app.models.training import ModelType, TrainingConfig

logger = logging.getLogger(__name__)


class ExperimentTracker:
    """
    MLflow-based experiment tracking.
    
    Manages experiment lifecycle including metrics, parameters,
    artifacts, and model versioning.
    """
    
    def __init__(
        self,
        tracking_uri: Optional[str] = None,
        artifact_location: Optional[str] = None,
    ):
        """
        Initialize experiment tracker.
        
        Args:
            tracking_uri: MLflow tracking server URI (None = local files)
            artifact_location: Base artifact storage location
        """
        if not MLFLOW_AVAILABLE:
            raise ImportError(
                "MLflow is not installed. Install with: pip install mlflow"
            )
        
        self.tracking_uri = tracking_uri or "file:///tmp/mlruns"
        self.artifact_location = artifact_location
        
        # Set tracking URI
        mlflow.set_tracking_uri(self.tracking_uri)
        
        # Create client
        self.client = MlflowClient(tracking_uri=self.tracking_uri)
        
        logger.info(f"ExperimentTracker initialized with URI: {self.tracking_uri}")
    
    def create_experiment(
        self,
        name: str,
        tenant_id: str,
        model_type: ModelType,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Create new experiment.
        
        Args:
            name: Experiment name
            tenant_id: Tenant ID
            model_type: Type of model
            description: Experiment description
            tags: Additional tags
            
        Returns:
            Experiment ID
        """
        try:
            # Try to get existing experiment
            experiment = self.client.get_experiment_by_name(name)
            if experiment:
                logger.info(f"Using existing experiment: {name}")
                return experiment.experiment_id
        except Exception:
            pass
        
        # Create new experiment
        experiment_tags = {
            "tenant_id": tenant_id,
            "model_type": model_type.value,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        if tags:
            experiment_tags.update(tags)
        
        experiment_id = self.client.create_experiment(
            name=name,
            artifact_location=self.artifact_location,
            tags=experiment_tags,
        )
        
        # Set description if provided
        if description:
            self.client.set_experiment_tag(
                experiment_id,
                "mlflow.note.content",
                description,
            )
        
        logger.info(f"Created experiment: {name} (ID: {experiment_id})")
        
        return experiment_id
    
    def start_run(
        self,
        experiment_id: str,
        run_name: str,
        tags: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Start new training run.
        
        Args:
            experiment_id: Experiment ID
            run_name: Run name
            tags: Run tags
            
        Returns:
            Run ID
        """
        run = self.client.create_run(
            experiment_id=experiment_id,
            run_name=run_name,
            tags=tags or {},
        )
        
        logger.info(f"Started run: {run_name} (ID: {run.info.run_id})")
        
        return run.info.run_id
    
    def log_params(
        self,
        run_id: str,
        params: Dict[str, Any],
    ) -> None:
        """
        Log parameters to run.
        
        Args:
            run_id: Run ID
            params: Parameters to log
        """
        for key, value in params.items():
            try:
                # MLflow requires string values for params
                self.client.log_param(run_id, key, str(value))
            except Exception as e:
                logger.warning(f"Failed to log param {key}: {e}")
    
    def log_metrics(
        self,
        run_id: str,
        metrics: Dict[str, float],
        step: Optional[int] = None,
    ) -> None:
        """
        Log metrics to run.
        
        Args:
            run_id: Run ID
            metrics: Metrics to log
            step: Step number (for time-series metrics)
        """
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        
        for key, value in metrics.items():
            try:
                self.client.log_metric(
                    run_id,
                    key,
                    value,
                    timestamp=timestamp,
                    step=step or 0,
                )
            except Exception as e:
                logger.warning(f"Failed to log metric {key}: {e}")
    
    def log_artifact(
        self,
        run_id: str,
        local_path: str,
        artifact_path: Optional[str] = None,
    ) -> None:
        """
        Log artifact file to run.
        
        Args:
            run_id: Run ID
            local_path: Local file path
            artifact_path: Artifact subdirectory path
        """
        try:
            self.client.log_artifact(
                run_id,
                local_path,
                artifact_path=artifact_path,
            )
            logger.info(f"Logged artifact: {local_path}")
        except Exception as e:
            logger.error(f"Failed to log artifact: {e}")
            raise
    
    def log_model(
        self,
        run_id: str,
        model: Any,
        artifact_path: str = "model",
        registered_model_name: Optional[str] = None,
    ) -> None:
        """
        Log model to run.
        
        Args:
            run_id: Run ID
            model: Model object
            artifact_path: Artifact path for model
            registered_model_name: Name for model registry
        """
        try:
            import mlflow.sklearn
            
            with mlflow.start_run(run_id=run_id):
                mlflow.sklearn.log_model(
                    model,
                    artifact_path=artifact_path,
                    registered_model_name=registered_model_name,
                )
            
            logger.info(f"Logged model to run {run_id}")
        except Exception as e:
            logger.error(f"Failed to log model: {e}")
            raise
    
    def set_tags(
        self,
        run_id: str,
        tags: Dict[str, str],
    ) -> None:
        """
        Set tags on run.
        
        Args:
            run_id: Run ID
            tags: Tags to set
        """
        for key, value in tags.items():
            try:
                self.client.set_tag(run_id, key, str(value))
            except Exception as e:
                logger.warning(f"Failed to set tag {key}: {e}")
    
    def end_run(
        self,
        run_id: str,
        status: str = "FINISHED",
    ) -> None:
        """
        End training run.
        
        Args:
            run_id: Run ID
            status: Final status (FINISHED, FAILED, KILLED)
        """
        try:
            # Map status strings to MLflow RunStatus
            status_map = {
                "FINISHED": RunStatus.to_string(RunStatus.FINISHED),
                "FAILED": RunStatus.to_string(RunStatus.FAILED),
                "KILLED": RunStatus.to_string(RunStatus.KILLED),
            }
            
            self.client.set_terminated(
                run_id,
                status=status_map.get(status, "FINISHED"),
            )
            
            logger.info(f"Ended run {run_id} with status: {status}")
        except Exception as e:
            logger.error(f"Failed to end run: {e}")
    
    def get_run(self, run_id: str) -> Dict[str, Any]:
        """
        Get run details.
        
        Args:
            run_id: Run ID
            
        Returns:
            Run information dictionary
        """
        try:
            run = self.client.get_run(run_id)
            
            return {
                "run_id": run.info.run_id,
                "experiment_id": run.info.experiment_id,
                "run_name": run.data.tags.get("mlflow.runName", ""),
                "status": run.info.status,
                "start_time": run.info.start_time,
                "end_time": run.info.end_time,
                "params": run.data.params,
                "metrics": run.data.metrics,
                "tags": run.data.tags,
                "artifact_uri": run.info.artifact_uri,
            }
        except Exception as e:
            logger.error(f"Failed to get run: {e}")
            raise
    
    def search_runs(
        self,
        experiment_ids: List[str],
        filter_string: Optional[str] = None,
        max_results: int = 100,
        order_by: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search runs across experiments.
        
        Args:
            experiment_ids: List of experiment IDs to search
            filter_string: Filter expression (e.g., "metrics.mae < 0.5")
            max_results: Maximum results to return
            order_by: Order by expressions (e.g., ["metrics.mae ASC"])
            
        Returns:
            List of matching runs
        """
        try:
            runs = self.client.search_runs(
                experiment_ids=experiment_ids,
                filter_string=filter_string or "",
                max_results=max_results,
                order_by=order_by or [],
            )
            
            results = []
            for run in runs:
                results.append({
                    "run_id": run.info.run_id,
                    "experiment_id": run.info.experiment_id,
                    "run_name": run.data.tags.get("mlflow.runName", ""),
                    "status": run.info.status,
                    "start_time": run.info.start_time,
                    "metrics": run.data.metrics,
                    "params": run.data.params,
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search runs: {e}")
            raise
    
    def compare_runs(
        self,
        run_ids: List[str],
        metric_keys: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Compare multiple runs.
        
        Args:
            run_ids: List of run IDs to compare
            metric_keys: Specific metrics to compare (None = all)
            
        Returns:
            Comparison data
        """
        runs_data = []
        
        for run_id in run_ids:
            try:
                run = self.client.get_run(run_id)
                
                run_info = {
                    "run_id": run_id,
                    "run_name": run.data.tags.get("mlflow.runName", ""),
                    "params": run.data.params,
                    "metrics": run.data.metrics,
                }
                
                # Filter metrics if specified
                if metric_keys:
                    run_info["metrics"] = {
                        k: v for k, v in run.data.metrics.items()
                        if k in metric_keys
                    }
                
                runs_data.append(run_info)
                
            except Exception as e:
                logger.warning(f"Failed to get run {run_id}: {e}")
        
        return {
            "runs": runs_data,
            "comparison_time": datetime.utcnow().isoformat(),
        }
    
    def get_best_run(
        self,
        experiment_id: str,
        metric_key: str,
        maximize: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Get best run from experiment based on metric.
        
        Args:
            experiment_id: Experiment ID
            metric_key: Metric to optimize
            maximize: True to maximize, False to minimize
            
        Returns:
            Best run information or None
        """
        try:
            order = "DESC" if maximize else "ASC"
            
            runs = self.client.search_runs(
                experiment_ids=[experiment_id],
                filter_string=f"metrics.{metric_key} != 'nan'",
                max_results=1,
                order_by=[f"metrics.{metric_key} {order}"],
            )
            
            if not runs:
                return None
            
            run = runs[0]
            
            return {
                "run_id": run.info.run_id,
                "run_name": run.data.tags.get("mlflow.runName", ""),
                "metrics": run.data.metrics,
                "params": run.data.params,
                "artifact_uri": run.info.artifact_uri,
            }
            
        except Exception as e:
            logger.error(f"Failed to get best run: {e}")
            return None
    
    def delete_run(self, run_id: str) -> None:
        """
        Delete run.
        
        Args:
            run_id: Run ID to delete
        """
        try:
            self.client.delete_run(run_id)
            logger.info(f"Deleted run: {run_id}")
        except Exception as e:
            logger.error(f"Failed to delete run: {e}")
            raise
    
    def get_experiment_stats(
        self,
        experiment_id: str,
    ) -> Dict[str, Any]:
        """
        Get experiment statistics.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            Statistics dictionary
        """
        try:
            # Get all runs
            runs = self.client.search_runs(
                experiment_ids=[experiment_id],
                max_results=10000,
            )
            
            total_runs = len(runs)
            
            # Count by status
            status_counts = {}
            for run in runs:
                status = run.info.status
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Get metric statistics (if runs have metrics)
            metric_stats = {}
            if runs:
                # Get first run's metrics as reference
                sample_metrics = runs[0].data.metrics.keys()
                
                for metric_key in sample_metrics:
                    values = []
                    for run in runs:
                        if metric_key in run.data.metrics:
                            values.append(run.data.metrics[metric_key])
                    
                    if values:
                        import numpy as np
                        metric_stats[metric_key] = {
                            "count": len(values),
                            "mean": float(np.mean(values)),
                            "std": float(np.std(values)),
                            "min": float(np.min(values)),
                            "max": float(np.max(values)),
                        }
            
            return {
                "experiment_id": experiment_id,
                "total_runs": total_runs,
                "status_counts": status_counts,
                "metric_stats": metric_stats,
            }
            
        except Exception as e:
            logger.error(f"Failed to get experiment stats: {e}")
            raise
    
    def log_training_config(
        self,
        run_id: str,
        config: TrainingConfig,
    ) -> None:
        """
        Log training configuration to run.
        
        Args:
            run_id: Run ID
            config: Training configuration
        """
        # Convert config to dict
        config_dict = config.model_dump()
        
        # Log as parameters (flatten nested dicts)
        flat_params = self._flatten_dict(config_dict)
        self.log_params(run_id, flat_params)
        
        # Also log as JSON artifact
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.json',
                delete=False,
            ) as f:
                json.dump(config_dict, f, indent=2, default=str)
                temp_path = f.name
            
            self.log_artifact(run_id, temp_path, "config")
            
            # Cleanup
            Path(temp_path).unlink()
            
        except Exception as e:
            logger.warning(f"Failed to log config artifact: {e}")
    
    def _flatten_dict(
        self,
        d: Dict[str, Any],
        parent_key: str = "",
        sep: str = ".",
    ) -> Dict[str, Any]:
        """
        Flatten nested dictionary.
        
        Args:
            d: Dictionary to flatten
            parent_key: Parent key prefix
            sep: Separator
            
        Returns:
            Flattened dictionary
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            
            if isinstance(v, dict):
                items.extend(
                    self._flatten_dict(v, new_key, sep=sep).items()
                )
            else:
                items.append((new_key, v))
        
        return dict(items)
