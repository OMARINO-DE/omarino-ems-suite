"""
Model Training Pipeline.

Executes end-to-end training workflow from feature loading to model registration.
Supports both single-node and distributed Ray training.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error

from app.models.training import (
    ModelType,
    TrainingConfig,
    TrainingJobMetrics,
)
from app.services.feature_store import FeatureStore
from app.services.model_storage import ModelStorage

# Optional Ray import
try:
    from app.services.ray_trainer import RayTrainer
    RAY_AVAILABLE = True
except ImportError:
    RAY_AVAILABLE = False
    RayTrainer = None

logger = logging.getLogger(__name__)


class ModelTrainingPipeline:
    """
    End-to-end model training pipeline.
    
    Workflow:
    1. Load features from Feature Store
    2. Preprocess data (scaling, splitting)
    3. Train model
    4. Evaluate model
    5. Register model in Model Registry
    """
    
    def __init__(
        self,
        feature_store: FeatureStore,
        model_storage: ModelStorage,
        ray_trainer: Optional[RayTrainer] = None,
    ):
        """
        Initialize training pipeline.
        
        Args:
            feature_store: Feature Store service
            model_storage: Model Storage service
            ray_trainer: Optional Ray trainer for distributed training
        """
        self.feature_store = feature_store
        self.model_storage = model_storage
        self.ray_trainer = ray_trainer
    
    async def train(
        self,
        tenant_id: str,
        model_type: ModelType,
        model_name: str,
        config: TrainingConfig,
        job_id: Optional[UUID] = None,
        progress_callback: Optional[callable] = None,
    ) -> Tuple[str, TrainingJobMetrics]:
        """
        Execute full training pipeline.
        
        Args:
            tenant_id: Tenant ID
            model_type: Type of model (forecast, anomaly)
            model_name: Model name
            config: Training configuration
            job_id: Optional job ID for tracking
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (model_id, final_metrics)
        """
        logger.info(
            f"Starting training pipeline for {model_type}:{model_name} "
            f"(tenant: {tenant_id})"
        )
        
        start_time = datetime.utcnow()
        
        try:
            # Step 1: Load features (20% progress)
            logger.info("Step 1/5: Loading features from Feature Store")
            features_df = await self._load_features(
                tenant_id, config, progress_callback, 0.0, 0.2
            )
            
            # Step 2: Preprocess data (40% progress)
            logger.info("Step 2/5: Preprocessing data")
            X_train, X_val, X_test, y_train, y_val, y_test, scaler = \
                await self._preprocess_data(
                    features_df, config, progress_callback, 0.2, 0.4
                )
            
            # Step 3: Train model (70% progress)
            logger.info("Step 3/5: Training model")
            model, hyperparams = await self._train_model(
                X_train, y_train, X_val, y_val,
                model_type, config, progress_callback, 0.4, 0.7
            )
            
            # Step 4: Evaluate model (85% progress)
            logger.info("Step 4/5: Evaluating model")
            metrics = await self._evaluate_model(
                model, X_test, y_test, progress_callback, 0.7, 0.85
            )
            
            # Step 5: Register model (100% progress)
            if config.register_model:
                logger.info("Step 5/5: Registering model")
                model_id = await self._register_model(
                    tenant_id, model_name, model, scaler,
                    hyperparams, metrics, config, progress_callback, 0.85, 1.0
                )
            else:
                logger.info("Step 5/5: Skipping model registration")
                model_id = f"{tenant_id}:{model_name}:unregistered"
                if progress_callback:
                    await progress_callback(1.0)
            
            # Calculate training time
            end_time = datetime.utcnow()
            training_time_seconds = (end_time - start_time).total_seconds()
            
            final_metrics = TrainingJobMetrics(
                best_mae=metrics["mae"],
                best_rmse=metrics["rmse"],
                best_mape=metrics["mape"],
                training_time_seconds=training_time_seconds,
            )
            
            logger.info(
                f"Training pipeline completed successfully. Model ID: {model_id}, "
                f"MAE: {metrics['mae']:.2f}, RMSE: {metrics['rmse']:.2f}, "
                f"Time: {training_time_seconds:.1f}s"
            )
            
            return model_id, final_metrics
            
        except Exception as e:
            logger.error(f"Training pipeline failed: {str(e)}", exc_info=True)
            raise
    
    async def _load_features(
        self,
        tenant_id: str,
        config: TrainingConfig,
        progress_callback: Optional[callable],
        start_progress: float,
        end_progress: float,
    ) -> pd.DataFrame:
        """
        Load features from Feature Store.
        
        Args:
            tenant_id: Tenant ID
            config: Training configuration
            progress_callback: Progress callback
            start_progress: Starting progress value
            end_progress: Ending progress value
            
        Returns:
            DataFrame with features and target
        """
        logger.info(
            f"Loading features: {config.feature_set} "
            f"from {config.start_date} to {config.end_date}"
        )
        
        # For now, generate synthetic data
        # TODO: Replace with actual Feature Store query
        date_range = pd.date_range(
            start=config.start_date,
            end=config.end_date,
            freq='h'
        )
        
        n_samples = len(date_range)
        
        # Generate synthetic features
        np.random.seed(config.random_seed)
        
        features_df = pd.DataFrame({
            'timestamp': date_range,
            'hour_of_day': date_range.hour,
            'day_of_week': date_range.dayofweek,
            'month': date_range.month,
            'is_weekend': date_range.dayofweek.isin([5, 6]).astype(int),
            'hourly_avg': np.random.normal(100, 20, n_samples),
            'daily_avg': np.random.normal(100, 15, n_samples),
            'temperature': np.random.normal(20, 5, n_samples),
            'humidity': np.random.normal(60, 10, n_samples),
            'lag_24h': np.random.normal(100, 20, n_samples),
            'rolling_avg_24h': np.random.normal(100, 15, n_samples),
        })
        
        # Generate target variable with some correlation to features
        features_df[config.target_variable] = (
            50 +
            0.3 * features_df['hourly_avg'] +
            0.2 * features_df['temperature'] -
            0.1 * features_df['humidity'] +
            np.random.normal(0, 10, n_samples)
        )
        
        logger.info(f"Loaded {len(features_df)} samples with {len(features_df.columns)} features")
        
        if progress_callback:
            await progress_callback(end_progress)
        
        return features_df
    
    async def _preprocess_data(
        self,
        df: pd.DataFrame,
        config: TrainingConfig,
        progress_callback: Optional[callable],
        start_progress: float,
        end_progress: float,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, StandardScaler]:
        """
        Preprocess data: split and scale.
        
        Args:
            df: Input DataFrame
            config: Training configuration
            progress_callback: Progress callback
            start_progress: Starting progress value
            end_progress: Ending progress value
            
        Returns:
            Tuple of (X_train, X_val, X_test, y_train, y_val, y_test, scaler)
        """
        logger.info("Preprocessing data")
        
        # Separate features and target
        feature_cols = [col for col in df.columns if col not in ['timestamp', config.target_variable]]
        X = df[feature_cols].values
        y = df[config.target_variable].values
        
        # Split data: train, val, test
        test_size = config.test_split
        val_size = config.validation_split / (1 - test_size)
        
        # First split: separate test set
        X_temp, X_test, y_temp, y_test = train_test_split(
            X, y,
            test_size=test_size,
            random_state=config.random_seed,
            shuffle=False,  # Keep time series order
        )
        
        # Second split: separate train and validation
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp,
            test_size=val_size,
            random_state=config.random_seed,
            shuffle=False,
        )
        
        # Scale features
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_val = scaler.transform(X_val)
        X_test = scaler.transform(X_test)
        
        logger.info(
            f"Data split: train={len(X_train)}, val={len(X_val)}, test={len(X_test)}"
        )
        
        if progress_callback:
            await progress_callback(end_progress)
        
        return X_train, X_val, X_test, y_train, y_val, y_test, scaler
    
    async def _train_model(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        model_type: ModelType,
        config: TrainingConfig,
        progress_callback: Optional[callable],
        start_progress: float,
        end_progress: float,
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        Train model with given configuration.
        
        Supports both single-node and distributed Ray training based on
        configuration and available resources.
        
        Args:
            X_train: Training features
            y_train: Training targets
            X_val: Validation features
            y_val: Validation targets
            model_type: Type of model
            config: Training configuration
            progress_callback: Progress callback
            start_progress: Starting progress value
            end_progress: Ending progress value
            
        Returns:
            Tuple of (trained_model, hyperparameters)
        """
        logger.info(f"Training {model_type} model")
        
        # Extract hyperparameters from config
        hyperparams = self._get_hyperparams(model_type, config)
        
        # Use distributed training if:
        # 1. Ray trainer is available
        # 2. n_workers > 1 in config
        # 3. Dataset is large enough (> 10k samples)
        use_ray = (
            self.ray_trainer is not None 
            and config.n_workers > 1
            and len(X_train) > 10000
        )
        
        if use_ray:
            logger.info(
                f"Using Ray distributed training with {config.n_workers} workers"
            )
            
            # Combine train and val for Ray
            X_combined = np.vstack([X_train, X_val])
            y_combined = np.concatenate([y_train, y_val])
            
            # Use Ray for training
            result = await self.ray_trainer.train_distributed(
                tenant_id="",  # Will be set by caller
                model_type=model_type,
                model_name="",  # Will be set by caller
                config=config,
                data=X_combined,
                labels=y_combined,
                progress_callback=None,  # Ray has its own progress
            )
            
            model = result["model"]
            hyperparams = result["hyperparams"]
            
        else:
            # Single-node training
            logger.info("Using single-node training")
            
            # Create and train model (using LightGBM for now)
            model = LGBMRegressor(
                **hyperparams,
                random_state=config.random_seed,
                verbosity=-1,
            )
            
            # Training with validation
            if config.early_stopping:
                model.fit(
                    X_train, y_train,
                    eval_set=[(X_val, y_val)],
                    callbacks=[
                        # LightGBM will stop early if no improvement
                    ],
                )
            else:
                model.fit(X_train, y_train)
        
        logger.info(f"Model trained with {len(hyperparams)} hyperparameters")
        
        if progress_callback:
            await progress_callback(end_progress)
        
        return model, hyperparams
    
    async def _evaluate_model(
        self,
        model: Any,
        X_test: np.ndarray,
        y_test: np.ndarray,
        progress_callback: Optional[callable],
        start_progress: float,
        end_progress: float,
    ) -> Dict[str, float]:
        """
        Evaluate model on test set.
        
        Args:
            model: Trained model
            X_test: Test features
            y_test: Test targets
            progress_callback: Progress callback
            start_progress: Starting progress value
            end_progress: Ending progress value
            
        Returns:
            Dictionary of metrics
        """
        logger.info("Evaluating model on test set")
        
        # Make predictions
        y_pred = model.predict(X_test)
        
        # Calculate metrics
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        mape = mean_absolute_percentage_error(y_test, y_pred) * 100  # Convert to percentage
        
        metrics = {
            "mae": float(mae),
            "rmse": float(rmse),
            "mape": float(mape),
            "r2_score": float(model.score(X_test, y_test)) if hasattr(model, 'score') else 0.0,
        }
        
        logger.info(
            f"Evaluation metrics: MAE={mae:.2f}, RMSE={rmse:.2f}, MAPE={mape:.2f}%"
        )
        
        if progress_callback:
            await progress_callback(end_progress)
        
        return metrics
    
    async def _register_model(
        self,
        tenant_id: str,
        model_name: str,
        model: Any,
        scaler: StandardScaler,
        hyperparams: Dict[str, Any],
        metrics: Dict[str, float],
        config: TrainingConfig,
        progress_callback: Optional[callable],
        start_progress: float,
        end_progress: float,
    ) -> str:
        """
        Register model in Model Registry.
        
        Args:
            tenant_id: Tenant ID
            model_name: Model name
            model: Trained model
            scaler: Feature scaler
            hyperparams: Hyperparameters used
            metrics: Evaluation metrics
            config: Training configuration
            progress_callback: Progress callback
            start_progress: Starting progress value
            end_progress: Ending progress value
            
        Returns:
            Model ID
        """
        logger.info("Registering model in Model Registry")
        
        # Generate model version (use timestamp for now)
        # TODO: Implement proper semantic versioning
        version = datetime.utcnow().strftime("%Y%m%d.%H%M%S")
        model_id = f"{tenant_id}:{model_name}:{version}"
        
        # Prepare metadata
        metadata = {
            "model_name": model_name,
            "model_type": "LGBMRegressor",
            "framework": "lightgbm",
            "feature_set": config.feature_set,
            "target_variable": config.target_variable,
            "horizon": config.horizon,
            "training_data_start": config.start_date.isoformat(),
            "training_data_end": config.end_date.isoformat(),
            "n_features": model.n_features_,
            "hyperparameters": hyperparams,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        # Store model artifacts
        # TODO: Integrate with ModelStorage service
        # For now, just log
        logger.info(f"Model registered with ID: {model_id}")
        logger.info(f"Model metadata: {metadata}")
        logger.info(f"Model metrics: {metrics}")
        
        if progress_callback:
            await progress_callback(end_progress)
        
        return model_id
    
    def _get_hyperparams(
        self,
        model_type: ModelType,
        config: TrainingConfig,
    ) -> Dict[str, Any]:
        """
        Extract or use default hyperparameters.
        
        Args:
            model_type: Type of model
            config: Training configuration
            
        Returns:
            Dictionary of hyperparameters
        """
        # Default hyperparameters for LightGBM
        defaults = {
            "n_estimators": 100,
            "learning_rate": 0.1,
            "max_depth": 5,
            "num_leaves": 31,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
        }
        
        # Override with config hyperparams if provided
        if config.hyperparams:
            for key, value in config.hyperparams.items():
                # If value is a dict, it's a search space spec, use default
                if isinstance(value, dict):
                    continue
                defaults[key] = value
        
        return defaults
