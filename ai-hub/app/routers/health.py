"""
Health check router
"""

from fastapi import APIRouter, Response
from pydantic import BaseModel
import structlog
from datetime import datetime

from app.config import settings

logger = structlog.get_logger()
router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    service: str
    version: str
    timestamp: datetime
    environment: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns service health status and metadata.
    """
    return HealthResponse(
        status="healthy",
        service=settings.SERVICE_NAME,
        version="0.1.0",
        timestamp=datetime.utcnow(),
        environment=settings.ENVIRONMENT
    )


@router.get("/api/health", response_model=HealthResponse)
async def api_health_check():
    """Alternative health check endpoint for API Gateway compatibility."""
    return await health_check()
