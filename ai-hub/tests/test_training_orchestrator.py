"""
Tests for TrainingOrchestrator service.

Tests job lifecycle management, queue operations, and state transitions.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.training_orchestrator import TrainingOrchestrator
from app.models.training import (
    TrainingJobCreate,
    TrainingConfig,
    ModelType,
    JobPriority,
    JobStatus,
    JobFilters,
)


@pytest.fixture
def mock_db_session():
    """Mock async database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def orchestrator(mock_db_session):
    """Create TrainingOrchestrator instance with mocked database."""
    return TrainingOrchestrator(mock_db_session, max_concurrent_jobs=3)


@pytest.fixture
def sample_training_config():
    """Sample training configuration."""
    return TrainingConfig(
        start_date=datetime(2025, 1, 1),
        end_date=datetime(2025, 10, 1),
        feature_set="forecast_basic",
        target_variable="load_kw",
        horizon=24,
        validation_split=0.2,
        test_split=0.1,
        enable_hpo=False,
        hyperparams={},
    )


@pytest.fixture
def sample_job_request(sample_training_config):
    """Sample training job request."""
    return TrainingJobCreate(
        tenant_id="tenant-123",
        model_type=ModelType.FORECAST,
        model_name="load_forecast",
        config=sample_training_config,
        priority=JobPriority.NORMAL,
    )


class TestJobCreation:
    """Tests for job creation."""
    
    @pytest.mark.asyncio
    async def test_create_job_success(self, orchestrator, sample_job_request, mock_db_session):
        """Test successful job creation."""
        # Mock database insert
        mock_db_session.execute = AsyncMock()
        mock_db_session.commit = AsyncMock()
        
        # Create job
        job = await orchestrator.create_job(sample_job_request, created_by="test_user")
        
        # Assertions
        assert job.tenant_id == "tenant-123"
        assert job.model_type == ModelType.FORECAST
        assert job.model_name == "load_forecast"
        assert job.status == JobStatus.QUEUED
        assert job.priority == JobPriority.NORMAL.value
        assert job.progress == 0.0
        assert job.created_by == "test_user"
        assert job.job_id is not None
        assert job.estimated_completion is not None
        
        # Verify database operations
        mock_db_session.execute.assert_called_once()
        mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_job_with_high_priority(self, orchestrator, sample_job_request, mock_db_session):
        """Test job creation with high priority."""
        sample_job_request.priority = JobPriority.HIGH
        
        job = await orchestrator.create_job(sample_job_request)
        
        assert job.priority == JobPriority.HIGH.value
    
    @pytest.mark.asyncio
    async def test_create_job_with_schedule(self, orchestrator, sample_job_request, mock_db_session):
        """Test job creation with cron schedule."""
        sample_job_request.schedule = "0 0 * * *"  # Daily at midnight
        
        job = await orchestrator.create_job(sample_job_request)
        
        # Verify schedule is stored (will be used later for recurring jobs)
        assert job is not None
    
    @pytest.mark.asyncio
    async def test_create_job_with_tags(self, orchestrator, sample_job_request, mock_db_session):
        """Test job creation with custom tags."""
        sample_job_request.tags = {"experiment": "test", "version": "v1"}
        
        job = await orchestrator.create_job(sample_job_request)
        
        assert job.tags == {"experiment": "test", "version": "v1"}
    
    @pytest.mark.asyncio
    async def test_duration_estimation_without_hpo(self, orchestrator, sample_job_request):
        """Test duration estimation without HPO."""
        sample_job_request.config.enable_hpo = False
        sample_job_request.config.n_workers = 1
        
        # Estimate should be ~3 minutes (180 seconds)
        estimated = orchestrator._estimate_duration(sample_job_request.config)
        
        assert 150 <= estimated <= 210  # Within reasonable range
    
    @pytest.mark.asyncio
    async def test_duration_estimation_with_hpo(self, orchestrator, sample_job_request):
        """Test duration estimation with HPO enabled."""
        sample_job_request.config.enable_hpo = True
        sample_job_request.config.n_trials = 50
        sample_job_request.config.n_workers = 2
        
        # Should be longer due to HPO trials
        estimated = orchestrator._estimate_duration(sample_job_request.config)
        
        assert estimated > 180  # More than base time


class TestJobRetrieval:
    """Tests for job retrieval operations."""
    
    @pytest.mark.asyncio
    async def test_get_job_exists(self, orchestrator, mock_db_session):
        """Test retrieving an existing job."""
        job_id = uuid4()
        
        # Mock database response
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.job_id = job_id
        mock_row.tenant_id = "tenant-123"
        mock_row.model_type = "forecast"
        mock_row.model_name = "test_model"
        mock_row.feature_set = "forecast_basic"
        mock_row.status = "queued"
        mock_row.priority = 0
        mock_row.progress = 0.0
        mock_row.metrics = None
        mock_row.error_message = None
        mock_row.model_id = None
        mock_row.created_at = datetime.utcnow()
        mock_row.started_at = None
        mock_row.completed_at = None
        mock_row.updated_at = datetime.utcnow()
        mock_row.created_by = None
        mock_row.tags = {}
        
        mock_result.fetchone.return_value = mock_row
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        # Get job
        job = await orchestrator.get_job(job_id)
        
        # Assertions
        assert job is not None
        assert job.job_id == job_id
        assert job.tenant_id == "tenant-123"
        assert job.model_type == ModelType.FORECAST
        assert job.status == JobStatus.QUEUED
    
    @pytest.mark.asyncio
    async def test_get_job_not_found(self, orchestrator, mock_db_session):
        """Test retrieving non-existent job."""
        job_id = uuid4()
        
        # Mock empty result
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        # Get job
        job = await orchestrator.get_job(job_id)
        
        assert job is None
    
    @pytest.mark.asyncio
    async def test_list_jobs_with_filters(self, orchestrator, mock_db_session):
        """Test listing jobs with filters."""
        # Mock database response
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0
        
        mock_db_session.execute = AsyncMock(side_effect=[mock_count_result, mock_result])
        
        # List jobs
        filters = JobFilters(
            tenant_id="tenant-123",
            model_type=ModelType.FORECAST,
            status=JobStatus.COMPLETED,
            page=1,
            page_size=20,
        )
        
        result = await orchestrator.list_jobs(filters)
        
        assert result.total == 0
        assert result.page == 1
        assert result.page_size == 20
        assert len(result.jobs) == 0
    
    @pytest.mark.asyncio
    async def test_list_jobs_pagination(self, orchestrator, mock_db_session):
        """Test job listing with pagination."""
        # Mock 50 total jobs
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 50
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        
        mock_db_session.execute = AsyncMock(side_effect=[mock_count_result, mock_result])
        
        # Request page 2
        filters = JobFilters(page=2, page_size=20)
        result = await orchestrator.list_jobs(filters)
        
        assert result.total == 50
        assert result.page == 2


class TestJobCancellation:
    """Tests for job cancellation."""
    
    @pytest.mark.asyncio
    async def test_cancel_queued_job(self, orchestrator, mock_db_session):
        """Test cancelling a queued job."""
        job_id = uuid4()
        
        # Mock job exists and is queued
        mock_select_result = MagicMock()
        mock_row = MagicMock()
        mock_row.status = "queued"
        mock_select_result.fetchone.return_value = mock_row
        
        mock_update_result = MagicMock()
        
        mock_db_session.execute = AsyncMock(side_effect=[mock_select_result, mock_update_result])
        mock_db_session.commit = AsyncMock()
        
        # Cancel job
        result = await orchestrator.cancel_job(job_id)
        
        assert result is True
        mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cancel_running_job(self, orchestrator, mock_db_session):
        """Test cancelling a running job."""
        job_id = uuid4()
        
        # Add mock running task
        mock_task = MagicMock()
        orchestrator._running_jobs[job_id] = mock_task
        
        # Mock job exists and is running
        mock_select_result = MagicMock()
        mock_row = MagicMock()
        mock_row.status = "running"
        mock_select_result.fetchone.return_value = mock_row
        
        mock_update_result = MagicMock()
        
        mock_db_session.execute = AsyncMock(side_effect=[mock_select_result, mock_update_result])
        mock_db_session.commit = AsyncMock()
        
        # Cancel job
        result = await orchestrator.cancel_job(job_id)
        
        assert result is True
        mock_task.cancel.assert_called_once()
        assert job_id not in orchestrator._running_jobs
    
    @pytest.mark.asyncio
    async def test_cancel_completed_job_fails(self, orchestrator, mock_db_session):
        """Test that completed jobs cannot be cancelled."""
        job_id = uuid4()
        
        # Mock job exists and is completed
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.status = "completed"
        mock_result.fetchone.return_value = mock_row
        
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        # Cancel job
        result = await orchestrator.cancel_job(job_id)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_job(self, orchestrator, mock_db_session):
        """Test cancelling a job that doesn't exist."""
        job_id = uuid4()
        
        # Mock empty result
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        # Cancel job
        result = await orchestrator.cancel_job(job_id)
        
        assert result is False


class TestJobRetry:
    """Tests for job retry functionality."""
    
    @pytest.mark.asyncio
    async def test_retry_failed_job(self, orchestrator, mock_db_session):
        """Test retrying a failed job."""
        original_job_id = uuid4()
        
        # Mock original job
        mock_select_result = MagicMock()
        mock_row = MagicMock()
        mock_row.job_id = original_job_id
        mock_row.tenant_id = "tenant-123"
        mock_row.model_type = "forecast"
        mock_row.model_name = "test_model"
        mock_row.config = {
            "start_date": "2025-01-01T00:00:00",
            "end_date": "2025-10-01T00:00:00",
            "feature_set": "forecast_basic",
            "target_variable": "load_kw",
            "horizon": 24,
            "validation_split": 0.2,
            "test_split": 0.1,
            "enable_hpo": False,
            "n_trials": 50,
            "hyperparams": {},
            "early_stopping": True,
            "early_stopping_rounds": 10,
            "random_seed": 42,
            "n_workers": 1,
            "save_artifacts": True,
            "register_model": True,
            "auto_promote": False,
        }
        mock_row.schedule = None
        mock_row.priority = 0
        mock_row.tags = {}
        mock_row.created_by = "test_user"
        mock_select_result.fetchone.return_value = mock_row
        
        # Mock insert for new job
        mock_insert_result = MagicMock()
        
        mock_db_session.execute = AsyncMock(side_effect=[mock_select_result, mock_insert_result])
        mock_db_session.commit = AsyncMock()
        
        # Retry job
        new_job = await orchestrator.retry_job(original_job_id)
        
        assert new_job is not None
        assert new_job.job_id != original_job_id
        assert new_job.tags.get("retry_of") == str(original_job_id)
    
    @pytest.mark.asyncio
    async def test_retry_nonexistent_job(self, orchestrator, mock_db_session):
        """Test retrying a job that doesn't exist."""
        job_id = uuid4()
        
        # Mock empty result
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        # Retry job
        new_job = await orchestrator.retry_job(job_id)
        
        assert new_job is None


class TestProgressTracking:
    """Tests for progress tracking."""
    
    @pytest.mark.asyncio
    async def test_update_progress(self, orchestrator, mock_db_session):
        """Test updating job progress."""
        job_id = uuid4()
        
        mock_db_session.execute = AsyncMock()
        mock_db_session.commit = AsyncMock()
        
        # Update progress
        await orchestrator.update_progress(job_id, 0.5)
        
        mock_db_session.execute.assert_called_once()
        mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_progress_with_metrics(self, orchestrator, mock_db_session):
        """Test updating progress with metrics."""
        from app.models.training import TrainingJobMetrics
        
        job_id = uuid4()
        metrics = TrainingJobMetrics(
            best_mae=12.5,
            best_rmse=18.3,
            training_time_seconds=180.5,
        )
        
        mock_db_session.execute = AsyncMock()
        mock_db_session.commit = AsyncMock()
        
        # Update progress with metrics
        await orchestrator.update_progress(job_id, 0.75, metrics)
        
        mock_db_session.execute.assert_called_once()
        mock_db_session.commit.assert_called_once()


class TestStateTransitions:
    """Tests for job state transitions."""
    
    @pytest.mark.asyncio
    async def test_mark_running(self, orchestrator, mock_db_session):
        """Test marking job as running."""
        job_id = uuid4()
        
        mock_db_session.execute = AsyncMock()
        mock_db_session.commit = AsyncMock()
        
        await orchestrator.mark_running(job_id)
        
        mock_db_session.execute.assert_called_once()
        mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mark_completed(self, orchestrator, mock_db_session):
        """Test marking job as completed."""
        from app.models.training import TrainingJobMetrics
        
        job_id = uuid4()
        model_id = "tenant-123:test_model:1.0.0"
        metrics = TrainingJobMetrics(
            best_mae=12.5,
            best_rmse=18.3,
            training_time_seconds=300.0,
        )
        
        mock_db_session.execute = AsyncMock()
        mock_db_session.commit = AsyncMock()
        
        await orchestrator.mark_completed(job_id, model_id, metrics)
        
        mock_db_session.execute.assert_called_once()
        mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mark_failed(self, orchestrator, mock_db_session):
        """Test marking job as failed."""
        job_id = uuid4()
        error_message = "Training failed: Out of memory"
        
        mock_db_session.execute = AsyncMock()
        mock_db_session.commit = AsyncMock()
        
        await orchestrator.mark_failed(job_id, error_message)
        
        mock_db_session.execute.assert_called_once()
        mock_db_session.commit.assert_called_once()


class TestQueueOperations:
    """Tests for queue operations."""
    
    @pytest.mark.asyncio
    async def test_get_queued_jobs(self, orchestrator, mock_db_session):
        """Test getting queued jobs."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        jobs = await orchestrator.get_queued_jobs(limit=10)
        
        assert isinstance(jobs, list)
        mock_db_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_active_jobs_count(self, orchestrator, mock_db_session):
        """Test getting count of active jobs."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 2
        
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        count = await orchestrator.get_active_jobs_count()
        
        assert count == 2
        mock_db_session.execute.assert_called_once()
