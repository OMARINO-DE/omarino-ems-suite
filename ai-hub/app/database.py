"""
Database configuration and table definitions for AI Hub.

This module defines SQLAlchemy tables for the training pipeline.
"""

from sqlalchemy import (
    Table,
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    MetaData,
    ForeignKey,
    CheckConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import uuid

from app.config import settings

# Metadata object for all tables
metadata = MetaData()

# =====================================================
# Training Jobs Table
# =====================================================

training_jobs_table = Table(
    "ai_training_jobs",
    metadata,
    Column("job_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("tenant_id", String, nullable=False, index=True),
    Column("model_type", String, nullable=False, index=True),
    Column("model_name", String, nullable=False),
    Column("feature_set", String, nullable=False),
    Column(
        "status",
        String,
        nullable=False,
        index=True,
    ),
    Column("priority", Integer, default=0),
    Column("config", JSONB, nullable=False),
    Column("schedule", String, nullable=True),
    Column("progress", Float, default=0.0),
    Column("metrics", JSONB, nullable=True),
    Column("error_message", Text, nullable=True),
    Column("model_id", String, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=True),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("created_by", String, nullable=True),
    Column("tags", JSONB, default={}),
)

# =====================================================
# Experiments Table
# =====================================================

experiments_table = Table(
    "ai_experiments",
    metadata,
    Column("experiment_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("name", String, nullable=False),
    Column("description", Text, nullable=True),
    Column("model_type", String, nullable=False, index=True),
    Column("tenant_id", String, nullable=False, index=True),
    Column("status", String, nullable=False, index=True),
    Column(
        "job_id",
        UUID(as_uuid=True),
        ForeignKey("ai_training_jobs.job_id", ondelete="SET NULL"),
        nullable=True,
    ),
    Column("model_id", String, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("tags", JSONB, default={}),
)

# =====================================================
# Experiment Metrics Table
# =====================================================

experiment_metrics_table = Table(
    "ai_experiment_metrics",
    metadata,
    Column("metric_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column(
        "experiment_id",
        UUID(as_uuid=True),
        ForeignKey("ai_experiments.experiment_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("metric_name", String, nullable=False),
    Column("metric_value", Float, nullable=False),
    Column("step", Integer, default=0),
    Column("timestamp", DateTime(timezone=True), nullable=False),
)

# =====================================================
# Experiment Parameters Table
# =====================================================

experiment_params_table = Table(
    "ai_experiment_params",
    metadata,
    Column("param_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column(
        "experiment_id",
        UUID(as_uuid=True),
        ForeignKey("ai_experiments.experiment_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("param_name", String, nullable=False),
    Column("param_value", String, nullable=False),
    Column("param_type", String, default="string"),
)

# =====================================================
# Training Logs Table
# =====================================================

training_logs_table = Table(
    "ai_training_logs",
    metadata,
    Column("log_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column(
        "job_id",
        UUID(as_uuid=True),
        ForeignKey("ai_training_jobs.job_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("timestamp", DateTime(timezone=True), nullable=False, index=True),
    Column("level", String, nullable=False),
    Column("message", Text, nullable=False),
    Column("metadata", JSONB, default={}),
)

# =====================================================
# Database Engine and Session
# =====================================================

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.ENVIRONMENT == "development",
    pool_size=10,
    max_overflow=20,
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """
    Dependency for getting database session.
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)


async def close_db():
    """Close database connections."""
    await engine.dispose()
