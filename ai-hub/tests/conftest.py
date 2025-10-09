"""
Pytest configuration and shared fixtures for AI Hub tests.
"""
import pytest
from typing import Dict, Any, List
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
import jwt
from datetime import datetime, timezone


# Test Configuration
@pytest.fixture(scope="session")
def test_config():
    """Test configuration settings"""
    return {
        "SERVICE_NAME": "ai-hub-test",
        "ENVIRONMENT": "test",
        "DATABASE_URL": "postgresql://test:test@localhost:5432/test_db",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": 6379,
        "REDIS_PASSWORD": "",
        "REDIS_DB": 1,  # Use different DB for tests
        "KEYCLOAK_URL": "http://localhost:8080",
        "KEYCLOAK_REALM": "test-realm",
        "KEYCLOAK_CLIENT_ID": "ai-hub-test",
        "JWT_ALGORITHM": "RS256",
        "MODEL_STORAGE_PATH": "./test_models",
        "MODEL_CACHE_SIZE": 2,
        "MODEL_CACHE_TTL": 300,
        "DEFAULT_FORECAST_HORIZON": 24,
        "ANOMALY_THRESHOLD": 3.0,
    }


@pytest.fixture
def app():
    """FastAPI application instance for testing"""
    # Import here to avoid circular imports
    from app.main import app
    return app


@pytest.fixture
def client(app):
    """Test client for making API requests"""
    return TestClient(app)


# JWT and Authentication Fixtures
@pytest.fixture
def jwt_secret():
    """Secret key for JWT signing in tests"""
    return "test-secret-key-do-not-use-in-production"


@pytest.fixture
def mock_jwt_payload():
    """Mock JWT payload with standard claims"""
    return {
        "sub": "test-user-123",
        "tenant_id": "test-tenant-123",
        "preferred_username": "test@example.com",
        "email": "test@example.com",
        "realm_access": {
            "roles": ["ai_user", "forecaster", "anomaly_analyst"]
        },
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
    }


@pytest.fixture
def mock_jwt_token(mock_jwt_payload, jwt_secret):
    """Generate a mock JWT token for testing"""
    return jwt.encode(mock_jwt_payload, jwt_secret, algorithm="HS256")


@pytest.fixture
def auth_headers(mock_jwt_token):
    """Authorization headers with JWT token"""
    return {
        "Authorization": f"Bearer {mock_jwt_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture
def admin_jwt_payload(mock_jwt_payload):
    """JWT payload with admin roles"""
    payload = mock_jwt_payload.copy()
    payload["realm_access"]["roles"].extend(["model_admin", "admin"])
    return payload


@pytest.fixture
def admin_jwt_token(admin_jwt_payload, jwt_secret):
    """Admin JWT token"""
    return jwt.encode(admin_jwt_payload, jwt_secret, algorithm="HS256")


@pytest.fixture
def admin_headers(admin_jwt_token):
    """Authorization headers with admin token"""
    return {
        "Authorization": f"Bearer {admin_jwt_token}",
        "Content-Type": "application/json"
    }


# Time Series Data Fixtures
@pytest.fixture
def sample_timeseries():
    """Sample time series data for testing"""
    base_time = datetime(2025, 10, 1, 0, 0, 0)
    return [
        {
            "timestamp": (base_time + timedelta(hours=i)).isoformat() + "Z",
            "value": 40.0 + (i * 0.5) + (5.0 if i % 4 == 0 else 0)  # Add some variation
        }
        for i in range(168)  # 7 days of hourly data
    ]


@pytest.fixture
def sample_timeseries_with_anomalies():
    """Time series data with known anomalies"""
    base_time = datetime(2025, 10, 1, 0, 0, 0)
    data = []
    
    for i in range(100):
        timestamp = (base_time + timedelta(hours=i)).isoformat() + "Z"
        
        # Normal value
        value = 45.0 + (i % 24) * 0.5
        
        # Inject anomalies at specific points
        if i in [10, 25, 50, 75]:
            value = value * 3.0  # Spike anomaly
        elif i in [30, 60]:
            value = value * 0.2  # Drop anomaly
        
        data.append({
            "timestamp": timestamp,
            "value": value,
            "metadata": {"anomaly_injected": i in [10, 25, 30, 50, 60, 75]}
        })
    
    return data


@pytest.fixture
def forecast_request_payload(mock_jwt_payload):
    """Valid forecast request payload"""
    return {
        "tenant_id": mock_jwt_payload["tenant_id"],
        "asset_id": "meter-001",
        "forecast_type": "load",
        "horizon_hours": 24,
        "interval_minutes": 60,
        "include_quantiles": True,
        "model_name": "lightgbm_v1"
    }


@pytest.fixture
def anomaly_request_payload(mock_jwt_payload, sample_timeseries):
    """Valid anomaly detection request payload"""
    return {
        "tenant_id": mock_jwt_payload["tenant_id"],
        "asset_id": "meter-001",
        "time_series": sample_timeseries[:48],  # 2 days of data
        "method": "isolation_forest",
        "sensitivity": 3.0
    }


@pytest.fixture
def explain_request_payload(mock_jwt_payload):
    """Valid explanation request payload"""
    return {
        "tenant_id": mock_jwt_payload["tenant_id"],
        "model_name": "lightgbm_v1",
        "model_version": "1.0.0",
        "input_features": {
            "hour_of_day": 14,
            "day_of_week": 3,
            "temperature": 22.5,
            "humidity": 65.0
        },
        "explanation_type": "shap",
        "max_samples": 100
    }


# Mock Services
@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    mock = Mock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=False)
    return mock


@pytest.fixture
def mock_database():
    """Mock database session"""
    mock = Mock()
    mock.execute = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_model_cache():
    """Mock model cache service"""
    mock = Mock()
    mock.get_model = AsyncMock(return_value=Mock())
    mock.load_model = AsyncMock(return_value=Mock())
    mock.cache_model = AsyncMock()
    mock.clear_cache = AsyncMock()
    return mock


@pytest.fixture
def mock_feature_store():
    """Mock feature store service"""
    mock = Mock()
    mock.get_features = AsyncMock(return_value={
        "hour_of_day": 14,
        "day_of_week": 3,
        "temperature": 22.5,
        "humidity": 65.0,
        "historical_avg_24h": 45.0
    })
    mock.store_features = AsyncMock()
    return mock


@pytest.fixture
def mock_ml_model():
    """Mock ML model for predictions"""
    mock = Mock()
    mock.predict = Mock(return_value=[45.0, 46.0, 44.5])
    mock.predict_proba = Mock(return_value=[[0.1, 0.8, 0.1]])
    mock.feature_names_in_ = ["hour_of_day", "day_of_week", "temperature"]
    return mock


# Keycloak and Auth Mocks
@pytest.fixture
def mock_keycloak_public_key():
    """Mock Keycloak public key for JWT validation"""
    return """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
-----END PUBLIC KEY-----"""


@pytest.fixture
def mock_jwt_validator():
    """Mock JWT validator that always succeeds"""
    async def validator(token: str) -> Dict[str, Any]:
        return {
            "sub": "test-user-123",
            "tenant_id": "test-tenant-123",
            "preferred_username": "test@example.com",
            "realm_access": {"roles": ["ai_user", "forecaster"]}
        }
    return validator


# Database Models and Fixtures
@pytest.fixture
def sample_forecast_record():
    """Sample forecast database record"""
    return {
        "id": "fc-uuid-123",
        "tenant_id": "test-tenant-123",
        "asset_id": "meter-001",
        "forecast_type": "load",
        "model_name": "lightgbm_v1",
        "model_version": "1.0.0",
        "horizon_hours": 24,
        "generated_at": datetime.utcnow(),
        "metadata": {"mae": 2.5, "rmse": 3.8}
    }


@pytest.fixture
def sample_model_metadata():
    """Sample model metadata"""
    return {
        "model_id": "model-uuid-123",
        "model_name": "lightgbm_v1",
        "version": "1.0.0",
        "tenant_id": "test-tenant-123",
        "model_type": "forecast",
        "algorithm": "lightgbm",
        "features": ["hour_of_day", "day_of_week", "temperature"],
        "training_date": datetime.utcnow().isoformat(),
        "performance_metrics": {
            "mae": 2.5,
            "rmse": 3.8,
            "mape": 0.05
        },
        "hyperparameters": {
            "num_leaves": 31,
            "learning_rate": 0.1
        }
    }


# Helper Functions
@pytest.fixture
def assert_response_structure():
    """Helper to assert common response structure"""
    def _assert(response_data: Dict, required_fields: List[str]):
        for field in required_fields:
            assert field in response_data, f"Missing required field: {field}"
    return _assert


# Cleanup Fixtures
@pytest.fixture(autouse=True)
def cleanup_test_models(test_config):
    """Cleanup test model files after each test"""
    yield
    # TODO: Implement cleanup of test_models directory
    pass


@pytest.fixture(autouse=True)
def reset_redis_test_db(mock_redis):
    """Reset Redis test database after each test"""
    yield
    # TODO: Implement Redis test DB flush
    pass


# Pytest Configuration
def pytest_configure(config):
    """Pytest configuration hook"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "auth: marks tests related to authentication"
    )
    config.addinivalue_line(
        "markers", "ml: marks tests related to ML models"
    )


# Async Test Support
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session"""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
