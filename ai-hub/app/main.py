"""
AI Hub Service - Main Application Entry Point

Provides AI/ML endpoints for forecasting, anomaly detection, and explainability.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from app.config import settings
from app.routers import health, forecast, anomaly, explain, model_registry, features, training, hpo, experiments
from app.services import get_model_cache

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
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("ai_hub_starting", environment=settings.ENVIRONMENT)
    
    # Initialize OpenTelemetry if configured
    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        trace.set_tracer_provider(TracerProvider())
        span_processor = BatchSpanProcessor(
            OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
        )
        trace.get_tracer_provider().add_span_processor(span_processor)
        logger.info("opentelemetry_initialized", endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
    
    # Warm up model cache with default models
    model_cache = get_model_cache()
    warmup_models = []  # TODO: Configure default models to warmup
    if warmup_models:
        await model_cache.warmup(warmup_models)
        logger.info("model_cache_warmed_up")
    
    yield
    
    # Shutdown
    logger.info("ai_hub_shutting_down")
    # Model cache cleanup (clear memory)
    await model_cache.clear_cache()


# Create FastAPI application
app = FastAPI(
    title="OMARINO AI Hub Service",
    description="AI/ML service for forecasting, anomaly detection, and explainability",
    version="0.1.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instrument with OpenTelemetry
if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
    FastAPIInstrumentor.instrument_app(app)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions."""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.ENVIRONMENT != "production" else "An error occurred"
        }
    )


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(forecast.router, prefix="/ai", tags=["Forecast"])
app.include_router(anomaly.router, prefix="/ai", tags=["Anomaly Detection"])
app.include_router(explain.router, prefix="/ai", tags=["Explainability"])
app.include_router(model_registry.router, tags=["Model Registry"])
app.include_router(features.router, tags=["Features"])
app.include_router(training.router, tags=["Training"])
app.include_router(hpo.router, tags=["HPO"])
app.include_router(experiments.router, tags=["Experiments"])


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "ai-hub",
        "version": "0.1.0",
        "status": "operational",
        "docs": "/docs" if settings.ENVIRONMENT != "production" else None
    }
