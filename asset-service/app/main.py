"""
FastAPI application for Asset Management Service.
"""
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.config import get_settings
from app.database import AssetDatabase
from app.routers import health, assets, batteries, generators, status as status_router

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    settings = get_settings()
    
    logger.info("asset_service_starting",
                version=settings.version,
                environment=settings.environment)
    
    # Initialize database connection
    db = AssetDatabase()
    try:
        await db.connect()
        app.state.asset_db = db
        logger.info("asset_database_connected")
    except Exception as e:
        logger.error("asset_database_connection_failed", error=str(e))
        app.state.asset_db = None
    
    yield
    
    # Cleanup database connection
    if hasattr(app.state, "asset_db") and app.state.asset_db:
        await app.state.asset_db.close()
        logger.info("asset_database_closed")
    
    logger.info("asset_service_shutting_down")


# Create FastAPI app
settings = get_settings()

app = FastAPI(
    title="OMARINO EMS - Asset Management Service",
    description="Comprehensive asset management for energy assets",
    version=settings.version,
    lifespan=lifespan,
    docs_url=f"{settings.api_prefix}/docs",
    openapi_url=f"{settings.api_prefix}/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error("unhandled_exception",
                 path=request.url.path,
                 method=request.method,
                 error=str(exc),
                 exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests."""
    logger.info("http_request_started",
                method=request.method,
                path=request.url.path,
                client=request.client.host if request.client else None)
    
    response = await call_next(request)
    
    logger.info("http_request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code)
    
    return response

# Include routers
app.include_router(health.router, prefix=settings.api_prefix, tags=["Health"])
app.include_router(assets.router, prefix=settings.api_prefix, tags=["Assets"])
app.include_router(batteries.router, prefix=settings.api_prefix, tags=["Batteries"])
app.include_router(generators.router, prefix=settings.api_prefix, tags=["Generators"])
app.include_router(status_router.router, prefix=settings.api_prefix, tags=["Status"])

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "version": settings.version,
        "docs": f"{settings.api_prefix}/docs"
    }
