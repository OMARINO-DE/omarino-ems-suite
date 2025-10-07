"""
Health check router.
"""
from datetime import datetime

from fastapi import APIRouter

from app.config import get_settings
from app.models import HealthResponse
from app.services.solver_manager import SolverManager

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    solver_manager = SolverManager()
    
    return HealthResponse(
        status="healthy",
        version=settings.version,
        timestamp=datetime.utcnow(),
        solvers_available=solver_manager.get_available_solvers()
    )


@router.get("/health/ready", response_model=HealthResponse)
async def readiness_check():
    """Readiness check endpoint."""
    settings = get_settings()
    solver_manager = SolverManager()
    
    # Check if at least one solver is available
    available_solvers = solver_manager.get_available_solvers()
    
    if not available_solvers:
        return HealthResponse(
            status="not_ready",
            version=settings.version,
            timestamp=datetime.utcnow(),
            solvers_available=[]
        )
    
    return HealthResponse(
        status="ready",
        version=settings.version,
        timestamp=datetime.utcnow(),
        solvers_available=available_solvers
    )


@router.get("/health/live", response_model=HealthResponse)
async def liveness_check():
    """Liveness check endpoint."""
    settings = get_settings()
    return HealthResponse(
        status="alive",
        version=settings.version,
        timestamp=datetime.utcnow()
    )
