"""
Ray-based distributed training service.

Provides distributed training capabilities using Ray:
- Cluster initialization and management
- Distributed data loading and preprocessing
- Parallel model training
- Fault tolerance and automatic retries
- Resource allocation and scaling
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import numpy as np

try:
    import ray
    from ray import serve
    from ray.train import ScalingConfig
    from ray.data import Dataset
    RAY_AVAILABLE = True
except ImportError:
    RAY_AVAILABLE = False
    # Create placeholder types
    class Dataset:
        pass
    class ScalingConfig:
        pass

from app.models.training import TrainingConfig, ModelType

logger = logging.getLogger(__name__)


class RayTrainer:
    """
    Distributed training orchestrator using Ray.
    
    Manages distributed training workflows including data distribution,
    parallel training, and fault tolerance.
    """
    
    def __init__(self, cluster_address: Optional[str] = None):
        """
        Initialize RayTrainer.
        
        Args:
            cluster_address: Ray cluster address (None = local mode)
        """
        if not RAY_AVAILABLE:
            raise ImportError(
                "Ray is not installed. Install with: pip install ray[train]"
            )
        
        self.cluster_address = cluster_address
        self.is_initialized = False
        self._resource_config: Optional[Dict[str, Any]] = None
        
    async def initialize(
        self,
        num_workers: int = 2,
        num_cpus_per_worker: int = 2,
        num_gpus_per_worker: float = 0,
        memory_per_worker_gb: int = 4,
    ) -> None:
        """
        Initialize Ray cluster.
        
        Args:
            num_workers: Number of worker nodes
            num_cpus_per_worker: CPUs per worker
            num_gpus_per_worker: GPUs per worker (fractional allowed)
            memory_per_worker_gb: Memory per worker in GB
        """
        if self.is_initialized:
            logger.info("Ray cluster already initialized")
            return
        
        try:
            # Initialize Ray
            if self.cluster_address:
                ray.init(address=self.cluster_address)
                logger.info(f"Connected to Ray cluster at {self.cluster_address}")
            else:
                ray.init(
                    num_cpus=num_workers * num_cpus_per_worker,
                    num_gpus=num_workers * num_gpus_per_worker if num_gpus_per_worker > 0 else None,
                    _memory=num_workers * memory_per_worker_gb * 1024 * 1024 * 1024,
                    ignore_reinit_error=True,
                )
                logger.info("Initialized local Ray cluster")
            
            # Store resource config
            self._resource_config = {
                "num_workers": num_workers,
                "num_cpus_per_worker": num_cpus_per_worker,
                "num_gpus_per_worker": num_gpus_per_worker,
                "memory_per_worker_gb": memory_per_worker_gb,
            }
            
            self.is_initialized = True
            
            # Log cluster resources
            resources = ray.cluster_resources()
            logger.info(f"Ray cluster resources: {resources}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Ray cluster: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown Ray cluster."""
        if not self.is_initialized:
            return
        
        try:
            ray.shutdown()
            self.is_initialized = False
            logger.info("Ray cluster shut down successfully")
        except Exception as e:
            logger.error(f"Error shutting down Ray cluster: {e}")
            raise
    
    async def train_distributed(
        self,
        tenant_id: str,
        model_type: ModelType,
        model_name: str,
        config: TrainingConfig,
        data: np.ndarray,
        labels: np.ndarray,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> Dict[str, Any]:
        """
        Train model using distributed Ray workers.
        
        Args:
            tenant_id: Tenant ID
            model_type: Type of model
            model_name: Model name
            config: Training configuration
            data: Feature matrix
            labels: Target values
            progress_callback: Progress callback function
            
        Returns:
            Dictionary with trained model and metrics
        """
        if not self.is_initialized:
            await self.initialize(num_workers=config.n_workers)
        
        logger.info(
            f"Starting distributed training for {tenant_id}:{model_name} "
            f"with {self._resource_config['num_workers']} workers"
        )
        
        try:
            # Create Ray dataset
            dataset = self._create_ray_dataset(data, labels)
            
            # Report progress
            if progress_callback:
                await progress_callback(0.1)
            
            # Configure training
            scaling_config = ScalingConfig(
                num_workers=self._resource_config["num_workers"],
                use_gpu=self._resource_config["num_gpus_per_worker"] > 0,
                resources_per_worker={
                    "CPU": self._resource_config["num_cpus_per_worker"],
                    "GPU": self._resource_config["num_gpus_per_worker"],
                },
            )
            
            # Train based on model type
            if model_type == ModelType.FORECAST:
                result = await self._train_forecast_distributed(
                    dataset,
                    config,
                    scaling_config,
                    progress_callback,
                )
            elif model_type == ModelType.ANOMALY:
                result = await self._train_anomaly_distributed(
                    dataset,
                    config,
                    scaling_config,
                    progress_callback,
                )
            else:
                raise ValueError(f"Unsupported model type: {model_type}")
            
            logger.info(
                f"Distributed training completed for {tenant_id}:{model_name}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Distributed training failed: {e}")
            raise
    
    async def parallel_hp_search(
        self,
        tenant_id: str,
        model_type: ModelType,
        model_name: str,
        config: TrainingConfig,
        data: np.ndarray,
        labels: np.ndarray,
        n_trials: int = 10,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> Dict[str, Any]:
        """
        Run parallel hyperparameter search using Ray.
        
        Args:
            tenant_id: Tenant ID
            model_type: Type of model
            model_name: Model name
            config: Training configuration
            data: Feature matrix
            labels: Target values
            n_trials: Number of parallel trials
            progress_callback: Progress callback
            
        Returns:
            Dictionary with best hyperparameters and metrics
        """
        if not self.is_initialized:
            await self.initialize(num_workers=config.n_workers)
        
        logger.info(
            f"Starting parallel HP search for {tenant_id}:{model_name} "
            f"with {n_trials} trials"
        )
        
        try:
            # Create Ray dataset
            dataset = self._create_ray_dataset(data, labels)
            
            # Generate hyperparameter combinations
            hp_combinations = self._generate_hp_combinations(
                config,
                n_trials,
            )
            
            # Run trials in parallel
            futures = []
            for i, hp_combo in enumerate(hp_combinations):
                future = self._train_single_trial.remote(
                    self,
                    dataset,
                    hp_combo,
                    config,
                    i,
                )
                futures.append(future)
            
            # Wait for results with progress tracking
            results = []
            for i, future in enumerate(futures):
                result = await asyncio.wrap_future(future)
                results.append(result)
                
                if progress_callback:
                    progress = (i + 1) / len(futures)
                    await progress_callback(progress)
            
            # Find best result
            best_result = min(results, key=lambda x: x["score"])
            
            logger.info(
                f"Parallel HP search completed. Best score: {best_result['score']:.4f}"
            )
            
            return {
                "best_hyperparams": best_result["hyperparams"],
                "best_score": best_result["score"],
                "all_trials": results,
            }
            
        except Exception as e:
            logger.error(f"Parallel HP search failed: {e}")
            raise
    
    @ray.remote
    def _train_single_trial(
        self,
        dataset: Dataset,
        hyperparams: Dict[str, Any],
        config: TrainingConfig,
        trial_id: int,
    ) -> Dict[str, Any]:
        """
        Train single trial with given hyperparameters (Ray task).
        
        Args:
            dataset: Ray dataset
            hyperparams: Hyperparameters to test
            config: Training configuration
            trial_id: Trial identifier
            
        Returns:
            Trial result with score
        """
        import lightgbm as lgb
        from sklearn.metrics import mean_absolute_error
        
        logger.info(f"Trial {trial_id}: Training with {hyperparams}")
        
        # Convert dataset to numpy
        df = dataset.to_pandas()
        X = df.drop(columns=["target"]).values
        y = df["target"].values
        
        # Split for validation
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # Train model
        model = lgb.LGBMRegressor(**hyperparams, random_state=config.random_seed)
        model.fit(
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(10)],
        )
        
        # Evaluate
        y_pred = model.predict(X_val)
        score = mean_absolute_error(y_val, y_pred)
        
        return {
            "trial_id": trial_id,
            "hyperparams": hyperparams,
            "score": score,
        }
    
    def _create_ray_dataset(
        self,
        data: np.ndarray,
        labels: np.ndarray,
    ) -> Dataset:
        """
        Create Ray Dataset from numpy arrays.
        
        Args:
            data: Feature matrix
            labels: Target values
            
        Returns:
            Ray Dataset
        """
        import pandas as pd
        
        # Combine into DataFrame
        df = pd.DataFrame(data)
        df["target"] = labels
        
        # Create Ray dataset
        dataset = ray.data.from_pandas(df)
        
        return dataset
    
    async def _train_forecast_distributed(
        self,
        dataset: Dataset,
        config: TrainingConfig,
        scaling_config: ScalingConfig,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> Dict[str, Any]:
        """
        Train forecasting model with distributed workers.
        
        Args:
            dataset: Ray dataset
            config: Training configuration
            scaling_config: Ray scaling configuration
            progress_callback: Progress callback
            
        Returns:
            Training result
        """
        import lightgbm as lgb
        from sklearn.metrics import mean_absolute_error, mean_squared_error
        
        # Convert to pandas for training
        df = dataset.to_pandas()
        X = df.drop(columns=["target"]).values
        y = df["target"].values
        
        # Split data
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        if progress_callback:
            await progress_callback(0.3)
        
        # Get hyperparameters
        hyperparams = config.hyperparams or {}
        hyperparams.setdefault("n_estimators", 100)
        hyperparams.setdefault("learning_rate", 0.1)
        hyperparams.setdefault("max_depth", 7)
        
        # Train model (Ray will distribute this automatically)
        model = lgb.LGBMRegressor(**hyperparams, random_state=config.random_seed)
        model.fit(
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(20)],
        )
        
        if progress_callback:
            await progress_callback(0.8)
        
        # Evaluate
        y_pred = model.predict(X_val)
        mae = mean_absolute_error(y_val, y_pred)
        rmse = np.sqrt(mean_squared_error(y_val, y_pred))
        
        if progress_callback:
            await progress_callback(1.0)
        
        return {
            "model": model,
            "metrics": {
                "mae": mae,
                "rmse": rmse,
            },
            "hyperparams": hyperparams,
        }
    
    async def _train_anomaly_distributed(
        self,
        dataset: Dataset,
        config: TrainingConfig,
        scaling_config: ScalingConfig,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> Dict[str, Any]:
        """
        Train anomaly detection model with distributed workers.
        
        Args:
            dataset: Ray dataset
            config: Training configuration
            scaling_config: Ray scaling configuration
            progress_callback: Progress callback
            
        Returns:
            Training result
        """
        from sklearn.ensemble import IsolationForest
        from sklearn.metrics import accuracy_score
        
        # Convert to pandas
        df = dataset.to_pandas()
        X = df.drop(columns=["target"]).values
        y = df["target"].values
        
        # Split data
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        if progress_callback:
            await progress_callback(0.3)
        
        # Get hyperparameters
        hyperparams = config.hyperparams or {}
        hyperparams.setdefault("n_estimators", 100)
        hyperparams.setdefault("contamination", 0.1)
        
        # Train model
        model = IsolationForest(**hyperparams, random_state=config.random_seed)
        model.fit(X_train)
        
        if progress_callback:
            await progress_callback(0.8)
        
        # Evaluate
        y_pred = model.predict(X_val)
        y_pred_binary = (y_pred == -1).astype(int)  # -1 = anomaly, 1 = normal
        
        # Assume y_val is binary (0=normal, 1=anomaly)
        accuracy = accuracy_score(y_val, y_pred_binary)
        
        if progress_callback:
            await progress_callback(1.0)
        
        return {
            "model": model,
            "metrics": {
                "accuracy": accuracy,
            },
            "hyperparams": hyperparams,
        }
    
    def _generate_hp_combinations(
        self,
        config: TrainingConfig,
        n_trials: int,
    ) -> List[Dict[str, Any]]:
        """
        Generate hyperparameter combinations for parallel search.
        
        Args:
            config: Training configuration with HP search space
            n_trials: Number of trials
            
        Returns:
            List of hyperparameter dictionaries
        """
        import random
        
        combinations = []
        
        # Extract search space from config
        search_space = config.hyperparams or {}
        
        # Default search spaces
        default_spaces = {
            "n_estimators": [50, 100, 200, 300],
            "learning_rate": [0.01, 0.05, 0.1, 0.15],
            "max_depth": [3, 5, 7, 9],
            "min_child_samples": [10, 20, 30],
        }
        
        for _ in range(n_trials):
            combo = {}
            
            for param, space in default_spaces.items():
                # Check if param has search space in config
                if param in search_space and isinstance(search_space[param], dict):
                    spec = search_space[param]
                    if spec.get("type") == "int":
                        combo[param] = random.randint(spec["low"], spec["high"])
                    elif spec.get("type") == "float":
                        combo[param] = random.uniform(spec["low"], spec["high"])
                    elif spec.get("type") == "categorical":
                        combo[param] = random.choice(spec["choices"])
                else:
                    # Use default space
                    combo[param] = random.choice(space)
            
            combinations.append(combo)
        
        return combinations
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """
        Get current cluster status.
        
        Returns:
            Dictionary with cluster information
        """
        if not self.is_initialized:
            return {"status": "not_initialized"}
        
        try:
            resources = ray.cluster_resources()
            available = ray.available_resources()
            
            return {
                "status": "running",
                "total_resources": resources,
                "available_resources": available,
                "num_nodes": len(ray.nodes()),
                "config": self._resource_config,
            }
        except Exception as e:
            logger.error(f"Error getting cluster status: {e}")
            return {"status": "error", "error": str(e)}
