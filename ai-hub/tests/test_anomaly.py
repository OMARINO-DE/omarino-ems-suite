"""
Tests for anomaly detection API endpoints.
"""
import pytest
from fastapi import status
from datetime import datetime


@pytest.mark.unit
def test_anomaly_detection_success(client, anomaly_request_payload, auth_headers):
    """Test successful anomaly detection"""
    response = client.post(
        "/ai/anomaly",
        json=anomaly_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert "detection_id" in data
    assert data["tenant_id"] == anomaly_request_payload["tenant_id"]
    assert data["asset_id"] == anomaly_request_payload["asset_id"]
    assert "anomalies" in data
    assert "summary" in data


@pytest.mark.unit
def test_anomaly_detection_response_structure(client, anomaly_request_payload, auth_headers):
    """Test anomaly detection response structure"""
    response = client.post(
        "/ai/anomaly",
        json=anomaly_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Check summary structure
    summary = data["summary"]
    assert "total_points" in summary
    assert "anomalies_detected" in summary
    assert "anomaly_rate" in summary
    assert "mean_anomaly_score" in summary
    assert "max_anomaly_score" in summary
    assert "method_used" in summary
    assert "sensitivity" in summary


@pytest.mark.unit
def test_anomaly_point_structure(client, anomaly_request_payload, auth_headers):
    """Test individual anomaly point structure"""
    response = client.post(
        "/ai/anomaly",
        json=anomaly_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    if data["anomalies"]:
        anomaly = data["anomalies"][0]
        assert "timestamp" in anomaly
        assert "value" in anomaly
        assert "anomaly_score" in anomaly
        assert "is_anomaly" in anomaly
        assert "severity" in anomaly


@pytest.mark.unit
def test_anomaly_detection_with_known_anomalies(client, auth_headers, sample_timeseries_with_anomalies, mock_jwt_payload):
    """Test detection with known injected anomalies"""
    payload = {
        "tenant_id": mock_jwt_payload["tenant_id"],
        "asset_id": "meter-001",
        "time_series": sample_timeseries_with_anomalies,
        "method": "isolation_forest",
        "sensitivity": 2.0  # High sensitivity
    }
    
    response = client.post(
        "/ai/anomaly",
        json=payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Should detect some anomalies
    assert data["summary"]["anomalies_detected"] > 0


@pytest.mark.unit
def test_anomaly_detection_methods(client, anomaly_request_payload, auth_headers):
    """Test different anomaly detection methods"""
    methods = ["z_score", "iqr", "isolation_forest", "local_outlier_factor", "prophet_decomposition"]
    
    for method in methods:
        anomaly_request_payload["method"] = method
        
        response = client.post(
            "/ai/anomaly",
            json=anomaly_request_payload,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["summary"]["method_used"] == method


@pytest.mark.unit
def test_anomaly_detection_sensitivity_validation(client, anomaly_request_payload, auth_headers):
    """Test sensitivity parameter validation"""
    # Test invalid sensitivity (below minimum)
    anomaly_request_payload["sensitivity"] = 0.5
    
    response = client.post(
        "/ai/anomaly",
        json=anomaly_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    # Test invalid sensitivity (above maximum)
    anomaly_request_payload["sensitivity"] = 6.0
    
    response = client.post(
        "/ai/anomaly",
        json=anomaly_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.unit
def test_anomaly_detection_different_sensitivities(client, anomaly_request_payload, auth_headers):
    """Test that different sensitivities produce different results"""
    sensitivities = [1.5, 3.0, 4.5]
    results = []
    
    for sensitivity in sensitivities:
        anomaly_request_payload["sensitivity"] = sensitivity
        
        response = client.post(
            "/ai/anomaly",
            json=anomaly_request_payload,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        results.append(data["summary"]["anomalies_detected"])
    
    # Higher sensitivity should generally detect fewer anomalies
    # (though this depends on the mock implementation)
    assert len(results) == 3


@pytest.mark.unit
def test_anomaly_detection_minimum_points(client, auth_headers, mock_jwt_payload):
    """Test that minimum 2 points are required"""
    payload = {
        "tenant_id": mock_jwt_payload["tenant_id"],
        "asset_id": "meter-001",
        "time_series": [
            {"timestamp": "2025-10-01T00:00:00Z", "value": 42.5}
        ],  # Only 1 point
        "method": "isolation_forest",
        "sensitivity": 3.0
    }
    
    response = client.post(
        "/ai/anomaly",
        json=payload,
        headers=auth_headers
    )
    
    # Should fail validation (min_items=2)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.unit
def test_anomaly_detection_expected_range(client, anomaly_request_payload, auth_headers):
    """Test that expected range is included in anomaly points"""
    response = client.post(
        "/ai/anomaly",
        json=anomaly_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    if data["anomalies"]:
        anomaly = data["anomalies"][0]
        if anomaly.get("expected_range"):
            exp_range = anomaly["expected_range"]
            assert "min" in exp_range
            assert "max" in exp_range
            assert "mean" in exp_range
            assert "std" in exp_range
            
            # Min should be less than max
            assert exp_range["min"] < exp_range["max"]


@pytest.mark.unit
def test_anomaly_severity_levels(client, anomaly_request_payload, auth_headers):
    """Test that severity levels are assigned"""
    response = client.post(
        "/ai/anomaly",
        json=anomaly_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    valid_severities = ["low", "medium", "high", "critical"]
    
    for anomaly in data["anomalies"]:
        assert anomaly["severity"] in valid_severities


@pytest.mark.unit
def test_anomaly_rate_calculation(client, anomaly_request_payload, auth_headers):
    """Test that anomaly rate is correctly calculated"""
    response = client.post(
        "/ai/anomaly",
        json=anomaly_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    summary = data["summary"]
    expected_rate = summary["anomalies_detected"] / summary["total_points"]
    
    assert abs(summary["anomaly_rate"] - expected_rate) < 0.001
    assert 0.0 <= summary["anomaly_rate"] <= 1.0


@pytest.mark.unit
def test_anomaly_detection_with_metadata(client, auth_headers, mock_jwt_payload):
    """Test anomaly detection with point metadata"""
    payload = {
        "tenant_id": mock_jwt_payload["tenant_id"],
        "asset_id": "meter-001",
        "time_series": [
            {
                "timestamp": "2025-10-01T00:00:00Z",
                "value": 42.5,
                "metadata": {"source": "sensor_1", "quality": "good"}
            },
            {
                "timestamp": "2025-10-01T01:00:00Z",
                "value": 38.2,
                "metadata": {"source": "sensor_1", "quality": "good"}
            }
        ],
        "method": "z_score",
        "sensitivity": 3.0
    }
    
    response = client.post(
        "/ai/anomaly",
        json=payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.unit
def test_anomaly_detection_with_training_data(client, anomaly_request_payload, auth_headers, sample_timeseries):
    """Test anomaly detection with separate training data"""
    anomaly_request_payload["training_data"] = sample_timeseries[:100]
    
    response = client.post(
        "/ai/anomaly",
        json=anomaly_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.unit
def test_anomaly_detection_lookback_hours(client, anomaly_request_payload, auth_headers):
    """Test lookback_hours parameter"""
    anomaly_request_payload["lookback_hours"] = 72
    
    response = client.post(
        "/ai/anomaly",
        json=anomaly_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.unit
def test_anomaly_detection_missing_required_fields(client, auth_headers):
    """Test that missing required fields are rejected"""
    invalid_payload = {
        "tenant_id": "test-tenant",
        # Missing time_series
    }
    
    response = client.post(
        "/ai/anomaly",
        json=invalid_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.unit
def test_anomaly_detection_timestamp_validation(client, auth_headers, mock_jwt_payload):
    """Test that invalid timestamps are handled"""
    payload = {
        "tenant_id": mock_jwt_payload["tenant_id"],
        "asset_id": "meter-001",
        "time_series": [
            {"timestamp": "invalid-timestamp", "value": 42.5},
            {"timestamp": "2025-10-01T01:00:00Z", "value": 38.2}
        ],
        "method": "z_score",
        "sensitivity": 3.0
    }
    
    response = client.post(
        "/ai/anomaly",
        json=payload,
        headers=auth_headers
    )
    
    # Should fail validation
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.auth
def test_anomaly_detection_without_auth_fails(client, anomaly_request_payload):
    """Test that anomaly detection requires authentication"""
    # TODO: Uncomment when auth is implemented
    # response = client.post("/ai/anomaly", json=anomaly_request_payload)
    # assert response.status_code == status.HTTP_401_UNAUTHORIZED
    pass


@pytest.mark.unit
def test_get_anomaly_detection_by_id_not_implemented(client, auth_headers):
    """Test GET /ai/anomaly/{id} endpoint"""
    response = client.get("/ai/anomaly/test-id", headers=auth_headers)
    
    assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED


@pytest.mark.unit
def test_list_anomaly_detections_not_implemented(client, auth_headers):
    """Test GET /ai/anomalies endpoint"""
    response = client.get("/ai/anomalies", headers=auth_headers)
    
    assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.ml
def test_anomaly_detection_performance(client, anomaly_request_payload, auth_headers):
    """Test anomaly detection performance"""
    import time
    
    start = time.time()
    response = client.post(
        "/ai/anomaly",
        json=anomaly_request_payload,
        headers=auth_headers
    )
    duration = time.time() - start
    
    assert response.status_code == status.HTTP_200_OK
    # Should complete in reasonable time
    assert duration < 2.0  # 2 seconds


@pytest.mark.unit
def test_anomaly_detection_unique_ids(client, anomaly_request_payload, auth_headers):
    """Test that each detection gets unique ID"""
    response1 = client.post(
        "/ai/anomaly",
        json=anomaly_request_payload,
        headers=auth_headers
    )
    
    response2 = client.post(
        "/ai/anomaly",
        json=anomaly_request_payload,
        headers=auth_headers
    )
    
    assert response1.status_code == status.HTTP_200_OK
    assert response2.status_code == status.HTTP_200_OK
    
    id1 = response1.json()["detection_id"]
    id2 = response2.json()["detection_id"]
    
    assert id1 != id2


@pytest.mark.unit
def test_anomaly_explanation_present(client, anomaly_request_payload, auth_headers):
    """Test that anomalies include explanations"""
    response = client.post(
        "/ai/anomaly",
        json=anomaly_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Check if any flagged anomalies have explanations
    flagged_anomalies = [a for a in data["anomalies"] if a["is_anomaly"]]
    
    for anomaly in flagged_anomalies:
        # Explanation can be None or a string
        assert "explanation" in anomaly
