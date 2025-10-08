"""
Asset status monitoring endpoints.
Provides real-time status information and updates for assets.
"""
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
import structlog

from app.models import (
    AssetStatusResponse,
    AssetStatusUpdate,
    ErrorResponse,
)

logger = structlog.get_logger()

router = APIRouter()


@router.get(
    "/status/{asset_id}",
    response_model=AssetStatusResponse,
    summary="Get asset status",
    description="Retrieve the current operational status of an asset.",
    responses={
        404: {"model": ErrorResponse, "description": "Asset not found"},
        503: {"model": ErrorResponse, "description": "Database unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_asset_status(
    request: Request,
    asset_id: UUID,
):
    """
    Get the current status of an asset.

    Returns operational status, online state, and last update time.
    """
    db = request.app.state.db
    if not db.pool:
        logger.error("database_unavailable", operation="get_asset_status")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not available",
        )

    try:
        asset_status = await db.get_asset_status(asset_id)

        if not asset_status:
            logger.warning("asset_status_not_found", asset_id=str(asset_id))
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Status for asset {asset_id} not found",
            )

        logger.info("asset_status_retrieved", asset_id=str(asset_id))
        
        return AssetStatusResponse(**asset_status)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_asset_status_error", asset_id=str(asset_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve asset status",
        )


@router.post(
    "/status/{asset_id}",
    response_model=AssetStatusResponse,
    summary="Update asset status",
    description="Update the operational status of an asset.",
    responses={
        503: {"model": ErrorResponse, "description": "Database unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def update_asset_status(
    request: Request,
    asset_id: UUID,
    status_update: AssetStatusUpdate,
):
    """
    Update the status of an asset.

    Creates or updates the current status record for the asset.
    """
    db = request.app.state.db
    if not db.pool:
        logger.error("database_unavailable", operation="update_asset_status")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not available",
        )

    try:
        updated_status = await db.upsert_asset_status(
            asset_id=asset_id,
            online=status_update.online,
            operational_status=status_update.operational_status,
            current_power_kw=status_update.current_power_kw,
            current_soc=status_update.current_soc,
            current_soh=status_update.current_soh,
            temperature_c=status_update.temperature_c,
            alarms=status_update.alarms,
        )

        logger.info(
            "asset_status_updated",
            asset_id=str(asset_id),
            online=status_update.online,
            operational_status=status_update.operational_status,
        )

        return AssetStatusResponse(**updated_status)

    except Exception as e:
        logger.exception("update_asset_status_error", asset_id=str(asset_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update asset status",
        )


@router.get(
    "/status",
    response_model=List[AssetStatusResponse],
    summary="List all asset statuses",
    description="Retrieve status information for all assets or filtered by site.",
    responses={
        503: {"model": ErrorResponse, "description": "Database unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_asset_statuses(
    request: Request,
    site_id: Optional[UUID] = Query(None, description="Filter by site ID"),
    online_only: bool = Query(False, description="Return only online assets"),
):
    """
    List status information for multiple assets.

    Optionally filter by site or show only online assets.
    """
    db = request.app.state.db
    if not db.pool:
        logger.error("database_unavailable", operation="list_asset_statuses")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not available",
        )

    try:
        # Build query based on filters
        conditions = []
        params = []
        param_idx = 1

        if site_id:
            conditions.append(f"a.site_id = ${param_idx}")
            params.append(site_id)
            param_idx += 1

        if online_only:
            conditions.append(f"ast.online = ${param_idx}")
            params.append(True)
            param_idx += 1

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        async with db.pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT 
                    ast.asset_id,
                    ast.online,
                    ast.operational_status,
                    ast.current_power_kw,
                    ast.current_soc,
                    ast.current_soh,
                    ast.temperature_c,
                    ast.alarms,
                    ast.last_update
                FROM asset_status ast
                INNER JOIN assets a ON ast.asset_id = a.asset_id
                {where_clause}
                ORDER BY ast.last_update DESC
                """,
                *params
            )

        statuses = [AssetStatusResponse(**dict(row)) for row in rows]

        logger.info(
            "asset_statuses_listed",
            count=len(statuses),
            site_id=str(site_id) if site_id else None,
            online_only=online_only,
        )

        return statuses

    except Exception as e:
        logger.exception("list_asset_statuses_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list asset statuses",
        )


@router.get(
    "/status/dashboard/summary",
    summary="Get dashboard summary",
    description="Get aggregated status summary for dashboard display.",
    responses={
        503: {"model": ErrorResponse, "description": "Database unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_status_summary(
    request: Request,
    site_id: Optional[UUID] = Query(None, description="Filter by site ID"),
):
    """
    Get aggregated status summary for dashboard.

    Returns counts of assets by status, total power, and alarm counts.
    """
    db = request.app.state.db
    if not db.pool:
        logger.error("database_unavailable", operation="get_status_summary")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not available",
        )

    try:
        site_filter = ""
        params = []
        if site_id:
            site_filter = "WHERE a.site_id = $1"
            params.append(site_id)

        async with db.pool.acquire() as conn:
            # Get status counts
            status_counts = await conn.fetch(
                f"""
                SELECT 
                    ast.operational_status,
                    COUNT(*) as count,
                    SUM(CASE WHEN ast.online THEN 1 ELSE 0 END) as online_count
                FROM asset_status ast
                INNER JOIN assets a ON ast.asset_id = a.asset_id
                {site_filter}
                GROUP BY ast.operational_status
                """,
                *params
            )

            # Get total power
            total_power = await conn.fetchval(
                f"""
                SELECT COALESCE(SUM(ast.current_power_kw), 0)
                FROM asset_status ast
                INNER JOIN assets a ON ast.asset_id = a.asset_id
                {site_filter}
                WHERE ast.online = true
                """,
                *params
            )

            # Get alarm counts
            alarm_counts = await conn.fetchval(
                f"""
                SELECT COUNT(*)
                FROM asset_status ast
                INNER JOIN assets a ON ast.asset_id = a.asset_id
                {site_filter}
                WHERE ast.alarms IS NOT NULL AND jsonb_array_length(ast.alarms) > 0
                """,
                *params
            )

        summary = {
            "status_breakdown": [dict(row) for row in status_counts],
            "total_power_kw": float(total_power) if total_power else 0.0,
            "active_alarms": alarm_counts if alarm_counts else 0,
            "site_id": str(site_id) if site_id else None,
        }

        logger.info("status_summary_retrieved", site_id=str(site_id) if site_id else None)

        return summary

    except Exception as e:
        logger.exception("get_status_summary_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve status summary",
        )
