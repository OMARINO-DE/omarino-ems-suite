"""
Optimize service configuration.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    # Service metadata
    service_name: str = "optimize-service"
    version: str = "0.1.0"
    environment: str = "development"
    
    # API configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8002
    api_prefix: str = "/api"
    
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/omarino_ems"
    
    # Redis (for Celery task queue)
    redis_url: str = "redis://localhost:6379/0"
    
    # Solver configuration
    default_solver: str = "highs"
    available_solvers: List[str] = ["highs", "cbc", "glpk"]
    solver_timeout_seconds: int = 300
    
    # Optimization limits
    max_time_horizon_hours: int = 168  # 1 week
    max_assets: int = 50
    
    # Task management
    max_concurrent_optimizations: int = 5
    job_retention_hours: int = 168  # Keep results for 1 week
    
    # Performance
    max_workers: int = 4
    request_timeout_seconds: int = 600
    
    # Logging
    log_level: str = "INFO"
    
    # CORS
    cors_allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5000"
    ]
    
    # Observability
    enable_metrics: bool = True
    metrics_port: int = 9090
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
