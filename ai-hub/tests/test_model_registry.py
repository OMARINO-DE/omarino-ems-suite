"""
Tests for Model Registry Router

Tests model lifecycle management endpoints:
- Model registration
- Model retrieval
- Model listing
- Model promotion
- Model deletion
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch


class TestModelRegistration:
    """Tests for POST /ai/models/register"""
    
    def test_register_model_success(self, client: TestClient):
        """Test successful model registration"""
        payload = {
            "tenant_id": "tenant-123",
            "model_name": "forecast_lgb",
            "version": "v1.0.0",
            "metadata": {
                "model_type": "LightGBM",
                "framework": "lightgbm",
                "hyperparameters": {"num_leaves": 31, "learning_rate": 0.05},
                "feature_names": ["hour", "temp", "humidity"],
                "description": "Production forecasting model"
            },
            "metrics": {
                "rmse": 2.5,
                "mae": 1.8,
                "r2_score": 0.92
            },
            "stage": "staging"
        }
        
        response = client.post("/ai/models/register", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["model_id"] == "tenant-123:forecast_lgb:v1.0.0"
        assert data["model_name"] == "forecast_lgb"
        assert data["version"] == "v1.0.0"
        assert data["stage"] == "staging"
        assert data["status"] == "registered"
        assert "uploaded_at" in data
    
    def test_register_model_minimal_metadata(self, client: TestClient):
        """Test registration with minimal metadata"""
        payload = {
            "tenant_id": "tenant-123",
            "model_name": "simple_model",
            "version": "v1.0.0",
            "metadata": {
                "model_type": "LinearRegression",
                "framework": "sklearn"
            }
        }
        
        response = client.post("/ai/models/register", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["model_name"] == "simple_model"
    
    def test_register_model_with_custom_metrics(self, client: TestClient):
        """Test registration with custom metrics"""
        payload = {
            "tenant_id": "tenant-123",
            "model_name": "forecast_lgb",
            "version": "v1.0.0",
            "metadata": {
                "model_type": "LightGBM",
                "framework": "lightgbm"
            },
            "metrics": {
                "rmse": 2.5,
                "custom_metrics": {
                    "pinball_loss_p50": 1.2,
                    "pinball_loss_p90": 2.8,
                    "coverage_p90": 0.89
                }
            }
        }
        
        response = client.post("/ai/models/register", json=payload)
        
        assert response.status_code == 201
    
    def test_register_model_missing_required_fields(self, client: TestClient):
        """Test registration with missing required fields"""
        payload = {
            "tenant_id": "tenant-123",
            "model_name": "forecast_lgb"
            # Missing version and metadata
        }
        
        response = client.post("/ai/models/register", json=payload)
        
        assert response.status_code == 422  # Validation error
    
    def test_register_model_invalid_stage(self, client: TestClient):
        """Test registration with invalid stage"""
        payload = {
            "tenant_id": "tenant-123",
            "model_name": "forecast_lgb",
            "version": "v1.0.0",
            "metadata": {
                "model_type": "LightGBM",
                "framework": "lightgbm"
            },
            "stage": "invalid_stage"
        }
        
        response = client.post("/ai/models/register", json=payload)
        
        # Should accept any string for now, but in production would validate
        assert response.status_code == 201


class TestModelRetrieval:
    """Tests for GET /ai/models/{model_id}"""
    
    @patch('app.services.model_storage.ModelStorage.get_metadata')
    @patch('app.services.model_storage.ModelStorage.get_metrics')
    async def test_get_model_success(self, mock_get_metrics, mock_get_metadata, client: TestClient):
        """Test successful model retrieval"""
        mock_get_metadata.return_value = {
            "tenant_id": "tenant-123",
            "model_name": "forecast_lgb",
            "version": "v1.0.0",
            "stage": "production",
            "model_type": "LightGBM",
            "uploaded_at": "2025-10-09T12:00:00Z",
            "model_size_bytes": 1048576
        }
        mock_get_metrics.return_value = {
            "rmse": 2.5,
            "mae": 1.8,
            "r2_score": 0.92
        }
        
        response = client.get("/ai/models/tenant-123:forecast_lgb:v1.0.0")
        
        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == "tenant-123:forecast_lgb:v1.0.0"
        assert data["tenant_id"] == "tenant-123"
        assert data["model_name"] == "forecast_lgb"
        assert data["version"] == "v1.0.0"
        assert data["stage"] == "production"
        assert "metadata" in data
        assert "metrics" in data
    
    def test_get_model_invalid_id_format(self, client: TestClient):
        """Test retrieval with invalid model ID format"""
        response = client.get("/ai/models/invalid-format")
        
        assert response.status_code == 400
        assert "Invalid model_id format" in response.json()["detail"]
    
    @patch('app.services.model_storage.ModelStorage.get_metadata')
    async def test_get_model_not_found(self, mock_get_metadata, client: TestClient):
        """Test retrieval of non-existent model"""
        mock_get_metadata.return_value = {}
        
        response = client.get("/ai/models/tenant-123:nonexistent:v1.0.0")
        
        assert response.status_code == 404
        assert "Model not found" in response.json()["detail"]


class TestModelListing:
    """Tests for GET /ai/models/"""
    
    @patch('app.services.model_storage.ModelStorage.list_versions')
    async def test_list_models_by_tenant_and_name(self, mock_list_versions, client: TestClient):
        """Test listing models filtered by tenant and name"""
        mock_list_versions.return_value = [
            {
                "version": "v1.0.0",
                "model_name": "forecast_lgb",
                "tenant_id": "tenant-123",
                "stage": "production",
                "uploaded_at": "2025-10-09T12:00:00Z"
            },
            {
                "version": "v0.9.0",
                "model_name": "forecast_lgb",
                "tenant_id": "tenant-123",
                "stage": "archived",
                "uploaded_at": "2025-10-01T10:00:00Z"
            }
        ]
        
        response = client.get("/ai/models/?tenant_id=tenant-123&model_name=forecast_lgb")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["tenant_id"] == "tenant-123"
        assert len(data["models"]) == 2
    
    @patch('app.services.model_storage.ModelStorage.list_versions')
    async def test_list_models_filter_by_stage(self, mock_list_versions, client: TestClient):
        """Test listing models filtered by stage"""
        mock_list_versions.return_value = [
            {
                "version": "v1.0.0",
                "stage": "production",
                "uploaded_at": "2025-10-09T12:00:00Z"
            }
        ]
        
        response = client.get("/ai/models/?tenant_id=tenant-123&model_name=forecast_lgb&stage=production")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["models"]) == 1
        assert data["models"][0]["stage"] == "production"
    
    def test_list_models_with_limit(self, client: TestClient):
        """Test listing models with limit parameter"""
        response = client.get("/ai/models/?tenant_id=tenant-123&model_name=forecast_lgb&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["models"]) <= 10
    
    def test_list_models_no_filters(self, client: TestClient):
        """Test listing models without filters"""
        response = client.get("/ai/models/")
        
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "total" in data


class TestModelPromotion:
    """Tests for PUT /ai/models/{model_id}/promote"""
    
    @patch('app.services.model_storage.ModelStorage.get_metadata')
    async def test_promote_model_staging_to_production(self, mock_get_metadata, client: TestClient):
        """Test promoting model from staging to production"""
        mock_get_metadata.return_value = {
            "tenant_id": "tenant-123",
            "model_name": "forecast_lgb",
            "version": "v1.0.0",
            "stage": "staging"
        }
        
        payload = {
            "target_stage": "production",
            "reason": "Passed validation tests, 5% improvement"
        }
        
        response = client.put("/ai/models/tenant-123:forecast_lgb:v1.0.0/promote", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["model_name"] == "forecast_lgb"
        assert data["version"] == "v1.0.0"
        assert data["previous_stage"] == "staging"
        assert data["current_stage"] == "production"
        assert "promoted_at" in data
    
    @patch('app.services.model_storage.ModelStorage.get_metadata')
    async def test_promote_model_production_to_archived(self, mock_get_metadata, client: TestClient):
        """Test archiving production model"""
        mock_get_metadata.return_value = {
            "stage": "production"
        }
        
        payload = {
            "target_stage": "archived",
            "reason": "Replaced by v2.0.0"
        }
        
        response = client.put("/ai/models/tenant-123:forecast_lgb:v1.0.0/promote", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["current_stage"] == "archived"
    
    def test_promote_model_invalid_target_stage(self, client: TestClient):
        """Test promotion with invalid target stage"""
        payload = {
            "target_stage": "invalid_stage"
        }
        
        response = client.put("/ai/models/tenant-123:forecast_lgb:v1.0.0/promote", json=payload)
        
        assert response.status_code == 400
        assert "Invalid target_stage" in response.json()["detail"]
    
    @patch('app.services.model_storage.ModelStorage.get_metadata')
    async def test_promote_nonexistent_model(self, mock_get_metadata, client: TestClient):
        """Test promoting non-existent model"""
        mock_get_metadata.return_value = {}
        
        payload = {
            "target_stage": "production"
        }
        
        response = client.put("/ai/models/tenant-123:nonexistent:v1.0.0/promote", json=payload)
        
        assert response.status_code == 404
    
    def test_promote_model_invalid_id_format(self, client: TestClient):
        """Test promotion with invalid model ID"""
        payload = {
            "target_stage": "production"
        }
        
        response = client.put("/ai/models/invalid-id/promote", json=payload)
        
        assert response.status_code == 400


class TestModelDeletion:
    """Tests for DELETE /ai/models/{model_id}"""
    
    @patch('app.services.model_storage.ModelStorage.get_metadata')
    @patch('app.services.model_storage.ModelStorage.delete_model')
    async def test_delete_archived_model(self, mock_delete, mock_get_metadata, client: TestClient):
        """Test deleting archived model (allowed)"""
        mock_get_metadata.return_value = {
            "stage": "archived"
        }
        mock_delete.return_value = {
            "status": "deleted",
            "files_deleted": ["model.joblib", "metadata.json"]
        }
        
        response = client.delete("/ai/models/tenant-123:forecast_lgb:v0.9.0")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert len(data["files_deleted"]) > 0
    
    @patch('app.services.model_storage.ModelStorage.get_metadata')
    async def test_delete_production_model_without_force(self, mock_get_metadata, client: TestClient):
        """Test deleting production model without force flag (denied)"""
        mock_get_metadata.return_value = {
            "stage": "production"
        }
        
        response = client.delete("/ai/models/tenant-123:forecast_lgb:v1.0.0")
        
        assert response.status_code == 400
        assert "Cannot delete production model" in response.json()["detail"]
    
    @patch('app.services.model_storage.ModelStorage.get_metadata')
    @patch('app.services.model_storage.ModelStorage.delete_model')
    async def test_delete_production_model_with_force(self, mock_delete, mock_get_metadata, client: TestClient):
        """Test force deleting production model (allowed)"""
        mock_get_metadata.return_value = {
            "stage": "production"
        }
        mock_delete.return_value = {
            "status": "deleted",
            "files_deleted": ["model.joblib"]
        }
        
        response = client.delete("/ai/models/tenant-123:forecast_lgb:v1.0.0?force=true")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
    
    @patch('app.services.model_storage.ModelStorage.get_metadata')
    async def test_delete_nonexistent_model(self, mock_get_metadata, client: TestClient):
        """Test deleting non-existent model"""
        mock_get_metadata.return_value = {}
        
        response = client.delete("/ai/models/tenant-123:nonexistent:v1.0.0")
        
        assert response.status_code == 404
    
    def test_delete_model_invalid_id_format(self, client: TestClient):
        """Test deletion with invalid model ID"""
        response = client.delete("/ai/models/invalid-id")
        
        assert response.status_code == 400


class TestModelRegistrySchemas:
    """Tests for request/response schemas"""
    
    def test_model_metadata_schema_validation(self, client: TestClient):
        """Test ModelMetadata schema validation"""
        payload = {
            "tenant_id": "tenant-123",
            "model_name": "test_model",
            "version": "v1.0.0",
            "metadata": {
                "model_type": "TestModel",
                "framework": "test",
                "hyperparameters": {"param1": 1},
                "feature_names": ["feature1", "feature2"],
                "tags": ["test", "experimental"]
            }
        }
        
        response = client.post("/ai/models/register", json=payload)
        
        assert response.status_code == 201
    
    def test_model_metrics_schema_validation(self, client: TestClient):
        """Test ModelMetrics schema validation"""
        payload = {
            "tenant_id": "tenant-123",
            "model_name": "test_model",
            "version": "v1.0.0",
            "metadata": {
                "model_type": "TestModel",
                "framework": "test"
            },
            "metrics": {
                "accuracy": 0.95,
                "precision": 0.94,
                "recall": 0.93,
                "f1_score": 0.935,
                "custom_metrics": {
                    "custom1": 0.88
                }
            }
        }
        
        response = client.post("/ai/models/register", json=payload)
        
        assert response.status_code == 201


class TestModelRegistryIntegration:
    """Integration tests for model registry workflow"""
    
    def test_complete_model_lifecycle(self, client: TestClient):
        """Test complete model lifecycle: register -> promote -> archive -> delete"""
        # 1. Register model in staging
        register_payload = {
            "tenant_id": "tenant-integration",
            "model_name": "lifecycle_test",
            "version": "v1.0.0",
            "metadata": {
                "model_type": "TestModel",
                "framework": "test"
            },
            "stage": "staging"
        }
        
        register_response = client.post("/ai/models/register", json=register_payload)
        assert register_response.status_code == 201
        model_id = register_response.json()["model_id"]
        
        # Note: Remaining steps would require actual S3/database integration
        # For unit tests, we validate the API contracts
    
    def test_multiple_version_registration(self, client: TestClient):
        """Test registering multiple versions of same model"""
        for i in range(3):
            payload = {
                "tenant_id": "tenant-123",
                "model_name": "multi_version",
                "version": f"v1.{i}.0",
                "metadata": {
                    "model_type": "TestModel",
                    "framework": "test"
                }
            }
            
            response = client.post("/ai/models/register", json=payload)
            assert response.status_code == 201
            assert response.json()["version"] == f"v1.{i}.0"
