# Forecast Service

**Time series forecasting microservice** for the OMARINO EMS Suite.

Provides multiple forecasting models (classical, ML, and deep learning) with probabilistic predictions (quantiles), REST API, and OpenTelemetry observability.

---

## Features

- **Multiple Forecasting Models**
  - **Baseline**: Last value, seasonal naive
  - **Classical**: ARIMA, Exponential Smoothing (ETS)
  - **Machine Learning**: XGBoost, LightGBM with time series features
  - **Auto mode**: Automatically selects best model based on data characteristics

- **Probabilistic Forecasting**
  - Point forecasts (mean/median)
  - Quantile forecasts (e.g., p10, p50, p90)
  - Prediction intervals with configurable confidence levels

- **REST API**
  - FastAPI with automatic OpenAPI documentation
  - Pydantic validation for request/response
  - Async operations for scalability

- **Observability**
  - Structured logging with `structlog`
  - OpenTelemetry tracing and metrics
  - Prometheus metrics endpoint
  - Health/readiness/liveness probes

- **Production-Ready**
  - Multi-stage Docker build with non-root user
  - Comprehensive test suite (pytest + coverage)
  - Type hints and static analysis (mypy, ruff)

---

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (optional)

### Local Development

1. **Clone repository and navigate to service**
   ```bash
   cd forecast-service
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run service**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
   ```

6. **Access API documentation**
   - Swagger UI: http://localhost:8001/api/docs
   - ReDoc: http://localhost:8001/api/redoc
   - Prometheus metrics: http://localhost:9090/metrics

### Docker

```bash
# Build image
docker build -t omarino/forecast-service:latest .

# Run container
docker run -d \
  --name forecast-service \
  -p 8001:8001 \
  -p 9090:9090 \
  -e DATABASE_URL="postgresql+asyncpg://postgres:postgres@host.docker.internal:5432/omarino_ems" \
  -e TIMESERIES_SERVICE_URL="http://host.docker.internal:5001" \
  omarino/forecast-service:latest
```

---

## API Usage

### Generate Forecast

```bash
curl -X POST http://localhost:8001/api/forecast \
  -H "Content-Type: application/json" \
  -d '{
    "series_id": "123e4567-e89b-12d3-a456-426614174000",
    "horizon": 96,
    "granularity": "PT15M",
    "model": "auto",
    "quantiles": [0.1, 0.5, 0.9],
    "training_window": 2016
  }'
```

**Response:**
```json
{
  "forecast_id": "987f6543-e21c-45d6-b789-123456789abc",
  "series_id": "123e4567-e89b-12d3-a456-426614174000",
  "model_used": "xgboost",
  "created_at": "2024-01-15T10:30:00Z",
  "timestamps": ["2024-01-15T11:00:00Z", "2024-01-15T11:15:00Z", ...],
  "point_forecast": [105.3, 107.8, 110.2, ...],
  "quantiles": {
    "p10": [95.1, 97.2, 99.8, ...],
    "p50": [105.3, 107.8, 110.2, ...],
    "p90": [115.5, 118.4, 120.6, ...]
  },
  "metrics": {
    "mae": 5.2,
    "mape": 4.8,
    "rmse": 7.1
  },
  "metadata": {
    "training_samples": 2016,
    "training_time_seconds": 2.345
  }
}
```

### List Available Models

```bash
curl http://localhost:8001/api/models
```

### Train Model

```bash
curl -X POST http://localhost:8001/api/train \
  -H "Content-Type: application/json" \
  -d '{
    "series_id": "123e4567-e89b-12d3-a456-426614174000",
    "model": "xgboost",
    "training_window": 4032,
    "hyperparameters": {
      "n_estimators": 200,
      "max_depth": 7
    }
  }'
```

### Health Checks

```bash
# Basic health
curl http://localhost:8001/api/health

# Readiness (checks dependencies)
curl http://localhost:8001/api/health/ready

# Liveness
curl http://localhost:8001/api/health/live
```

---

## Models

### Auto Model Selection

The `auto` model automatically selects the best forecasting approach based on:
- **Data length**: More data enables complex models
- **Seasonality**: Detected patterns influence model choice
- **Forecast horizon**: Short vs. long-term forecasts

Selection logic:
- `< 100 points` → `last_value` (insufficient data)
- `100-500 points` → `ets` (classical statistical)
- `> 500 points` → `xgboost` (machine learning)

### Model Comparison

| Model | Type | Strengths | Quantiles | Training Time |
|-------|------|-----------|-----------|---------------|
| **last_value** | Baseline | Fast, simple | ❌ | Instant |
| **seasonal_naive** | Baseline | Captures seasonality | ❌ | Instant |
| **arima** | Classical | Handles trends, seasonality | ✅ | Medium |
| **ets** | Classical | Robust, interpretable | ✅ | Fast |
| **xgboost** | ML | High accuracy, handles complex patterns | ✅ | Medium |
| **lightgbm** | ML | Fast training, memory-efficient | ✅ | Fast |

### Time Series Features (ML Models)

ML models automatically generate features:
- **Lagged values**: t-1, t-2, t-3, t-96 (1 day), t-672 (1 week)
- **Calendar features**: Hour, day of week, month
- **Holiday indicators**: (when external features provided)
- **Weather data**: Temperature, humidity, irradiance (optional)

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVICE_NAME` | Service identifier | `forecast-service` |
| `API_PORT` | HTTP port | `8001` |
| `DATABASE_URL` | PostgreSQL connection | `postgresql+asyncpg://...` |
| `TIMESERIES_SERVICE_URL` | Time series service endpoint | `http://localhost:5001` |
| `MODELS_DIR` | Directory for trained models | `./models` |
| `MAX_HORIZON_MINUTES` | Maximum forecast horizon | `10080` (1 week) |
| `LOG_LEVEL` | Logging level | `INFO` |
| `ENABLE_METRICS` | Enable Prometheus metrics | `true` |
| `METRICS_PORT` | Metrics endpoint port | `9090` |

### Granularity Support

Supported forecast granularities (ISO 8601 durations):
- `PT5M` - 5 minutes
- `PT15M` - 15 minutes (default for energy data)
- `PT30M` - 30 minutes
- `PT1H` - 1 hour
- `P1D` - 1 day

---

## Development

### Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/test_forecast_service.py

# Specific test
pytest tests/test_api.py::TestHealthEndpoints::test_health_check
```

### Code Quality

```bash
# Format code
black app/ tests/

# Lint
ruff check app/ tests/

# Type check
mypy app/

# Run all checks
black app/ tests/ && ruff check app/ tests/ && mypy app/
```

### Project Structure

```
forecast-service/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration management
│   ├── models.py               # Pydantic models (API contracts)
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── forecast.py         # Forecast endpoints
│   │   └── health.py           # Health check endpoints
│   └── services/
│       ├── __init__.py
│       ├── forecast_service.py # Core forecasting logic
│       └── timeseries_client.py # Time series service client
├── tests/
│   ├── __init__.py
│   ├── test_api.py             # Integration tests
│   └── test_forecast_service.py # Unit tests
├── models/                     # Trained model artifacts (gitignored)
├── requirements.txt
├── pyproject.toml              # Tool configuration (pytest, black, ruff)
├── Dockerfile
├── .dockerignore
├── .env.example
└── README.md
```

---

## Architecture

### Data Flow

```
1. Client → POST /api/forecast (series_id, horizon, model)
2. Forecast Service → GET /api/series/{id}/data (historical data)
3. Timeseries Service → Returns time series points
4. Forecast Service → Train model & generate predictions
5. Forecast Service → Returns forecast with quantiles
```

### Model Pipeline

```
Historical Data
  ↓
Feature Engineering (lags, calendar, external)
  ↓
Model Training (ARIMA/ETS/XGBoost/LightGBM)
  ↓
Prediction (point + quantiles)
  ↓
Post-processing (validation, metrics)
  ↓
Response
```

---

## Observability

### Structured Logging

All logs are JSON-formatted with context:

```json
{
  "event": "forecast_request_received",
  "series_id": "123e4567-e89b-12d3-a456-426614174000",
  "horizon": 96,
  "model": "xgboost",
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "info"
}
```

### Prometheus Metrics

Available at `http://localhost:9090/metrics`:

- **HTTP metrics**: Request duration, status codes
- **Forecast metrics**: Model selection, training time, prediction errors
- **System metrics**: CPU, memory usage

### Tracing

OpenTelemetry spans for distributed tracing:
- Request handling
- Model training
- External API calls (timeseries-service)

---

## Performance

### Benchmarks

| Model | Training Time (1K points) | Prediction Time (96 steps) | Memory |
|-------|---------------------------|----------------------------|--------|
| last_value | < 1ms | < 1ms | ~1 MB |
| seasonal_naive | < 1ms | < 1ms | ~1 MB |
| ets | ~200ms | ~50ms | ~10 MB |
| arima | ~500ms | ~100ms | ~20 MB |
| xgboost | ~2s | ~20ms | ~50 MB |
| lightgbm | ~1s | ~10ms | ~30 MB |

### Optimization Tips

1. **Use model caching**: Train once, predict multiple times
2. **Limit training window**: 2-4 weeks typically sufficient
3. **Batch requests**: Group multiple forecasts
4. **Use quantile regression**: More efficient than full distribution

---

## Troubleshooting

### Common Issues

**Issue**: `Insufficient historical data` error
- **Solution**: Ensure time series has at least 10 data points. Increase `training_window`.

**Issue**: ARIMA/ETS model fails
- **Solution**: Data may be non-stationary or have irregular patterns. Use `xgboost` or `lightgbm`.

**Issue**: Slow forecasts
- **Solution**: Reduce `training_window`, use simpler model (`ets` vs `xgboost`), or enable model caching.

**Issue**: Quantiles are too narrow
- **Solution**: Increase `confidence_level` or use ensemble of models.

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
uvicorn app.main:app --log-level debug
```

---

## Roadmap

- [ ] **Neural forecasting models**: N-HiTS, N-BEATS, TFT
- [ ] **Ensemble forecasting**: Combine multiple models
- [ ] **Feature importance**: SHAP values for interpretability
- [ ] **Backtesting**: Automated model evaluation on historical data
- [ ] **Hyperparameter tuning**: Optuna-based optimization
- [ ] **Model registry**: MLflow integration for model versioning
- [ ] **Batch forecasting**: Generate forecasts for multiple series
- [ ] **GPU acceleration**: For deep learning models

---

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for development guidelines.

---

## License

MIT License - see [LICENSE](../LICENSE) for details.

---

## Support

For issues and questions:
- GitHub Issues: https://github.com/your-org/omarino-ems/issues
- Documentation: https://your-org.github.io/omarino-ems/
