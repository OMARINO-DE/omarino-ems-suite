"""
Configuration management for Asset Service using Pydantic Settings.
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings."""
    
    # Service information
    service_name: str = "asset-service"
    version: str = "1.0.0"
    environment: str = "development"
    
    # API settings
    api_prefix: str = "/api/assets"
    
    # Database settings
    database_url: str = "postgresql://omarino:omarino_dev_pass@localhost:5432/omarino"
    db_min_pool_size: int = 2
    db_max_pool_size: int = 10
    db_command_timeout: int = 60
    
    # CORS settings
    cors_allowed_origins: List[str] = ["*"]
    
    # Logging
    log_level: str = "INFO"
    
    # Metrics
    enable_metrics: bool = True
    metrics_port: int = 9003
    
    # Pagination
    default_page_size: int = 50
    max_page_size: int = 100
    
    class Config:
        env_file = ".env"
        case_sensitive = False


_settings = None


def get_settings() -> Settings:
    """Get application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
