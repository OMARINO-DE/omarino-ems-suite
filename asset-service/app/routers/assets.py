"""
Assets router for general asset management operations.
"""
from fastapi import APIRouter, HTTPException, status, Request, Query
from typing import Optional
from uuid import uuid4, UUID
import structlog

from app.models import (
    AssetCreate, AssetUpdate, AssetListResponse, AssetSummary, Asset,
    AssetType, AssetStatus, ErrorResponse
)

logger = structlog.get_logger()
router = APIRouter()


@router.get("/assets", response_model=AssetListResponse)
async def list_assets(
    request: Request,
    asset_type: Optional[AssetType] = Query(None, description="Filter by asset type"),
    status: Optional[AssetStatus] = Query(None, description="Filter by status"),
    site_id: Optional[UUID] = Query(None, description="Filter by site ID"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip")
):
    """
    List all assets with optional filtering and pagination.
    
    Supports filtering by:
    - asset_type: Type of asset (battery, generator, etc.)
    - status: Asset status (active, inactive, maintenance, decommissioned)
    - site_id: Filter by specific site
    - search: Search in name and description fields
    """
    if not hasattr(request.app.state, "asset_db") or not request.app.state.asset_db:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available"
        )
    
    try:
        db = request.app.state.asset_db
        assets, total = await db.list_assets(
            asset_type=asset_type,
            status=status,
            site_id=site_id,
            search=search,
            limit=limit,
            offset=offset
        )
        
        # Convert to Pydantic models
        asset_summaries = []
        for asset_data in assets:
            asset_summaries.append(AssetSummary(
                asset_id=asset_data["asset_id"],
                asset_type=AssetType(asset_data["asset_type"]),
                name=asset_data["name"],
                description=asset_data.get("description"),
                location=asset_data.get("location"),
                site_id=asset_data.get("site_id"),
                site_name=asset_data.get("site_name"),
                manufacturer=asset_data.get("manufacturer"),
                model=asset_data.get("model"),
                serial_number=asset_data.get("serial_number"),
                installation_date=asset_data.get("installation_date"),
                status=AssetStatus(asset_data["status"]),
                online=asset_data.get("online"),
                created_at=asset_data["created_at"],
                metadata=asset_data.get("metadata")
            ))
        
        return AssetListResponse(
            assets=asset_summaries,
            total=total,
            limit=limit,
            offset=offset
        )
    
    except Exception as e:
        logger.error("list_assets_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list assets: {str(e)}"
        )


@router.post("/assets", response_model=Asset, status_code=status.HTTP_201_CREATED)
async def create_asset(
    request: Request,
    asset: AssetCreate
):
    """
    Create a new asset.
    
    Note: This creates the base asset record. For type-specific assets with
    specifications (battery, generator, etc.), use the dedicated type endpoints
    (e.g., POST /batteries).
    """
    if not hasattr(request.app.state, "asset_db") or not request.app.state.asset_db:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available"
        )
    
    try:
        db = request.app.state.asset_db
        asset_id = uuid4()
        
        asset_data = await db.create_asset(
            asset_id=asset_id,
            asset_data=asset,
            created_by=None  # TODO: Get from authentication
        )
        
        return Asset(
            asset_id=asset_data["asset_id"],
            asset_type=AssetType(asset_data["asset_type"]),
            name=asset_data["name"],
            description=asset_data.get("description"),
            location=asset_data.get("location"),
            site_id=asset_data.get("site_id"),
            manufacturer=asset_data.get("manufacturer"),
            model=asset_data.get("model"),
            serial_number=asset_data.get("serial_number"),
            installation_date=asset_data.get("installation_date"),
            status=AssetStatus(asset_data["status"]),
            created_at=asset_data["created_at"],
            updated_at=asset_data["updated_at"],
            metadata=asset_data.get("metadata")
        )
    
    except Exception as e:
        logger.error("create_asset_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create asset: {str(e)}"
        )


@router.get("/assets/{asset_id}", response_model=Asset)
async def get_asset(
    request: Request,
    asset_id: UUID
):
    """
    Get detailed information about a specific asset.
    
    Returns the base asset information. For type-specific details with
    specifications, use the dedicated type endpoints (e.g., GET /batteries/{asset_id}).
    """
    if not hasattr(request.app.state, "asset_db") or not request.app.state.asset_db:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available"
        )
    
    try:
        db = request.app.state.asset_db
        asset_data = await db.get_asset(asset_id)
        
        if not asset_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset {asset_id} not found"
            )
        
        return Asset(
            asset_id=asset_data["asset_id"],
            asset_type=AssetType(asset_data["asset_type"]),
            name=asset_data["name"],
            description=asset_data.get("description"),
            location=asset_data.get("location"),
            site_id=asset_data.get("site_id"),
            site_name=asset_data.get("site_name"),
            manufacturer=asset_data.get("manufacturer"),
            model=asset_data.get("model"),
            serial_number=asset_data.get("serial_number"),
            installation_date=asset_data.get("installation_date"),
            status=AssetStatus(asset_data["status"]),
            created_at=asset_data["created_at"],
            updated_at=asset_data["updated_at"],
            metadata=asset_data.get("metadata")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_asset_failed", error=str(e), asset_id=str(asset_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get asset: {str(e)}"
        )


@router.put("/assets/{asset_id}", response_model=Asset)
async def update_asset(
    request: Request,
    asset_id: UUID,
    asset: AssetUpdate
):
    """
    Update asset information.
    
    Updates base asset fields. For updating type-specific specifications,
    use the dedicated type endpoints.
    """
    if not hasattr(request.app.state, "asset_db") or not request.app.state.asset_db:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available"
        )
    
    try:
        db = request.app.state.asset_db
        
        # Check if asset exists
        existing = await db.get_asset(asset_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset {asset_id} not found"
            )
        
        asset_data = await db.update_asset(
            asset_id=asset_id,
            asset_data=asset,
            updated_by=None  # TODO: Get from authentication
        )
        
        return Asset(
            asset_id=asset_data["asset_id"],
            asset_type=AssetType(asset_data["asset_type"]),
            name=asset_data["name"],
            description=asset_data.get("description"),
            location=asset_data.get("location"),
            site_id=asset_data.get("site_id"),
            manufacturer=asset_data.get("manufacturer"),
            model=asset_data.get("model"),
            serial_number=asset_data.get("serial_number"),
            installation_date=asset_data.get("installation_date"),
            status=AssetStatus(asset_data["status"]),
            created_at=asset_data["created_at"],
            updated_at=asset_data["updated_at"],
            metadata=asset_data.get("metadata")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_asset_failed", error=str(e), asset_id=str(asset_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update asset: {str(e)}"
        )


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    request: Request,
    asset_id: UUID,
    permanent: bool = Query(False, description="Permanently delete the asset")
):
    """
    Delete an asset.
    
    By default, this performs a soft delete by setting status to 'decommissioned'.
    Set permanent=true to permanently delete the asset and all related data.
    """
    if not hasattr(request.app.state, "asset_db") or not request.app.state.asset_db:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available"
        )
    
    try:
        db = request.app.state.asset_db
        
        # Check if asset exists
        existing = await db.get_asset(asset_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset {asset_id} not found"
            )
        
        if permanent:
            # Permanent delete
            deleted = await db.delete_asset(asset_id)
            if not deleted:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete asset"
                )
        else:
            # Soft delete - set status to decommissioned
            await db.update_asset(
                asset_id=asset_id,
                asset_data=AssetUpdate(status=AssetStatus.DECOMMISSIONED),
                updated_by=None
            )
        
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_asset_failed", error=str(e), asset_id=str(asset_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete asset: {str(e)}"
        )
