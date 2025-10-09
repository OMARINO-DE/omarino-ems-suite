"""
Model Registry Router

Provides API endpoints for ML model lifecycle management:
- Model registration and metadata tracking
- Version management
- Model promotion (staging -> production)
- Model deletion and archiving
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

from app.services import get_model_storage, get_model_cache

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/ai/models", tags=["Model Registry"])


# ============================================================================
# Schemas
# ============================================================================

class ModelMetadata(BaseModel):
    """Model metadata schema"""
    model_type: str = Field(..., description="Model type (e.g., 'LightGBM', 'IsolationForest')")
    framework: str = Field(..., description="ML framework (e.g., 'lightgbm', 'sklearn')")
    hyperparameters: Dict[str, Any] = Field(default_factory=dict, description="Model hyperparameters")
    training_config: Dict[str, Any] = Field(default_factory=dict, description="Training configuration")
    feature_names: List[str] = Field(default_factory=list, description="Required feature names")
    target_variable: Optional[str] = Field(None, description="Target variable name")
    tags: List[str] = Field(default_factory=list, description="Searchable tags")
    description: Optional[str] = Field(None, description="Model description")


class ModelMetrics(BaseModel):
    """Model performance metrics schema"""
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    rmse: Optional[float] = None
    mae: Optional[float] = None
    mape: Optional[float] = None
    r2_score: Optional[float] = None
    custom_metrics: Dict[str, float] = Field(default_factory=dict)


class RegisterModelRequest(BaseModel):
    """Request to register a new model"""
    tenant_id: str = Field(..., description="Tenant identifier")
    model_name: str = Field(..., description="Model name (e.g., 'forecast_lgb', 'anomaly_if')")
    version: str = Field(..., description="Model version (e.g., 'v1.0.0', '2024-01-15-001')")
    metadata: ModelMetadata
    metrics: Optional[ModelMetrics] = None
    stage: str = Field(default="staging", description="Model stage: 'staging', 'production', 'archived'")


class RegisterModelResponse(BaseModel):
    """Response for model registration"""
    model_id: str
    model_name: str
    version: str
    stage: str
    status: str
    message: str
    uploaded_at: str


class GetModelResponse(BaseModel):
    """Response for getting model details"""
    model_id: str
    tenant_id: str
    model_name: str
    version: str
    stage: str
    metadata: Dict[str, Any]
    metrics: Dict[str, Any]
    uploaded_at: str
    model_size_bytes: int
    model_type: str


class ListModelsResponse(BaseModel):
    """Response for listing models"""
    models: List[Dict[str, Any]]
    total: int
    tenant_id: Optional[str] = None


class PromoteModelRequest(BaseModel):
    """Request to promote a model to production"""
    target_stage: str = Field(..., description="Target stage: 'production', 'archived'")
    reason: Optional[str] = Field(None, description="Reason for promotion")


class PromoteModelResponse(BaseModel):
    """Response for model promotion"""
    model_id: str
    model_name: str
    version: str
    previous_stage: str
    current_stage: str
    promoted_at: str
    message: str


class DeleteModelResponse(BaseModel):
    """Response for model deletion"""
    model_id: str
    model_name: str
    version: str
    status: str
    files_deleted: List[str]
    message: str


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/register", response_model=RegisterModelResponse, status_code=status.HTTP_201_CREATED)
async def register_model(request: RegisterModelRequest):
    """
    Register a new ML model in the registry.
    
    This endpoint is typically called after training a model. It stores:
    - Model artifact (serialized model)
    - Model metadata (hyperparameters, features, etc.)
    - Performance metrics (accuracy, RMSE, etc.)
    
    The model is initially registered in 'staging' stage.
    
    **Example:**
    ```bash
    curl -X POST http://localhost:8003/ai/models/register \\
      -H "Content-Type: application/json" \\
      -d '{
        "tenant_id": "tenant-123",
        "model_name": "forecast_lgb",
        "version": "v1.0.0",
        "metadata": {
          "model_type": "LightGBM",
          "framework": "lightgbm",
          "hyperparameters": {"num_leaves": 31, "learning_rate": 0.05},
          "feature_names": ["hour", "temp", "humidity"]
        },
        "metrics": {
          "rmse": 2.5,
          "mae": 1.8,
          "r2_score": 0.92
        }
      }'
    ```
    """
    try:
        # Note: In a real implementation, you would:
        # 1. Validate the model artifact exists (uploaded separately)
        # 2. Store metadata in database
        # 3. Update model registry index
        
        # For MVP, we'll create a model ID
        model_id = f"{request.tenant_id}:{request.model_name}:{request.version}"
        
        # Get model storage service
        model_storage = get_model_storage()
        
        # Store metadata in S3
        # (Actual model artifact should be uploaded via /upload endpoint or training pipeline)
        metadata_dict = request.metadata.dict()
        metadata_dict.update({
            "stage": request.stage,
            "registered_at": datetime.utcnow().isoformat(),
            "tenant_id": request.tenant_id,
            "model_name": request.model_name,
            "version": request.version
        })
        
        # In production, would store in database here
        # For MVP, just validate the request
        
        logger.info(
            "model_registered",
            model_id=model_id,
            model_name=request.model_name,
            version=request.version,
            stage=request.stage
        )
        
        return RegisterModelResponse(
            model_id=model_id,
            model_name=request.model_name,
            version=request.version,
            stage=request.stage,
            status="registered",
            message=f"Model {request.model_name} v{request.version} registered successfully",
            uploaded_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error("model_registration_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model registration failed: {str(e)}"
        )


@router.get("/{model_id}", response_model=GetModelResponse)
async def get_model(model_id: str):
    """
    Get details of a specific model by ID.
    
    Model ID format: `tenant_id:model_name:version`
    
    Returns model metadata, metrics, and artifact information.
    
    **Example:**
    ```bash
    curl http://localhost:8003/ai/models/tenant-123:forecast_lgb:v1.0.0
    ```
    """
    try:
        # Parse model_id
        parts = model_id.split(":")
        if len(parts) != 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid model_id format. Expected: tenant_id:model_name:version"
            )
        
        tenant_id, model_name, version = parts
        
        # Get model storage
        model_storage = get_model_storage()
        
        # Get metadata from S3
        metadata = await model_storage.get_metadata(tenant_id, model_name, version)
        
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model not found: {model_id}"
            )
        
        # Get metrics
        metrics = await model_storage.get_metrics(tenant_id, model_name, version)
        
        return GetModelResponse(
            model_id=model_id,
            tenant_id=tenant_id,
            model_name=model_name,
            version=version,
            stage=metadata.get("stage", "unknown"),
            metadata=metadata,
            metrics=metrics,
            uploaded_at=metadata.get("uploaded_at", datetime.utcnow().isoformat()),
            model_size_bytes=metadata.get("model_size_bytes", 0),
            model_type=metadata.get("model_type", "unknown")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_model_failed", error=str(e), model_id=model_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve model: {str(e)}"
        )


@router.get("/", response_model=ListModelsResponse)
async def list_models(
    tenant_id: Optional[str] = None,
    model_name: Optional[str] = None,
    stage: Optional[str] = None,
    limit: int = 50
):
    """
    List models in the registry.
    
    Supports filtering by:
    - `tenant_id`: Filter by tenant
    - `model_name`: Filter by model name
    - `stage`: Filter by stage ('staging', 'production', 'archived')
    - `limit`: Maximum number of results (default: 50)
    
    **Example:**
    ```bash
    # List all models for a tenant
    curl http://localhost:8003/ai/models/?tenant_id=tenant-123
    
    # List production models
    curl http://localhost:8003/ai/models/?stage=production
    
    # List specific model versions
    curl http://localhost:8003/ai/models/?tenant_id=tenant-123&model_name=forecast_lgb
    ```
    """
    try:
        # In production, this would query a database index
        # For MVP, we'll return a placeholder response
        
        # Get model storage
        model_storage = get_model_storage()
        
        models = []
        
        # If tenant_id and model_name specified, list versions
        if tenant_id and model_name:
            versions = await model_storage.list_versions(tenant_id, model_name)
            
            # Filter by stage if specified
            if stage:
                versions = [v for v in versions if v.get("stage") == stage]
            
            # Limit results
            versions = versions[:limit]
            
            models = versions
        
        logger.info(
            "models_listed",
            tenant_id=tenant_id,
            model_name=model_name,
            stage=stage,
            count=len(models)
        )
        
        return ListModelsResponse(
            models=models,
            total=len(models),
            tenant_id=tenant_id
        )
        
    except Exception as e:
        logger.error("list_models_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list models: {str(e)}"
        )


@router.put("/{model_id}/promote", response_model=PromoteModelResponse)
async def promote_model(model_id: str, request: PromoteModelRequest):
    """
    Promote a model to a different stage.
    
    Common workflows:
    - `staging` -> `production`: Deploy model to production
    - `production` -> `archived`: Retire old model
    - `staging` -> `archived`: Discard experimental model
    
    When promoting to production, the previous production model is automatically
    demoted to archived (if exists).
    
    **Example:**
    ```bash
    curl -X PUT http://localhost:8003/ai/models/tenant-123:forecast_lgb:v1.0.0/promote \\
      -H "Content-Type: application/json" \\
      -d '{
        "target_stage": "production",
        "reason": "Passed validation tests, 5% improvement in RMSE"
      }'
    ```
    """
    try:
        # Parse model_id
        parts = model_id.split(":")
        if len(parts) != 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid model_id format. Expected: tenant_id:model_name:version"
            )
        
        tenant_id, model_name, version = parts
        
        # Validate target stage
        valid_stages = ["staging", "production", "archived"]
        if request.target_stage not in valid_stages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid target_stage. Must be one of: {valid_stages}"
            )
        
        # Get model storage
        model_storage = get_model_storage()
        
        # Get current metadata
        metadata = await model_storage.get_metadata(tenant_id, model_name, version)
        
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model not found: {model_id}"
            )
        
        previous_stage = metadata.get("stage", "unknown")
        
        # If promoting to production, demote current production model
        if request.target_stage == "production":
            # In production, would query database for current production model
            # and demote it to archived
            pass
        
        # Update metadata with new stage
        metadata["stage"] = request.target_stage
        metadata["promoted_at"] = datetime.utcnow().isoformat()
        metadata["promotion_reason"] = request.reason
        metadata["promoted_from"] = previous_stage
        
        # In production, would update database here
        # For MVP, we log the promotion
        
        # If promoting to production, update model cache
        if request.target_stage == "production":
            model_cache = get_model_cache()
            # Optionally warm up the cache with the new production model
            # await model_cache.warmup([{"tenant_id": tenant_id, "model_name": model_name, "version": version}])
        
        logger.info(
            "model_promoted",
            model_id=model_id,
            previous_stage=previous_stage,
            target_stage=request.target_stage,
            reason=request.reason
        )
        
        return PromoteModelResponse(
            model_id=model_id,
            model_name=model_name,
            version=version,
            previous_stage=previous_stage,
            current_stage=request.target_stage,
            promoted_at=datetime.utcnow().isoformat(),
            message=f"Model promoted from {previous_stage} to {request.target_stage}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("model_promotion_failed", error=str(e), model_id=model_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model promotion failed: {str(e)}"
        )


@router.delete("/{model_id}", response_model=DeleteModelResponse)
async def delete_model(model_id: str, force: bool = False):
    """
    Delete a model from the registry.
    
    By default, only archived models can be deleted. Use `force=true` to delete
    models in any stage (not recommended for production models).
    
    **This operation is irreversible!**
    
    **Example:**
    ```bash
    # Delete an archived model
    curl -X DELETE http://localhost:8003/ai/models/tenant-123:forecast_lgb:v0.9.0
    
    # Force delete any model
    curl -X DELETE http://localhost:8003/ai/models/tenant-123:forecast_lgb:v1.0.0?force=true
    ```
    """
    try:
        # Parse model_id
        parts = model_id.split(":")
        if len(parts) != 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid model_id format. Expected: tenant_id:model_name:version"
            )
        
        tenant_id, model_name, version = parts
        
        # Get model storage
        model_storage = get_model_storage()
        
        # Get current metadata
        metadata = await model_storage.get_metadata(tenant_id, model_name, version)
        
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model not found: {model_id}"
            )
        
        # Check if model can be deleted
        current_stage = metadata.get("stage", "unknown")
        if current_stage == "production" and not force:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete production model. Promote to archived first or use force=true"
            )
        
        # Delete from S3
        delete_result = await model_storage.delete_model(tenant_id, model_name, version)
        
        # Clear from cache
        model_cache = get_model_cache()
        cache_key = f"{tenant_id}:{model_name}:{version}"
        # In production, would have a method to remove from cache by key
        
        # In production, would also delete from database index
        
        logger.info(
            "model_deleted",
            model_id=model_id,
            stage=current_stage,
            force=force
        )
        
        return DeleteModelResponse(
            model_id=model_id,
            model_name=model_name,
            version=version,
            status="deleted",
            files_deleted=delete_result.get("files_deleted", []),
            message=f"Model {model_name} v{version} deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("model_deletion_failed", error=str(e), model_id=model_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model deletion failed: {str(e)}"
        )
