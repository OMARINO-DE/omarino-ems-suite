"""
Optimize router with optimization endpoints.
"""
from datetime import datetime
from uuid import uuid4
from typing import Dict

from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Request
import structlog

from app.models import (
    OptimizeRequest,
    OptimizeResponse,
    OptimizationJob,
    OptimizationStatus,
    OptimizationType
)
from app.services.optimization_service import OptimizationService

logger = structlog.get_logger()
router = APIRouter()

# In-memory job storage (replace with Redis/database in production)
jobs: Dict[str, OptimizeResponse] = {}

optimization_service = OptimizationService()


@router.post("/optimize", response_model=OptimizeResponse, status_code=status.HTTP_202_ACCEPTED)
async def request_optimization(req: Request, request: OptimizeRequest, background_tasks: BackgroundTasks):
    """
    Request energy optimization.
    
    Supports multiple optimization types:
    - **battery_dispatch**: Optimize battery charge/discharge schedule
    - **unit_commitment**: Optimize generator on/off schedule
    - **procurement**: Optimize energy procurement from grid
    - **self_consumption**: Maximize self-consumption of renewable energy
    - **peak_shaving**: Minimize peak demand charges
    
    Returns optimization job ID immediately (202 Accepted).
    Use GET /optimize/{optimization_id} to retrieve results.
    """
    try:
        optimization_id = uuid4()
        
        logger.info("optimization_request_received",
                    optimization_id=str(optimization_id),
                    optimization_type=request.optimization_type.value,
                    num_assets=len(request.assets),
                    time_horizon_hours=(request.end_time - request.start_time).total_seconds() / 3600)
        
        # Create initial job response
        response = OptimizeResponse(
            optimization_id=optimization_id,
            status=OptimizationStatus.PENDING,
            optimization_type=request.optimization_type,
            created_at=datetime.utcnow()
        )
        
        jobs[str(optimization_id)] = response
        
        # Run optimization in background
        background_tasks.add_task(
            run_optimization_task,
            optimization_id,
            request,
            req.app
        )
        
        return response
        
    except ValueError as e:
        logger.error("optimization_validation_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("optimization_request_failed",
                     error=str(e),
                     exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization request failed: {str(e)}"
        )


async def run_optimization_task(optimization_id: uuid4, request: OptimizeRequest, app):
    """Background task to run optimization."""
    try:
        # Update status to running
        jobs[str(optimization_id)].status = OptimizationStatus.RUNNING
        
        logger.info("optimization_started", optimization_id=str(optimization_id))
        
        # Run optimization
        result = await optimization_service.optimize(optimization_id, request)
        
        # Update job with results
        jobs[str(optimization_id)] = result
        
        logger.info("optimization_completed",
                    optimization_id=str(optimization_id),
                    objective_value=result.objective_value,
                    solve_time=result.solver_info.solve_time_seconds if result.solver_info else None)
        
        # Save to database if available
        if hasattr(app.state, "optimization_db") and app.state.optimization_db:
            try:
                db = app.state.optimization_db
                
                # Save optimization job
                await db.save_optimization_job(
                    optimization_id=str(optimization_id),
                    optimization_type=result.optimization_type.value,
                    solver=result.solver_info.solver_name if result.solver_info else "unknown",
                    objective_value=result.objective_value,
                    solve_time_seconds=result.solver_info.solve_time_seconds if result.solver_info else None,
                    solver_status=result.solver_info.status if result.solver_info else None,
                    total_cost=result.total_cost
                )
                
                # Save assets
                assets = []
                for asset in request.assets:
                    asset_dict = {
                        "asset_id": asset.asset_id,
                        "asset_type": asset.asset_type.value,
                        "specifications": asset.dict(exclude={"asset_id", "asset_type"})
                    }
                    assets.append(asset_dict)
                
                await db.save_optimization_assets(
                    optimization_id=str(optimization_id),
                    assets=assets
                )
                
                # Save results schedule
                if result.schedule:
                    timestamps = [point.timestamp for point in result.schedule]
                    schedules = []
                    for point in result.schedule:
                        schedules.append({
                            "battery_soc": point.battery_soc,
                            "battery_charge": point.battery_charge,
                            "battery_discharge": point.battery_discharge,
                            "grid_import": point.grid_import,
                            "grid_export": point.grid_export,
                            "generator_output": point.generator_output,
                            "generator_status": point.generator_status,
                            "load_served": point.load_served,
                            "renewable_used": point.renewable_used,
                            "renewable_curtailed": point.renewable_curtailed,
                            "interval_cost": point.interval_cost
                        })
                    
                    await db.save_optimization_results(
                        optimization_id=str(optimization_id),
                        timestamps=timestamps,
                        schedules=schedules
                    )
                
                # Save costs breakdown
                costs = {}
                if result.energy_cost is not None:
                    costs["energy"] = result.energy_cost
                if result.grid_cost is not None:
                    costs["grid"] = result.grid_cost
                if result.fuel_cost is not None:
                    costs["fuel"] = result.fuel_cost
                if result.startup_cost is not None:
                    costs["startup"] = result.startup_cost
                if result.degradation_cost is not None:
                    costs["degradation"] = result.degradation_cost
                if result.penalty_cost is not None:
                    costs["penalty"] = result.penalty_cost
                
                if costs:
                    await db.save_optimization_costs(
                        optimization_id=str(optimization_id),
                        costs=costs
                    )
                
                logger.info("optimization_saved_to_database", optimization_id=str(optimization_id))
            except Exception as e:
                # Don't fail the optimization if database save fails
                logger.error("optimization_database_save_failed", error=str(e), optimization_id=str(optimization_id))
        
    except Exception as e:
        logger.error("optimization_failed",
                     optimization_id=str(optimization_id),
                     error=str(e),
                     exc_info=True)
        
        # Update job with error
        jobs[str(optimization_id)].status = OptimizationStatus.FAILED
        jobs[str(optimization_id)].error = str(e)
        jobs[str(optimization_id)].completed_at = datetime.utcnow()
        
        # Try to mark as failed in database
        if hasattr(app.state, "optimization_db") and app.state.optimization_db:
            try:
                await app.state.optimization_db.mark_optimization_failed(
                    str(optimization_id),
                    str(e)
                )
            except Exception as db_error:
                logger.error("optimization_mark_failed_error", error=str(db_error))


@router.get("/optimize/{optimization_id}", response_model=OptimizeResponse)
async def get_optimization_result(optimization_id: str):
    """
    Get optimization result by ID.
    
    Returns the optimization result including:
    - Status (pending, running, completed, failed)
    - Optimized schedule (if completed)
    - Objective value and cost breakdown
    - Solver information
    - Sensitivity analysis
    """
    if optimization_id not in jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Optimization {optimization_id} not found"
        )
    
    return jobs[optimization_id]


@router.delete("/optimize/{optimization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_optimization(optimization_id: str):
    """
    Cancel a running optimization.
    
    Note: This implementation provides the endpoint but cancellation
    of running Pyomo models requires additional implementation.
    """
    if optimization_id not in jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Optimization {optimization_id} not found"
        )
    
    job = jobs[optimization_id]
    
    if job.status in [OptimizationStatus.COMPLETED, OptimizationStatus.FAILED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel optimization in status: {job.status}"
        )
    
    job.status = OptimizationStatus.CANCELLED
    job.completed_at = datetime.utcnow()
    
    logger.info("optimization_cancelled", optimization_id=optimization_id)


@router.get("/optimizations")
async def get_optimizations(req: Request, limit: int = 20, offset: int = 0):
    """Get list of saved optimizations from database."""
    try:
        if not hasattr(req.app.state, "optimization_db") or not req.app.state.optimization_db:
            # Fall back to in-memory jobs if database not available
            results = []
            for job_id, job in list(jobs.items())[offset:offset+limit]:
                results.append({
                    "optimization_id": str(job.optimization_id),
                    "optimization_type": job.optimization_type.value,
                    "status": job.status.value,
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    "objective_value": job.objective_value,
                    "total_cost": job.total_cost
                })
            return {
                "optimizations": results,
                "limit": limit,
                "offset": offset,
                "count": len(results)
            }
        
        db = req.app.state.optimization_db
        optimizations = await db.get_optimizations(limit=limit, offset=offset)
        
        return {
            "optimizations": optimizations,
            "limit": limit,
            "offset": offset,
            "count": len(optimizations)
        }
    except Exception as e:
        logger.error("get_optimizations_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve optimizations: {str(e)}"
        )


@router.get("/optimizations/{optimization_id}")
async def get_optimization_detail(req: Request, optimization_id: str):
    """Get a specific optimization with full results from database."""
    try:
        # Check in-memory first for recent jobs
        if optimization_id in jobs:
            job = jobs[optimization_id]
            # Return in-memory job if it exists
            return job
        
        # Check database
        if not hasattr(req.app.state, "optimization_db") or not req.app.state.optimization_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Optimization {optimization_id} not found"
            )
        
        db = req.app.state.optimization_db
        optimization = await db.get_optimization(optimization_id)
        
        if not optimization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Optimization {optimization_id} not found"
            )
        
        return optimization
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_optimization_failed", error=str(e), optimization_id=optimization_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve optimization: {str(e)}"
        )


@router.get("/optimize", response_model=list[OptimizationJob])
async def list_optimizations(
    status: OptimizationStatus = None,
    optimization_type: OptimizationType = None,
    limit: int = 50
):
    """
    List optimization jobs (in-memory only, use /optimizations for database).
    
    Optionally filter by status and optimization type.
    """
    results = []
    
    for job_id, job in jobs.items():
        # Apply filters
        if status and job.status != status:
            continue
        if optimization_type and job.optimization_type != optimization_type:
            continue
        
        results.append(OptimizationJob(
            optimization_id=job.optimization_id,
            status=job.status,
            optimization_type=job.optimization_type,
            created_at=job.created_at,
            completed_at=job.completed_at,
            progress=1.0 if job.status == OptimizationStatus.COMPLETED else 0.0
        ))
        
        if len(results) >= limit:
            break
    
    return results


@router.get("/types")
async def list_optimization_types():
    """List available optimization types and their descriptions."""
    return {
        "types": [
            {
                "name": "battery_dispatch",
                "description": "Optimize battery charge/discharge schedule to minimize energy costs",
                "requires": ["battery", "import_prices", "load_forecast"]
            },
            {
                "name": "unit_commitment",
                "description": "Optimize generator on/off schedule considering startup costs and constraints",
                "requires": ["generator", "load_forecast"]
            },
            {
                "name": "procurement",
                "description": "Optimize energy procurement from grid considering price forecasts",
                "requires": ["grid", "import_prices", "load_forecast"]
            },
            {
                "name": "self_consumption",
                "description": "Maximize self-consumption of renewable energy with battery",
                "requires": ["battery", "solar_forecast or wind_forecast", "load_forecast"]
            },
            {
                "name": "peak_shaving",
                "description": "Minimize peak demand charges using battery",
                "requires": ["battery", "load_forecast"]
            }
        ]
    }
