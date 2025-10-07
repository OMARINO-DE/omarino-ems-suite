"""
FastAPI application for optimize service.
"""
from contextlib import asynccontextmanager
from datetime import datetime
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from opentelemetry import metrics, trace
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from prometheus_client import start_http_server
import structlog

from app.config import get_settings
from app.routers import optimize, health
from app.services.solver_manager import SolverManager
from app.services.optimization_database import OptimizationDatabase

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
    
    # Initialize solver manager
    solver_manager = SolverManager()
    available_solvers = solver_manager.get_available_solvers()
    
    logger.info("optimize_service_starting",
                version=settings.version,
                environment=settings.environment,
                available_solvers=available_solvers)
    
    # Initialize database connection
    db = OptimizationDatabase()
    try:
        await db.connect()
        app.state.optimization_db = db
        logger.info("optimization_database_connected")
    except Exception as e:
        logger.error("optimization_database_connection_failed", error=str(e))
        app.state.optimization_db = None
    
    # Start Prometheus metrics server
    if settings.enable_metrics:
        try:
            start_http_server(settings.metrics_port)
            logger.info("prometheus_metrics_started", port=settings.metrics_port)
        except Exception as e:
            logger.warning("prometheus_metrics_failed", error=str(e))
    
    yield
    
    # Cleanup database connection
    if hasattr(app.state, "optimization_db") and app.state.optimization_db:
        await app.state.optimization_db.close()
        logger.info("optimization_database_closed")
    
    logger.info("optimize_service_shutting_down")


# Create FastAPI app
settings = get_settings()

app = FastAPI(
    title="OMARINO EMS - Optimize Service",
    description="Energy optimization with Pyomo: battery dispatch, unit commitment, procurement",
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

# Configure OpenTelemetry
resource = Resource.create({"service.name": settings.service_name})

# Tracing
tracer_provider = TracerProvider(resource=resource)
trace.set_tracer_provider(tracer_provider)

# Metrics
if settings.enable_metrics:
    reader = PrometheusMetricReader()
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(meter_provider)

# Instrument FastAPI
FastAPIInstrumentor.instrument_app(app)

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
            "detail": "Internal server error",
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
app.include_router(optimize.router, prefix=settings.api_prefix, tags=["Optimize"])

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "version": settings.version,
        "docs": f"{settings.api_prefix}/docs"
    }
