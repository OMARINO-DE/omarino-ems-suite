# Forecast Service - Quick Reference

## Service Info
- **Language**: Python 3.11
- **Framework**: FastAPI 0.109.0
- **Port**: 8001 (API), 9090 (Metrics)
- **Files**: 18 files created

## Quick Start

```bash
cd forecast-service

# Install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env

# Run
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Test
pytest --cov=app

# Docker
docker build -t omarino/forecast-service:latest .
docker run -p 8001:8001 -p 9090:9090 omarino/forecast-service:latest
```

## API Endpoints

### Forecast
```bash
# Generate forecast
curl -X POST http://localhost:8001/api/forecast \
  -H "Content-Type: application/json" \
  -d '{
    "series_id": "123e4567-e89b-12d3-a456-426614174000",
    "horizon": 96,
    "granularity": "PT15M",
    "model": "auto",
    "quantiles": [0.1, 0.5, 0.9]
  }'

# List models
curl http://localhost:8001/api/models

# Train model
curl -X POST http://localhost:8001/api/train \
  -H "Content-Type: application/json" \
  -d '{
    "series_id": "123e4567-e89b-12d3-a456-426614174000",
    "model": "xgboost"
  }'
```

### Health
```bash
curl http://localhost:8001/api/health
curl http://localhost:8001/api/health/ready
curl http://localhost:8001/api/health/live
```

### Docs
- Swagger UI: http://localhost:8001/api/docs
- ReDoc: http://localhost:8001/api/redoc
- Metrics: http://localhost:9090/metrics

## Available Models

| Model | Type | Quantiles | Use Case |
|-------|------|-----------|----------|
| `auto` | Ensemble | ✅ | Auto-select best model |
| `arima` | Classical | ✅ | Trend + seasonality |
| `ets` | Classical | ✅ | Exponential smoothing |
| `xgboost` | ML | ✅ | High accuracy |
| `lightgbm` | ML | ✅ | Fast training |
| `seasonal_naive` | Baseline | ❌ | Seasonal patterns |
| `last_value` | Baseline | ❌ | Simple persistence |

## File Structure

```
forecast-service/
├── app/
│   ├── main.py                      # FastAPI app
│   ├── config.py                    # Configuration
│   ├── models.py                    # Pydantic models
│   ├── routers/
│   │   ├── forecast.py              # Forecast endpoints
│   │   └── health.py                # Health checks
│   └── services/
│       ├── forecast_service.py      # Core forecasting logic
│       └── timeseries_client.py     # TS service client
├── tests/
│   ├── test_api.py                  # Integration tests
│   └── test_forecast_service.py     # Unit tests
├── requirements.txt                 # Dependencies
├── pyproject.toml                   # Tool config
├── Dockerfile                       # Container image
└── README.md                        # Full documentation
```

## Environment Variables

```bash
API_PORT=8001
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/omarino_ems
TIMESERIES_SERVICE_URL=http://localhost:5001
LOG_LEVEL=INFO
ENABLE_METRICS=true
METRICS_PORT=9090
```

## Testing

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test
pytest tests/test_api.py::TestHealthEndpoints::test_health_check

# Code quality
black app/ tests/
ruff check app/ tests/
mypy app/
```

## Next Steps

1. ✅ **DONE**: Forecast-service scaffolded
2. ⏳ **TODO**: Integrate with timeseries-service (replace dummy data)
3. ⏳ **TODO**: Add model persistence (save/load trained models)
4. ⏳ **TODO**: Continue with Step 6: optimize-service

## Key Features

- ✅ 6 forecasting models + auto mode
- ✅ Probabilistic forecasting (quantiles)
- ✅ REST API with FastAPI
- ✅ OpenTelemetry observability
- ✅ Comprehensive tests (unit + integration)
- ✅ Docker containerization
- ✅ Health probes (K8s-ready)

---

**Status**: ✅ Complete  
**Date**: 2024-01-15  
**Ready for**: Integration testing
