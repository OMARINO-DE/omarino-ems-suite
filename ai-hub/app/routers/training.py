"""
Training API Router.

Provides REST API endpoints for training job management.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.training import (
    TrainingJobCreate,
    TrainingJobResponse,
    TrainingJobListResponse,
    JobCreatedResponse,
    JobCancelledResponse,
    JobFilters,
    JobStatus,
    ModelType,
)
from app.services.training_orchestrator import TrainingOrchestrator
from app.services.training_pipeline import ModelTrainingPipeline
from app.services.feature_store import FeatureStore
from app.services.model_storage import ModelStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/training", tags=["training"])


def get_training_orchestrator(db: AsyncSession = Depends(get_db)) -> TrainingOrchestrator:
    """Dependency for getting TrainingOrchestrator instance."""
    return TrainingOrchestrator(db)


def get_training_pipeline() -> ModelTrainingPipeline:
    """Dependency for getting ModelTrainingPipeline instance."""
    # TODO: Properly inject dependencies
    feature_store = FeatureStore(None, None)
    model_storage = ModelStorage()
    return ModelTrainingPipeline(feature_store, model_storage)


@router.post("/jobs/start", response_model=JobCreatedResponse, status_code=201)
async def start_training_job(
    request: TrainingJobCreate,
    orchestrator: TrainingOrchestrator = Depends(get_training_orchestrator),
) -> JobCreatedResponse:
    """
    Start a new training job.
    
    Creates and queues a training job for execution. The job will be picked up
    by the training worker pool and executed asynchronously.
    
    Args:
        request: Training job creation request
        orchestrator: Training orchestrator instance
        
    Returns:
        Job creation response with job ID and status
        
    Example:
        ```bash
        curl -X POST http://ai-hub:8003/ai/training/jobs/start \\
          -H "Content-Type: application/json" \\
          -d '{
            "tenant_id": "tenant-123",
            "model_type": "forecast",
            "model_name": "load_forecast",
            "config": {
              "start_date": "2025-01-01T00:00:00Z",
              "end_date": "2025-10-01T00:00:00Z",
              "feature_set": "forecast_basic",
              "target_variable": "load_kw",
              "horizon": 24,
              "enable_hpo": false
            }
          }'
        ```
    """
    try:
        logger.info(f"Received training job request for {request.model_type}:{request.model_name}")
        
        # Create job
        job = await orchestrator.create_job(request)
        
        # TODO: Trigger async execution
        # For now, job is just queued
        
        return JobCreatedResponse(
            job_id=job.job_id,
            status=job.status,
            created_at=job.created_at,
            estimated_duration_seconds=int(job.estimated_completion.timestamp() - job.created_at.timestamp())
            if job.estimated_completion else None,
            message="Training job queued successfully",
        )
        
    except Exception as e:
        logger.error(f"Failed to create training job: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create training job: {str(e)}")


@router.get("/jobs/{job_id}", response_model=TrainingJobResponse)
async def get_training_job(
    job_id: UUID,
    orchestrator: TrainingOrchestrator = Depends(get_training_orchestrator),
) -> TrainingJobResponse:
    """
    Get training job details.
    
    Retrieves detailed information about a training job including status,
    progress, metrics, and logs.
    
    Args:
        job_id: Training job ID
        orchestrator: Training orchestrator instance
        
    Returns:
        Training job details
        
    Raises:
        404: Job not found
        
    Example:
        ```bash
        curl http://ai-hub:8003/ai/training/jobs/550e8400-e29b-41d4-a716-446655440000
        ```
    """
    job = await orchestrator.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Training job {job_id} not found")
    
    return job


@router.get("/jobs", response_model=TrainingJobListResponse)
async def list_training_jobs(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    model_type: Optional[ModelType] = Query(None, description="Filter by model type"),
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    status: Optional[JobStatus] = Query(None, description="Filter by job status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    orchestrator: TrainingOrchestrator = Depends(get_training_orchestrator),
) -> TrainingJobListResponse:
    """
    List training jobs with filters.
    
    Retrieves a paginated list of training jobs matching the specified filters.
    
    Args:
        tenant_id: Optional tenant ID filter
        model_type: Optional model type filter
        model_name: Optional model name filter
        status: Optional status filter
        page: Page number (1-indexed)
        page_size: Number of items per page
        orchestrator: Training orchestrator instance
        
    Returns:
        Paginated list of training jobs
        
    Example:
        ```bash
        curl "http://ai-hub:8003/ai/training/jobs?tenant_id=tenant-123&status=completed&page=1&page_size=20"
        ```
    """
    filters = JobFilters(
        tenant_id=tenant_id,
        model_type=model_type,
        model_name=model_name,
        status=status,
        page=page,
        page_size=page_size,
    )
    
    return await orchestrator.list_jobs(filters)


@router.delete("/jobs/{job_id}", response_model=JobCancelledResponse)
async def cancel_training_job(
    job_id: UUID,
    orchestrator: TrainingOrchestrator = Depends(get_training_orchestrator),
) -> JobCancelledResponse:
    """
    Cancel a training job.
    
    Cancels a queued or running training job. Completed or failed jobs
    cannot be cancelled.
    
    Args:
        job_id: Training job ID
        orchestrator: Training orchestrator instance
        
    Returns:
        Job cancellation response
        
    Raises:
        404: Job not found
        400: Job cannot be cancelled (already completed/failed)
        
    Example:
        ```bash
        curl -X DELETE http://ai-hub:8003/ai/training/jobs/550e8400-e29b-41d4-a716-446655440000
        ```
    """
    cancelled = await orchestrator.cancel_job(job_id)
    
    if not cancelled:
        # Check if job exists
        job = await orchestrator.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Training job {job_id} not found")
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Training job {job_id} cannot be cancelled (status: {job.status})"
            )
    
    return JobCancelledResponse(
        job_id=job_id,
        status=JobStatus.CANCELLED,
        message="Training job cancelled successfully",
    )


@router.post("/jobs/{job_id}/retry", response_model=JobCreatedResponse, status_code=201)
async def retry_training_job(
    job_id: UUID,
    orchestrator: TrainingOrchestrator = Depends(get_training_orchestrator),
) -> JobCreatedResponse:
    """
    Retry a failed training job.
    
    Creates a new training job with the same configuration as the original job.
    Useful for retrying jobs that failed due to transient errors.
    
    Args:
        job_id: Original job ID to retry
        orchestrator: Training orchestrator instance
        
    Returns:
        New job creation response
        
    Raises:
        404: Original job not found
        
    Example:
        ```bash
        curl -X POST http://ai-hub:8003/ai/training/jobs/550e8400-e29b-41d4-a716-446655440000/retry
        ```
    """
    new_job = await orchestrator.retry_job(job_id)
    
    if not new_job:
        raise HTTPException(status_code=404, detail=f"Training job {job_id} not found")
    
    return JobCreatedResponse(
        job_id=new_job.job_id,
        status=new_job.status,
        created_at=new_job.created_at,
        estimated_duration_seconds=int(new_job.estimated_completion.timestamp() - new_job.created_at.timestamp())
        if new_job.estimated_completion else None,
        message=f"Retry job created from original job {job_id}",
    )


@router.get("/jobs/{job_id}/logs")
async def get_training_logs(
    job_id: UUID,
    tail: int = Query(100, ge=1, le=1000, description="Number of log lines to return"),
    orchestrator: TrainingOrchestrator = Depends(get_training_orchestrator),
):
    """
    Get training job logs.
    
    Retrieves recent log entries for a training job. Useful for debugging
    and monitoring training progress.
    
    Args:
        job_id: Training job ID
        tail: Number of recent log lines to return (max 1000)
        orchestrator: Training orchestrator instance
        
    Returns:
        Training logs
        
    Raises:
        404: Job not found
        
    Example:
        ```bash
        curl "http://ai-hub:8003/ai/training/jobs/550e8400-e29b-41d4-a716-446655440000/logs?tail=50"
        ```
    """
    # Check if job exists
    job = await orchestrator.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Training job {job_id} not found")
    
    # TODO: Implement log retrieval from database
    return {
        "job_id": job_id,
        "logs": [
            {
                "timestamp": "2025-10-11T10:30:00Z",
                "level": "INFO",
                "message": "Training job started",
            },
            {
                "timestamp": "2025-10-11T10:30:05Z",
                "level": "INFO",
                "message": "Loading features from Feature Store...",
            },
        ],
        "total_lines": 2,
    }


@router.get("/stats")
async def get_training_stats(
    orchestrator: TrainingOrchestrator = Depends(get_training_orchestrator),
):
    """
    Get training statistics.
    
    Retrieves aggregate statistics about training jobs including counts by status,
    average duration, success rate, etc.
    
    Returns:
        Training statistics
        
    Example:
        ```bash
        curl http://ai-hub:8003/ai/training/stats
        ```
    """
    active_count = await orchestrator.get_active_jobs_count()
    queued_jobs = await orchestrator.get_queued_jobs(limit=100)
    
    return {
        "active_jobs": active_count,
        "queued_jobs": len(queued_jobs),
        "total_capacity": orchestrator.max_concurrent_jobs,
        "utilization": active_count / orchestrator.max_concurrent_jobs if orchestrator.max_concurrent_jobs > 0 else 0,
    }
