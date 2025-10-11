"""
Tests for ModelTrainingPipeline service.

Tests end-to-end training workflow including feature loading,
preprocessing, training, evaluation, and model registration.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.training_pipeline import ModelTrainingPipeline
from app.models.training import ModelType, TrainingConfig


@pytest.fixture
def mock_feature_store():
    """Mock FeatureStore service."""
    store = AsyncMock()
    return store


@pytest.fixture
def mock_model_storage():
    """Mock ModelStorage service."""
    storage = AsyncMock()
    return storage


@pytest.fixture
def pipeline(mock_feature_store, mock_model_storage):
    """Create ModelTrainingPipeline instance."""
    return ModelTrainingPipeline(mock_feature_store, mock_model_storage)


@pytest.fixture
def sample_config():
    """Sample training configuration."""
    return TrainingConfig(
        start_date=datetime(2025, 1, 1),
        end_date=datetime(2025, 3, 1),  # 2 months for faster tests
        feature_set="forecast_basic",
        target_variable="load_kw",
        horizon=24,
        validation_split=0.2,
        test_split=0.1,
        enable_hpo=False,
        hyperparams={"n_estimators": 10},  # Small for fast tests
        n_workers=1,
        random_seed=42,
    )


class TestFeatureLoading:
    """Tests for feature loading step."""
    
    @pytest.mark.asyncio
    async def test_load_features_synthetic_data(self, pipeline, sample_config):
        """Test loading synthetic features."""
        df = await pipeline._load_features(
            "tenant-123",
            sample_config,
            progress_callback=None,
            start_progress=0.0,
            end_progress=0.2,
        )
        
        # Check DataFrame structure
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert 'timestamp' in df.columns
        assert sample_config.target_variable in df.columns
        
        # Check feature columns
        expected_features = [
            'hour_of_day', 'day_of_week', 'month', 'is_weekend',
            'hourly_avg', 'daily_avg', 'temperature', 'humidity',
            'lag_24h', 'rolling_avg_24h'
        ]
        for feature in expected_features:
            assert feature in df.columns
    
    @pytest.mark.asyncio
    async def test_load_features_date_range(self, pipeline, sample_config):
        """Test that loaded features respect date range."""
        df = await pipeline._load_features(
            "tenant-123",
            sample_config,
            progress_callback=None,
            start_progress=0.0,
            end_progress=0.2,
        )
        
        # Check date range
        assert df['timestamp'].min() >= sample_config.start_date
        assert df['timestamp'].max() <= sample_config.end_date
    
    @pytest.mark.asyncio
    async def test_load_features_with_progress_callback(self, pipeline, sample_config):
        """Test feature loading with progress callback."""
        callback_called = False
        progress_value = None
        
        async def callback(progress):
            nonlocal callback_called, progress_value
            callback_called = True
            progress_value = progress
        
        df = await pipeline._load_features(
            "tenant-123",
            sample_config,
            progress_callback=callback,
            start_progress=0.0,
            end_progress=0.2,
        )
        
        assert callback_called
        assert progress_value == 0.2


class TestDataPreprocessing:
    """Tests for data preprocessing step."""
    
    @pytest.mark.asyncio
    async def test_preprocess_data_splits(self, pipeline, sample_config):
        """Test data splitting."""
        # Create sample DataFrame
        df = pd.DataFrame({
            'timestamp': pd.date_range(start='2025-01-01', periods=1000, freq='h'),
            'feature1': np.random.randn(1000),
            'feature2': np.random.randn(1000),
            'load_kw': np.random.randn(1000) * 100 + 100,
        })
        
        X_train, X_val, X_test, y_train, y_val, y_test, scaler = \
            await pipeline._preprocess_data(
                df,
                sample_config,
                progress_callback=None,
                start_progress=0.2,
                end_progress=0.4,
            )
        
        # Check shapes
        total_samples = len(df)
        test_size = int(total_samples * sample_config.test_split)
        remaining = total_samples - test_size
        val_size = int(remaining * sample_config.validation_split)
        
        assert len(X_test) == test_size
        assert len(X_val) > 0
        assert len(X_train) > 0
        assert len(X_train) + len(X_val) + len(X_test) == total_samples
    
    @pytest.mark.asyncio
    async def test_preprocess_data_scaling(self, pipeline, sample_config):
        """Test feature scaling."""
        df = pd.DataFrame({
            'timestamp': pd.date_range(start='2025-01-01', periods=100, freq='h'),
            'feature1': np.random.randn(100) * 100,  # Large scale
            'feature2': np.random.randn(100) * 0.01,  # Small scale
            'load_kw': np.random.randn(100) * 100 + 100,
        })
        
        X_train, X_val, X_test, y_train, y_val, y_test, scaler = \
            await pipeline._preprocess_data(
                df,
                sample_config,
                progress_callback=None,
                start_progress=0.2,
                end_progress=0.4,
            )
        
        # Check scaling (mean ≈ 0, std ≈ 1)
        assert np.abs(X_train.mean()) < 0.5
        assert np.abs(X_train.std() - 1.0) < 0.5
    
    @pytest.mark.asyncio
    async def test_preprocess_preserves_time_order(self, pipeline, sample_config):
        """Test that preprocessing preserves time series order (no shuffle)."""
        # Create DataFrame with monotonic target
        df = pd.DataFrame({
            'timestamp': pd.date_range(start='2025-01-01', periods=100, freq='h'),
            'feature1': np.arange(100),  # Monotonic
            'load_kw': np.arange(100),  # Monotonic
        })
        
        X_train, X_val, X_test, y_train, y_val, y_test, scaler = \
            await pipeline._preprocess_data(
                df,
                sample_config,
                progress_callback=None,
                start_progress=0.2,
                end_progress=0.4,
            )
        
        # y_test should have largest values (since it's the last split)
        assert y_test.mean() > y_train.mean()


class TestModelTraining:
    """Tests for model training step."""
    
    @pytest.mark.asyncio
    async def test_train_model_basic(self, pipeline, sample_config):
        """Test basic model training."""
        # Create sample data
        X_train = np.random.randn(100, 5)
        y_train = np.random.randn(100) * 10 + 50
        X_val = np.random.randn(20, 5)
        y_val = np.random.randn(20) * 10 + 50
        
        model, hyperparams = await pipeline._train_model(
            X_train, y_train, X_val, y_val,
            ModelType.FORECAST,
            sample_config,
            progress_callback=None,
            start_progress=0.4,
            end_progress=0.7,
        )
        
        # Check model is trained
        assert model is not None
        assert hasattr(model, 'predict')
        assert isinstance(hyperparams, dict)
        assert 'n_estimators' in hyperparams
    
    @pytest.mark.asyncio
    async def test_train_model_with_custom_hyperparams(self, pipeline, sample_config):
        """Test training with custom hyperparameters."""
        sample_config.hyperparams = {
            "n_estimators": 50,
            "learning_rate": 0.05,
            "max_depth": 3,
        }
        
        X_train = np.random.randn(100, 5)
        y_train = np.random.randn(100) * 10 + 50
        X_val = np.random.randn(20, 5)
        y_val = np.random.randn(20) * 10 + 50
        
        model, hyperparams = await pipeline._train_model(
            X_train, y_train, X_val, y_val,
            ModelType.FORECAST,
            sample_config,
            progress_callback=None,
            start_progress=0.4,
            end_progress=0.7,
        )
        
        # Check custom hyperparams were used
        assert hyperparams["n_estimators"] == 50
        assert hyperparams["learning_rate"] == 0.05
        assert hyperparams["max_depth"] == 3
    
    @pytest.mark.asyncio
    async def test_train_model_deterministic(self, pipeline, sample_config):
        """Test that training with same seed produces consistent results."""
        X_train = np.random.randn(100, 5)
        y_train = np.random.randn(100) * 10 + 50
        X_val = np.random.randn(20, 5)
        y_val = np.random.randn(20) * 10 + 50
        
        # Train twice with same seed
        model1, _ = await pipeline._train_model(
            X_train, y_train, X_val, y_val,
            ModelType.FORECAST,
            sample_config,
            progress_callback=None,
            start_progress=0.4,
            end_progress=0.7,
        )
        
        model2, _ = await pipeline._train_model(
            X_train, y_train, X_val, y_val,
            ModelType.FORECAST,
            sample_config,
            progress_callback=None,
            start_progress=0.4,
            end_progress=0.7,
        )
        
        # Predictions should be identical
        X_test = np.random.randn(10, 5)
        pred1 = model1.predict(X_test)
        pred2 = model2.predict(X_test)
        
        np.testing.assert_array_almost_equal(pred1, pred2, decimal=5)


class TestModelEvaluation:
    """Tests for model evaluation step."""
    
    @pytest.mark.asyncio
    async def test_evaluate_model(self, pipeline):
        """Test model evaluation with metrics."""
        # Create simple model (mock)
        model = MagicMock()
        model.predict.return_value = np.array([100, 105, 95, 110, 90])
        model.score.return_value = 0.85
        
        # Test data
        X_test = np.random.randn(5, 5)
        y_test = np.array([102, 103, 98, 108, 92])
        
        metrics = await pipeline._evaluate_model(
            model, X_test, y_test,
            progress_callback=None,
            start_progress=0.7,
            end_progress=0.85,
        )
        
        # Check metrics exist
        assert 'mae' in metrics
        assert 'rmse' in metrics
        assert 'mape' in metrics
        assert 'r2_score' in metrics
        
        # Check metrics are reasonable
        assert metrics['mae'] > 0
        assert metrics['rmse'] > 0
        assert metrics['mape'] > 0
    
    @pytest.mark.asyncio
    async def test_evaluate_perfect_model(self, pipeline):
        """Test evaluation with perfect predictions."""
        model = MagicMock()
        y_true = np.array([100, 105, 95, 110, 90])
        model.predict.return_value = y_true  # Perfect predictions
        model.score.return_value = 1.0
        
        X_test = np.random.randn(5, 5)
        
        metrics = await pipeline._evaluate_model(
            model, X_test, y_true,
            progress_callback=None,
            start_progress=0.7,
            end_progress=0.85,
        )
        
        # Perfect model should have near-zero error
        assert metrics['mae'] < 0.001
        assert metrics['rmse'] < 0.001
        assert metrics['mape'] < 0.001


class TestModelRegistration:
    """Tests for model registration step."""
    
    @pytest.mark.asyncio
    async def test_register_model(self, pipeline):
        """Test model registration."""
        from sklearn.preprocessing import StandardScaler
        
        model = MagicMock()
        model.n_features_ = 10
        scaler = StandardScaler()
        hyperparams = {"n_estimators": 100, "learning_rate": 0.1}
        metrics = {"mae": 12.5, "rmse": 18.3, "mape": 5.6, "r2_score": 0.85}
        
        config = TrainingConfig(
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 10, 1),
            feature_set="forecast_basic",
            target_variable="load_kw",
            horizon=24,
        )
        
        model_id = await pipeline._register_model(
            "tenant-123",
            "test_model",
            model,
            scaler,
            hyperparams,
            metrics,
            config,
            progress_callback=None,
            start_progress=0.85,
            end_progress=1.0,
        )
        
        # Check model ID format
        assert model_id.startswith("tenant-123:test_model:")
        assert len(model_id.split(":")) == 3  # tenant:name:version


class TestEndToEndPipeline:
    """Tests for complete end-to-end training pipeline."""
    
    @pytest.mark.asyncio
    async def test_train_complete_pipeline(self, pipeline, sample_config):
        """Test complete training pipeline."""
        # Enable model registration
        sample_config.register_model = True
        
        # Run full pipeline
        model_id, final_metrics = await pipeline.train(
            tenant_id="tenant-123",
            model_type=ModelType.FORECAST,
            model_name="test_model",
            config=sample_config,
            job_id=None,
            progress_callback=None,
        )
        
        # Check outputs
        assert model_id is not None
        assert "tenant-123" in model_id
        assert final_metrics is not None
        assert final_metrics.best_mae is not None
        assert final_metrics.best_rmse is not None
        assert final_metrics.best_mape is not None
        assert final_metrics.training_time_seconds > 0
    
    @pytest.mark.asyncio
    async def test_train_without_registration(self, pipeline, sample_config):
        """Test training without model registration."""
        sample_config.register_model = False
        
        model_id, final_metrics = await pipeline.train(
            tenant_id="tenant-123",
            model_type=ModelType.FORECAST,
            model_name="test_model",
            config=sample_config,
        )
        
        # Model ID should be unregistered
        assert "unregistered" in model_id
        assert final_metrics is not None
    
    @pytest.mark.asyncio
    async def test_train_with_progress_tracking(self, pipeline, sample_config):
        """Test training with progress tracking."""
        progress_updates = []
        
        async def callback(progress):
            progress_updates.append(progress)
        
        model_id, final_metrics = await pipeline.train(
            tenant_id="tenant-123",
            model_type=ModelType.FORECAST,
            model_name="test_model",
            config=sample_config,
            progress_callback=callback,
        )
        
        # Check progress updates were made
        assert len(progress_updates) >= 4  # At least 4 steps
        
        # Progress should be monotonically increasing
        for i in range(1, len(progress_updates)):
            assert progress_updates[i] >= progress_updates[i-1]
        
        # Final progress should be 1.0
        assert progress_updates[-1] == 1.0
    
    @pytest.mark.asyncio
    async def test_train_anomaly_model(self, pipeline, sample_config):
        """Test training anomaly detection model."""
        model_id, final_metrics = await pipeline.train(
            tenant_id="tenant-123",
            model_type=ModelType.ANOMALY,
            model_name="anomaly_detector",
            config=sample_config,
        )
        
        assert model_id is not None
        assert final_metrics is not None


class TestHyperparameterExtraction:
    """Tests for hyperparameter extraction."""
    
    def test_get_hyperparams_defaults(self, pipeline):
        """Test default hyperparameters."""
        config = TrainingConfig(
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 10, 1),
            feature_set="forecast_basic",
            target_variable="load_kw",
        )
        
        hyperparams = pipeline._get_hyperparams(ModelType.FORECAST, config)
        
        # Check defaults exist
        assert "n_estimators" in hyperparams
        assert "learning_rate" in hyperparams
        assert "max_depth" in hyperparams
    
    def test_get_hyperparams_overrides(self, pipeline):
        """Test hyperparameter overrides."""
        config = TrainingConfig(
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 10, 1),
            feature_set="forecast_basic",
            target_variable="load_kw",
            hyperparams={
                "n_estimators": 200,
                "learning_rate": 0.05,
            }
        )
        
        hyperparams = pipeline._get_hyperparams(ModelType.FORECAST, config)
        
        # Check overrides applied
        assert hyperparams["n_estimators"] == 200
        assert hyperparams["learning_rate"] == 0.05
    
    def test_get_hyperparams_ignores_search_specs(self, pipeline):
        """Test that search space specs are ignored."""
        config = TrainingConfig(
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 10, 1),
            feature_set="forecast_basic",
            target_variable="load_kw",
            hyperparams={
                "n_estimators": {"type": "int", "low": 50, "high": 300},  # Search spec
                "learning_rate": 0.05,  # Fixed value
            }
        )
        
        hyperparams = pipeline._get_hyperparams(ModelType.FORECAST, config)
        
        # Search spec should be ignored, default used
        assert hyperparams["n_estimators"] == 100  # Default
        assert hyperparams["learning_rate"] == 0.05  # Override
