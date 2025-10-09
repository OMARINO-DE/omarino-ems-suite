"""
Configuration settings for AI Hub Service
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Service Configuration
    SERVICE_NAME: str = "ai-hub"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "info"
    
    # API Configuration
    API_PREFIX: str = "/ai"
    CORS_ORIGINS: List[str] = ["*"]
    
    # Database Configuration
    DATABASE_URL: str = "postgresql://omarino:omarino_dev_pass@postgres:5432/omarino"
    
    # Redis Configuration
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "omarino_redis_pass"
    REDIS_DB: int = 0
    
    # Model Storage
    MODEL_STORAGE_PATH: str = "./models"
    MODEL_CACHE_SIZE: int = 5
    MODEL_CACHE_TTL: int = 3600  # 1 hour
    
    # MinIO/S3 Storage
    MINIO_ENDPOINT_URL: str = ""  # e.g., http://minio:9000
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MODEL_STORAGE_BUCKET: str = "ml-models"
    AWS_REGION: str = "us-east-1"
    
    # Feature Store
    FEATURE_CACHE_TTL: int = 300  # 5 minutes
    EXPORT_STORAGE_PATH: str = "./exports"
    
    # Authentication (Keycloak/OIDC)
    KEYCLOAK_URL: str = "http://keycloak:8080"
    KEYCLOAK_REALM: str = "omarino"
    KEYCLOAK_CLIENT_ID: str = "ai-hub"
    KEYCLOAK_CLIENT_SECRET: str = ""
    JWT_ALGORITHM: str = "RS256"
    JWT_AUDIENCE: str = "account"
    
    # OpenTelemetry
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    OTEL_SERVICE_NAME: str = "ai-hub"
    
    # ML Configuration
    DEFAULT_FORECAST_HORIZON: int = 24  # hours
    DEFAULT_FORECAST_INTERVAL: int = 60  # minutes
    ANOMALY_THRESHOLD: float = 3.0  # standard deviations
    SHAP_MAX_SAMPLES: int = 100
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
