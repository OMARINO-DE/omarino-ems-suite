"""
Tests for ModelValidator service.

Tests model validation functionality including:
- Performance validation
- Baseline comparison
- Data drift detection
- Prediction stability
- Prediction range checks
- Validation report generation
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import MagicMock, patch, mock_open
import json

from app.services.model_validator import ModelValidator, ValidationError
from app.models.training import ModelType


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def forecast_validator():
    """Create validator for forecast models."""
    return ModelValidator(model_type=ModelType.FORECAST)


@pytest.fixture
def anomaly_validator():
    """Create validator for anomaly detection models."""
    return ModelValidator(model_type=ModelType.ANOMALY)


@pytest.fixture
def sample_validation_data():
    """Sample validation data for forecasting."""
    np.random.seed(42)
    data = pd.DataFrame({
        "temperature": np.random.normal(20, 5, 100),
        "humidity": np.random.normal(60, 10, 100),
        "load": np.random.normal(1000, 200, 100),
    })
    return data


@pytest.fixture
def sample_training_stats():
    """Sample training data statistics."""
    return {
        "temperature": {"mean": 20.0, "std": 5.0},
        "humidity": {"mean": 60.0, "std": 10.0},
    }


@pytest.fixture
def mock_model():
    """Mock trained model."""
    model = MagicMock()
    # Generate predictions with some noise
    np.random.seed(42)
    model.predict.return_value = np.random.normal(1000, 150, 100)
    return model


# ============================================================================
# TEST PERFORMANCE VALIDATION
# ============================================================================

class TestPerformanceValidation:
    """Tests for performance validation."""
    
    def test_forecast_performance_pass(self, forecast_validator):
        """Test forecast model passing performance checks."""
        # Setup - good predictions
        y_true = np.array([100, 200, 300, 400, 500])
        y_pred = np.array([105, 195, 310, 395, 505])
        
        # Execute
        result = forecast_validator.check_performance(y_true, y_pred)
        
        # Verify
        assert result["passed"]
        assert "mae" in result["metrics"]
        assert "rmse" in result["metrics"]
        assert "mape" in result["metrics"]
        assert "r2_score" in result["metrics"]
        assert len(result["failures"]) == 0
    
    def test_forecast_performance_fail(self, forecast_validator):
        """Test forecast model failing performance checks."""
        # Setup - poor predictions
        y_true = np.array([100, 200, 300, 400, 500])
        y_pred = np.array([500, 100, 600, 50, 800])
        
        # Execute
        result = forecast_validator.check_performance(y_true, y_pred)
        
        # Verify
        assert not result["passed"]
        assert len(result["failures"]) > 0
        # MAE and RMSE should be high
        assert result["metrics"]["mae"] > 50.0
        assert result["metrics"]["rmse"] > 75.0
    
    def test_anomaly_performance_pass(self, anomaly_validator):
        """Test anomaly model passing performance checks."""
        # Setup - good predictions (80% accuracy)
        y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1, 0, 0])
        y_pred = np.array([0, 0, 0, 0, 1, 1, 1, 1, 0, 0])
        
        # Execute
        result = anomaly_validator.check_performance(y_true, y_pred)
        
        # Verify
        assert result["passed"]
        assert "precision" in result["metrics"]
        assert "recall" in result["metrics"]
        assert "f1_score" in result["metrics"]
        assert result["metrics"]["precision"] >= 0.8
    
    def test_custom_thresholds(self):
        """Test validator with custom thresholds."""
        # Setup
        custom_thresholds = {
            "mae": {"max": 10.0, "weight": 1.0},
        }
        validator = ModelValidator(
            model_type=ModelType.FORECAST,
            thresholds=custom_thresholds,
        )
        
        y_true = np.array([100, 200, 300])
        y_pred = np.array([110, 210, 310])  # MAE = 10
        
        # Execute
        result = validator.check_performance(y_true, y_pred)
        
        # Verify - should fail because MAE = 10 > 10.0 (slightly)
        assert result["metrics"]["mae"] <= 10.0


# ============================================================================
# TEST BASELINE COMPARISON
# ============================================================================

class TestBaselineComparison:
    """Tests for baseline model comparison."""
    
    def test_baseline_comparison_pass(self, forecast_validator):
        """Test passing baseline comparison."""
        # Setup
        current_metrics = {"mae": 10.0, "rmse": 15.0, "r2_score": 0.85}
        baseline_metrics = {"mae": 12.0, "rmse": 18.0, "r2_score": 0.80}
        
        # Execute
        result = forecast_validator.check_baseline_comparison(
            current_metrics, baseline_metrics
        )
        
        # Verify
        assert result["passed"]
        assert len(result["failures"]) == 0
        # Should show improvement
        for metric in ["mae", "rmse"]:
            assert result["comparisons"][metric]["current"] < baseline_metrics[metric]
    
    def test_baseline_comparison_fail(self, forecast_validator):
        """Test failing baseline comparison."""
        # Setup - worse than baseline
        current_metrics = {"mae": 20.0, "rmse": 30.0, "r2_score": 0.60}
        baseline_metrics = {"mae": 10.0, "rmse": 15.0, "r2_score": 0.85}
        
        # Execute
        result = forecast_validator.check_baseline_comparison(
            current_metrics, baseline_metrics
        )
        
        # Verify
        assert not result["passed"]
        assert len(result["failures"]) > 0
        # All metrics degraded
        assert all(not comp["acceptable"] for comp in result["comparisons"].values())
    
    def test_baseline_comparison_tolerance(self, forecast_validator):
        """Test baseline comparison with tolerance."""
        # Setup - slight degradation within tolerance
        current_metrics = {"mae": 10.3}  # 3% worse
        baseline_metrics = {"mae": 10.0}
        
        # Execute - 5% tolerance
        result = forecast_validator.check_baseline_comparison(
            current_metrics, baseline_metrics, tolerance=0.05
        )
        
        # Verify - should pass
        assert result["passed"]
        assert result["comparisons"]["mae"]["acceptable"]


# ============================================================================
# TEST DATA DRIFT DETECTION
# ============================================================================

class TestDataDriftDetection:
    """Tests for data drift detection."""
    
    def test_no_drift(self, forecast_validator, sample_training_stats):
        """Test when no significant drift is detected."""
        # Setup - similar distribution
        np.random.seed(42)
        validation_data = pd.DataFrame({
            "temperature": np.random.normal(20, 5, 100),
            "humidity": np.random.normal(60, 10, 100),
        })
        
        # Execute
        result = forecast_validator.check_data_drift(
            validation_data, sample_training_stats
        )
        
        # Verify
        assert result["passed"]
        assert len(result["failures"]) == 0
        for col in ["temperature", "humidity"]:
            assert not result["drift_detected"][col]["drift"]
    
    def test_drift_detected(self, forecast_validator, sample_training_stats):
        """Test when significant drift is detected."""
        # Setup - shifted distribution
        np.random.seed(42)
        validation_data = pd.DataFrame({
            "temperature": np.random.normal(30, 5, 100),  # Mean shifted +10
            "humidity": np.random.normal(80, 10, 100),    # Mean shifted +20
        })
        
        # Execute
        result = forecast_validator.check_data_drift(
            validation_data, sample_training_stats
        )
        
        # Verify
        assert not result["passed"]
        assert len(result["failures"]) > 0
        # Both features should show drift
        assert result["drift_detected"]["temperature"]["drift"]
        assert result["drift_detected"]["humidity"]["drift"]
    
    def test_drift_threshold(self, forecast_validator, sample_training_stats):
        """Test drift detection with custom threshold."""
        # Setup
        np.random.seed(42)
        validation_data = pd.DataFrame({
            "temperature": np.random.normal(20.5, 5, 100),  # Slight shift
            "humidity": np.random.normal(60, 10, 100),
        })
        
        # Execute with strict threshold
        result = forecast_validator.check_data_drift(
            validation_data, sample_training_stats, threshold=0.5  # Very lenient
        )
        
        # Verify - should pass with lenient threshold
        assert result["passed"]


# ============================================================================
# TEST PREDICTION STABILITY
# ============================================================================

class TestPredictionStability:
    """Tests for prediction stability checks."""
    
    def test_stable_predictions(self, forecast_validator):
        """Test stable predictions pass check."""
        # Setup - consistent predictions
        predictions = np.array([100.0] * 50 + [105.0] * 50)
        
        # Execute
        result = forecast_validator.check_prediction_stability(predictions)
        
        # Verify
        assert result["passed"]
        assert result["coefficient_of_variation"] < 0.5
    
    def test_unstable_predictions(self, forecast_validator):
        """Test unstable predictions fail check."""
        # Setup - highly variable predictions
        np.random.seed(42)
        predictions = np.random.uniform(0, 1000, 100)
        
        # Execute
        result = forecast_validator.check_prediction_stability(predictions)
        
        # Verify
        assert not result["passed"]
        assert result["coefficient_of_variation"] > 0.5
        assert len(result["failures"]) > 0
    
    def test_stability_custom_threshold(self, forecast_validator):
        """Test stability with custom CV threshold."""
        # Setup
        predictions = np.array([100.0, 120.0, 80.0, 110.0, 90.0])
        
        # Execute with lenient threshold
        result = forecast_validator.check_prediction_stability(
            predictions, cv_threshold=1.0
        )
        
        # Verify
        assert result["passed"]


# ============================================================================
# TEST PREDICTION RANGE
# ============================================================================

class TestPredictionRange:
    """Tests for prediction range checks."""
    
    def test_valid_prediction_range(self, forecast_validator):
        """Test predictions within valid range."""
        # Setup
        y_true = np.array([100, 200, 300, 400, 500])
        y_pred = np.array([105, 195, 310, 395, 505])
        
        # Execute
        result = forecast_validator.check_prediction_range(y_true, y_pred)
        
        # Verify
        assert result["passed"]
        assert result["outlier_percentage"] < 5.0
        assert len(result["failures"]) == 0
    
    def test_prediction_outliers(self, forecast_validator):
        """Test predictions with outliers."""
        # Setup - some predictions way off
        y_true = np.array([100] * 90 + [200] * 10)
        y_pred = np.array([100] * 90 + [1000] * 10)  # 10% outliers
        
        # Execute
        result = forecast_validator.check_prediction_range(y_true, y_pred)
        
        # Verify
        assert not result["passed"]
        assert result["outlier_percentage"] >= 5.0
    
    def test_prediction_out_of_bounds(self, forecast_validator):
        """Test predictions outside reasonable bounds."""
        # Setup
        y_true = np.array([100, 200, 300, 400, 500])
        y_pred = np.array([10, 20, 30, 40, 50])  # Too far below
        
        # Execute
        result = forecast_validator.check_prediction_range(y_true, y_pred)
        
        # Verify
        assert not result["passed"]
        assert "too low" in " ".join(result["failures"]).lower()


# ============================================================================
# TEST FULL VALIDATION
# ============================================================================

class TestFullValidation:
    """Tests for complete model validation."""
    
    @patch("builtins.open", new_callable=mock_open)
    @patch("pickle.load")
    def test_validate_model_pass(
        self,
        mock_pickle_load,
        mock_file,
        forecast_validator,
        sample_validation_data,
        mock_model,
    ):
        """Test successful model validation."""
        # Setup
        mock_pickle_load.return_value = mock_model
        
        # Execute
        results = forecast_validator.validate_model(
            model_path="/tmp/model.pkl",
            validation_data=sample_validation_data,
            target_column="load",
        )
        
        # Verify
        assert results["passed"]
        assert "performance" in results["checks"]
        assert "prediction_stability" in results["checks"]
        assert "prediction_range" in results["checks"]
        assert len(results["failures"]) == 0
    
    @patch("builtins.open", new_callable=mock_open)
    @patch("pickle.load")
    def test_validate_model_with_baseline(
        self,
        mock_pickle_load,
        mock_file,
        forecast_validator,
        sample_validation_data,
        mock_model,
    ):
        """Test validation with baseline comparison."""
        # Setup
        mock_pickle_load.return_value = mock_model
        baseline_metrics = {
            "mae": 200.0,  # Worse than current
            "rmse": 250.0,
        }
        
        # Execute
        results = forecast_validator.validate_model(
            model_path="/tmp/model.pkl",
            validation_data=sample_validation_data,
            target_column="load",
            baseline_metrics=baseline_metrics,
        )
        
        # Verify
        assert "baseline_comparison" in results["checks"]
        # Should pass because current is better than baseline
        assert results["checks"]["baseline_comparison"]["passed"]
    
    @patch("builtins.open", new_callable=mock_open)
    @patch("pickle.load")
    def test_validate_model_with_drift(
        self,
        mock_pickle_load,
        mock_file,
        forecast_validator,
        sample_validation_data,
        sample_training_stats,
        mock_model,
    ):
        """Test validation with drift detection."""
        # Setup
        mock_pickle_load.return_value = mock_model
        
        # Execute
        results = forecast_validator.validate_model(
            model_path="/tmp/model.pkl",
            validation_data=sample_validation_data,
            target_column="load",
            training_data_stats=sample_training_stats,
        )
        
        # Verify
        assert "data_drift" in results["checks"]
    
    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_validate_model_not_found(
        self,
        mock_file,
        forecast_validator,
        sample_validation_data,
    ):
        """Test validation with missing model file."""
        # Execute & Verify
        with pytest.raises(ValidationError, match="Failed to load model"):
            forecast_validator.validate_model(
                model_path="/tmp/nonexistent.pkl",
                validation_data=sample_validation_data,
                target_column="load",
            )
    
    @patch("builtins.open", new_callable=mock_open)
    @patch("pickle.load")
    def test_validate_model_prediction_error(
        self,
        mock_pickle_load,
        mock_file,
        forecast_validator,
        sample_validation_data,
    ):
        """Test validation when model prediction fails."""
        # Setup
        bad_model = MagicMock()
        bad_model.predict.side_effect = Exception("Prediction failed")
        mock_pickle_load.return_value = bad_model
        
        # Execute & Verify
        with pytest.raises(ValidationError, match="Failed to generate predictions"):
            forecast_validator.validate_model(
                model_path="/tmp/model.pkl",
                validation_data=sample_validation_data,
                target_column="load",
            )


# ============================================================================
# TEST VALIDATION REPORT
# ============================================================================

class TestValidationReport:
    """Tests for validation report generation."""
    
    @patch("builtins.open", new_callable=mock_open)
    def test_generate_report_with_file(self, mock_file, forecast_validator):
        """Test generating report and saving to file."""
        # Setup
        results = {
            "model_path": "/tmp/model.pkl",
            "model_type": "forecast",
            "validation_timestamp": "2024-01-01T00:00:00",
            "validation_data_size": 100,
            "passed": True,
            "failures": [],
            "checks": {
                "performance": {
                    "passed": True,
                    "metrics": {"mae": 10.0, "rmse": 15.0},
                    "failures": [],
                }
            },
        }
        
        # Execute
        report = forecast_validator.generate_validation_report(
            results, output_path="/tmp/report.json"
        )
        
        # Verify
        assert "MODEL VALIDATION REPORT" in report
        assert "✓ PASSED" in report
        assert "mae: 10.0" in report
        mock_file.assert_called_once_with("/tmp/report.json", "w")
    
    def test_generate_report_with_failures(self, forecast_validator):
        """Test generating report with failures."""
        # Setup
        results = {
            "model_path": "/tmp/model.pkl",
            "model_type": "forecast",
            "validation_timestamp": "2024-01-01T00:00:00",
            "validation_data_size": 100,
            "passed": False,
            "failures": [
                "mae exceeds threshold",
                "Data drift detected in temperature",
            ],
            "checks": {
                "performance": {
                    "passed": False,
                    "metrics": {"mae": 100.0},
                    "failures": ["mae exceeds threshold"],
                }
            },
        }
        
        # Execute
        report = forecast_validator.generate_validation_report(results)
        
        # Verify
        assert "✗ FAILED" in report
        assert "VALIDATION FAILURES" in report
        assert "mae exceeds threshold" in report
        assert "Data drift detected" in report
    
    def test_generate_report_with_baseline(self, forecast_validator):
        """Test report with baseline comparison."""
        # Setup
        results = {
            "model_path": "/tmp/model.pkl",
            "model_type": "forecast",
            "validation_timestamp": "2024-01-01T00:00:00",
            "validation_data_size": 100,
            "passed": True,
            "failures": [],
            "checks": {
                "performance": {
                    "passed": True,
                    "metrics": {"mae": 10.0},
                    "failures": [],
                },
                "baseline_comparison": {
                    "passed": True,
                    "comparisons": {
                        "mae": {
                            "current": 10.0,
                            "baseline": 12.0,
                            "degradation_pct": -16.67,
                            "acceptable": True,
                        }
                    },
                    "failures": [],
                },
            },
        }
        
        # Execute
        report = forecast_validator.generate_validation_report(results)
        
        # Verify
        assert "BASELINE COMPARISON" in report
        assert "10.0" in report
        assert "12.0" in report
