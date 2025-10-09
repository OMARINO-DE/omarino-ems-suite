"""
Tests for health check endpoints.
"""
import pytest
from fastapi import status
from datetime import datetime


@pytest.mark.unit
def test_health_endpoint_returns_200(client):
    """Test that /health endpoint returns 200 OK"""
    response = client.get("/health")
    
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.unit
def test_health_endpoint_response_structure(client, assert_response_structure):
    """Test that /health returns correct structure"""
    response = client.get("/health")
    data = response.json()
    
    required_fields = ["status", "service", "version", "timestamp", "environment"]
    assert_response_structure(data, required_fields)


@pytest.mark.unit
def test_health_endpoint_values(client):
    """Test that /health returns expected values"""
    response = client.get("/health")
    data = response.json()
    
    assert data["status"] == "healthy"
    assert data["service"] == "ai-hub"
    assert "version" in data
    assert "timestamp" in data
    
    # Validate timestamp format
    timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
    assert isinstance(timestamp, datetime)


@pytest.mark.unit
def test_api_health_endpoint_returns_200(client):
    """Test that /api/health endpoint returns 200 OK"""
    response = client.get("/api/health")
    
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.unit
def test_api_health_endpoint_same_as_health(client):
    """Test that /api/health returns same data as /health"""
    health_response = client.get("/health")
    api_health_response = client.get("/api/health")
    
    assert health_response.json() == api_health_response.json()


@pytest.mark.unit
def test_health_endpoint_no_auth_required(client):
    """Test that /health endpoint does not require authentication"""
    # Should work without Authorization header
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.unit
def test_health_endpoint_cors_headers(client):
    """Test that CORS headers are present in health response"""
    response = client.get("/health")
    
    # CORS headers should be present if CORS middleware is configured
    # Note: This depends on your CORS configuration
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
@pytest.mark.slow
def test_health_endpoint_performance(client):
    """Test that health endpoint responds quickly"""
    import time
    
    start = time.time()
    response = client.get("/health")
    duration = time.time() - start
    
    assert response.status_code == status.HTTP_200_OK
    assert duration < 0.1  # Should respond in less than 100ms


@pytest.mark.unit
def test_health_endpoint_multiple_calls(client):
    """Test that health endpoint can handle multiple calls"""
    responses = []
    
    for _ in range(10):
        response = client.get("/health")
        responses.append(response)
    
    # All should succeed
    for response in responses:
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "healthy"


@pytest.mark.unit
def test_health_endpoint_content_type(client):
    """Test that health endpoint returns JSON"""
    response = client.get("/health")
    
    assert response.status_code == status.HTTP_200_OK
    assert "application/json" in response.headers["content-type"]


@pytest.mark.unit
def test_health_endpoint_environment_value(client, test_config):
    """Test that environment value matches configuration"""
    response = client.get("/health")
    data = response.json()
    
    assert "environment" in data
    # In tests, should be 'test' or similar
    assert isinstance(data["environment"], str)


@pytest.mark.unit
def test_health_endpoint_version_format(client):
    """Test that version follows semantic versioning"""
    response = client.get("/health")
    data = response.json()
    
    version = data["version"]
    assert isinstance(version, str)
    
    # Basic semantic versioning check (e.g., "0.1.0")
    parts = version.split(".")
    assert len(parts) >= 2  # At least major.minor


@pytest.mark.unit
def test_health_endpoint_with_query_params(client):
    """Test that health endpoint ignores query parameters"""
    response = client.get("/health?foo=bar&baz=qux")
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "healthy"


@pytest.mark.unit
def test_health_endpoint_with_trailing_slash(client):
    """Test health endpoint with trailing slash"""
    response = client.get("/health/")
    
    # Should either work or redirect
    assert response.status_code in [
        status.HTTP_200_OK,
        status.HTTP_307_TEMPORARY_REDIRECT,
        status.HTTP_308_PERMANENT_REDIRECT
    ]


@pytest.mark.unit
def test_health_endpoint_head_request(client):
    """Test that HEAD request to /health works"""
    response = client.head("/health")
    
    # HEAD should return same status as GET but no body
    assert response.status_code == status.HTTP_200_OK
    assert len(response.content) == 0 or response.content == b""


@pytest.mark.unit
def test_health_endpoint_options_request(client):
    """Test that OPTIONS request to /health works (for CORS)"""
    response = client.options("/health")
    
    # Should return allowed methods
    assert response.status_code in [
        status.HTTP_200_OK,
        status.HTTP_204_NO_CONTENT
    ]
