"""
Pydantic models for training pipeline.

Defines request/response models for training jobs, experiments, and related data.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class JobStatus(str, Enum):
    """Training job status."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExperimentStatus(str, Enum):
    """Experiment status."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ModelType(str, Enum):
    """Type of model to train."""
    FORECAST = "forecast"
    ANOMALY = "anomaly"


class JobPriority(int, Enum):
    """Job priority levels."""
    LOW = -1
    NORMAL = 0
    HIGH = 1
    URGENT = 2


class HyperparamType(str, Enum):
    """Hyperparameter types for search space."""
    INT = "int"
    FLOAT = "float"
    CATEGORICAL = "categorical"
    LOGUNIFORM = "loguniform"


# =====================================================
# Training Configuration Models
# =====================================================

class HyperparameterSpec(BaseModel):
    """Specification for a hyperparameter search space."""
    type: HyperparamType
    low: Optional[float] = None  # For int, float, loguniform
    high: Optional[float] = None  # For int, float, loguniform
    choices: Optional[List[Any]] = None  # For categorical
    log: bool = False  # For loguniform
    step: Optional[float] = None  # For int, float

    @field_validator("low", "high")
    @classmethod
    def validate_range(cls, v, info):
        """Validate range parameters."""
        if v is not None and info.data.get("type") in [
            HyperparamType.INT,
            HyperparamType.FLOAT,
            HyperparamType.LOGUNIFORM,
        ]:
            if info.data.get("type") == HyperparamType.INT and not isinstance(v, int):
                raise ValueError("low/high must be integers for int type")
        return v


class TrainingConfig(BaseModel):
    """Configuration for a training job."""
    # Data configuration
    start_date: datetime
    end_date: datetime
    feature_set: str = Field(
        ..., description="Feature set to use (e.g., 'forecast_basic', 'forecast_advanced')"
    )
    target_variable: str = Field(default="load_kw", description="Target variable to predict")
    
    # Model configuration
    horizon: int = Field(default=24, ge=1, description="Forecast horizon (hours)")
    validation_split: float = Field(default=0.2, ge=0.0, le=0.5)
    test_split: float = Field(default=0.1, ge=0.0, le=0.5)
    
    # Hyperparameter optimization
    enable_hpo: bool = Field(default=False, description="Enable hyperparameter optimization")
    n_trials: int = Field(default=50, ge=1, le=500, description="Number of HPO trials")
    hpo_timeout_seconds: Optional[int] = Field(
        default=None, ge=60, description="HPO timeout in seconds"
    )
    
    # Hyperparameters (either fixed values or search space specs)
    hyperparams: Dict[str, Any] = Field(
        default_factory=dict,
        description="Fixed hyperparameters or search space specifications"
    )
    
    # Training options
    early_stopping: bool = Field(default=True, description="Enable early stopping")
    early_stopping_rounds: int = Field(default=10, ge=1)
    random_seed: int = Field(default=42, ge=0)
    
    # Resource configuration
    n_workers: int = Field(default=1, ge=1, le=16, description="Number of parallel workers")
    memory_limit_gb: Optional[float] = Field(default=None, ge=1.0, le=128.0)
    
    # Additional options
    save_artifacts: bool = Field(default=True, description="Save training artifacts")
    register_model: bool = Field(default=True, description="Register model after training")
    auto_promote: bool = Field(
        default=False, description="Automatically promote model if better than current"
    )


# =====================================================
# Training Job Models
# =====================================================

class TrainingJobCreate(BaseModel):
    """Request to create a training job."""
    tenant_id: str
    model_type: ModelType
    model_name: str
    config: TrainingConfig
    schedule: Optional[str] = Field(
        default=None, description="Cron expression for recurring jobs"
    )
    priority: JobPriority = JobPriority.NORMAL
    tags: Dict[str, str] = Field(default_factory=dict)


class TrainingJobMetrics(BaseModel):
    """Training metrics tracked during job execution."""
    current_epoch: Optional[int] = None
    total_epochs: Optional[int] = None
    current_trial: Optional[int] = None
    total_trials: Optional[int] = None
    train_loss: Optional[float] = None
    val_loss: Optional[float] = None
    best_mae: Optional[float] = None
    best_rmse: Optional[float] = None
    best_mape: Optional[float] = None
    training_time_seconds: Optional[float] = None


class TrainingJobResponse(BaseModel):
    """Response model for a training job."""
    job_id: UUID
    tenant_id: str
    model_type: ModelType
    model_name: str
    feature_set: str
    status: JobStatus
    priority: int
    progress: float = Field(ge=0.0, le=1.0)
    metrics: Optional[TrainingJobMetrics] = None
    error_message: Optional[str] = None
    model_id: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime
    created_by: Optional[str] = None
    tags: Dict[str, str] = Field(default_factory=dict)
    
    # Computed fields
    duration_seconds: Optional[float] = None
    estimated_completion: Optional[datetime] = None

    class Config:
        from_attributes = True


class TrainingJobListResponse(BaseModel):
    """Response for listing training jobs."""
    jobs: List[TrainingJobResponse]
    total: int
    page: int = 1
    page_size: int = 20


# =====================================================
# Experiment Models
# =====================================================

class ExperimentCreate(BaseModel):
    """Request to create an experiment."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    model_type: ModelType
    tenant_id: str
    job_id: Optional[UUID] = None
    tags: Dict[str, str] = Field(default_factory=dict)


class ExperimentMetric(BaseModel):
    """A single metric logged during an experiment."""
    metric_name: str
    metric_value: float
    step: int = 0
    timestamp: datetime


class ExperimentParameter(BaseModel):
    """A parameter used in an experiment."""
    param_name: str
    param_value: str
    param_type: str = "string"


class ExperimentResponse(BaseModel):
    """Response model for an experiment."""
    experiment_id: UUID
    name: str
    description: Optional[str] = None
    model_type: ModelType
    tenant_id: str
    status: ExperimentStatus
    job_id: Optional[UUID] = None
    model_id: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    updated_at: datetime
    tags: Dict[str, str] = Field(default_factory=dict)
    
    # Related data
    metrics: Optional[Dict[str, float]] = None  # Latest metrics
    params: Optional[Dict[str, str]] = None  # All parameters

    class Config:
        from_attributes = True


class ExperimentListResponse(BaseModel):
    """Response for listing experiments."""
    experiments: List[ExperimentResponse]
    total: int
    page: int = 1
    page_size: int = 20


class ExperimentComparison(BaseModel):
    """Comparison of multiple experiments."""
    experiment_id: UUID
    name: str
    metrics: Dict[str, float]
    params: Dict[str, str]
    created_at: datetime
    duration_seconds: Optional[float] = None


class ExperimentComparisonResponse(BaseModel):
    """Response for experiment comparison."""
    experiments: List[ExperimentComparison]
    metric_names: List[str]  # All metric names across experiments
    param_names: List[str]  # All parameter names across experiments


# =====================================================
# Training Log Models
# =====================================================

class LogLevel(str, Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class TrainingLog(BaseModel):
    """A single training log entry."""
    log_id: UUID
    job_id: UUID
    timestamp: datetime
    level: LogLevel
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class TrainingLogsResponse(BaseModel):
    """Response for training logs."""
    job_id: UUID
    logs: List[TrainingLog]
    total_lines: int
    page: int = 1
    page_size: int = 100


# =====================================================
# Job Filters
# =====================================================

class JobFilters(BaseModel):
    """Filters for querying training jobs."""
    tenant_id: Optional[str] = None
    model_type: Optional[ModelType] = None
    model_name: Optional[str] = None
    status: Optional[JobStatus] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ExperimentFilters(BaseModel):
    """Filters for querying experiments."""
    tenant_id: Optional[str] = None
    model_type: Optional[ModelType] = None
    status: Optional[ExperimentStatus] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# =====================================================
# Response Models for Job Operations
# =====================================================

class JobCreatedResponse(BaseModel):
    """Response when a job is created."""
    job_id: UUID
    status: JobStatus
    created_at: datetime
    estimated_duration_seconds: Optional[int] = None
    message: str = "Training job queued successfully"


class JobCancelledResponse(BaseModel):
    """Response when a job is cancelled."""
    job_id: UUID
    status: JobStatus
    message: str = "Training job cancelled successfully"


class JobStatusResponse(BaseModel):
    """Detailed status of a training job."""
    job_id: UUID
    status: JobStatus
    progress: float
    created_at: datetime
    started_at: Optional[datetime] = None
    updated_at: datetime
    estimated_completion: Optional[datetime] = None
    config: Dict[str, Any]
    metrics: Optional[TrainingJobMetrics] = None
    logs_url: str
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate duration if job has started."""
        if self.started_at:
            end_time = self.updated_at
            return (end_time - self.started_at).total_seconds()
        return None
