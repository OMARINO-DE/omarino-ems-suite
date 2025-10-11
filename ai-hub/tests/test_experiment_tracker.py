"""
Tests for ExperimentTracker service.

Tests MLflow-based experiment tracking functionality including:
- Experiment creation
- Run lifecycle management
- Metrics and parameter logging
- Run search and comparison
- Best model selection
- Experiment statistics
"""

import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime

from app.services.experiment_tracker import ExperimentTracker
from app.models.training import ModelType, TrainingConfig


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_mlflow():
    """Mock MLflow module."""
    with patch("app.services.experiment_tracker.mlflow") as mock:
        yield mock


@pytest.fixture
def mock_mlflow_client():
    """Mock MLflow tracking client."""
    client = MagicMock()
    return client


@pytest.fixture
def tracker(mock_mlflow, mock_mlflow_client):
    """Create ExperimentTracker with mocked MLflow."""
    mock_mlflow.tracking.MlflowClient.return_value = mock_mlflow_client
    tracker = ExperimentTracker(tracking_uri="http://mlflow:5000")
    return tracker


@pytest.fixture
def sample_training_config():
    """Sample training configuration."""
    return TrainingConfig(
        model_type=ModelType.FORECAST,
        algorithm="lgbm",
        hyperparameters={
            "n_estimators": 100,
            "learning_rate": 0.1,
            "max_depth": 7,
        },
        training_start="2024-01-01T00:00:00",
        training_end="2024-12-31T23:59:59",
        features=["temperature", "humidity", "load_lag_1"],
        target="load",
    )


# ============================================================================
# TEST EXPERIMENT CREATION
# ============================================================================

class TestExperimentCreation:
    """Tests for experiment creation."""
    
    def test_create_new_experiment(self, tracker, mock_mlflow_client):
        """Test creating new experiment."""
        # Setup
        mock_mlflow_client.get_experiment_by_name.return_value = None
        mock_mlflow_client.create_experiment.return_value = "exp123"
        
        # Execute
        experiment_id = tracker.create_experiment(
            name="test_experiment",
            tenant_id="tenant1",
            model_type=ModelType.FORECAST,
            description="Test experiment",
            tags={"version": "v1"},
        )
        
        # Verify
        assert experiment_id == "exp123"
        mock_mlflow_client.create_experiment.assert_called_once()
        call_args = mock_mlflow_client.create_experiment.call_args
        assert call_args[0][0] == "test_experiment"
        tags = call_args[1]["tags"]
        assert tags["tenant_id"] == "tenant1"
        assert tags["model_type"] == "forecast"
        assert tags["version"] == "v1"
    
    def test_get_existing_experiment(self, tracker, mock_mlflow_client):
        """Test retrieving existing experiment."""
        # Setup
        mock_experiment = MagicMock()
        mock_experiment.experiment_id = "exp456"
        mock_mlflow_client.get_experiment_by_name.return_value = mock_experiment
        
        # Execute
        experiment_id = tracker.create_experiment(
            name="existing_experiment",
            tenant_id="tenant1",
            model_type=ModelType.ANOMALY,
        )
        
        # Verify
        assert experiment_id == "exp456"
        mock_mlflow_client.create_experiment.assert_not_called()
    
    def test_create_experiment_with_minimal_info(self, tracker, mock_mlflow_client):
        """Test creating experiment with minimal information."""
        # Setup
        mock_mlflow_client.get_experiment_by_name.return_value = None
        mock_mlflow_client.create_experiment.return_value = "exp789"
        
        # Execute
        experiment_id = tracker.create_experiment(
            name="minimal_exp",
            tenant_id="tenant2",
            model_type=ModelType.FORECAST,
        )
        
        # Verify
        assert experiment_id == "exp789"
        call_args = mock_mlflow_client.create_experiment.call_args
        tags = call_args[1]["tags"]
        assert "tenant_id" in tags
        assert "model_type" in tags
        assert "created_at" in tags


# ============================================================================
# TEST RUN LIFECYCLE
# ============================================================================

class TestRunLifecycle:
    """Tests for run lifecycle management."""
    
    def test_start_run(self, tracker, mock_mlflow_client):
        """Test starting a new run."""
        # Setup
        mock_run = MagicMock()
        mock_run.info.run_id = "run123"
        mock_mlflow_client.create_run.return_value = mock_run
        
        # Execute
        run_id = tracker.start_run(
            experiment_id="exp1",
            run_name="test_run",
            tags={"baseline": "true"},
        )
        
        # Verify
        assert run_id == "run123"
        mock_mlflow_client.create_run.assert_called_once_with(
            experiment_id="exp1",
            run_name="test_run",
            tags={"baseline": "true"},
        )
    
    def test_start_run_without_tags(self, tracker, mock_mlflow_client):
        """Test starting run without tags."""
        # Setup
        mock_run = MagicMock()
        mock_run.info.run_id = "run456"
        mock_mlflow_client.create_run.return_value = mock_run
        
        # Execute
        run_id = tracker.start_run(
            experiment_id="exp2",
            run_name="simple_run",
        )
        
        # Verify
        assert run_id == "run456"
        call_args = mock_mlflow_client.create_run.call_args
        assert call_args[1].get("tags") is None
    
    def test_end_run_finished(self, tracker, mock_mlflow_client):
        """Test ending run with FINISHED status."""
        # Execute
        tracker.end_run(run_id="run123", status="FINISHED")
        
        # Verify
        mock_mlflow_client.set_terminated.assert_called_once_with(
            "run123", "FINISHED"
        )
    
    def test_end_run_failed(self, tracker, mock_mlflow_client):
        """Test ending run with FAILED status."""
        # Execute
        tracker.end_run(run_id="run456", status="FAILED")
        
        # Verify
        mock_mlflow_client.set_terminated.assert_called_once_with(
            "run456", "FAILED"
        )


# ============================================================================
# TEST LOGGING
# ============================================================================

class TestLogging:
    """Tests for logging metrics, params, and artifacts."""
    
    def test_log_params(self, tracker, mock_mlflow_client):
        """Test logging parameters."""
        # Execute
        tracker.log_params(
            run_id="run123",
            params={"n_estimators": 100, "learning_rate": 0.1},
        )
        
        # Verify
        assert mock_mlflow_client.log_param.call_count == 2
        calls = mock_mlflow_client.log_param.call_args_list
        assert call(run_id="run123", key="n_estimators", value="100") in calls
        assert call(run_id="run123", key="learning_rate", value="0.1") in calls
    
    def test_log_metrics(self, tracker, mock_mlflow_client):
        """Test logging metrics."""
        # Execute
        tracker.log_metrics(
            run_id="run123",
            metrics={"mae": 12.5, "rmse": 18.3},
            step=10,
        )
        
        # Verify
        assert mock_mlflow_client.log_metric.call_count == 2
        calls = mock_mlflow_client.log_metric.call_args_list
        # Check that both metrics were logged with correct step
        for call_obj in calls:
            assert call_obj[1]["run_id"] == "run123"
            assert call_obj[1]["step"] == 10
    
    def test_log_metrics_without_step(self, tracker, mock_mlflow_client):
        """Test logging metrics without step."""
        # Execute
        tracker.log_metrics(
            run_id="run456",
            metrics={"accuracy": 0.95},
        )
        
        # Verify
        mock_mlflow_client.log_metric.assert_called_once()
        call_args = mock_mlflow_client.log_metric.call_args
        assert "step" not in call_args[1] or call_args[1]["step"] is None
    
    def test_log_artifact(self, tracker, mock_mlflow_client):
        """Test logging artifact."""
        # Execute
        tracker.log_artifact(
            run_id="run123",
            local_path="/tmp/model.pkl",
            artifact_path="models",
        )
        
        # Verify
        mock_mlflow_client.log_artifact.assert_called_once_with(
            run_id="run123",
            local_path="/tmp/model.pkl",
            artifact_path="models",
        )
    
    def test_set_tags(self, tracker, mock_mlflow_client):
        """Test setting tags."""
        # Execute
        tracker.set_tags(
            run_id="run123",
            tags={"version": "v2", "environment": "production"},
        )
        
        # Verify
        mock_mlflow_client.set_tag.assert_called()
        assert mock_mlflow_client.set_tag.call_count == 2
    
    @patch("app.services.experiment_tracker.mlflow.sklearn.log_model")
    def test_log_model(self, mock_log_model, tracker, mock_mlflow_client):
        """Test logging sklearn model."""
        # Setup
        mock_model = MagicMock()
        
        # Execute
        tracker.log_model(
            run_id="run123",
            model=mock_model,
            artifact_path="model",
            registered_model_name="my_model",
        )
        
        # Verify
        mock_log_model.assert_called_once_with(
            mock_model,
            "model",
            registered_model_name="my_model",
        )
    
    def test_log_training_config(self, tracker, mock_mlflow_client, sample_training_config):
        """Test logging training configuration."""
        # Execute
        with patch("builtins.open", MagicMock()):
            with patch("json.dump", MagicMock()):
                tracker.log_training_config(
                    run_id="run123",
                    config=sample_training_config,
                )
        
        # Verify - should log flattened params
        assert mock_mlflow_client.log_param.called
        # Should log multiple params from flattened config
        assert mock_mlflow_client.log_param.call_count > 5


# ============================================================================
# TEST RUN RETRIEVAL
# ============================================================================

class TestRunRetrieval:
    """Tests for retrieving run information."""
    
    def test_get_run(self, tracker, mock_mlflow_client):
        """Test getting run details."""
        # Setup
        mock_run = MagicMock()
        mock_run.info.run_id = "run123"
        mock_run.info.experiment_id = "exp1"
        mock_run.info.run_name = "test_run"
        mock_run.info.status = "FINISHED"
        mock_run.info.start_time = 1234567890
        mock_run.info.end_time = 1234567900
        mock_run.info.artifact_uri = "s3://bucket/artifacts"
        mock_run.data.params = {"n_estimators": "100"}
        mock_run.data.metrics = {"mae": 12.5}
        mock_run.data.tags = {"version": "v1"}
        mock_mlflow_client.get_run.return_value = mock_run
        
        # Execute
        run_data = tracker.get_run("run123")
        
        # Verify
        assert run_data["run_id"] == "run123"
        assert run_data["experiment_id"] == "exp1"
        assert run_data["run_name"] == "test_run"
        assert run_data["status"] == "FINISHED"
        assert run_data["params"] == {"n_estimators": "100"}
        assert run_data["metrics"] == {"mae": 12.5}
        assert run_data["tags"] == {"version": "v1"}
    
    def test_get_run_not_found(self, tracker, mock_mlflow_client):
        """Test getting non-existent run."""
        # Setup
        mock_mlflow_client.get_run.side_effect = Exception("Run not found")
        
        # Execute & Verify
        with pytest.raises(Exception, match="Run not found"):
            tracker.get_run("run999")


# ============================================================================
# TEST RUN SEARCH
# ============================================================================

class TestRunSearch:
    """Tests for searching runs."""
    
    def test_search_runs(self, tracker, mock_mlflow_client):
        """Test searching runs."""
        # Setup
        mock_run1 = MagicMock()
        mock_run1.info.run_id = "run1"
        mock_run1.data.metrics = {"mae": 10.0}
        
        mock_run2 = MagicMock()
        mock_run2.info.run_id = "run2"
        mock_run2.data.metrics = {"mae": 15.0}
        
        mock_mlflow_client.search_runs.return_value = [mock_run1, mock_run2]
        
        # Execute
        runs = tracker.search_runs(
            experiment_ids=["exp1"],
            filter_string="metrics.mae < 20",
            max_results=10,
        )
        
        # Verify
        assert len(runs) == 2
        mock_mlflow_client.search_runs.assert_called_once_with(
            experiment_ids=["exp1"],
            filter_string="metrics.mae < 20",
            max_results=10,
            order_by=None,
        )
    
    def test_search_runs_with_ordering(self, tracker, mock_mlflow_client):
        """Test searching runs with ordering."""
        # Setup
        mock_mlflow_client.search_runs.return_value = []
        
        # Execute
        tracker.search_runs(
            experiment_ids=["exp1"],
            order_by=["metrics.mae ASC"],
        )
        
        # Verify
        call_args = mock_mlflow_client.search_runs.call_args
        assert call_args[1]["order_by"] == ["metrics.mae ASC"]
    
    def test_search_runs_multiple_experiments(self, tracker, mock_mlflow_client):
        """Test searching across multiple experiments."""
        # Setup
        mock_mlflow_client.search_runs.return_value = []
        
        # Execute
        tracker.search_runs(experiment_ids=["exp1", "exp2", "exp3"])
        
        # Verify
        call_args = mock_mlflow_client.search_runs.call_args
        assert call_args[1]["experiment_ids"] == ["exp1", "exp2", "exp3"]


# ============================================================================
# TEST RUN COMPARISON
# ============================================================================

class TestRunComparison:
    """Tests for comparing runs."""
    
    def test_compare_runs(self, tracker, mock_mlflow_client):
        """Test comparing multiple runs."""
        # Setup
        mock_run1 = MagicMock()
        mock_run1.info.run_id = "run1"
        mock_run1.data.params = {"n_estimators": "100"}
        mock_run1.data.metrics = {"mae": 10.0, "rmse": 15.0}
        
        mock_run2 = MagicMock()
        mock_run2.info.run_id = "run2"
        mock_run2.data.params = {"n_estimators": "200"}
        mock_run2.data.metrics = {"mae": 12.0, "rmse": 16.0}
        
        mock_mlflow_client.get_run.side_effect = [mock_run1, mock_run2]
        
        # Execute
        comparison = tracker.compare_runs(
            run_ids=["run1", "run2"],
            metric_keys=["mae", "rmse"],
        )
        
        # Verify
        assert len(comparison["runs"]) == 2
        assert comparison["runs"][0]["run_id"] == "run1"
        assert comparison["runs"][0]["metrics"]["mae"] == 10.0
        assert comparison["runs"][1]["run_id"] == "run2"
        assert comparison["runs"][1]["metrics"]["mae"] == 12.0
    
    def test_compare_runs_all_metrics(self, tracker, mock_mlflow_client):
        """Test comparing runs with all metrics."""
        # Setup
        mock_run = MagicMock()
        mock_run.info.run_id = "run1"
        mock_run.data.params = {}
        mock_run.data.metrics = {"mae": 10.0, "rmse": 15.0, "mape": 5.0}
        mock_mlflow_client.get_run.return_value = mock_run
        
        # Execute
        comparison = tracker.compare_runs(run_ids=["run1"])
        
        # Verify
        assert len(comparison["runs"][0]["metrics"]) == 3


# ============================================================================
# TEST BEST RUN SELECTION
# ============================================================================

class TestBestRunSelection:
    """Tests for finding best run."""
    
    def test_get_best_run_minimize(self, tracker, mock_mlflow_client):
        """Test getting best run by minimizing metric."""
        # Setup
        mock_run = MagicMock()
        mock_run.info.run_id = "run_best"
        mock_run.data.metrics = {"mae": 8.5}
        mock_mlflow_client.search_runs.return_value = [mock_run]
        
        # Execute
        best_run = tracker.get_best_run(
            experiment_id="exp1",
            metric_key="mae",
            maximize=False,
        )
        
        # Verify
        assert best_run["run_id"] == "run_best"
        # Should order by metric ascending (minimize)
        call_args = mock_mlflow_client.search_runs.call_args
        assert "ASC" in call_args[1]["order_by"][0]
    
    def test_get_best_run_maximize(self, tracker, mock_mlflow_client):
        """Test getting best run by maximizing metric."""
        # Setup
        mock_run = MagicMock()
        mock_run.info.run_id = "run_best"
        mock_run.data.metrics = {"r2_score": 0.95}
        mock_mlflow_client.search_runs.return_value = [mock_run]
        
        # Execute
        best_run = tracker.get_best_run(
            experiment_id="exp1",
            metric_key="r2_score",
            maximize=True,
        )
        
        # Verify
        assert best_run["run_id"] == "run_best"
        # Should order by metric descending (maximize)
        call_args = mock_mlflow_client.search_runs.call_args
        assert "DESC" in call_args[1]["order_by"][0]
    
    def test_get_best_run_no_runs(self, tracker, mock_mlflow_client):
        """Test getting best run when no runs exist."""
        # Setup
        mock_mlflow_client.search_runs.return_value = []
        
        # Execute
        best_run = tracker.get_best_run(
            experiment_id="exp_empty",
            metric_key="mae",
        )
        
        # Verify
        assert best_run is None


# ============================================================================
# TEST EXPERIMENT STATISTICS
# ============================================================================

class TestExperimentStatistics:
    """Tests for experiment statistics."""
    
    def test_get_experiment_stats(self, tracker, mock_mlflow_client):
        """Test calculating experiment statistics."""
        # Setup
        mock_run1 = MagicMock()
        mock_run1.info.status = "FINISHED"
        mock_run1.data.metrics = {"mae": 10.0, "rmse": 15.0}
        
        mock_run2 = MagicMock()
        mock_run2.info.status = "FINISHED"
        mock_run2.data.metrics = {"mae": 12.0, "rmse": 18.0}
        
        mock_run3 = MagicMock()
        mock_run3.info.status = "FAILED"
        mock_run3.data.metrics = {}
        
        mock_mlflow_client.search_runs.return_value = [mock_run1, mock_run2, mock_run3]
        
        # Execute
        stats = tracker.get_experiment_stats("exp1")
        
        # Verify
        assert stats["experiment_id"] == "exp1"
        assert stats["total_runs"] == 3
        assert stats["status_counts"]["FINISHED"] == 2
        assert stats["status_counts"]["FAILED"] == 1
        assert "mae" in stats["metric_stats"]
        assert "rmse" in stats["metric_stats"]
        
        # Check MAE statistics
        mae_stats = stats["metric_stats"]["mae"]
        assert mae_stats["count"] == 2
        assert mae_stats["mean"] == 11.0  # (10 + 12) / 2
        assert mae_stats["min"] == 10.0
        assert mae_stats["max"] == 12.0
    
    def test_get_experiment_stats_empty(self, tracker, mock_mlflow_client):
        """Test statistics for empty experiment."""
        # Setup
        mock_mlflow_client.search_runs.return_value = []
        
        # Execute
        stats = tracker.get_experiment_stats("exp_empty")
        
        # Verify
        assert stats["total_runs"] == 0
        assert stats["status_counts"] == {}
        assert stats["metric_stats"] == {}


# ============================================================================
# TEST RUN DELETION
# ============================================================================

class TestRunDeletion:
    """Tests for deleting runs."""
    
    def test_delete_run(self, tracker, mock_mlflow_client):
        """Test deleting run."""
        # Execute
        tracker.delete_run("run123")
        
        # Verify
        mock_mlflow_client.delete_run.assert_called_once_with("run123")


# ============================================================================
# TEST UTILITY METHODS
# ============================================================================

class TestUtilityMethods:
    """Tests for utility methods."""
    
    def test_flatten_dict_simple(self, tracker):
        """Test flattening simple dict."""
        # Execute
        result = tracker._flatten_dict({"a": 1, "b": 2})
        
        # Verify
        assert result == {"a": 1, "b": 2}
    
    def test_flatten_dict_nested(self, tracker):
        """Test flattening nested dict."""
        # Execute
        result = tracker._flatten_dict({
            "model": {
                "type": "lgbm",
                "params": {
                    "n_estimators": 100,
                    "learning_rate": 0.1,
                }
            }
        })
        
        # Verify
        assert result["model.type"] == "lgbm"
        assert result["model.params.n_estimators"] == 100
        assert result["model.params.learning_rate"] == 0.1
    
    def test_flatten_dict_with_lists(self, tracker):
        """Test flattening dict with lists."""
        # Execute
        result = tracker._flatten_dict({
            "features": ["temp", "humidity"],
            "metadata": {"version": "v1"}
        })
        
        # Verify
        assert "features" in result
        # Lists should be converted to strings
        assert isinstance(result["features"], str)
        assert result["metadata.version"] == "v1"
