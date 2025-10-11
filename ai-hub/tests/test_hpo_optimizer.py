"""
Tests for HPO (Hyperparameter Optimization) service.

Tests Optuna integration including study creation, optimization,
trial tracking, and parameter importance analysis.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.hpo_optimizer import HPOOptimizer
from app.models.training import ModelType, HyperparameterSpec


@pytest.fixture
def optimizer():
    """Create HPOOptimizer instance."""
    return HPOOptimizer(storage_url=None)


@pytest.fixture
def sample_hp_space():
    """Sample hyperparameter search space."""
    return {
        "n_estimators": HyperparameterSpec(
            type="int",
            low=50,
            high=300,
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
    }


class TestStudyCreation:
    """Tests for HPO study creation."""
    
    @pytest.mark.asyncio
    async def test_create_study_basic(self, optimizer):
        """Test basic study creation."""
        result = await optimizer.create_study(
            study_name="test_study",
            tenant_id="tenant-123",
            model_type=ModelType.FORECAST,
            optimization_direction="minimize",
            sampler_type="tpe",
            pruner_type="median",
            n_trials=20,
        )
        
        assert result["study_id"] == "test_study"
        assert result["tenant_id"] == "tenant-123"
        assert result["model_type"] == "forecast"
        assert result["direction"] == "minimize"
        assert result["sampler"] == "tpe"
        assert result["pruner"] == "median"
        assert result["n_trials"] == 20
        assert result["status"] == "created"
    
    @pytest.mark.asyncio
    async def test_create_study_with_random_sampler(self, optimizer):
        """Test study creation with random sampler."""
        result = await optimizer.create_study(
            study_name="random_study",
            tenant_id="tenant-123",
            model_type=ModelType.ANOMALY,
            sampler_type="random",
            pruner_type="none",
        )
        
        assert result["sampler"] == "random"
        assert result["pruner"] == "none"
    
    @pytest.mark.asyncio
    async def test_create_study_with_timeout(self, optimizer):
        """Test study creation with timeout."""
        result = await optimizer.create_study(
            study_name="timeout_study",
            tenant_id="tenant-123",
            model_type=ModelType.FORECAST,
            n_trials=100,
            timeout_seconds=3600,
        )
        
        assert result["n_trials"] == 100
    
    @pytest.mark.asyncio
    async def test_create_study_invalid_sampler(self, optimizer):
        """Test study creation with invalid sampler."""
        with pytest.raises(ValueError, match="Unknown sampler type"):
            await optimizer.create_study(
                study_name="invalid_study",
                tenant_id="tenant-123",
                model_type=ModelType.FORECAST,
                sampler_type="invalid",
            )
    
    @pytest.mark.asyncio
    async def test_create_study_invalid_pruner(self, optimizer):
        """Test study creation with invalid pruner."""
        with pytest.raises(ValueError, match="Unknown pruner type"):
            await optimizer.create_study(
                study_name="invalid_study",
                tenant_id="tenant-123",
                model_type=ModelType.FORECAST,
                pruner_type="invalid",
            )


class TestOptimization:
    """Tests for optimization execution."""
    
    @pytest.mark.asyncio
    async def test_optimize_basic(self, optimizer, sample_hp_space):
        """Test basic optimization."""
        # Create study
        await optimizer.create_study(
            study_name="opt_test",
            tenant_id="tenant-123",
            model_type=ModelType.FORECAST,
        )
        
        # Mock objective function
        def objective(params, trial):
            return params["n_estimators"] * 0.001 + params["learning_rate"]
        
        # Run optimization
        result = await optimizer.optimize(
            study_name="opt_test",
            objective_func=objective,
            hyperparameter_space=sample_hp_space,
            n_trials=5,
            n_jobs=1,
        )
        
        assert result["study_id"] == "opt_test"
        assert result["n_trials"] == 5
        assert result["completed_trials"] <= 5
        assert "best_value" in result
        assert "best_params" in result
        assert "best_trial_number" in result
    
    @pytest.mark.asyncio
    async def test_optimize_with_progress_callback(self, optimizer, sample_hp_space):
        """Test optimization with progress callback."""
        await optimizer.create_study(
            study_name="progress_test",
            tenant_id="tenant-123",
            model_type=ModelType.FORECAST,
        )
        
        progress_updates = []
        
        async def progress_callback(current, total):
            progress_updates.append((current, total))
        
        def objective(params, trial):
            return params["n_estimators"] * 0.001
        
        result = await optimizer.optimize(
            study_name="progress_test",
            objective_func=objective,
            hyperparameter_space=sample_hp_space,
            n_trials=3,
            progress_callback=progress_callback,
        )
        
        # Check progress updates were made
        assert len(progress_updates) >= 1
    
    @pytest.mark.asyncio
    async def test_optimize_nonexistent_study(self, optimizer, sample_hp_space):
        """Test optimization on non-existent study."""
        def objective(params, trial):
            return 0.5
        
        with pytest.raises(ValueError, match="Study not found"):
            await optimizer.optimize(
                study_name="nonexistent",
                objective_func=objective,
                hyperparameter_space=sample_hp_space,
                n_trials=5,
            )
    
    @pytest.mark.asyncio
    async def test_optimize_with_timeout(self, optimizer, sample_hp_space):
        """Test optimization with timeout."""
        await optimizer.create_study(
            study_name="timeout_test",
            tenant_id="tenant-123",
            model_type=ModelType.FORECAST,
        )
        
        def objective(params, trial):
            import time
            time.sleep(0.1)
            return params["n_estimators"] * 0.001
        
        result = await optimizer.optimize(
            study_name="timeout_test",
            objective_func=objective,
            hyperparameter_space=sample_hp_space,
            n_trials=100,
            timeout_seconds=1,  # Very short timeout
        )
        
        # Should complete fewer trials due to timeout
        assert result["completed_trials"] < 100


class TestStudyStatus:
    """Tests for study status retrieval."""
    
    @pytest.mark.asyncio
    async def test_get_study_status_new(self, optimizer):
        """Test status of newly created study."""
        await optimizer.create_study(
            study_name="status_test",
            tenant_id="tenant-123",
            model_type=ModelType.FORECAST,
        )
        
        status = await optimizer.get_study_status("status_test")
        
        assert status["study_id"] == "status_test"
        assert status["tenant_id"] == "tenant-123"
        assert status["model_type"] == "forecast"
        assert status["n_trials"] == 0
        assert status["completed_trials"] == 0
        assert status["best_value"] is None
    
    @pytest.mark.asyncio
    async def test_get_study_status_after_optimization(self, optimizer, sample_hp_space):
        """Test status after optimization."""
        await optimizer.create_study(
            study_name="status_opt_test",
            tenant_id="tenant-123",
            model_type=ModelType.FORECAST,
        )
        
        def objective(params, trial):
            return params["n_estimators"] * 0.001
        
        await optimizer.optimize(
            study_name="status_opt_test",
            objective_func=objective,
            hyperparameter_space=sample_hp_space,
            n_trials=3,
        )
        
        status = await optimizer.get_study_status("status_opt_test")
        
        assert status["completed_trials"] > 0
        assert status["best_value"] is not None
        assert status["best_params"] is not None
        assert status["best_trial_number"] is not None
    
    @pytest.mark.asyncio
    async def test_get_study_status_nonexistent(self, optimizer):
        """Test status of non-existent study."""
        with pytest.raises(ValueError, match="Study not found"):
            await optimizer.get_study_status("nonexistent")


class TestTrialHistory:
    """Tests for trial history retrieval."""
    
    @pytest.mark.asyncio
    async def test_get_trial_history(self, optimizer, sample_hp_space):
        """Test retrieving trial history."""
        await optimizer.create_study(
            study_name="history_test",
            tenant_id="tenant-123",
            model_type=ModelType.FORECAST,
        )
        
        def objective(params, trial):
            return params["n_estimators"] * 0.001
        
        await optimizer.optimize(
            study_name="history_test",
            objective_func=objective,
            hyperparameter_space=sample_hp_space,
            n_trials=3,
        )
        
        history = await optimizer.get_trial_history("history_test")
        
        assert len(history) > 0
        assert all("trial_number" in trial for trial in history)
        assert all("state" in trial for trial in history)
        assert all("params" in trial for trial in history)
    
    @pytest.mark.asyncio
    async def test_get_trial_history_exclude_pruned(self, optimizer, sample_hp_space):
        """Test excluding pruned trials."""
        await optimizer.create_study(
            study_name="pruned_test",
            tenant_id="tenant-123",
            model_type=ModelType.FORECAST,
            pruner_type="median",
        )
        
        def objective(params, trial):
            # Report intermediate values for pruning
            for step in range(5):
                trial.report(params["n_estimators"] * 0.001 * step, step)
                if trial.should_prune():
                    raise Exception("Pruned")
            return params["n_estimators"] * 0.001
        
        await optimizer.optimize(
            study_name="pruned_test",
            objective_func=objective,
            hyperparameter_space=sample_hp_space,
            n_trials=5,
        )
        
        # Get history excluding pruned
        history_no_pruned = await optimizer.get_trial_history(
            "pruned_test",
            include_pruned=False,
        )
        
        # Get history including pruned
        history_all = await optimizer.get_trial_history(
            "pruned_test",
            include_pruned=True,
        )
        
        # Should have fewer trials when excluding pruned
        assert len(history_no_pruned) <= len(history_all)


class TestParameterImportance:
    """Tests for parameter importance analysis."""
    
    @pytest.mark.asyncio
    async def test_get_param_importances(self, optimizer, sample_hp_space):
        """Test parameter importance calculation."""
        await optimizer.create_study(
            study_name="importance_test",
            tenant_id="tenant-123",
            model_type=ModelType.FORECAST,
        )
        
        def objective(params, trial):
            # learning_rate has high impact
            return params["learning_rate"] * 10 + params["n_estimators"] * 0.001
        
        await optimizer.optimize(
            study_name="importance_test",
            objective_func=objective,
            hyperparameter_space=sample_hp_space,
            n_trials=10,
        )
        
        importances = await optimizer.get_param_importances("importance_test")
        
        # Should have importances for all params (if enough trials)
        if len(importances) > 0:
            assert all(0 <= v <= 1 for v in importances.values())
    
    @pytest.mark.asyncio
    async def test_get_param_importances_insufficient_trials(self, optimizer, sample_hp_space):
        """Test importance with insufficient trials."""
        await optimizer.create_study(
            study_name="few_trials",
            tenant_id="tenant-123",
            model_type=ModelType.FORECAST,
        )
        
        def objective(params, trial):
            return params["n_estimators"] * 0.001
        
        await optimizer.optimize(
            study_name="few_trials",
            objective_func=objective,
            hyperparameter_space=sample_hp_space,
            n_trials=1,
        )
        
        importances = await optimizer.get_param_importances("few_trials")
        
        # Should return empty dict with <2 trials
        assert importances == {}


class TestOptimizationHistory:
    """Tests for optimization history."""
    
    @pytest.mark.asyncio
    async def test_get_optimization_history(self, optimizer, sample_hp_space):
        """Test optimization history retrieval."""
        await optimizer.create_study(
            study_name="opt_history",
            tenant_id="tenant-123",
            model_type=ModelType.FORECAST,
        )
        
        def objective(params, trial):
            return params["n_estimators"] * 0.001
        
        await optimizer.optimize(
            study_name="opt_history",
            objective_func=objective,
            hyperparameter_space=sample_hp_space,
            n_trials=5,
        )
        
        history = await optimizer.get_optimization_history("opt_history")
        
        assert "trial_numbers" in history
        assert "values" in history
        assert "best_values" in history
        assert len(history["trial_numbers"]) == len(history["values"])
        assert len(history["values"]) == len(history["best_values"])
    
    @pytest.mark.asyncio
    async def test_optimization_history_best_values_decrease(self, optimizer, sample_hp_space):
        """Test that best values improve over time (for minimize)."""
        await optimizer.create_study(
            study_name="best_decrease",
            tenant_id="tenant-123",
            model_type=ModelType.FORECAST,
            optimization_direction="minimize",
        )
        
        def objective(params, trial):
            return params["n_estimators"] * 0.001
        
        await optimizer.optimize(
            study_name="best_decrease",
            objective_func=objective,
            hyperparameter_space=sample_hp_space,
            n_trials=5,
        )
        
        history = await optimizer.get_optimization_history("best_decrease")
        
        best_values = history["best_values"]
        
        # Best values should be monotonically decreasing (or equal)
        for i in range(1, len(best_values)):
            assert best_values[i] <= best_values[i-1]


class TestStudyDeletion:
    """Tests for study deletion."""
    
    @pytest.mark.asyncio
    async def test_delete_study(self, optimizer):
        """Test study deletion."""
        await optimizer.create_study(
            study_name="delete_test",
            tenant_id="tenant-123",
            model_type=ModelType.FORECAST,
        )
        
        # Verify study exists
        status = await optimizer.get_study_status("delete_test")
        assert status["study_id"] == "delete_test"
        
        # Delete study
        await optimizer.delete_study("delete_test")
        
        # Verify study no longer exists
        with pytest.raises(ValueError, match="Study not found"):
            await optimizer.get_study_status("delete_test")
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_study(self, optimizer):
        """Test deleting non-existent study."""
        with pytest.raises(ValueError, match="Study not found"):
            await optimizer.delete_study("nonexistent")


class TestHyperparameterSuggestions:
    """Tests for hyperparameter space suggestions."""
    
    def test_suggest_hyperparameters_forecast(self, optimizer):
        """Test suggested hyperparameters for forecast model."""
        suggestions = optimizer.suggest_hyperparameters(ModelType.FORECAST)
        
        assert "n_estimators" in suggestions
        assert "learning_rate" in suggestions
        assert "max_depth" in suggestions
        assert isinstance(suggestions["n_estimators"], HyperparameterSpec)
    
    def test_suggest_hyperparameters_anomaly(self, optimizer):
        """Test suggested hyperparameters for anomaly model."""
        suggestions = optimizer.suggest_hyperparameters(ModelType.ANOMALY)
        
        assert "n_estimators" in suggestions
        assert "contamination" in suggestions
        assert isinstance(suggestions["n_estimators"], HyperparameterSpec)


class TestHyperparameterTypes:
    """Tests for different hyperparameter types."""
    
    @pytest.mark.asyncio
    async def test_int_hyperparameter(self, optimizer):
        """Test integer hyperparameter sampling."""
        await optimizer.create_study(
            study_name="int_test",
            tenant_id="tenant-123",
            model_type=ModelType.FORECAST,
        )
        
        hp_space = {
            "n_estimators": HyperparameterSpec(
                type="int",
                low=50,
                high=200,
            ),
        }
        
        def objective(params, trial):
            assert isinstance(params["n_estimators"], int)
            assert 50 <= params["n_estimators"] <= 200
            return params["n_estimators"] * 0.001
        
        await optimizer.optimize(
            study_name="int_test",
            objective_func=objective,
            hyperparameter_space=hp_space,
            n_trials=3,
        )
    
    @pytest.mark.asyncio
    async def test_float_hyperparameter(self, optimizer):
        """Test float hyperparameter sampling."""
        await optimizer.create_study(
            study_name="float_test",
            tenant_id="tenant-123",
            model_type=ModelType.FORECAST,
        )
        
        hp_space = {
            "learning_rate": HyperparameterSpec(
                type="float",
                low=0.01,
                high=0.3,
            ),
        }
        
        def objective(params, trial):
            assert isinstance(params["learning_rate"], float)
            assert 0.01 <= params["learning_rate"] <= 0.3
            return params["learning_rate"]
        
        await optimizer.optimize(
            study_name="float_test",
            objective_func=objective,
            hyperparameter_space=hp_space,
            n_trials=3,
        )
    
    @pytest.mark.asyncio
    async def test_categorical_hyperparameter(self, optimizer):
        """Test categorical hyperparameter sampling."""
        await optimizer.create_study(
            study_name="cat_test",
            tenant_id="tenant-123",
            model_type=ModelType.FORECAST,
        )
        
        hp_space = {
            "boosting_type": HyperparameterSpec(
                type="categorical",
                choices=["gbdt", "dart", "goss"],
            ),
        }
        
        def objective(params, trial):
            assert params["boosting_type"] in ["gbdt", "dart", "goss"]
            return 0.5
        
        await optimizer.optimize(
            study_name="cat_test",
            objective_func=objective,
            hyperparameter_space=hp_space,
            n_trials=3,
        )
