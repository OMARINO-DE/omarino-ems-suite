"""
Battery asset management endpoints.
Provides specialized CRUD operations for battery assets with their specifications.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
import structlog

from app.models import (
    BatteryAsset,
    BatteryAssetCreate,
    BatteryListResponse,
    ErrorResponse,
)

logger = structlog.get_logger()

router = APIRouter()


@router.get(
    "/batteries",
    response_model=BatteryListResponse,
    summary="List battery assets",
    description="Retrieve a paginated list of battery assets with their specifications.",
    responses={
        503: {"model": ErrorResponse, "description": "Database unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_batteries(
    request: Request,
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by operational status (e.g., 'active', 'inactive')",
    ),
    site_id: Optional[UUID] = Query(None, description="Filter by site ID"),
    chemistry: Optional[str] = Query(
        None, description="Filter by battery chemistry (e.g., 'lithium_ion')"
    ),
    search: Optional[str] = Query(
        None,
        description="Search in name and description",
        min_length=2,
    ),
    limit: int = Query(50, ge=1, le=100, description="Number of items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
):
    """
    List battery assets with optional filtering.

    Filters:
    - status: Operational status
    - site_id: Associated site
    - chemistry: Battery chemistry type
    - search: Text search in name/description
    """
    db = request.app.state.db
    if not db.pool:
        logger.error("database_unavailable", operation="list_batteries")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not available",
        )

    try:
        batteries, total = await db.list_batteries(
            status_filter=status_filter,
            site_id=site_id,
            chemistry=chemistry,
            search=search,
            limit=limit,
            offset=offset,
        )

        logger.info(
            "batteries_listed",
            total=total,
            returned=len(batteries),
            offset=offset,
            limit=limit,
        )

        return BatteryListResponse(
            items=batteries,
            total=total,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.exception("list_batteries_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list battery assets",
        )


@router.post(
    "/batteries",
    response_model=BatteryAsset,
    status_code=status.HTTP_201_CREATED,
    summary="Create battery asset",
    description="Create a new battery asset with specifications.",
    responses={
        503: {"model": ErrorResponse, "description": "Database unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def create_battery(
    request: Request,
    battery_data: BatteryAssetCreate,
):
    """
    Create a new battery asset with specifications.

    The request body includes both asset information and battery-specific specifications.
    """
    db = request.app.state.db
    if not db.pool:
        logger.error("database_unavailable", operation="create_battery")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not available",
        )

    try:
        # Create the base asset first
        from uuid import uuid4

        asset_id = uuid4()

        await db.create_asset(
            asset_id=asset_id,
            site_id=battery_data.site_id,
            name=battery_data.name,
            asset_type="battery",
            description=battery_data.description,
            manufacturer=battery_data.manufacturer,
            model_number=battery_data.model,
            serial_number=battery_data.serial_number,
            installation_date=battery_data.installation_date,
            metadata=battery_data.metadata,
        )

        # Create the battery specifications
        await db.create_battery_spec(
            asset_id=asset_id,
            chemistry=battery_data.chemistry,
            capacity=battery_data.capacity,
            usable_capacity=battery_data.usable_capacity,
            voltage=battery_data.voltage,
            max_charge_rate=battery_data.max_charge_rate,
            max_discharge_rate=battery_data.max_discharge_rate,
            efficiency=battery_data.efficiency,
            cycle_life=battery_data.cycle_life,
            depth_of_discharge=battery_data.depth_of_discharge,
            min_soc=battery_data.min_soc,
            max_soc=battery_data.max_soc,
        )

        # Retrieve the complete battery asset
        battery = await db.get_battery(asset_id)
        if not battery:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Battery created but failed to retrieve",
            )

        logger.info(
            "battery_created",
            asset_id=str(asset_id),
            name=battery_data.name,
            chemistry=battery_data.chemistry,
            capacity=battery_data.capacity,
        )

        return battery

    except Exception as e:
        logger.exception("create_battery_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create battery asset: {str(e)}",
        )


@router.get(
    "/batteries/{asset_id}",
    response_model=BatteryAsset,
    summary="Get battery asset",
    description="Retrieve a specific battery asset with its specifications.",
    responses={
        404: {"model": ErrorResponse, "description": "Battery not found"},
        503: {"model": ErrorResponse, "description": "Database unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_battery(
    request: Request,
    asset_id: UUID,
):
    """
    Get a specific battery asset by ID.

    Returns the battery with all its specifications and site information.
    """
    db = request.app.state.db
    if not db.pool:
        logger.error("database_unavailable", operation="get_battery")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not available",
        )

    try:
        battery = await db.get_battery(asset_id)

        if not battery:
            logger.warning("battery_not_found", asset_id=str(asset_id))
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Battery with ID {asset_id} not found",
            )

        logger.info("battery_retrieved", asset_id=str(asset_id))
        return battery

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_battery_error", asset_id=str(asset_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve battery asset",
        )


@router.put(
    "/batteries/{asset_id}",
    response_model=BatteryAsset,
    summary="Update battery asset",
    description="Update a battery asset and/or its specifications.",
    responses={
        404: {"model": ErrorResponse, "description": "Battery not found"},
        503: {"model": ErrorResponse, "description": "Database unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def update_battery(
    request: Request,
    asset_id: UUID,
    battery_data: BatteryAssetCreate,
):
    """
    Update a battery asset.

    Updates both the base asset information and battery-specific specifications.
    """
    db = request.app.state.db
    if not db.pool:
        logger.error("database_unavailable", operation="update_battery")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not available",
        )

    try:
        # Check if battery exists
        existing = await db.get_battery(asset_id)
        if not existing:
            logger.warning("battery_not_found_for_update", asset_id=str(asset_id))
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Battery with ID {asset_id} not found",
            )

        # Update base asset
        await db.update_asset(
            asset_id=asset_id,
            site_id=battery_data.site_id,
            name=battery_data.name,
            description=battery_data.description,
            manufacturer=battery_data.manufacturer,
            model_number=battery_data.model,
            serial_number=battery_data.serial_number,
            installation_date=battery_data.installation_date,
            metadata=battery_data.metadata,
        )

        # Update battery specifications
        async with db.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE battery_specifications
                SET chemistry = $2,
                    capacity = $3,
                    usable_capacity = $4,
                    voltage = $5,
                    max_charge_rate = $6,
                    max_discharge_rate = $7,
                    efficiency = $8,
                    cycle_life = $9,
                    depth_of_discharge = $10,
                    min_soc = $11,
                    max_soc = $12,
                    updated_at = CURRENT_TIMESTAMP
                WHERE asset_id = $1
                """,
                asset_id,
                battery_data.chemistry,
                battery_data.capacity,
                battery_data.usable_capacity,
                battery_data.voltage,
                battery_data.max_charge_rate,
                battery_data.max_discharge_rate,
                battery_data.efficiency,
                battery_data.cycle_life,
                battery_data.depth_of_discharge,
                battery_data.min_soc,
                battery_data.max_soc,
            )

        # Retrieve updated battery
        battery = await db.get_battery(asset_id)

        logger.info("battery_updated", asset_id=str(asset_id))
        return battery

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("update_battery_error", asset_id=str(asset_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update battery asset",
        )


@router.delete(
    "/batteries/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete battery asset",
    description="Delete a battery asset. Supports both soft delete (decommission) and hard delete.",
    responses={
        404: {"model": ErrorResponse, "description": "Battery not found"},
        503: {"model": ErrorResponse, "description": "Database unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def delete_battery(
    request: Request,
    asset_id: UUID,
    permanent: bool = Query(
        False,
        description="If true, permanently delete the battery. If false, mark as decommissioned.",
    ),
):
    """
    Delete a battery asset.

    - permanent=false (default): Soft delete - marks as decommissioned
    - permanent=true: Hard delete - permanently removes from database
    """
    db = request.app.state.db
    if not db.pool:
        logger.error("database_unavailable", operation="delete_battery")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not available",
        )

    try:
        # Check if battery exists
        existing = await db.get_battery(asset_id)
        if not existing:
            logger.warning("battery_not_found_for_delete", asset_id=str(asset_id))
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Battery with ID {asset_id} not found",
            )

        # Delete the asset (uses the base asset delete method)
        await db.delete_asset(asset_id, permanent=permanent)

        logger.info(
            "battery_deleted",
            asset_id=str(asset_id),
            permanent=permanent,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("delete_battery_error", asset_id=str(asset_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete battery asset",
        )
