"""
Database client for forecast service
"""
import asyncpg
import os
import structlog
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

logger = structlog.get_logger()


class ForecastDatabase:
    """Database client for storing forecast results"""
    
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
            logger.info("forecast_db_connected", database="forecast_results")
        except Exception as e:
            logger.error("forecast_db_connection_failed", error=str(e))
            raise
    
    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("forecast_db_closed")
    
    async def save_forecast_job(
        self,
        forecast_id: str,
        series_id: str,
        model_name: str,
        horizon: int,
        granularity: str,
        training_samples: Optional[int] = None,
        metrics: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None
    ) -> str:
        """
        Save forecast job metadata
        
        Returns:
            forecast_id: The UUID of the saved forecast job
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO forecast_jobs (
                        forecast_id, series_id, model_name, horizon, granularity,
                        status, training_samples, metrics, created_by, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                    uuid.UUID(forecast_id),
                    series_id,
                    model_name,
                    horizon,
                    granularity,
                    "completed",
                    training_samples,
                    metrics,
                    created_by,
                    datetime.utcnow()
                )
            
            logger.info("forecast_job_saved", forecast_id=forecast_id, model=model_name)
            return forecast_id
        
        except Exception as e:
            logger.error("forecast_job_save_failed", error=str(e), forecast_id=forecast_id)
            raise
    
    async def save_forecast_results(
        self,
        forecast_id: str,
        timestamps: List[datetime],
        values: List[float],
        lower_bounds: Optional[List[float]] = None,
        upper_bounds: Optional[List[float]] = None
    ):
        """Save forecast result data points"""
        try:
            # Prepare data for bulk insert
            records = []
            for i, (ts, val) in enumerate(zip(timestamps, values)):
                lower = lower_bounds[i] if lower_bounds else None
                upper = upper_bounds[i] if upper_bounds else None
                records.append((uuid.UUID(forecast_id), ts, val, lower, upper))
            
            async with self.pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO forecast_results (forecast_id, timestamp, value, lower_bound, upper_bound)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    records
                )
            
            logger.info("forecast_results_saved", forecast_id=forecast_id, count=len(records))
        
        except Exception as e:
            logger.error("forecast_results_save_failed", error=str(e), forecast_id=forecast_id)
            raise
    
    async def mark_forecast_failed(self, forecast_id: str, error_message: str):
        """Mark a forecast job as failed"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE forecast_jobs
                    SET status = 'failed', error_message = $2, completed_at = $3
                    WHERE forecast_id = $1
                    """,
                    uuid.UUID(forecast_id),
                    error_message,
                    datetime.utcnow()
                )
            
            logger.info("forecast_marked_failed", forecast_id=forecast_id)
        
        except Exception as e:
            logger.error("forecast_mark_failed_error", error=str(e), forecast_id=forecast_id)
    
    async def get_forecasts(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Get list of forecast jobs"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT 
                        forecast_id, series_id, model_name, horizon, granularity,
                        status, training_samples, metrics, created_at, completed_at,
                        (SELECT COUNT(*) FROM forecast_results WHERE forecast_results.forecast_id = forecast_jobs.forecast_id) as result_count
                    FROM forecast_jobs
                    ORDER BY created_at DESC
                    LIMIT $1 OFFSET $2
                    """,
                    limit,
                    offset
                )
            
            forecasts = []
            for row in rows:
                forecasts.append({
                    "forecast_id": str(row["forecast_id"]),
                    "series_id": row["series_id"],
                    "model_name": row["model_name"],
                    "horizon": row["horizon"],
                    "granularity": row["granularity"],
                    "status": row["status"],
                    "training_samples": row["training_samples"],
                    "metrics": row["metrics"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
                    "result_count": row["result_count"]
                })
            
            return forecasts
        
        except Exception as e:
            logger.error("get_forecasts_failed", error=str(e))
            return []
    
    async def get_forecast(self, forecast_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific forecast with its results"""
        try:
            async with self.pool.acquire() as conn:
                # Get forecast metadata
                job_row = await conn.fetchrow(
                    """
                    SELECT 
                        forecast_id, series_id, model_name, horizon, granularity,
                        status, training_samples, metrics, created_at, completed_at
                    FROM forecast_jobs
                    WHERE forecast_id = $1
                    """,
                    uuid.UUID(forecast_id)
                )
                
                if not job_row:
                    return None
                
                # Get forecast results
                result_rows = await conn.fetch(
                    """
                    SELECT timestamp, value, lower_bound, upper_bound
                    FROM forecast_results
                    WHERE forecast_id = $1
                    ORDER BY timestamp
                    """,
                    uuid.UUID(forecast_id)
                )
                
                results = []
                for row in result_rows:
                    results.append({
                        "timestamp": row["timestamp"].isoformat(),
                        "value": float(row["value"]),
                        "lower_bound": float(row["lower_bound"]) if row["lower_bound"] is not None else None,
                        "upper_bound": float(row["upper_bound"]) if row["upper_bound"] is not None else None
                    })
                
                return {
                    "forecast_id": str(job_row["forecast_id"]),
                    "series_id": job_row["series_id"],
                    "model_name": job_row["model_name"],
                    "horizon": job_row["horizon"],
                    "granularity": job_row["granularity"],
                    "status": job_row["status"],
                    "training_samples": job_row["training_samples"],
                    "metrics": job_row["metrics"],
                    "created_at": job_row["created_at"].isoformat() if job_row["created_at"] else None,
                    "completed_at": job_row["completed_at"].isoformat() if job_row["completed_at"] else None,
                    "results": results
                }
        
        except Exception as e:
            logger.error("get_forecast_failed", error=str(e), forecast_id=forecast_id)
            return None
