# AI Hub Testing Guide

## Overview

This directory contains the comprehensive test suite for the AI Hub service. The tests are organized by feature area and use pytest as the testing framework.

## Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Shared fixtures and configuration
├── pytest.ini               # Pytest configuration
├── test_health.py           # Health check endpoint tests
├── test_forecast.py         # Forecast generation tests
├── test_anomaly.py          # Anomaly detection tests
├── test_explain.py          # Model explainability tests
├── test_auth.py             # Authentication tests (TODO)
└── integration/             # Integration tests (TODO)
    ├── test_forecast_e2e.py
    └── test_model_lifecycle.py
```

## Running Tests

### Basic Usage

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_health.py

# Run specific test function
pytest tests/test_health.py::test_health_endpoint_returns_200

# Run with coverage report
pytest --cov=app --cov-report=html

# Run with coverage and open report
pytest --cov=app --cov-report=html && open htmlcov/index.html
```

### Using Test Markers

```bash
# Run only unit tests (fast)
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Run authentication tests
pytest -m auth

# Run ML model tests
pytest -m ml

# Combine markers
pytest -m "unit and not slow"
```

### Test Selection by Pattern

```bash
# Run tests matching pattern
pytest -k "health"
pytest -k "forecast and not slow"

# Run tests in specific directory
pytest tests/integration/
```

## Test Coverage

### Current Coverage Target

- **Overall**: >80% code coverage
- **Critical paths**: 100% coverage (health, auth, core endpoints)
- **ML algorithms**: >70% coverage

### Generating Coverage Reports

```bash
# Terminal report
pytest --cov=app --cov-report=term-missing

# HTML report (recommended)
pytest --cov=app --cov-report=html

# XML report (for CI/CD)
pytest --cov=app --cov-report=xml

# Multiple formats
pytest --cov=app --cov-report=html --cov-report=term-missing
```

## Test Categories

### Unit Tests (`@pytest.mark.unit`)

Fast, isolated tests that don't require external dependencies.

**Characteristics:**
- No database connections
- No Redis connections
- Use mocks for external services
- Run in <1 second each
- Can be run in parallel

**Examples:**
```python
@pytest.mark.unit
def test_health_endpoint_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200
```

### Integration Tests (`@pytest.mark.integration`)

Tests that require external services (database, Redis, etc.)

**Characteristics:**
- Require running services
- Test actual integrations
- Slower execution
- Use test databases

**Examples:**
```python
@pytest.mark.integration
def test_forecast_with_real_database(client, db_session):
    # Test with actual database
    pass
```

### Slow Tests (`@pytest.mark.slow`)

Tests that take longer than 1 second to execute.

**Characteristics:**
- Performance tests
- Large dataset tests
- Can be skipped in development

**Examples:**
```python
@pytest.mark.slow
def test_forecast_large_dataset(client):
    # Test with 10,000 data points
    pass
```

### Authentication Tests (`@pytest.mark.auth`)

Tests related to authentication and authorization.

**Examples:**
```python
@pytest.mark.auth
def test_forecast_without_auth_fails(client):
    response = client.post("/ai/forecast", json={})
    assert response.status_code == 401
```

### ML Model Tests (`@pytest.mark.ml`)

Tests that involve actual machine learning models.

**Characteristics:**
- Test model inference
- Test model loading/caching
- May require trained models

## Fixtures

### Available Fixtures (from `conftest.py`)

#### Configuration
- `test_config`: Test configuration settings
- `app`: FastAPI application instance
- `client`: TestClient for making requests

#### Authentication
- `mock_jwt_payload`: JWT payload with standard claims
- `mock_jwt_token`: Encoded JWT token
- `auth_headers`: Headers with Bearer token
- `admin_jwt_payload`: Admin user JWT payload
- `admin_jwt_token`: Admin JWT token
- `admin_headers`: Admin authorization headers

#### Test Data
- `sample_timeseries`: 7 days of hourly data
- `sample_timeseries_with_anomalies`: Data with injected anomalies
- `forecast_request_payload`: Valid forecast request
- `anomaly_request_payload`: Valid anomaly detection request
- `explain_request_payload`: Valid explanation request

#### Mocks
- `mock_redis`: Mock Redis client
- `mock_database`: Mock database session
- `mock_model_cache`: Mock model cache service
- `mock_feature_store`: Mock feature store
- `mock_ml_model`: Mock ML model

### Using Fixtures

```python
def test_with_fixtures(client, auth_headers, forecast_request_payload):
    response = client.post(
        "/ai/forecast",
        json=forecast_request_payload,
        headers=auth_headers
    )
    assert response.status_code == 200
```

## Writing New Tests

### Test Naming Convention

```python
# Pattern: test_<feature>_<scenario>
def test_forecast_returns_correct_horizon():
    pass

def test_forecast_validates_invalid_input():
    pass

def test_forecast_requires_authentication():
    pass
```

### Test Structure (AAA Pattern)

```python
def test_example():
    # Arrange - Set up test data
    payload = {"tenant_id": "test", "asset_id": "meter-001"}
    
    # Act - Perform the action
    response = client.post("/ai/forecast", json=payload)
    
    # Assert - Verify the results
    assert response.status_code == 200
    assert "forecast_id" in response.json()
```

### Best Practices

1. **One assertion per test** (when possible)
   ```python
   # Good
   def test_health_returns_200(client):
       response = client.get("/health")
       assert response.status_code == 200
   
   def test_health_returns_json(client):
       response = client.get("/health")
       assert "application/json" in response.headers["content-type"]
   ```

2. **Use descriptive test names**
   ```python
   # Good
   def test_forecast_with_invalid_horizon_returns_422()
   
   # Bad
   def test_forecast_error()
   ```

3. **Test edge cases**
   ```python
   def test_forecast_minimum_horizon():
       # Test with horizon_hours = 1
       pass
   
   def test_forecast_maximum_horizon():
       # Test with horizon_hours = 168
       pass
   ```

4. **Use fixtures for setup**
   ```python
   @pytest.fixture
   def complex_test_data():
       return generate_complex_data()
   
   def test_with_complex_data(complex_test_data):
       # Use the fixture
       pass
   ```

## Mocking External Services

### Mocking Redis

```python
@patch('app.services.redis_client')
def test_with_mocked_redis(mock_redis, client):
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    
    # Test code
    pass
```

### Mocking Database

```python
@pytest.fixture
def mock_db_session():
    session = Mock()
    session.execute = AsyncMock(return_value=Mock())
    return session

def test_with_mocked_db(mock_db_session):
    # Test code
    pass
```

### Mocking ML Models

```python
@patch('app.services.model_cache.load_model')
def test_with_mocked_model(mock_load_model, client):
    mock_model = Mock()
    mock_model.predict.return_value = [45.0, 46.0]
    mock_load_model.return_value = mock_model
    
    # Test code
    pass
```

## Continuous Integration

### Running Tests in CI

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    pytest -v \
      --cov=app \
      --cov-report=xml \
      --cov-report=term-missing \
      -m "not slow"

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

### Test Requirements

Tests should:
- Pass in CI environment
- Be deterministic (no random failures)
- Clean up after themselves
- Not depend on execution order
- Run quickly (<5 minutes total)

## Debugging Tests

### Running with Debug Output

```bash
# Show print statements
pytest -s

# Show local variables on failure
pytest --showlocals

# Drop into debugger on failure
pytest --pdb

# Increase verbosity
pytest -vv
```

### Using pytest-pudb

```bash
# Install
pip install pytest-pudb

# Run with debugger
pytest --pudb
```

### Logging During Tests

```python
import logging

def test_with_logging(caplog):
    with caplog.at_level(logging.INFO):
        # Code that logs
        pass
    
    assert "expected message" in caplog.text
```

## Performance Testing

### Measuring Test Duration

```bash
# Show slowest tests
pytest --durations=10

# Show all test durations
pytest --durations=0
```

### Profiling Tests

```bash
# Install
pip install pytest-profiling

# Run with profiling
pytest --profile

# Generate SVG call graph
pytest --profile-svg
```

## Test Data Management

### Using Factories

```python
# tests/factories.py
def create_forecast_request(tenant_id="test", **overrides):
    defaults = {
        "tenant_id": tenant_id,
        "asset_id": "meter-001",
        "forecast_type": "load",
        "horizon_hours": 24
    }
    return {**defaults, **overrides}

# In tests
def test_example():
    request = create_forecast_request(horizon_hours=48)
```

### Fixture Parametrization

```python
@pytest.mark.parametrize("forecast_type", ["load", "generation", "price"])
def test_all_forecast_types(client, forecast_type):
    payload = {"forecast_type": forecast_type, ...}
    response = client.post("/ai/forecast", json=payload)
    assert response.status_code == 200
```

## Common Issues and Solutions

### Issue: Tests fail locally but pass in CI

**Solution:** Check for environment-specific dependencies, file paths, or timing issues.

### Issue: Tests are too slow

**Solutions:**
- Use `@pytest.mark.slow` to mark slow tests
- Mock external services
- Reduce test data size
- Run tests in parallel: `pytest -n auto` (requires pytest-xdist)

### Issue: Flaky tests (random failures)

**Solutions:**
- Remove time-based assertions
- Use proper mocking
- Avoid global state
- Set random seeds

### Issue: Import errors in tests

**Solution:** Ensure PYTHONPATH includes project root:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

## Test Maintenance

### Regular Tasks

1. **Review coverage reports** weekly
2. **Update mocks** when APIs change
3. **Add regression tests** for bugs
4. **Refactor duplicate code** into fixtures
5. **Update test documentation**

### When to Update Tests

- After adding new features
- After fixing bugs (add regression test)
- When API contracts change
- When dependencies are updated
- Before major releases

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)

## Support

For questions or issues with tests:
1. Check this documentation
2. Review existing test examples
3. Check pytest documentation
4. Ask the team in #engineering channel
