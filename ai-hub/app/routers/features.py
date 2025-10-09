"""
Features Router

Provides API endpoints for feature engineering and batch exports:
- Feature retrieval for specific assets
- Batch feature computation
- Parquet exports for offline training
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

from app.services import get_feature_store

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/ai/features", tags=["Features"])


# ============================================================================
# Schemas
# ============================================================================

class GetFeaturesRequest(BaseModel):
    """Request to get features for an asset"""
    tenant_id: str = Field(..., description="Tenant identifier")
    asset_id: str = Field(..., description="Asset identifier")
    timestamp: Optional[str] = Field(None, description="ISO timestamp (default: now)")
    lookback_hours: int = Field(168, description="Historical lookback in hours", ge=1, le=8760)
    feature_set: Optional[str] = Field(None, description="Predefined feature set name")
    feature_names: Optional[List[str]] = Field(None, description="Specific features to retrieve")


class GetFeaturesResponse(BaseModel):
    """Response with computed features"""
    tenant_id: str
    asset_id: str
    timestamp: str
    features: Dict[str, Any]
    feature_count: int
    computed_at: str


class ExportFeaturesRequest(BaseModel):
    """Request to export features to Parquet"""
    tenant_id: str = Field(..., description="Tenant identifier")
    feature_set: str = Field(..., description="Feature set name ('forecast_basic', 'anomaly_detection', etc.)")
    start_time: str = Field(..., description="Start timestamp (ISO format)")
    end_time: str = Field(..., description="End timestamp (ISO format)")
    asset_ids: Optional[List[str]] = Field(None, description="Specific assets (default: all)")
    output_path: Optional[str] = Field(None, description="Output path (default: auto-generated)")


class ExportFeaturesResponse(BaseModel):
    """Response for feature export"""
    export_id: str
    tenant_id: str
    feature_set: str
    start_time: str
    end_time: str
    status: str
    storage_path: str
    row_count: int
    file_size_bytes: int
    file_size_mb: float
    message: str


class ListExportsResponse(BaseModel):
    """Response for listing exports"""
    exports: List[Dict[str, Any]]
    total: int


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/get", response_model=GetFeaturesResponse)
async def get_features(request: GetFeaturesRequest):
    """
    Get computed features for a specific asset at a point in time.
    
    This endpoint is used for online inference - it returns features from the
    feature store with Redis caching for low latency (<100ms typical).
    
    **Feature Sets:**
    - `forecast_basic`: Hour, day, weekend, historical averages, lag features
    - `forecast_advanced`: + weather, advanced statistics
    - `anomaly_detection`: Statistical features optimized for anomaly detection
    
    **Example:**
    ```bash
    curl -X POST http://localhost:8003/ai/features/get \\
      -H "Content-Type: application/json" \\
      -d '{
        "tenant_id": "tenant-123",
        "asset_id": "meter-001",
        "feature_set": "forecast_basic",
        "lookback_hours": 168
      }'
    ```
    """
    try:
        # Parse timestamp if provided
        timestamp = None
        if request.timestamp:
            timestamp = datetime.fromisoformat(request.timestamp.replace('Z', '+00:00'))
        
        # Get feature store
        feature_store = get_feature_store()
        
        # Get features
        if request.feature_set:
            features = await feature_store.compute_feature_set(
                tenant_id=request.tenant_id,
                asset_id=request.asset_id,
                feature_set_name=request.feature_set,
                timestamp=timestamp
            )
        else:
            features = await feature_store.get_features(
                tenant_id=request.tenant_id,
                asset_id=request.asset_id,
                timestamp=timestamp,
                lookback_hours=request.lookback_hours,
                feature_names=request.feature_names
            )
        
        return GetFeaturesResponse(
            tenant_id=request.tenant_id,
            asset_id=request.asset_id,
            timestamp=features.get("_timestamp", datetime.utcnow().isoformat()),
            features=features,
            feature_count=len(features),
            computed_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error("get_features_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get features: {str(e)}"
        )


@router.post("/export", response_model=ExportFeaturesResponse, status_code=status.HTTP_202_ACCEPTED)
async def export_features(request: ExportFeaturesRequest):
    """
    Export features to Parquet format for offline model training.
    
    This endpoint queries TimescaleDB feature views and exports large datasets
    to Parquet files for batch training jobs. Files are stored in S3/MinIO
    and metadata is tracked in the database.
    
    **Supported Feature Sets:**
    - `forecast_basic`: Basic forecasting features
    - `forecast_advanced`: Advanced forecasting features with weather
    - `anomaly_detection`: Anomaly detection feature set
    
    **Example:**
    ```bash
    curl -X POST http://localhost:8003/ai/features/export \\
      -H "Content-Type: application/json" \\
      -d '{
        "tenant_id": "tenant-123",
        "feature_set": "forecast_basic",
        "start_time": "2024-01-01T00:00:00Z",
        "end_time": "2024-12-31T23:59:59Z",
        "asset_ids": ["meter-001", "meter-002"]
      }'
    ```
    
    **Returns:**
    HTTP 202 Accepted with export metadata. Check the `storage_path` for the
    resulting Parquet file.
    """
    try:
        # Parse timestamps
        start_time = datetime.fromisoformat(request.start_time.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(request.end_time.replace('Z', '+00:00'))
        
        # Validate time range
        if start_time >= end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_time must be before end_time"
            )
        
        # Get feature store
        feature_store = get_feature_store()
        
        # Export to Parquet
        export_result = await feature_store.export_features_to_parquet(
            tenant_id=request.tenant_id,
            feature_set=request.feature_set,
            start_time=start_time,
            end_time=end_time,
            asset_ids=request.asset_ids,
            output_path=request.output_path
        )
        
        if export_result.get("status") == "no_data":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No data found for the specified time range and feature set"
            )
        
        file_size_mb = export_result["file_size_bytes"] / (1024 * 1024)
        
        return ExportFeaturesResponse(
            export_id=export_result.get("export_id", "unknown"),
            tenant_id=request.tenant_id,
            feature_set=request.feature_set,
            start_time=request.start_time,
            end_time=request.end_time,
            status=export_result["status"],
            storage_path=export_result["storage_path"],
            row_count=export_result["row_count"],
            file_size_bytes=export_result["file_size_bytes"],
            file_size_mb=round(file_size_mb, 2),
            message=f"Exported {export_result['row_count']} rows to {export_result['storage_path']}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("export_features_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feature export failed: {str(e)}"
        )


@router.get("/exports", response_model=ListExportsResponse)
async def list_exports(
    tenant_id: Optional[str] = None,
    feature_set: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 50
):
    """
    List feature export jobs.
    
    Supports filtering by:
    - `tenant_id`: Filter by tenant
    - `feature_set`: Filter by feature set name
    - `status_filter`: Filter by status ('pending', 'processing', 'completed', 'failed')
    - `limit`: Maximum number of results (default: 50)
    
    **Example:**
    ```bash
    # List all exports for a tenant
    curl http://localhost:8003/ai/features/exports?tenant_id=tenant-123
    
    # List completed exports
    curl http://localhost:8003/ai/features/exports?status_filter=completed
    ```
    """
    try:
        # In production, this would query the feature_exports table
        # For MVP, return empty list
        
        logger.info(
            "list_exports",
            tenant_id=tenant_id,
            feature_set=feature_set,
            status_filter=status_filter
        )
        
        return ListExportsResponse(
            exports=[],
            total=0
        )
        
    except Exception as e:
        logger.error("list_exports_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list exports: {str(e)}"
        )


@router.get("/sets")
async def list_feature_sets():
    """
    List available feature sets.
    
    Returns metadata about predefined feature sets including:
    - Feature set name
    - Description
    - Feature names included
    - Use cases
    
    **Example:**
    ```bash
    curl http://localhost:8003/ai/features/sets
    ```
    """
    feature_sets = {
        "forecast_basic": {
            "name": "forecast_basic",
            "description": "Basic features for time series forecasting",
            "features": [
                "hour_of_day",
                "day_of_week",
                "is_weekend",
                "historical_avg_24h",
                "lag_1h",
                "lag_24h"
            ],
            "use_cases": ["Load forecasting", "Generation forecasting", "Price forecasting"],
            "latency": "< 50ms (online cache)",
            "storage": "TimescaleDB + Redis"
        },
        "forecast_advanced": {
            "name": "forecast_advanced",
            "description": "Advanced features with weather and statistics",
            "features": [
                "hour_of_day",
                "day_of_week",
                "day_of_month",
                "month",
                "is_weekend",
                "historical_avg_24h",
                "historical_std_24h",
                "lag_1h",
                "lag_24h",
                "lag_168h",
                "temperature",
                "humidity",
                "solar_irradiance"
            ],
            "use_cases": ["Advanced forecasting", "Multi-horizon prediction"],
            "latency": "< 100ms",
            "storage": "TimescaleDB + Redis + Weather API"
        },
        "anomaly_detection": {
            "name": "anomaly_detection",
            "description": "Features optimized for anomaly detection",
            "features": [
                "hour_of_day",
                "day_of_week",
                "historical_avg_24h",
                "historical_std_24h",
                "historical_min_24h",
                "historical_max_24h",
                "lag_1h"
            ],
            "use_cases": ["Real-time anomaly detection", "Outlier identification"],
            "latency": "< 50ms",
            "storage": "TimescaleDB + Redis"
        }
    }
    
    return {
        "feature_sets": feature_sets,
        "total": len(feature_sets)
    }
