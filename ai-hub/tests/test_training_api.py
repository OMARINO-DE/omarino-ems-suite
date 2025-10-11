"""
Tests for Training API router.

Tests REST API endpoints for training job management including
job creation, retrieval, cancellation, retry, and statistics.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.training import (
    JobStatus, ModelType, JobPriority,
    TrainingJobCreate, TrainingJobResponse,
    TrainingConfig, TrainingJobMetrics,
)
from app.services.training_orchestrator import TrainingOrchestrator


@pytest.fixture
def mock_orchestrator():
    """Mock TrainingOrchestrator."""
    orchestrator = AsyncMock(spec=TrainingOrchestrator)
    return orchestrator


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_job_request():
    """Sample job creation request."""
    return {
        "tenant_id": "tenant-123",
        "model_type": "forecast",
        "model_name": "load_forecaster",
        "config": {
            "start_date": "2025-01-01T00:00:00",
            "end_date": "2025-10-01T00:00:00",
            "feature_set": "forecast_basic",
            "target_variable": "load_kw",
            "horizon": 24,
            "validation_split": 0.2,
            "test_split": 0.1,
        }
    }


@pytest.fixture
def sample_job_response():
    """Sample job response."""
    return TrainingJobResponse(
        id="job-123",
        tenant_id="tenant-123",
        status=JobStatus.QUEUED,
        priority=JobPriority.NORMAL,
        model_type=ModelType.FORECAST,
        model_name="load_forecaster",
        config=TrainingConfig(
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 10, 1),
            feature_set="forecast_basic",
            target_variable="load_kw",
            horizon=24,
        ),
        created_at=datetime(2025, 3, 25, 10, 0, 0),
        started_at=None,
        completed_at=None,
        estimated_duration_minutes=None,
        progress=0.0,
        metrics=None,
        model_id=None,
        error_message=None,
        tags=[],
    )


class TestJobCreation:
    """Tests for POST /ai/training/jobs/start endpoint."""
    
    def test_start_job_success(self, client, mock_orchestrator, sample_job_request, sample_job_response, monkeypatch):
        """Test successful job creation."""
        # Mock dependency
        async def mock_create_job(*args, **kwargs):
            return sample_job_response
        
        mock_orchestrator.create_job = mock_create_job
        
        # Override dependency
        app.dependency_overrides[TrainingOrchestrator] = lambda: mock_orchestrator
        
        # Make request
        response = client.post("/ai/training/jobs/start", json=sample_job_request)
        
        # Check response
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "job-123"
        assert data["status"] == "queued"
        assert data["tenant_id"] == "tenant-123"
        
        # Cleanup
        app.dependency_overrides.clear()
    
    def test_start_job_with_priority(self, client, sample_job_request):
        """Test job creation with priority."""
        sample_job_request["priority"] = "high"
        
        # Mock orchestrator
        mock_orch = AsyncMock()
        async def mock_create(*args, **kwargs):
            assert kwargs.get("priority") == JobPriority.HIGH
            return TrainingJobResponse(
                id="job-124",
                tenant_id="tenant-123",
                status=JobStatus.QUEUED,
                priority=JobPriority.HIGH,
                model_type=ModelType.FORECAST,
                model_name="load_forecaster",
                config=TrainingConfig(
                    start_date=datetime(2025, 1, 1),
                    end_date=datetime(2025, 10, 1),
                    feature_set="forecast_basic",
                    target_variable="load_kw",
                ),
                created_at=datetime.now(),
            )
        
        mock_orch.create_job = mock_create
        app.dependency_overrides[TrainingOrchestrator] = lambda: mock_orch
        
        response = client.post("/ai/training/jobs/start", json=sample_job_request)
        
        assert response.status_code == 201
        assert response.json()["priority"] == "high"
        
        app.dependency_overrides.clear()
    
    def test_start_job_invalid_config(self, client):
        """Test job creation with invalid config."""
        request = {
            "tenant_id": "tenant-123",
            "model_type": "forecast",
            "model_name": "test",
            "config": {
                # Missing required fields
                "target_variable": "load_kw",
            }
        }
        
        response = client.post("/ai/training/jobs/start", json=request)
        
        # Should return 422 (validation error)
        assert response.status_code == 422


class TestJobRetrieval:
    """Tests for job retrieval endpoints."""
    
    def test_get_job_success(self, client, sample_job_response):
        """Test GET /ai/training/jobs/{job_id}."""
        mock_orch = AsyncMock()
        mock_orch.get_job.return_value = sample_job_response
        
        app.dependency_overrides[TrainingOrchestrator] = lambda: mock_orch
        
        response = client.get("/ai/training/jobs/job-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "job-123"
        assert data["status"] == "queued"
        
        app.dependency_overrides.clear()
    
    def test_get_job_not_found(self, client):
        """Test getting non-existent job."""
        mock_orch = AsyncMock()
        mock_orch.get_job.return_value = None
        
        app.dependency_overrides[TrainingOrchestrator] = lambda: mock_orch
        
        response = client.get("/ai/training/jobs/nonexistent")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
        
        app.dependency_overrides.clear()
    
    def test_list_jobs_no_filters(self, client, sample_job_response):
        """Test GET /ai/training/jobs without filters."""
        mock_orch = AsyncMock()
        mock_orch.list_jobs.return_value = ([sample_job_response], 1)
        
        app.dependency_overrides[TrainingOrchestrator] = lambda: mock_orch
        
        response = client.get("/ai/training/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == "job-123"
        
        app.dependency_overrides.clear()
    
    def test_list_jobs_with_filters(self, client):
        """Test listing jobs with filters."""
        mock_orch = AsyncMock()
        mock_orch.list_jobs.return_value = ([], 0)
        
        app.dependency_overrides[TrainingOrchestrator] = lambda: mock_orch
        
        response = client.get(
            "/ai/training/jobs",
            params={
                "tenant_id": "tenant-123",
                "status": "running",
                "model_type": "forecast",
            }
        )
        
        assert response.status_code == 200
        
        # Check orchestrator was called with filters
        call_args = mock_orch.list_jobs.call_args
        filters = call_args[0][0]
        assert filters.tenant_id == "tenant-123"
        assert filters.status == JobStatus.RUNNING
        assert filters.model_type == ModelType.FORECAST
        
        app.dependency_overrides.clear()
    
    def test_list_jobs_with_pagination(self, client):
        """Test listing jobs with pagination."""
        mock_orch = AsyncMock()
        mock_orch.list_jobs.return_value = ([], 100)
        
        app.dependency_overrides[TrainingOrchestrator] = lambda: mock_orch
        
        response = client.get(
            "/ai/training/jobs",
            params={
                "page": 3,
                "page_size": 20,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 3
        assert data["page_size"] == 20
        assert data["total"] == 100
        assert data["pages"] == 5  # 100 / 20
        
        app.dependency_overrides.clear()


class TestJobCancellation:
    """Tests for DELETE /ai/training/jobs/{job_id} endpoint."""
    
    def test_cancel_job_success(self, client):
        """Test successful job cancellation."""
        mock_orch = AsyncMock()
        mock_orch.cancel_job.return_value = True
        
        app.dependency_overrides[TrainingOrchestrator] = lambda: mock_orch
        
        response = client.delete("/ai/training/jobs/job-123")
        
        assert response.status_code == 200
        data = response.json()
        assert "cancelled" in data["message"].lower()
        
        app.dependency_overrides.clear()
    
    def test_cancel_job_not_found(self, client):
        """Test cancelling non-existent job."""
        mock_orch = AsyncMock()
        mock_orch.cancel_job.return_value = False
        
        app.dependency_overrides[TrainingOrchestrator] = lambda: mock_orch
        
        response = client.delete("/ai/training/jobs/nonexistent")
        
        assert response.status_code == 404
        
        app.dependency_overrides.clear()
    
    def test_cancel_job_error(self, client):
        """Test cancellation error handling."""
        mock_orch = AsyncMock()
        mock_orch.cancel_job.side_effect = Exception("Cannot cancel completed job")
        
        app.dependency_overrides[TrainingOrchestrator] = lambda: mock_orch
        
        response = client.delete("/ai/training/jobs/job-123")
        
        assert response.status_code == 500
        
        app.dependency_overrides.clear()


class TestJobRetry:
    """Tests for POST /ai/training/jobs/{job_id}/retry endpoint."""
    
    def test_retry_job_success(self, client, sample_job_response):
        """Test successful job retry."""
        new_job = sample_job_response.model_copy()
        new_job.id = "job-456"
        new_job.tags = ["retry_of:job-123"]
        
        mock_orch = AsyncMock()
        mock_orch.retry_job.return_value = new_job
        
        app.dependency_overrides[TrainingOrchestrator] = lambda: mock_orch
        
        response = client.post("/ai/training/jobs/job-123/retry")
        
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "job-456"
        assert "retry_of:job-123" in data["tags"]
        
        app.dependency_overrides.clear()
    
    def test_retry_job_not_found(self, client):
        """Test retrying non-existent job."""
        mock_orch = AsyncMock()
        mock_orch.retry_job.return_value = None
        
        app.dependency_overrides[TrainingOrchestrator] = lambda: mock_orch
        
        response = client.post("/ai/training/jobs/nonexistent/retry")
        
        assert response.status_code == 404
        
        app.dependency_overrides.clear()


class TestJobLogs:
    """Tests for GET /ai/training/jobs/{job_id}/logs endpoint."""
    
    def test_get_logs_success(self, client):
        """Test retrieving job logs."""
        # Mock database
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            MagicMock(
                id="log-1",
                job_id="job-123",
                timestamp=datetime(2025, 3, 25, 10, 5, 0),
                level="INFO",
                message="Training started",
            ),
            MagicMock(
                id="log-2",
                job_id="job-123",
                timestamp=datetime(2025, 3, 25, 10, 10, 0),
                level="INFO",
                message="Epoch 1 complete",
            ),
        ]
        mock_db.execute.return_value = mock_result
        
        from app.database import get_db
        
        async def mock_get_db():
            yield mock_db
        
        app.dependency_overrides[get_db] = mock_get_db
        
        response = client.get("/ai/training/jobs/job-123/logs")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["message"] == "Training started"
        
        app.dependency_overrides.clear()
    
    def test_get_logs_with_level_filter(self, client):
        """Test filtering logs by level."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result
        
        from app.database import get_db
        
        async def mock_get_db():
            yield mock_db
        
        app.dependency_overrides[get_db] = mock_get_db
        
        response = client.get(
            "/ai/training/jobs/job-123/logs",
            params={"level": "ERROR"}
        )
        
        assert response.status_code == 200
        
        # Check query includes level filter
        call_args = mock_db.execute.call_args
        query_str = str(call_args[0][0])
        assert "level" in query_str.lower()
        
        app.dependency_overrides.clear()


class TestJobStats:
    """Tests for GET /ai/training/stats endpoint."""
    
    def test_get_stats_success(self, client):
        """Test retrieving training statistics."""
        mock_db = AsyncMock()
        
        # Mock total jobs count
        total_result = MagicMock()
        total_result.scalar.return_value = 150
        
        # Mock status counts
        status_result = MagicMock()
        status_result.fetchall.return_value = [
            MagicMock(status="queued", count=10),
            MagicMock(status="running", count=5),
            MagicMock(status="completed", count=120),
            MagicMock(status="failed", count=10),
            MagicMock(status="cancelled", count=5),
        ]
        
        # Mock avg duration
        duration_result = MagicMock()
        duration_result.scalar.return_value = timedelta(minutes=15)
        
        # Set up side effects
        mock_db.execute.side_effect = [
            total_result,
            status_result,
            duration_result,
        ]
        
        from app.database import get_db
        
        async def mock_get_db():
            yield mock_db
        
        app.dependency_overrides[get_db] = mock_get_db
        
        response = client.get("/ai/training/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_jobs"] == 150
        assert data["by_status"]["completed"] == 120
        assert data["by_status"]["running"] == 5
        assert data["avg_duration_minutes"] == 15.0
        
        app.dependency_overrides.clear()
    
    def test_get_stats_with_tenant_filter(self, client):
        """Test stats filtered by tenant."""
        mock_db = AsyncMock()
        
        total_result = MagicMock()
        total_result.scalar.return_value = 50
        
        status_result = MagicMock()
        status_result.fetchall.return_value = [
            MagicMock(status="completed", count=45),
            MagicMock(status="failed", count=5),
        ]
        
        duration_result = MagicMock()
        duration_result.scalar.return_value = timedelta(minutes=12)
        
        mock_db.execute.side_effect = [
            total_result,
            status_result,
            duration_result,
        ]
        
        from app.database import get_db
        
        async def mock_get_db():
            yield mock_db
        
        app.dependency_overrides[get_db] = mock_get_db
        
        response = client.get(
            "/ai/training/stats",
            params={"tenant_id": "tenant-123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_jobs"] == 50
        
        # Check queries include tenant filter
        for call in mock_db.execute.call_args_list:
            query_str = str(call[0][0])
            assert "tenant_id" in query_str.lower()
        
        app.dependency_overrides.clear()


class TestErrorHandling:
    """Tests for API error handling."""
    
    def test_internal_error_handling(self, client):
        """Test 500 error handling."""
        mock_orch = AsyncMock()
        mock_orch.list_jobs.side_effect = Exception("Database connection failed")
        
        app.dependency_overrides[TrainingOrchestrator] = lambda: mock_orch
        
        response = client.get("/ai/training/jobs")
        
        assert response.status_code == 500
        assert "error" in response.json()
        
        app.dependency_overrides.clear()
    
    def test_validation_error_handling(self, client):
        """Test 422 validation error."""
        invalid_request = {
            "tenant_id": "tenant-123",
            "model_type": "invalid_type",  # Invalid enum
            "model_name": "test",
            "config": {
                "start_date": "2025-01-01T00:00:00",
                "end_date": "2025-10-01T00:00:00",
                "feature_set": "forecast_basic",
                "target_variable": "load_kw",
            }
        }
        
        response = client.post("/ai/training/jobs/start", json=invalid_request)
        
        assert response.status_code == 422
