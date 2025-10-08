"""
Health check router for Asset Management Service.
"""
from fastapi import APIRouter, Request
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.get("/health")
async def health_check(request: Request):
    """
    Health check endpoint.
    
    Returns service health status including database connectivity.
    """
    health_status = {
        "status": "healthy",
        "version": "1.0.0",
        "database": "unknown"
    }
    
    # Check database connectivity
    if hasattr(request.app.state, "asset_db") and request.app.state.asset_db:
        try:
            # Simple database ping
            async with request.app.state.asset_db.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            health_status["database"] = "connected"
        except Exception as e:
            logger.error("health_check_database_failed", error=str(e))
            health_status["database"] = "disconnected"
            health_status["status"] = "degraded"
    
    return health_status
