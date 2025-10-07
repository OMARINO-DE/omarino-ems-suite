"""
Integration tests for forecast API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app

client = TestClient(app)


class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    def test_health_check(self):
        """Test basic health check."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data
    
    def test_readiness_check(self):
        """Test readiness check."""
        response = client.get("/api/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
    
    def test_liveness_check(self):
        """Test liveness check."""
        response = client.get("/api/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"


class TestForecastEndpoints:
    """Tests for forecast endpoints."""
    
    def test_list_models(self):
        """Test listing available models."""
        response = client.get("/api/models")
        assert response.status_code == 200
        data = response.json()
        
        assert "models" in data
        assert len(data["models"]) > 0
        
        # Check model structure
        for model in data["models"]:
            assert "name" in model
            assert "description" in model
            assert "type" in model
            assert "supports_quantiles" in model
    
    @pytest.mark.asyncio
    async def test_forecast_request_last_value(self):
        """Test forecast request with last_value model."""
        request_data = {
            "series_id": str(uuid4()),
            "horizon": 24,
            "granularity": "PT15M",
            "model": "last_value",
            "quantiles": [0.1, 0.5, 0.9]
        }
        
        response = client.post("/api/forecast", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "forecast_id" in data
        assert "series_id" in data
        assert data["model_used"] == "last_value"
        assert len(data["point_forecast"]) == 24
        assert len(data["timestamps"]) == 24
        assert "metadata" in data
    
    def test_forecast_request_validation_error(self):
        """Test forecast request with invalid data."""
        request_data = {
            "series_id": str(uuid4()),
            "horizon": -1,  # Invalid: must be >= 1
            "granularity": "PT15M",
            "model": "last_value"
        }
        
        response = client.post("/api/forecast", json=request_data)
        assert response.status_code == 422  # Validation error
    
    def test_forecast_request_invalid_model(self):
        """Test forecast request with invalid model."""
        request_data = {
            "series_id": str(uuid4()),
            "horizon": 24,
            "granularity": "PT15M",
            "model": "invalid_model"
        }
        
        response = client.post("/api/forecast", json=request_data)
        assert response.status_code == 422  # Validation error


class TestRootEndpoint:
    """Tests for root endpoint."""
    
    def test_root(self):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        
        assert "service" in data
        assert data["service"] == "forecast-service"
        assert "version" in data
        assert "docs" in data
