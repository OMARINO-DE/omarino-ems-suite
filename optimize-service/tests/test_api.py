"""
Integration tests for optimize API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
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
        assert "solvers_available" in data
    
    def test_readiness_check(self):
        """Test readiness check."""
        response = client.get("/api/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ready", "not_ready"]
    
    def test_liveness_check(self):
        """Test liveness check."""
        response = client.get("/api/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"


class TestOptimizeEndpoints:
    """Tests for optimize endpoints."""
    
    def test_list_optimization_types(self):
        """Test listing available optimization types."""
        response = client.get("/api/types")
        assert response.status_code == 200
        data = response.json()
        
        assert "types" in data
        assert len(data["types"]) > 0
        
        # Check structure
        for opt_type in data["types"]:
            assert "name" in opt_type
            assert "description" in opt_type
            assert "requires" in opt_type
    
    def test_request_optimization_simple(self):
        """Test requesting simple battery dispatch optimization."""
        start_time = datetime.utcnow().replace(microsecond=0)
        end_time = start_time + timedelta(hours=2)
        
        request_data = {
            "optimization_type": "battery_dispatch",
            "objective": "minimize_cost",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "time_step_minutes": 60,
            "assets": [
                {
                    "asset_id": "battery-1",
                    "asset_type": "battery",
                    "name": "Test Battery",
                    "battery": {
                        "capacity_kwh": 100.0,
                        "max_charge_kw": 50.0,
                        "max_discharge_kw": 50.0,
                        "efficiency": 0.95,
                        "initial_soc": 0.5
                    }
                },
                {
                    "asset_id": "grid-1",
                    "asset_type": "grid_connection",
                    "name": "Grid",
                    "grid": {
                        "max_import_kw": 200.0,
                        "max_export_kw": 100.0
                    }
                }
            ],
            "solver": "highs"
        }
        
        response = client.post("/api/optimize", json=request_data)
        assert response.status_code == 202  # Accepted
        
        data = response.json()
        assert "optimization_id" in data
        assert data["status"] == "pending"
        assert data["optimization_type"] == "battery_dispatch"
    
    def test_get_optimization_not_found(self):
        """Test getting non-existent optimization."""
        fake_id = str(uuid4())
        response = client.get(f"/api/optimize/{fake_id}")
        assert response.status_code == 404
    
    def test_list_optimizations(self):
        """Test listing optimizations."""
        response = client.get("/api/optimize")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)


class TestRootEndpoint:
    """Tests for root endpoint."""
    
    def test_root(self):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        
        assert "service" in data
        assert data["service"] == "optimize-service"
        assert "version" in data
        assert "docs" in data
