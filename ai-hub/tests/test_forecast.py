"""
Tests for forecast API endpoints.
"""
import pytest
from fastapi import status
from datetime import datetime, timedelta
from unittest.mock import patch, Mock


@pytest.mark.unit
def test_forecast_endpoint_success(client, forecast_request_payload, auth_headers):
    """Test successful forecast generation"""
    response = client.post(
        "/ai/forecast",
        json=forecast_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert "forecast_id" in data
    assert data["tenant_id"] == forecast_request_payload["tenant_id"]
    assert data["asset_id"] == forecast_request_payload["asset_id"]
    assert "forecasts" in data
    assert "metadata" in data


@pytest.mark.unit
def test_forecast_endpoint_returns_correct_horizon(client, forecast_request_payload, auth_headers):
    """Test that forecast returns requested horizon"""
    forecast_request_payload["horizon_hours"] = 48
    
    response = client.post(
        "/ai/forecast",
        json=forecast_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert len(data["forecasts"]) == 48


@pytest.mark.unit
def test_forecast_endpoint_with_quantiles(client, forecast_request_payload, auth_headers):
    """Test forecast with probabilistic quantiles"""
    forecast_request_payload["include_quantiles"] = True
    
    response = client.post(
        "/ai/forecast",
        json=forecast_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Check first forecast point has quantiles
    first_forecast = data["forecasts"][0]
    assert "quantiles" in first_forecast
    assert "p10" in first_forecast["quantiles"]
    assert "p50" in first_forecast["quantiles"]
    assert "p90" in first_forecast["quantiles"]


@pytest.mark.unit
def test_forecast_endpoint_without_quantiles(client, forecast_request_payload, auth_headers):
    """Test forecast without probabilistic quantiles"""
    forecast_request_payload["include_quantiles"] = False
    
    response = client.post(
        "/ai/forecast",
        json=forecast_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Quantiles should be None
    first_forecast = data["forecasts"][0]
    assert first_forecast.get("quantiles") is None


@pytest.mark.unit
def test_forecast_endpoint_validates_horizon(client, forecast_request_payload, auth_headers):
    """Test that invalid horizon is rejected"""
    forecast_request_payload["horizon_hours"] = 200  # Exceeds max of 168
    
    response = client.post(
        "/ai/forecast",
        json=forecast_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.unit
def test_forecast_endpoint_validates_interval(client, forecast_request_payload, auth_headers):
    """Test that invalid interval is rejected"""
    forecast_request_payload["interval_minutes"] = 5  # Below min of 15
    
    response = client.post(
        "/ai/forecast",
        json=forecast_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.unit
def test_forecast_endpoint_missing_required_fields(client, auth_headers):
    """Test that missing required fields are rejected"""
    invalid_payload = {
        "tenant_id": "test-tenant",
        # Missing asset_id and forecast_type
    }
    
    response = client.post(
        "/ai/forecast",
        json=invalid_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.unit
def test_forecast_endpoint_metadata_structure(client, forecast_request_payload, auth_headers):
    """Test forecast metadata structure"""
    response = client.post(
        "/ai/forecast",
        json=forecast_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    metadata = data["metadata"]
    
    required_fields = [
        "generated_at",
        "model_name",
        "model_version",
        "features_used",
        "training_samples"
    ]
    
    for field in required_fields:
        assert field in metadata, f"Missing metadata field: {field}"


@pytest.mark.unit
def test_forecast_point_structure(client, forecast_request_payload, auth_headers):
    """Test individual forecast point structure"""
    response = client.post(
        "/ai/forecast",
        json=forecast_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    forecast_point = data["forecasts"][0]
    assert "timestamp" in forecast_point
    assert "point_forecast" in forecast_point
    assert "confidence" in forecast_point
    
    # Validate confidence is between 0 and 1
    assert 0.0 <= forecast_point["confidence"] <= 1.0


@pytest.mark.unit
def test_forecast_timestamps_sequential(client, forecast_request_payload, auth_headers):
    """Test that forecast timestamps are sequential"""
    response = client.post(
        "/ai/forecast",
        json=forecast_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    forecasts = data["forecasts"]
    for i in range(len(forecasts) - 1):
        t1 = datetime.fromisoformat(forecasts[i]["timestamp"].replace("Z", "+00:00"))
        t2 = datetime.fromisoformat(forecasts[i + 1]["timestamp"].replace("Z", "+00:00"))
        
        # Each timestamp should be 1 hour after previous (for 60 min interval)
        assert t2 > t1


@pytest.mark.unit
def test_forecast_quantiles_ordering(client, forecast_request_payload, auth_headers):
    """Test that quantiles are properly ordered (p10 < p50 < p90)"""
    forecast_request_payload["include_quantiles"] = True
    
    response = client.post(
        "/ai/forecast",
        json=forecast_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    for forecast in data["forecasts"]:
        if forecast.get("quantiles"):
            q = forecast["quantiles"]
            assert q["p10"] <= q["p50"] <= q["p90"]


@pytest.mark.unit
def test_forecast_different_types(client, forecast_request_payload, auth_headers):
    """Test forecasting different types (load, generation, price)"""
    forecast_types = ["load", "generation", "price"]
    
    for ftype in forecast_types:
        forecast_request_payload["forecast_type"] = ftype
        
        response = client.post(
            "/ai/forecast",
            json=forecast_request_payload,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.unit
def test_forecast_with_historical_data(client, forecast_request_payload, auth_headers, sample_timeseries):
    """Test forecast with provided historical data"""
    forecast_request_payload["historical_data"] = sample_timeseries[:24]
    
    response = client.post(
        "/ai/forecast",
        json=forecast_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.unit
def test_forecast_with_custom_model(client, forecast_request_payload, auth_headers):
    """Test forecast with specific model name"""
    forecast_request_payload["model_name"] = "custom_model_v2"
    
    response = client.post(
        "/ai/forecast",
        json=forecast_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert data["metadata"]["model_name"] == "custom_model_v2"


@pytest.mark.unit
def test_forecast_with_features(client, forecast_request_payload, auth_headers):
    """Test forecast with additional features"""
    forecast_request_payload["features"] = {
        "temperature": 22.5,
        "humidity": 65.0,
        "wind_speed": 5.2
    }
    
    response = client.post(
        "/ai/forecast",
        json=forecast_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.auth
def test_forecast_without_auth_fails(client, forecast_request_payload):
    """Test that forecast endpoint requires authentication"""
    # TODO: Uncomment when auth is implemented
    # response = client.post("/ai/forecast", json=forecast_request_payload)
    # assert response.status_code == status.HTTP_401_UNAUTHORIZED
    pass


@pytest.mark.auth
def test_forecast_tenant_id_mismatch_fails(client, forecast_request_payload, auth_headers):
    """Test that mismatched tenant_id is rejected"""
    # TODO: Uncomment when auth validation is implemented
    # forecast_request_payload["tenant_id"] = "different-tenant"
    # response = client.post(
    #     "/ai/forecast",
    #     json=forecast_request_payload,
    #     headers=auth_headers
    # )
    # assert response.status_code == status.HTTP_403_FORBIDDEN
    pass


@pytest.mark.unit
def test_get_forecast_by_id_not_implemented(client, auth_headers):
    """Test GET /ai/forecast/{id} endpoint"""
    response = client.get("/ai/forecast/test-id", headers=auth_headers)
    
    # Currently returns 501 Not Implemented
    assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED


@pytest.mark.unit
def test_list_forecasts_not_implemented(client, auth_headers):
    """Test GET /ai/forecasts endpoint"""
    response = client.get("/ai/forecasts", headers=auth_headers)
    
    # Currently returns 501 Not Implemented
    assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.ml
def test_forecast_performance(client, forecast_request_payload, auth_headers):
    """Test forecast generation performance"""
    import time
    
    start = time.time()
    response = client.post(
        "/ai/forecast",
        json=forecast_request_payload,
        headers=auth_headers
    )
    duration = time.time() - start
    
    assert response.status_code == status.HTTP_200_OK
    # Should complete in reasonable time (adjust threshold as needed)
    assert duration < 2.0  # 2 seconds


@pytest.mark.unit
def test_forecast_prediction_intervals(client, forecast_request_payload, auth_headers):
    """Test that prediction intervals are included"""
    response = client.post(
        "/ai/forecast",
        json=forecast_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    forecast_point = data["forecasts"][0]
    assert "prediction_interval_lower" in forecast_point
    assert "prediction_interval_upper" in forecast_point
    
    # Upper should be greater than lower
    if forecast_point["prediction_interval_lower"] is not None:
        assert forecast_point["prediction_interval_upper"] > forecast_point["prediction_interval_lower"]


@pytest.mark.unit
def test_forecast_unique_ids(client, forecast_request_payload, auth_headers):
    """Test that each forecast gets unique ID"""
    response1 = client.post(
        "/ai/forecast",
        json=forecast_request_payload,
        headers=auth_headers
    )
    
    response2 = client.post(
        "/ai/forecast",
        json=forecast_request_payload,
        headers=auth_headers
    )
    
    assert response1.status_code == status.HTTP_200_OK
    assert response2.status_code == status.HTTP_200_OK
    
    id1 = response1.json()["forecast_id"]
    id2 = response2.json()["forecast_id"]
    
    assert id1 != id2
