"""
Database client for optimization service
"""
import asyncpg
import os
import structlog
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import json

logger = structlog.get_logger()


class OptimizationDatabase:
    """Database client for storing optimization results"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://omarino:omarino@omarino-postgres:5432/omarino"
        )
    
    async def connect(self):
        """Create connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            logger.info("optimization_db_connected", database="optimization_results")
        except Exception as e:
            logger.error("optimization_db_connection_failed", error=str(e))
            raise
    
    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("optimization_db_closed")
    
    async def save_optimization_job(
        self,
        optimization_id: str,
        optimization_type: str,
        solver: str,
        objective_value: Optional[float] = None,
        solve_time_seconds: Optional[float] = None,
        solver_status: Optional[str] = None,
        total_cost: Optional[float] = None,
        created_by: Optional[str] = None
    ) -> str:
        """
        Save optimization job metadata
        
        Returns:
            optimization_id: The UUID of the saved optimization job
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO optimization_jobs (
                        optimization_id, optimization_type, solver, objective_value,
                        solve_time_seconds, solver_status, total_cost, status,
                        created_by, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                    uuid.UUID(optimization_id),
                    optimization_type,
                    solver,
                    objective_value,
                    solve_time_seconds,
                    solver_status,
                    total_cost,
                    "completed",
                    created_by,
                    datetime.utcnow()
                )
            
            logger.info("optimization_job_saved", optimization_id=optimization_id, solver=solver)
            return optimization_id
        
        except Exception as e:
            logger.error("optimization_job_save_failed", error=str(e), optimization_id=optimization_id)
            raise
    
    async def save_optimization_assets(
        self,
        optimization_id: str,
        assets: List[Dict[str, Any]]
    ):
        """Save optimization asset configurations"""
        try:
            records = []
            for asset in assets:
                records.append((
                    uuid.UUID(optimization_id),
                    asset.get("asset_id"),
                    asset.get("asset_type"),
                    json.dumps(asset.get("specifications", {}))
                ))
            
            async with self.pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO optimization_assets (optimization_id, asset_id, asset_type, specifications)
                    VALUES ($1, $2, $3, $4)
                    """,
                    records
                )
            
            logger.info("optimization_assets_saved", optimization_id=optimization_id, count=len(records))
        
        except Exception as e:
            logger.error("optimization_assets_save_failed", error=str(e), optimization_id=optimization_id)
            raise
    
    async def save_optimization_results(
        self,
        optimization_id: str,
        timestamps: List[datetime],
        schedules: List[Dict[str, Any]]
    ):
        """Save optimization result schedules"""
        try:
            records = []
            for ts, schedule in zip(timestamps, schedules):
                records.append((
                    uuid.UUID(optimization_id),
                    ts,
                    schedule.get("battery_soc"),
                    schedule.get("battery_charge"),
                    schedule.get("battery_discharge"),
                    schedule.get("grid_import"),
                    schedule.get("grid_export"),
                    schedule.get("generator_output"),
                    schedule.get("generator_status"),
                    schedule.get("load_served"),
                    schedule.get("renewable_used"),
                    schedule.get("renewable_curtailed"),
                    schedule.get("interval_cost")
                ))
            
            async with self.pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO optimization_results (
                        optimization_id, timestamp, battery_soc, battery_charge, battery_discharge,
                        grid_import, grid_export, generator_output, generator_status,
                        load_served, renewable_used, renewable_curtailed, interval_cost
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    """,
                    records
                )
            
            logger.info("optimization_results_saved", optimization_id=optimization_id, count=len(records))
        
        except Exception as e:
            logger.error("optimization_results_save_failed", error=str(e), optimization_id=optimization_id)
            raise
    
    async def save_optimization_costs(
        self,
        optimization_id: str,
        costs: Dict[str, float]
    ):
        """Save optimization cost breakdown"""
        try:
            records = []
            for cost_type, amount in costs.items():
                records.append((uuid.UUID(optimization_id), cost_type, amount))
            
            async with self.pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO optimization_costs (optimization_id, cost_type, amount)
                    VALUES ($1, $2, $3)
                    """,
                    records
                )
            
            logger.info("optimization_costs_saved", optimization_id=optimization_id, count=len(records))
        
        except Exception as e:
            logger.error("optimization_costs_save_failed", error=str(e), optimization_id=optimization_id)
            raise
    
    async def mark_optimization_failed(self, optimization_id: str, error_message: str):
        """Mark an optimization job as failed"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE optimization_jobs
                    SET status = 'failed', error_message = $2, completed_at = $3
                    WHERE optimization_id = $1
                    """,
                    uuid.UUID(optimization_id),
                    error_message,
                    datetime.utcnow()
                )
            
            logger.info("optimization_marked_failed", optimization_id=optimization_id)
        
        except Exception as e:
            logger.error("optimization_mark_failed_error", error=str(e), optimization_id=optimization_id)
    
    async def get_optimizations(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Get list of optimization jobs"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT 
                        o.optimization_id, o.optimization_type, o.solver, o.objective_value,
                        o.solve_time_seconds, o.solver_status, o.total_cost, o.status,
                        o.created_at, o.completed_at,
                        (SELECT COUNT(*) FROM optimization_results WHERE optimization_results.optimization_id = o.optimization_id) as result_count,
                        (SELECT COUNT(*) FROM optimization_assets WHERE optimization_assets.optimization_id = o.optimization_id) as asset_count
                    FROM optimization_jobs o
                    ORDER BY o.created_at DESC
                    LIMIT $1 OFFSET $2
                    """,
                    limit,
                    offset
                )
            
            optimizations = []
            for row in rows:
                optimizations.append({
                    "optimization_id": str(row["optimization_id"]),
                    "optimization_type": row["optimization_type"],
                    "solver": row["solver"],
                    "objective_value": float(row["objective_value"]) if row["objective_value"] is not None else None,
                    "solve_time_seconds": float(row["solve_time_seconds"]) if row["solve_time_seconds"] is not None else None,
                    "solver_status": row["solver_status"],
                    "total_cost": float(row["total_cost"]) if row["total_cost"] is not None else None,
                    "status": row["status"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
                    "result_count": row["result_count"],
                    "asset_count": row["asset_count"]
                })
            
            return optimizations
        
        except Exception as e:
            logger.error("get_optimizations_failed", error=str(e))
            return []
    
    async def get_optimization(self, optimization_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific optimization with full results"""
        try:
            async with self.pool.acquire() as conn:
                # Get optimization metadata
                job_row = await conn.fetchrow(
                    """
                    SELECT 
                        optimization_id, optimization_type, solver, objective_value,
                        solve_time_seconds, solver_status, total_cost, status,
                        created_at, completed_at
                    FROM optimization_jobs
                    WHERE optimization_id = $1
                    """,
                    uuid.UUID(optimization_id)
                )
                
                if not job_row:
                    return None
                
                # Get assets
                asset_rows = await conn.fetch(
                    """
                    SELECT asset_id, asset_type, specifications
                    FROM optimization_assets
                    WHERE optimization_id = $1
                    """,
                    uuid.UUID(optimization_id)
                )
                
                assets = []
                for row in asset_rows:
                    assets.append({
                        "asset_id": row["asset_id"],
                        "asset_type": row["asset_type"],
                        "specifications": json.loads(row["specifications"]) if row["specifications"] else {}
                    })
                
                # Get results
                result_rows = await conn.fetch(
                    """
                    SELECT 
                        timestamp, battery_soc, battery_charge, battery_discharge,
                        grid_import, grid_export, generator_output, generator_status,
                        load_served, renewable_used, renewable_curtailed, interval_cost
                    FROM optimization_results
                    WHERE optimization_id = $1
                    ORDER BY timestamp
                    """,
                    uuid.UUID(optimization_id)
                )
                
                results = []
                for row in result_rows:
                    results.append({
                        "timestamp": row["timestamp"].isoformat(),
                        "battery_soc": float(row["battery_soc"]) if row["battery_soc"] is not None else None,
                        "battery_charge": float(row["battery_charge"]) if row["battery_charge"] is not None else None,
                        "battery_discharge": float(row["battery_discharge"]) if row["battery_discharge"] is not None else None,
                        "grid_import": float(row["grid_import"]) if row["grid_import"] is not None else None,
                        "grid_export": float(row["grid_export"]) if row["grid_export"] is not None else None,
                        "generator_output": float(row["generator_output"]) if row["generator_output"] is not None else None,
                        "generator_status": row["generator_status"],
                        "load_served": float(row["load_served"]) if row["load_served"] is not None else None,
                        "renewable_used": float(row["renewable_used"]) if row["renewable_used"] is not None else None,
                        "renewable_curtailed": float(row["renewable_curtailed"]) if row["renewable_curtailed"] is not None else None,
                        "interval_cost": float(row["interval_cost"]) if row["interval_cost"] is not None else None
                    })
                
                # Get costs
                cost_rows = await conn.fetch(
                    """
                    SELECT cost_type, amount
                    FROM optimization_costs
                    WHERE optimization_id = $1
                    """,
                    uuid.UUID(optimization_id)
                )
                
                costs = {}
                for row in cost_rows:
                    costs[row["cost_type"]] = float(row["amount"])
                
                return {
                    "optimization_id": str(job_row["optimization_id"]),
                    "optimization_type": job_row["optimization_type"],
                    "solver": job_row["solver"],
                    "objective_value": float(job_row["objective_value"]) if job_row["objective_value"] is not None else None,
                    "solve_time_seconds": float(job_row["solve_time_seconds"]) if job_row["solve_time_seconds"] is not None else None,
                    "solver_status": job_row["solver_status"],
                    "total_cost": float(job_row["total_cost"]) if job_row["total_cost"] is not None else None,
                    "status": job_row["status"],
                    "created_at": job_row["created_at"].isoformat() if job_row["created_at"] else None,
                    "completed_at": job_row["completed_at"].isoformat() if job_row["completed_at"] else None,
                    "assets": assets,
                    "results": results,
                    "costs": costs
                }
        
        except Exception as e:
            logger.error("get_optimization_failed", error=str(e), optimization_id=optimization_id)
            return None
