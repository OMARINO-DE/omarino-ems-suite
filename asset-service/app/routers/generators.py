"""
Generator asset management endpoints.
Provides specialized CRUD operations for generator assets with their specifications.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
import structlog

from app.models import (
    GeneratorAsset,
    GeneratorListResponse,
    ErrorResponse,
)

logger = structlog.get_logger()

router = APIRouter()


@router.get(
    "/generators",
    response_model=GeneratorListResponse,
    summary="List generator assets",
    description="Retrieve a paginated list of generator assets with their specifications.",
    responses={
        503: {"model": ErrorResponse, "description": "Database unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_generators(
    request: Request,
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by operational status (e.g., 'active', 'inactive')",
    ),
    site_id: Optional[UUID] = Query(None, description="Filter by site ID"),
    generator_type: Optional[str] = Query(
        None, description="Filter by generator type (e.g., 'diesel', 'natural_gas')"
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
    List generator assets with optional filtering.

    Filters:
    - status: Operational status
    - site_id: Associated site
    - generator_type: Type of generator
    - search: Text search in name/description
    """
    db = request.app.state.db
    if not db.pool:
        logger.error("database_unavailable", operation="list_generators")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not available",
        )

    try:
        generators, total = await db.list_generators(
            status_filter=status_filter,
            site_id=site_id,
            generator_type=generator_type,
            search=search,
            limit=limit,
            offset=offset,
        )

        logger.info(
            "generators_listed",
            total=total,
            returned=len(generators),
            offset=offset,
            limit=limit,
        )

        return GeneratorListResponse(
            items=generators,
            total=total,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.exception("list_generators_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list generator assets",
        )


@router.post(
    "/generators",
    response_model=GeneratorAsset,
    status_code=status.HTTP_201_CREATED,
    summary="Create generator asset",
    description="Create a new generator asset with specifications.",
    responses={
        503: {"model": ErrorResponse, "description": "Database unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def create_generator(
    request: Request,
    generator_data: dict,
):
    """
    Create a new generator asset with specifications.

    The request body includes both asset information and generator-specific specifications.
    """
    db = request.app.state.db
    if not db.pool:
        logger.error("database_unavailable", operation="create_generator")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not available",
        )

    try:
        from uuid import uuid4

        asset_id = uuid4()

        # Create the base asset
        await db.create_asset(
            asset_id=asset_id,
            site_id=generator_data["site_id"],
            name=generator_data["name"],
            asset_type="generator",
            description=generator_data.get("description"),
            manufacturer=generator_data.get("manufacturer"),
            model_number=generator_data.get("model"),
            serial_number=generator_data.get("serial_number"),
            installation_date=generator_data.get("installation_date"),
            metadata=generator_data.get("metadata", {}),
        )

        # Create the generator specifications
        async with db.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO generator_specs (
                    asset_id, rated_capacity_kw, max_output_kw, min_output_kw,
                    generator_type, fuel_cost_per_kwh, startup_cost, shutdown_cost,
                    min_uptime_hours, min_downtime_hours, co2_emissions_kg_per_kwh,
                    updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                asset_id,
                generator_data["rated_capacity_kw"],
                generator_data.get("max_output_kw"),
                generator_data.get("min_output_kw"),
                generator_data.get("generator_type"),
                generator_data.get("fuel_cost_per_kwh"),
                generator_data.get("startup_cost"),
                generator_data.get("shutdown_cost"),
                generator_data.get("min_uptime_hours"),
                generator_data.get("min_downtime_hours"),
                generator_data.get("co2_emissions_kg_per_kwh"),
                "now()",
            )

        # Retrieve the complete generator asset
        generator = await db.get_generator(asset_id)
        if not generator:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Generator created but failed to retrieve",
            )

        logger.info(
            "generator_created",
            asset_id=str(asset_id),
            name=generator_data["name"],
            generator_type=generator_data.get("generator_type"),
            rated_capacity_kw=generator_data["rated_capacity_kw"],
        )

        return GeneratorAsset(**generator)

    except Exception as e:
        logger.exception("create_generator_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create generator asset: {str(e)}",
        )


@router.get(
    "/generators/{asset_id}",
    response_model=GeneratorAsset,
    summary="Get generator asset",
    description="Retrieve a specific generator asset with its specifications.",
    responses={
        404: {"model": ErrorResponse, "description": "Generator not found"},
        503: {"model": ErrorResponse, "description": "Database unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_generator(
    request: Request,
    asset_id: UUID,
):
    """
    Get a specific generator asset by ID.

    Returns the generator with all its specifications and site information.
    """
    db = request.app.state.db
    if not db.pool:
        logger.error("database_unavailable", operation="get_generator")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not available",
        )

    try:
        generator = await db.get_generator(asset_id)

        if not generator:
            logger.warning("generator_not_found", asset_id=str(asset_id))
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Generator with ID {asset_id} not found",
            )

        logger.info("generator_retrieved", asset_id=str(asset_id))
        return GeneratorAsset(**generator)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_generator_error", asset_id=str(asset_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve generator asset",
        )


@router.delete(
    "/generators/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete generator asset",
    description="Delete a generator asset. Supports both soft delete (decommission) and hard delete.",
    responses={
        404: {"model": ErrorResponse, "description": "Generator not found"},
        503: {"model": ErrorResponse, "description": "Database unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def delete_generator(
    request: Request,
    asset_id: UUID,
    permanent: bool = Query(
        False,
        description="If true, permanently delete the generator. If false, mark as decommissioned.",
    ),
):
    """
    Delete a generator asset.

    - permanent=false (default): Soft delete - marks as decommissioned
    - permanent=true: Hard delete - permanently removes from database
    """
    db = request.app.state.db
    if not db.pool:
        logger.error("database_unavailable", operation="delete_generator")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not available",
        )

    try:
        # Check if generator exists
        existing = await db.get_generator(asset_id)
        if not existing:
            logger.warning("generator_not_found_for_delete", asset_id=str(asset_id))
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Generator with ID {asset_id} not found",
            )

        # Delete the asset
        await db.delete_asset(asset_id, permanent=permanent)

        logger.info(
            "generator_deleted",
            asset_id=str(asset_id),
            permanent=permanent,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("delete_generator_error", asset_id=str(asset_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete generator asset",
        )
