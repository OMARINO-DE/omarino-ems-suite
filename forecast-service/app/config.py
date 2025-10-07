"""
Forecast service configuration.
"""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    # Service metadata
    service_name: str = "forecast-service"
    version: str = "0.1.0"
    environment: str = "development"
    
    # API configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8001
    api_prefix: str = "/api"
    
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/omarino_ems"
    
    # Time series service
    timeseries_service_url: str = "http://localhost:5001"
    
    # Model configuration
    models_dir: str = "./models"
    max_horizon_minutes: int = 10080  # 1 week in 15-min intervals = 672, but allowing up to 1 week in minutes
    default_quantiles: list[float] = [0.1, 0.5, 0.9]
    
    # Performance
    max_workers: int = 4
    request_timeout_seconds: int = 300
    
    # Logging
    log_level: str = "INFO"
    
    # CORS
    cors_allowed_origins: list[str] = [
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
