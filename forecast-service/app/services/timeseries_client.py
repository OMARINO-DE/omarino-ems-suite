"""
Client for interacting with timeseries-service.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger()


class TimeSeriesClient:
    """Client for timeseries-service API."""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.timeseries_service_url
        self.timeout = self.settings.request_timeout_seconds
    
    async def get_series(self, series_id: UUID):
        """Get series metadata."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/api/series/{series_id}")
            response.raise_for_status()
            return response.json()
    
    async def get_data_points(
        self,
        series_id: UUID,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[dict]:
        """Fetch time series data points."""
        params = {}
        if from_time:
            params["from"] = from_time.isoformat()
        if to_time:
            params["to"] = to_time.isoformat()
        if limit:
            params["limit"] = limit
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/api/series/{series_id}/data",
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    async def health_check(self) -> bool:
        """Check if timeseries service is available."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/health")
                return response.status_code == 200
        except Exception as e:
            logger.warning("timeseries_health_check_failed", error=str(e))
            return False
