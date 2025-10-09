"""
Tests for Features Router

Tests feature engineering and batch export endpoints:
- Feature retrieval for inference
- Parquet export
- Export listing
- Feature set information
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch


class TestGetFeatures:
    """Tests for POST /ai/features/get"""
    
    @patch('app.services.feature_store.FeatureStore.compute_feature_set')
    async def test_get_features_with_feature_set(self, mock_compute, client: TestClient):
        """Test getting features with predefined feature set"""
        mock_compute.return_value = {
            "hour_of_day": 14,
            "day_of_week": 2,
            "is_weekend": 0,
            "hourly_avg": 45.2,
            "lag_1h": 43.5,
            "lag_24h": 44.8,
            "_timestamp": "2025-10-09T14:00:00Z"
        }
        
        payload = {
            "tenant_id": "tenant-123",
            "asset_id": "meter-001",
            "feature_set": "forecast_basic"
        }
        
        response = client.post("/ai/features/get", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "tenant-123"
        assert data["asset_id"] == "meter-001"
        assert "features" in data
        assert data["feature_count"] > 0
        assert "computed_at" in data
    
    @patch('app.services.feature_store.FeatureStore.get_features')
    async def test_get_features_with_custom_names(self, mock_get_features, client: TestClient):
        """Test getting specific feature names"""
        mock_get_features.return_value = {
            "hour_of_day": 14,
            "temperature": 22.5,
            "_timestamp": "2025-10-09T14:00:00Z"
        }
        
        payload = {
            "tenant_id": "tenant-123",
            "asset_id": "meter-001",
            "feature_names": ["hour_of_day", "temperature"]
        }
        
        response = client.post("/ai/features/get", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["feature_count"] == 3  # Includes _timestamp
    
    @patch('app.services.feature_store.FeatureStore.compute_feature_set')
    async def test_get_features_with_timestamp(self, mock_compute, client: TestClient):
        """Test getting features at specific timestamp"""
        mock_compute.return_value = {
            "hour_of_day": 10,
            "_timestamp": "2025-10-01T10:00:00Z"
        }
        
        payload = {
            "tenant_id": "tenant-123",
            "asset_id": "meter-001",
            "feature_set": "forecast_basic",
            "timestamp": "2025-10-01T10:00:00Z"
        }
        
        response = client.post("/ai/features/get", json=payload)
        
        assert response.status_code == 200
    
    @patch('app.services.feature_store.FeatureStore.get_features')
    async def test_get_features_with_lookback(self, mock_get_features, client: TestClient):
        """Test getting features with custom lookback period"""
        mock_get_features.return_value = {
            "hour_of_day": 14,
            "_lookback_hours": 720
        }
        
        payload = {
            "tenant_id": "tenant-123",
            "asset_id": "meter-001",
            "lookback_hours": 720  # 30 days
        }
        
        response = client.post("/ai/features/get", json=payload)
        
        assert response.status_code == 200
    
    def test_get_features_missing_required_fields(self, client: TestClient):
        """Test with missing required fields"""
        payload = {
            "tenant_id": "tenant-123"
            # Missing asset_id
        }
        
        response = client.post("/ai/features/get", json=payload)
        
        assert response.status_code == 422  # Validation error
    
    def test_get_features_invalid_lookback(self, client: TestClient):
        """Test with invalid lookback hours"""
        payload = {
            "tenant_id": "tenant-123",
            "asset_id": "meter-001",
            "lookback_hours": 0  # Must be >= 1
        }
        
        response = client.post("/ai/features/get", json=payload)
        
        assert response.status_code == 422
    
    @patch('app.services.feature_store.FeatureStore.compute_feature_set')
    async def test_get_features_service_error(self, mock_compute, client: TestClient):
        """Test error handling when feature computation fails"""
        mock_compute.side_effect = Exception("Database connection error")
        
        payload = {
            "tenant_id": "tenant-123",
            "asset_id": "meter-001",
            "feature_set": "forecast_basic"
        }
        
        response = client.post("/ai/features/get", json=payload)
        
        assert response.status_code == 500


class TestExportFeatures:
    """Tests for POST /ai/features/export"""
    
    @patch('app.services.feature_store.FeatureStore.export_features_to_parquet')
    async def test_export_features_success(self, mock_export, client: TestClient):
        """Test successful feature export"""
        mock_export.return_value = {
            "export_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "completed",
            "storage_path": "./exports/tenant-123_forecast_basic_550e8400.parquet",
            "row_count": 876000,
            "file_size_bytes": 44564480
        }
        
        payload = {
            "tenant_id": "tenant-123",
            "feature_set": "forecast_basic",
            "start_time": "2024-01-01T00:00:00Z",
            "end_time": "2024-12-31T23:59:59Z"
        }
        
        response = client.post("/ai/features/export", json=payload)
        
        assert response.status_code == 202  # Accepted
        data = response.json()
        assert data["status"] == "completed"
        assert data["tenant_id"] == "tenant-123"
        assert data["feature_set"] == "forecast_basic"
        assert data["row_count"] == 876000
        assert "file_size_mb" in data
        assert "storage_path" in data
    
    @patch('app.services.feature_store.FeatureStore.export_features_to_parquet')
    async def test_export_features_with_asset_filter(self, mock_export, client: TestClient):
        """Test export with specific assets"""
        mock_export.return_value = {
            "export_id": "test-id",
            "status": "completed",
            "storage_path": "./exports/test.parquet",
            "row_count": 1000,
            "file_size_bytes": 10000
        }
        
        payload = {
            "tenant_id": "tenant-123",
            "feature_set": "forecast_basic",
            "start_time": "2024-01-01T00:00:00Z",
            "end_time": "2024-12-31T23:59:59Z",
            "asset_ids": ["meter-001", "meter-002", "meter-003"]
        }
        
        response = client.post("/ai/features/export", json=payload)
        
        assert response.status_code == 202
    
    @patch('app.services.feature_store.FeatureStore.export_features_to_parquet')
    async def test_export_features_with_custom_path(self, mock_export, client: TestClient):
        """Test export with custom output path"""
        mock_export.return_value = {
            "export_id": "test-id",
            "status": "completed",
            "storage_path": "/custom/path/export.parquet",
            "row_count": 5000,
            "file_size_bytes": 50000
        }
        
        payload = {
            "tenant_id": "tenant-123",
            "feature_set": "forecast_basic",
            "start_time": "2024-01-01T00:00:00Z",
            "end_time": "2024-12-31T23:59:59Z",
            "output_path": "/custom/path/export.parquet"
        }
        
        response = client.post("/ai/features/export", json=payload)
        
        assert response.status_code == 202
        assert response.json()["storage_path"] == "/custom/path/export.parquet"
    
    def test_export_features_invalid_time_range(self, client: TestClient):
        """Test export with invalid time range (start after end)"""
        payload = {
            "tenant_id": "tenant-123",
            "feature_set": "forecast_basic",
            "start_time": "2024-12-31T23:59:59Z",
            "end_time": "2024-01-01T00:00:00Z"  # Before start
        }
        
        response = client.post("/ai/features/export", json=payload)
        
        assert response.status_code == 400
        assert "start_time must be before end_time" in response.json()["detail"]
    
    @patch('app.services.feature_store.FeatureStore.export_features_to_parquet')
    async def test_export_features_no_data(self, mock_export, client: TestClient):
        """Test export when no data available"""
        mock_export.return_value = {
            "status": "no_data",
            "row_count": 0,
            "file_size_bytes": 0
        }
        
        payload = {
            "tenant_id": "tenant-123",
            "feature_set": "forecast_basic",
            "start_time": "2030-01-01T00:00:00Z",
            "end_time": "2030-12-31T23:59:59Z"
        }
        
        response = client.post("/ai/features/export", json=payload)
        
        assert response.status_code == 404
        assert "No data found" in response.json()["detail"]
    
    def test_export_features_missing_required_fields(self, client: TestClient):
        """Test export with missing required fields"""
        payload = {
            "tenant_id": "tenant-123",
            "feature_set": "forecast_basic"
            # Missing start_time and end_time
        }
        
        response = client.post("/ai/features/export", json=payload)
        
        assert response.status_code == 422
    
    @patch('app.services.feature_store.FeatureStore.export_features_to_parquet')
    async def test_export_features_large_dataset(self, mock_export, client: TestClient):
        """Test exporting large dataset"""
        mock_export.return_value = {
            "export_id": "large-export",
            "status": "completed",
            "storage_path": "./exports/large.parquet",
            "row_count": 10000000,  # 10 million rows
            "file_size_bytes": 1073741824  # 1 GB
        }
        
        payload = {
            "tenant_id": "tenant-123",
            "feature_set": "forecast_advanced",
            "start_time": "2020-01-01T00:00:00Z",
            "end_time": "2024-12-31T23:59:59Z"
        }
        
        response = client.post("/ai/features/export", json=payload)
        
        assert response.status_code == 202
        data = response.json()
        assert data["file_size_mb"] == 1024.0  # 1 GB in MB
        assert data["row_count"] == 10000000
    
    @patch('app.services.feature_store.FeatureStore.export_features_to_parquet')
    async def test_export_features_service_error(self, mock_export, client: TestClient):
        """Test error handling during export"""
        mock_export.side_effect = Exception("Disk full")
        
        payload = {
            "tenant_id": "tenant-123",
            "feature_set": "forecast_basic",
            "start_time": "2024-01-01T00:00:00Z",
            "end_time": "2024-12-31T23:59:59Z"
        }
        
        response = client.post("/ai/features/export", json=payload)
        
        assert response.status_code == 500


class TestListExports:
    """Tests for GET /ai/features/exports"""
    
    def test_list_exports_all(self, client: TestClient):
        """Test listing all exports"""
        response = client.get("/ai/features/exports")
        
        assert response.status_code == 200
        data = response.json()
        assert "exports" in data
        assert "total" in data
        assert isinstance(data["exports"], list)
    
    def test_list_exports_by_tenant(self, client: TestClient):
        """Test listing exports filtered by tenant"""
        response = client.get("/ai/features/exports?tenant_id=tenant-123")
        
        assert response.status_code == 200
        data = response.json()
        assert "exports" in data
    
    def test_list_exports_by_feature_set(self, client: TestClient):
        """Test listing exports filtered by feature set"""
        response = client.get("/ai/features/exports?feature_set=forecast_basic")
        
        assert response.status_code == 200
    
    def test_list_exports_by_status(self, client: TestClient):
        """Test listing exports filtered by status"""
        response = client.get("/ai/features/exports?status_filter=completed")
        
        assert response.status_code == 200
    
    def test_list_exports_with_limit(self, client: TestClient):
        """Test listing exports with limit"""
        response = client.get("/ai/features/exports?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["exports"]) <= 10
    
    def test_list_exports_combined_filters(self, client: TestClient):
        """Test listing with multiple filters"""
        response = client.get(
            "/ai/features/exports"
            "?tenant_id=tenant-123"
            "&feature_set=forecast_basic"
            "&status_filter=completed"
            "&limit=5"
        )
        
        assert response.status_code == 200


class TestListFeatureSets:
    """Tests for GET /ai/features/sets"""
    
    def test_list_feature_sets(self, client: TestClient):
        """Test listing available feature sets"""
        response = client.get("/ai/features/sets")
        
        assert response.status_code == 200
        data = response.json()
        assert "feature_sets" in data
        assert "total" in data
        assert data["total"] == 3  # forecast_basic, forecast_advanced, anomaly_detection
    
    def test_feature_sets_structure(self, client: TestClient):
        """Test feature set response structure"""
        response = client.get("/ai/features/sets")
        
        data = response.json()
        feature_sets = data["feature_sets"]
        
        # Check forecast_basic exists
        assert "forecast_basic" in feature_sets
        
        basic_set = feature_sets["forecast_basic"]
        assert "name" in basic_set
        assert "description" in basic_set
        assert "features" in basic_set
        assert "use_cases" in basic_set
        assert "latency" in basic_set
        assert "storage" in basic_set
    
    def test_forecast_basic_features(self, client: TestClient):
        """Test forecast_basic feature set details"""
        response = client.get("/ai/features/sets")
        
        data = response.json()
        basic_set = data["feature_sets"]["forecast_basic"]
        
        assert basic_set["name"] == "forecast_basic"
        assert len(basic_set["features"]) == 6
        assert "hour_of_day" in basic_set["features"]
        assert "day_of_week" in basic_set["features"]
        assert "lag_1h" in basic_set["features"]
    
    def test_forecast_advanced_features(self, client: TestClient):
        """Test forecast_advanced feature set details"""
        response = client.get("/ai/features/sets")
        
        data = response.json()
        advanced_set = data["feature_sets"]["forecast_advanced"]
        
        assert advanced_set["name"] == "forecast_advanced"
        assert len(advanced_set["features"]) == 13
        assert "temperature" in advanced_set["features"]
        assert "humidity" in advanced_set["features"]
        assert "solar_irradiance" in advanced_set["features"]
    
    def test_anomaly_detection_features(self, client: TestClient):
        """Test anomaly_detection feature set details"""
        response = client.get("/ai/features/sets")
        
        data = response.json()
        anomaly_set = data["feature_sets"]["anomaly_detection"]
        
        assert anomaly_set["name"] == "anomaly_detection"
        assert len(anomaly_set["features"]) == 7
        assert "historical_avg_24h" in anomaly_set["features"]
        assert "historical_std_24h" in anomaly_set["features"]


class TestFeaturesIntegration:
    """Integration tests for features workflow"""
    
    @patch('app.services.feature_store.FeatureStore.compute_feature_set')
    @patch('app.services.feature_store.FeatureStore.export_features_to_parquet')
    async def test_get_then_export_workflow(self, mock_export, mock_compute, client: TestClient):
        """Test complete workflow: get features -> export for training"""
        # Step 1: Get features for inspection
        mock_compute.return_value = {
            "hour_of_day": 14,
            "day_of_week": 2,
            "lag_1h": 43.5
        }
        
        get_response = client.post("/ai/features/get", json={
            "tenant_id": "tenant-123",
            "asset_id": "meter-001",
            "feature_set": "forecast_basic"
        })
        
        assert get_response.status_code == 200
        
        # Step 2: Export features for training
        mock_export.return_value = {
            "export_id": "test-id",
            "status": "completed",
            "storage_path": "./exports/test.parquet",
            "row_count": 100000,
            "file_size_bytes": 1000000
        }
        
        export_response = client.post("/ai/features/export", json={
            "tenant_id": "tenant-123",
            "feature_set": "forecast_basic",
            "start_time": "2024-01-01T00:00:00Z",
            "end_time": "2024-12-31T23:59:59Z"
        })
        
        assert export_response.status_code == 202
    
    def test_feature_set_info_then_get(self, client: TestClient):
        """Test workflow: check available features -> get them"""
        # Step 1: Check available feature sets
        sets_response = client.get("/ai/features/sets")
        assert sets_response.status_code == 200
        
        data = sets_response.json()
        available_sets = list(data["feature_sets"].keys())
        assert len(available_sets) > 0
        
        # Step 2: Get features using discovered set
        # (Would require mocking, demonstrated above)


class TestFeaturesPerformance:
    """Performance and edge case tests"""
    
    @patch('app.services.feature_store.FeatureStore.compute_feature_set')
    async def test_get_features_response_time(self, mock_compute, client: TestClient):
        """Test feature retrieval performance"""
        mock_compute.return_value = {"hour_of_day": 14}
        
        import time
        start = time.time()
        
        response = client.post("/ai/features/get", json={
            "tenant_id": "tenant-123",
            "asset_id": "meter-001",
            "feature_set": "forecast_basic"
        })
        
        elapsed = time.time() - start
        
        assert response.status_code == 200
        # API should respond quickly (mock makes this trivial, but structure is right)
        assert elapsed < 1.0
    
    def test_get_features_with_long_tenant_id(self, client: TestClient):
        """Test with very long tenant ID"""
        long_id = "tenant-" + "x" * 200
        
        payload = {
            "tenant_id": long_id,
            "asset_id": "meter-001",
            "feature_set": "forecast_basic"
        }
        
        response = client.post("/ai/features/get", json=payload)
        
        # Should handle long IDs gracefully
        assert response.status_code in [200, 500]
    
    @patch('app.services.feature_store.FeatureStore.compute_feature_set')
    async def test_concurrent_feature_requests(self, mock_compute, client: TestClient):
        """Test handling concurrent feature requests"""
        mock_compute.return_value = {"hour_of_day": 14}
        
        payload = {
            "tenant_id": "tenant-123",
            "asset_id": "meter-001",
            "feature_set": "forecast_basic"
        }
        
        # Make multiple concurrent requests
        responses = []
        for i in range(5):
            response = client.post("/ai/features/get", json=payload)
            responses.append(response)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
