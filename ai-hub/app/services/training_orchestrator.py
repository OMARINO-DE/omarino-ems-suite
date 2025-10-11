"""
Training Orchestrator Service.

Manages the lifecycle of training jobs including scheduling, queueing,
execution, and monitoring.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.training import (
    JobStatus,
    JobFilters,
    JobPriority,
    ModelType,
    TrainingConfig,
    TrainingJobCreate,
    TrainingJobResponse,
    TrainingJobMetrics,
    TrainingJobListResponse,
)

logger = logging.getLogger(__name__)


class TrainingOrchestrator:
    """
    Orchestrates training jobs lifecycle.
    
    Responsibilities:
    - Create and schedule training jobs
    - Manage job queue (FIFO with priority)
    - Monitor job execution
    - Handle failures and retries
    - Store job history
    """
    
    def __init__(
        self,
        db_session: AsyncSession,
        max_concurrent_jobs: int = 3,
        default_timeout_seconds: int = 3600,
    ):
        """
        Initialize the training orchestrator.
        
        Args:
            db_session: Database session
            max_concurrent_jobs: Maximum number of concurrent training jobs
            default_timeout_seconds: Default timeout for training jobs
        """
        self.db = db_session
        self.max_concurrent_jobs = max_concurrent_jobs
        self.default_timeout_seconds = default_timeout_seconds
        self._running_jobs: Dict[UUID, asyncio.Task] = {}
        
    async def create_job(
        self,
        request: TrainingJobCreate,
        created_by: Optional[str] = None,
    ) -> TrainingJobResponse:
        """
        Create a new training job.
        
        Args:
            request: Job creation request
            created_by: User who created the job
            
        Returns:
            Created training job
        """
        logger.info(
            f"Creating training job for {request.model_type}:{request.model_name} "
            f"(tenant: {request.tenant_id})"
        )
        
        # Create job record
        job_id = uuid4()
        now = datetime.utcnow()
        
        job_data = {
            "job_id": job_id,
            "tenant_id": request.tenant_id,
            "model_type": request.model_type.value,
            "model_name": request.model_name,
            "feature_set": request.config.feature_set,
            "status": JobStatus.QUEUED.value,
            "priority": request.priority.value,
            "config": request.config.model_dump(),
            "schedule": request.schedule,
            "progress": 0.0,
            "created_at": now,
            "updated_at": now,
            "created_by": created_by,
            "tags": request.tags,
        }
        
        # Insert into database
        from app.database import training_jobs_table
        
        insert_stmt = training_jobs_table.insert().values(**job_data)
        await self.db.execute(insert_stmt)
        await self.db.commit()
        
        logger.info(f"Training job {job_id} created and queued")
        
        # Estimate duration based on config
        estimated_duration = self._estimate_duration(request.config)
        
        return TrainingJobResponse(
            job_id=job_id,
            tenant_id=request.tenant_id,
            model_type=request.model_type,
            model_name=request.model_name,
            feature_set=request.config.feature_set,
            status=JobStatus.QUEUED,
            priority=request.priority.value,
            progress=0.0,
            created_at=now,
            updated_at=now,
            created_by=created_by,
            tags=request.tags,
            duration_seconds=None,
            estimated_completion=now + timedelta(seconds=estimated_duration),
        )
    
    async def get_job(self, job_id: UUID) -> Optional[TrainingJobResponse]:
        """
        Get a training job by ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            Training job or None if not found
        """
        from app.database import training_jobs_table
        
        stmt = select(training_jobs_table).where(
            training_jobs_table.c.job_id == job_id
        )
        result = await self.db.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return self._row_to_response(row)
    
    async def list_jobs(
        self, filters: JobFilters
    ) -> TrainingJobListResponse:
        """
        List training jobs with filters.
        
        Args:
            filters: Query filters
            
        Returns:
            List of training jobs
        """
        from app.database import training_jobs_table
        
        # Build query
        stmt = select(training_jobs_table)
        
        # Apply filters
        if filters.tenant_id:
            stmt = stmt.where(training_jobs_table.c.tenant_id == filters.tenant_id)
        if filters.model_type:
            stmt = stmt.where(training_jobs_table.c.model_type == filters.model_type.value)
        if filters.model_name:
            stmt = stmt.where(training_jobs_table.c.model_name == filters.model_name)
        if filters.status:
            stmt = stmt.where(training_jobs_table.c.status == filters.status.value)
        if filters.created_after:
            stmt = stmt.where(training_jobs_table.c.created_at >= filters.created_after)
        if filters.created_before:
            stmt = stmt.where(training_jobs_table.c.created_at <= filters.created_before)
        
        # Count total
        count_stmt = select(func.count()).select_from(stmt.alias())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar()
        
        # Apply pagination
        stmt = stmt.order_by(training_jobs_table.c.created_at.desc())
        stmt = stmt.limit(filters.page_size)
        stmt = stmt.offset((filters.page - 1) * filters.page_size)
        
        # Execute query
        result = await self.db.execute(stmt)
        rows = result.fetchall()
        
        jobs = [self._row_to_response(row) for row in rows]
        
        return TrainingJobListResponse(
            jobs=jobs,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
        )
    
    async def cancel_job(self, job_id: UUID) -> bool:
        """
        Cancel a training job.
        
        Args:
            job_id: Job ID
            
        Returns:
            True if cancelled, False if not found or already completed
        """
        logger.info(f"Cancelling training job {job_id}")
        
        from app.database import training_jobs_table
        
        # Check if job exists and can be cancelled
        stmt = select(training_jobs_table).where(
            training_jobs_table.c.job_id == job_id
        )
        result = await self.db.execute(stmt)
        row = result.fetchone()
        
        if not row:
            logger.warning(f"Job {job_id} not found")
            return False
        
        current_status = row.status
        if current_status in [JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value]:
            logger.warning(f"Job {job_id} already in terminal state: {current_status}")
            return False
        
        # Cancel running task if exists
        if job_id in self._running_jobs:
            task = self._running_jobs[job_id]
            task.cancel()
            del self._running_jobs[job_id]
        
        # Update status in database
        update_stmt = (
            update(training_jobs_table)
            .where(training_jobs_table.c.job_id == job_id)
            .values(
                status=JobStatus.CANCELLED.value,
                updated_at=datetime.utcnow(),
            )
        )
        await self.db.execute(update_stmt)
        await self.db.commit()
        
        logger.info(f"Job {job_id} cancelled successfully")
        return True
    
    async def retry_job(self, job_id: UUID) -> Optional[TrainingJobResponse]:
        """
        Retry a failed job.
        
        Args:
            job_id: Job ID
            
        Returns:
            New training job or None if original job not found
        """
        logger.info(f"Retrying training job {job_id}")
        
        # Get original job
        original_job = await self.get_job(job_id)
        if not original_job:
            return None
        
        # Create new job with same config
        from app.database import training_jobs_table
        
        stmt = select(training_jobs_table).where(
            training_jobs_table.c.job_id == job_id
        )
        result = await self.db.execute(stmt)
        row = result.fetchone()
        
        config = TrainingConfig(**row.config)
        
        retry_request = TrainingJobCreate(
            tenant_id=row.tenant_id,
            model_type=ModelType(row.model_type),
            model_name=row.model_name,
            config=config,
            schedule=row.schedule,
            priority=JobPriority(row.priority),
            tags={**row.tags, "retry_of": str(job_id)},
        )
        
        new_job = await self.create_job(retry_request, created_by=row.created_by)
        logger.info(f"Created retry job {new_job.job_id} for original job {job_id}")
        
        return new_job
    
    async def update_progress(
        self,
        job_id: UUID,
        progress: float,
        metrics: Optional[TrainingJobMetrics] = None,
    ) -> None:
        """
        Update job progress and metrics.
        
        Args:
            job_id: Job ID
            progress: Progress value (0.0 to 1.0)
            metrics: Optional training metrics
        """
        from app.database import training_jobs_table
        
        update_data = {
            "progress": progress,
            "updated_at": datetime.utcnow(),
        }
        
        if metrics:
            update_data["metrics"] = metrics.model_dump()
        
        stmt = (
            update(training_jobs_table)
            .where(training_jobs_table.c.job_id == job_id)
            .values(**update_data)
        )
        await self.db.execute(stmt)
        await self.db.commit()
    
    async def mark_running(self, job_id: UUID) -> None:
        """Mark job as running."""
        from app.database import training_jobs_table
        
        stmt = (
            update(training_jobs_table)
            .where(training_jobs_table.c.job_id == job_id)
            .values(
                status=JobStatus.RUNNING.value,
                started_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()
        
        logger.info(f"Job {job_id} marked as running")
    
    async def mark_completed(
        self,
        job_id: UUID,
        model_id: str,
        final_metrics: TrainingJobMetrics,
    ) -> None:
        """Mark job as completed."""
        from app.database import training_jobs_table
        
        stmt = (
            update(training_jobs_table)
            .where(training_jobs_table.c.job_id == job_id)
            .values(
                status=JobStatus.COMPLETED.value,
                progress=1.0,
                model_id=model_id,
                metrics=final_metrics.model_dump(),
                completed_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()
        
        logger.info(f"Job {job_id} completed successfully with model {model_id}")
    
    async def mark_failed(
        self,
        job_id: UUID,
        error_message: str,
    ) -> None:
        """Mark job as failed."""
        from app.database import training_jobs_table
        
        stmt = (
            update(training_jobs_table)
            .where(training_jobs_table.c.job_id == job_id)
            .values(
                status=JobStatus.FAILED.value,
                error_message=error_message,
                completed_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()
        
        logger.error(f"Job {job_id} failed: {error_message}")
    
    async def get_queued_jobs(self, limit: int = 10) -> List[TrainingJobResponse]:
        """
        Get queued jobs ordered by priority and creation time.
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of queued jobs
        """
        from app.database import training_jobs_table
        
        stmt = (
            select(training_jobs_table)
            .where(training_jobs_table.c.status == JobStatus.QUEUED.value)
            .order_by(
                training_jobs_table.c.priority.desc(),
                training_jobs_table.c.created_at.asc(),
            )
            .limit(limit)
        )
        
        result = await self.db.execute(stmt)
        rows = result.fetchall()
        
        return [self._row_to_response(row) for row in rows]
    
    async def get_active_jobs_count(self) -> int:
        """Get count of active (running) jobs."""
        from app.database import training_jobs_table
        
        stmt = select(func.count()).where(
            training_jobs_table.c.status == JobStatus.RUNNING.value
        )
        result = await self.db.execute(stmt)
        return result.scalar()
    
    def _row_to_response(self, row) -> TrainingJobResponse:
        """Convert database row to response model."""
        metrics = None
        if row.metrics:
            metrics = TrainingJobMetrics(**row.metrics)
        
        duration_seconds = None
        if row.started_at:
            end_time = row.completed_at or datetime.utcnow()
            duration_seconds = (end_time - row.started_at).total_seconds()
        
        return TrainingJobResponse(
            job_id=row.job_id,
            tenant_id=row.tenant_id,
            model_type=ModelType(row.model_type),
            model_name=row.model_name,
            feature_set=row.feature_set,
            status=JobStatus(row.status),
            priority=row.priority,
            progress=row.progress,
            metrics=metrics,
            error_message=row.error_message,
            model_id=row.model_id,
            created_at=row.created_at,
            started_at=row.started_at,
            completed_at=row.completed_at,
            updated_at=row.updated_at,
            created_by=row.created_by,
            tags=row.tags or {},
            duration_seconds=duration_seconds,
        )
    
    def _estimate_duration(self, config: TrainingConfig) -> int:
        """
        Estimate training duration in seconds.
        
        Args:
            config: Training configuration
            
        Returns:
            Estimated duration in seconds
        """
        # Base time: 3 minutes per worker
        base_time = 180 / config.n_workers
        
        # Add time for HPO
        if config.enable_hpo:
            # ~30 seconds per trial, parallelized
            hpo_time = (config.n_trials * 30) / config.n_workers
            base_time += hpo_time
        
        # Add time based on data size (rough estimate)
        data_days = (config.end_date - config.start_date).days
        if data_days > 365:
            base_time *= 2  # Double time for >1 year of data
        
        return int(base_time)
