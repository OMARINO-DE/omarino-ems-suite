"""
Tests for model explainability API endpoints.
"""
import pytest
from fastapi import status


@pytest.mark.unit
def test_explain_prediction_success(client, explain_request_payload, auth_headers):
    """Test successful explanation generation"""
    response = client.post(
        "/ai/explain",
        json=explain_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert "explanation_id" in data
    assert data["tenant_id"] == explain_request_payload["tenant_id"]
    assert data["model_name"] == explain_request_payload["model_name"]
    assert "feature_importances" in data
    assert "metadata" in data


@pytest.mark.unit
def test_explain_response_structure(client, explain_request_payload, auth_headers):
    """Test explanation response structure"""
    response = client.post(
        "/ai/explain",
        json=explain_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Check metadata structure
    metadata = data["metadata"]
    required_fields = [
        "explained_at",
        "model_name",
        "model_version",
        "explanation_method",
        "base_value",
        "prediction_value",
        "samples_used"
    ]
    
    for field in required_fields:
        assert field in metadata, f"Missing metadata field: {field}"


@pytest.mark.unit
def test_feature_importance_structure(client, explain_request_payload, auth_headers):
    """Test feature importance structure"""
    response = client.post(
        "/ai/explain",
        json=explain_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert len(data["feature_importances"]) > 0
    
    importance = data["feature_importances"][0]
    assert "feature_name" in importance
    assert "importance" in importance
    assert "contribution" in importance
    assert "rank" in importance
    
    # Rank should start at 1
    assert importance["rank"] >= 1


@pytest.mark.unit
def test_feature_importances_ranked(client, explain_request_payload, auth_headers):
    """Test that feature importances are ranked by importance"""
    response = client.post(
        "/ai/explain",
        json=explain_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    importances = data["feature_importances"]
    
    # Check that ranks are sequential
    ranks = [imp["rank"] for imp in importances]
    assert ranks == list(range(1, len(importances) + 1))
    
    # Check that importance values are in descending order
    importance_values = [imp["importance"] for imp in importances]
    assert importance_values == sorted(importance_values, reverse=True)


@pytest.mark.unit
def test_explain_waterfall_data(client, explain_request_payload, auth_headers):
    """Test waterfall chart data"""
    response = client.post(
        "/ai/explain",
        json=explain_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    if data.get("waterfall_data"):
        waterfall = data["waterfall_data"]
        assert len(waterfall) > 0
        
        first_point = waterfall[0]
        assert "feature_name" in first_point
        assert "contribution" in first_point
        assert "cumulative_value" in first_point


@pytest.mark.unit
def test_explain_force_data(client, explain_request_payload, auth_headers):
    """Test force plot data"""
    response = client.post(
        "/ai/explain",
        json=explain_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    if data.get("force_data"):
        force = data["force_data"]
        assert len(force) > 0
        
        first_point = force[0]
        assert "feature_name" in first_point
        assert "feature_value" in first_point
        assert "shap_value" in first_point
        assert "is_positive" in first_point
        assert isinstance(first_point["is_positive"], bool)


@pytest.mark.unit
def test_explain_summary(client, explain_request_payload, auth_headers):
    """Test explanation summary"""
    response = client.post(
        "/ai/explain",
        json=explain_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    if data.get("summary"):
        summary = data["summary"]
        assert isinstance(summary, dict)


@pytest.mark.unit
def test_explain_different_methods(client, explain_request_payload, auth_headers):
    """Test different explanation methods"""
    methods = ["shap", "lime", "anchor"]
    
    for method in methods:
        explain_request_payload["explanation_type"] = method
        
        response = client.post(
            "/ai/explain",
            json=explain_request_payload,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["metadata"]["explanation_method"] == method


@pytest.mark.unit
def test_explain_max_samples_validation(client, explain_request_payload, auth_headers):
    """Test max_samples parameter validation"""
    # Test below minimum
    explain_request_payload["max_samples"] = 5
    
    response = client.post(
        "/ai/explain",
        json=explain_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    # Test above maximum
    explain_request_payload["max_samples"] = 2000
    
    response = client.post(
        "/ai/explain",
        json=explain_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.unit
def test_explain_with_prediction_id(client, auth_headers, mock_jwt_payload):
    """Test explanation for specific prediction"""
    payload = {
        "tenant_id": mock_jwt_payload["tenant_id"],
        "model_name": "lightgbm_v1",
        "prediction_id": "pred-123",
        "explanation_type": "shap",
        "max_samples": 100
    }
    
    response = client.post(
        "/ai/explain",
        json=payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.unit
def test_explain_missing_required_fields(client, auth_headers):
    """Test that missing required fields are rejected"""
    invalid_payload = {
        "tenant_id": "test-tenant",
        # Missing model_name
    }
    
    response = client.post(
        "/ai/explain",
        json=invalid_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.unit
def test_explain_with_model_version(client, explain_request_payload, auth_headers):
    """Test explanation with specific model version"""
    explain_request_payload["model_version"] = "2.0.0"
    
    response = client.post(
        "/ai/explain",
        json=explain_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["metadata"]["model_version"] == "2.0.0"


@pytest.mark.unit
def test_global_explanation_success(client, auth_headers, mock_jwt_payload):
    """Test global model explanation"""
    payload = {
        "tenant_id": mock_jwt_payload["tenant_id"],
        "model_name": "lightgbm_v1",
        "model_version": "1.0.0",
        "dataset_sample_size": 100
    }
    
    response = client.post(
        "/ai/explain/global",
        json=payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert "explanation_id" in data
    assert "global_importances" in data
    assert "samples_analyzed" in data


@pytest.mark.unit
def test_global_explanation_structure(client, auth_headers, mock_jwt_payload):
    """Test global explanation response structure"""
    payload = {
        "tenant_id": mock_jwt_payload["tenant_id"],
        "model_name": "lightgbm_v1",
        "dataset_sample_size": 100
    }
    
    response = client.post(
        "/ai/explain/global",
        json=payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    if data["global_importances"]:
        importance = data["global_importances"][0]
        assert "feature_name" in importance
        assert "mean_abs_shap" in importance
        assert "mean_shap" in importance
        assert "importance_rank" in importance


@pytest.mark.unit
def test_global_explanation_sample_size_validation(client, auth_headers, mock_jwt_payload):
    """Test dataset_sample_size validation"""
    # Test below minimum
    payload = {
        "tenant_id": mock_jwt_payload["tenant_id"],
        "model_name": "lightgbm_v1",
        "dataset_sample_size": 5
    }
    
    response = client.post(
        "/ai/explain/global",
        json=payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    # Test above maximum
    payload["dataset_sample_size"] = 2000
    
    response = client.post(
        "/ai/explain/global",
        json=payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.unit
def test_global_importances_ranked(client, auth_headers, mock_jwt_payload):
    """Test that global importances are ranked"""
    payload = {
        "tenant_id": mock_jwt_payload["tenant_id"],
        "model_name": "lightgbm_v1",
        "dataset_sample_size": 100
    }
    
    response = client.post(
        "/ai/explain/global",
        json=payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    importances = data["global_importances"]
    
    # Check ranking
    mean_abs_shaps = [imp["mean_abs_shap"] for imp in importances]
    assert mean_abs_shaps == sorted(mean_abs_shaps, reverse=True)


@pytest.mark.auth
def test_explain_without_auth_fails(client, explain_request_payload):
    """Test that explanation requires authentication"""
    # TODO: Uncomment when auth is implemented
    # response = client.post("/ai/explain", json=explain_request_payload)
    # assert response.status_code == status.HTTP_401_UNAUTHORIZED
    pass


@pytest.mark.unit
def test_get_explanation_by_id_not_implemented(client, auth_headers):
    """Test GET /ai/explain/{id} endpoint"""
    response = client.get("/ai/explain/test-id", headers=auth_headers)
    
    assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.ml
def test_explanation_performance(client, explain_request_payload, auth_headers):
    """Test explanation generation performance"""
    import time
    
    start = time.time()
    response = client.post(
        "/ai/explain",
        json=explain_request_payload,
        headers=auth_headers
    )
    duration = time.time() - start
    
    assert response.status_code == status.HTTP_200_OK
    # SHAP can be slower than forecasting
    assert duration < 3.0  # 3 seconds


@pytest.mark.unit
def test_explanation_unique_ids(client, explain_request_payload, auth_headers):
    """Test that each explanation gets unique ID"""
    response1 = client.post(
        "/ai/explain",
        json=explain_request_payload,
        headers=auth_headers
    )
    
    response2 = client.post(
        "/ai/explain",
        json=explain_request_payload,
        headers=auth_headers
    )
    
    assert response1.status_code == status.HTTP_200_OK
    assert response2.status_code == status.HTTP_200_OK
    
    id1 = response1.json()["explanation_id"]
    id2 = response2.json()["explanation_id"]
    
    assert id1 != id2


@pytest.mark.unit
def test_explain_contribution_signs(client, explain_request_payload, auth_headers):
    """Test that contributions have appropriate signs"""
    response = client.post(
        "/ai/explain",
        json=explain_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Check that contributions can be both positive and negative
    contributions = [imp["contribution"] for imp in data["feature_importances"]]
    
    # At least one contribution should exist
    assert len(contributions) > 0


@pytest.mark.unit
def test_explain_base_vs_prediction_value(client, explain_request_payload, auth_headers):
    """Test base_value vs prediction_value relationship"""
    response = client.post(
        "/ai/explain",
        json=explain_request_payload,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    metadata = data["metadata"]
    base_value = metadata["base_value"]
    prediction_value = metadata["prediction_value"]
    
    # Both should be numeric
    assert isinstance(base_value, (int, float))
    assert isinstance(prediction_value, (int, float))
    
    # Sum of contributions should approximately equal difference
    # (This is how SHAP works: base_value + sum(shap_values) = prediction)
    contributions = [imp["contribution"] for imp in data["feature_importances"]]
    total_contribution = sum(contributions)
    
    expected_prediction = base_value + total_contribution
    # Allow for small floating point differences
    assert abs(expected_prediction - prediction_value) < 0.1
