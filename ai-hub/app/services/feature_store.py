"""
Feature Store Service

Handles feature extraction, caching, and serving for ML models.
Integrates with TimescaleDB for historical features and Redis for online features.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import structlog
import json

logger = structlog.get_logger(__name__)


class FeatureStore:
    """
    Service for managing ML features.
    
    Features:
    - Online features (Redis cache, <5 min latency)
    - Offline features (TimescaleDB historical data)
    - Feature engineering pipelines
    - Feature versioning
    """
    
    def __init__(
        self,
        redis_client=None,
        db_session=None,
        online_ttl: int = 300  # 5 minutes
    ):
        """
        Initialize feature store.
        
        Args:
            redis_client: Redis client for online features
            db_session: Database session for offline features
            online_ttl: TTL for online features in seconds
        """
        self.redis_client = redis_client
        self.db_session = db_session
        self.online_ttl = online_ttl
        
        logger.info(
            "feature_store_initialized",
            online_ttl=online_ttl
        )
    
    def _get_cache_key(self, tenant_id: str, asset_id: str, feature_type: str) -> str:
        """Generate Redis cache key for features"""
        return f"features:{tenant_id}:{asset_id}:{feature_type}"
    
    async def get_features(
        self,
        tenant_id: str,
        asset_id: str,
        timestamp: Optional[datetime] = None,
        lookback_hours: int = 168,
        feature_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get features for model inference.
        
        Args:
            tenant_id: Tenant identifier
            asset_id: Asset/meter identifier
            timestamp: Point-in-time for features (default: now)
            lookback_hours: Historical lookback period
            feature_names: Specific features to retrieve (default: all)
        
        Returns:
            Dictionary of feature name -> value
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        cache_key = self._get_cache_key(tenant_id, asset_id, "latest")
        
        # Try online cache first (for recent features)
        if self.redis_client:
            try:
                cached = await self.redis_client.get(cache_key)
                if cached:
                    logger.info("feature_cache_hit", cache_key=cache_key)
                    features = json.loads(cached)
                    
                    # Filter by feature_names if specified
                    if feature_names:
                        features = {k: v for k, v in features.items() if k in feature_names}
                    
                    return features
            except Exception as e:
                logger.warning("feature_cache_miss", error=str(e))
        
        # Compute features from database
        features = await self._compute_features(
            tenant_id=tenant_id,
            asset_id=asset_id,
            timestamp=timestamp,
            lookback_hours=lookback_hours
        )
        
        # Filter by feature_names if specified
        if feature_names:
            features = {k: v for k, v in features.items() if k in feature_names}
        
        # Cache online features
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    cache_key,
                    self.online_ttl,
                    json.dumps(features, default=str)
                )
            except Exception as e:
                logger.warning("feature_cache_store_failed", error=str(e))
        
        logger.info(
            "features_computed",
            tenant_id=tenant_id,
            asset_id=asset_id,
            feature_count=len(features)
        )
        
        return features
    
    async def _compute_features(
        self,
        tenant_id: str,
        asset_id: str,
        timestamp: datetime,
        lookback_hours: int
    ) -> Dict[str, Any]:
        """
        Compute features from TimescaleDB.
        
        Queries:
        1. Time-based features (hour, day, month)
        2. Lag features from get_lag_features()
        3. Rolling statistics from get_rolling_features()
        4. Weather features (if available)
        5. Historical aggregates from continuous aggregates
        
        Args:
            tenant_id: Tenant identifier
            asset_id: Asset identifier
            timestamp: Point-in-time for features
            lookback_hours: Historical lookback
        
        Returns:
            Feature dictionary
        """
        features = {}
        
        # Time-based features (always available)
        features.update({
            "hour_of_day": timestamp.hour,
            "day_of_week": timestamp.weekday(),
            "day_of_month": timestamp.day,
            "month": timestamp.month,
            "quarter": (timestamp.month - 1) // 3 + 1,
            "is_weekend": 1 if timestamp.weekday() >= 5 else 0,
        })
        
        # If no database session, return time features only
        if not self.db_session:
            logger.warning("no_db_session", message="Using time features only")
            return features
        
        try:
            # Get hourly aggregates from continuous aggregate
            hourly_query = """
                SELECT 
                    avg_value, std_value, min_value, max_value,
                    median_value, coefficient_of_variation
                FROM hourly_features
                WHERE tenant_id = :tenant_id
                AND asset_id = :asset_id
                AND hour = time_bucket('1 hour', :timestamp::timestamptz)
                LIMIT 1
            """
            
            hourly_result = await self.db_session.execute(
                hourly_query,
                {
                    "tenant_id": tenant_id,
                    "asset_id": asset_id,
                    "timestamp": timestamp
                }
            )
            hourly_row = hourly_result.fetchone()
            
            if hourly_row:
                features.update({
                    "hourly_avg": float(hourly_row[0]) if hourly_row[0] else None,
                    "hourly_std": float(hourly_row[1]) if hourly_row[1] else None,
                    "hourly_min": float(hourly_row[2]) if hourly_row[2] else None,
                    "hourly_max": float(hourly_row[3]) if hourly_row[3] else None,
                    "hourly_median": float(hourly_row[4]) if hourly_row[4] else None,
                    "hourly_cv": float(hourly_row[5]) if hourly_row[5] else None,
                })
            
            # Get daily aggregates
            daily_query = """
                SELECT 
                    avg_value, std_value, min_value, max_value,
                    p10_value, p90_value
                FROM daily_features
                WHERE tenant_id = :tenant_id
                AND asset_id = :asset_id
                AND day = time_bucket('1 day', :timestamp::timestamptz)
                LIMIT 1
            """
            
            daily_result = await self.db_session.execute(
                daily_query,
                {
                    "tenant_id": tenant_id,
                    "asset_id": asset_id,
                    "timestamp": timestamp
                }
            )
            daily_row = daily_result.fetchone()
            
            if daily_row:
                features.update({
                    "daily_avg": float(daily_row[0]) if daily_row[0] else None,
                    "daily_std": float(daily_row[1]) if daily_row[1] else None,
                    "daily_min": float(daily_row[2]) if daily_row[2] else None,
                    "daily_max": float(daily_row[3]) if daily_row[3] else None,
                    "daily_p10": float(daily_row[4]) if daily_row[4] else None,
                    "daily_p90": float(daily_row[5]) if daily_row[5] else None,
                })
            
            # Get lag features using stored function
            lag_query = """
                SELECT lag_hour, lag_value
                FROM get_lag_features(
                    :tenant_id, :asset_id, :timestamp::timestamptz,
                    ARRAY[1, 24, 168]::int[]
                )
            """
            
            lag_result = await self.db_session.execute(
                lag_query,
                {
                    "tenant_id": tenant_id,
                    "asset_id": asset_id,
                    "timestamp": timestamp
                }
            )
            
            for lag_row in lag_result.fetchall():
                lag_hour = lag_row[0]
                lag_value = float(lag_row[1]) if lag_row[1] else None
                features[f"lag_{lag_hour}h"] = lag_value
            
            # Get rolling window features
            for window in [24, 168]:  # 24h and 168h windows
                rolling_query = """
                    SELECT 
                        window_avg, window_std, window_min, window_max,
                        window_median, window_count
                    FROM get_rolling_features(
                        :tenant_id, :asset_id, :timestamp::timestamptz, :window_hours
                    )
                """
                
                rolling_result = await self.db_session.execute(
                    rolling_query,
                    {
                        "tenant_id": tenant_id,
                        "asset_id": asset_id,
                        "timestamp": timestamp,
                        "window_hours": window
                    }
                )
                rolling_row = rolling_result.fetchone()
                
                if rolling_row:
                    prefix = f"rolling_{window}h"
                    features.update({
                        f"{prefix}_avg": float(rolling_row[0]) if rolling_row[0] else None,
                        f"{prefix}_std": float(rolling_row[1]) if rolling_row[1] else None,
                        f"{prefix}_min": float(rolling_row[2]) if rolling_row[2] else None,
                        f"{prefix}_max": float(rolling_row[3]) if rolling_row[3] else None,
                        f"{prefix}_median": float(rolling_row[4]) if rolling_row[4] else None,
                        f"{prefix}_count": int(rolling_row[5]) if rolling_row[5] else 0,
                    })
            
            # Get weather features (if available)
            # Assumes asset has location mapping
            weather_query = """
                SELECT 
                    temperature, humidity, wind_speed, wind_direction,
                    solar_irradiance, cloud_cover, precipitation, pressure
                FROM weather_features
                WHERE tenant_id = :tenant_id
                AND timestamp <= :timestamp::timestamptz
                ORDER BY timestamp DESC
                LIMIT 1
            """
            
            weather_result = await self.db_session.execute(
                weather_query,
                {
                    "tenant_id": tenant_id,
                    "timestamp": timestamp
                }
            )
            weather_row = weather_result.fetchone()
            
            if weather_row:
                features.update({
                    "temperature": float(weather_row[0]) if weather_row[0] else None,
                    "humidity": float(weather_row[1]) if weather_row[1] else None,
                    "wind_speed": float(weather_row[2]) if weather_row[2] else None,
                    "wind_direction": float(weather_row[3]) if weather_row[3] else None,
                    "solar_irradiance": float(weather_row[4]) if weather_row[4] else None,
                    "cloud_cover": float(weather_row[5]) if weather_row[5] else None,
                    "precipitation": float(weather_row[6]) if weather_row[6] else None,
                    "pressure": float(weather_row[7]) if weather_row[7] else None,
                })
            
            logger.info(
                "features_computed_from_db",
                tenant_id=tenant_id,
                asset_id=asset_id,
                feature_count=len(features)
            )
            
        except Exception as e:
            logger.error(
                "feature_computation_error",
                error=str(e),
                tenant_id=tenant_id,
                asset_id=asset_id
            )
            # Return time features as fallback
        
        # Add metadata
        features.update({
            "_tenant_id": tenant_id,
            "_asset_id": asset_id,
            "_timestamp": timestamp.isoformat(),
            "_lookback_hours": lookback_hours
        })
        
        return features
    
    async def store_features(
        self,
        tenant_id: str,
        asset_id: str,
        features: Dict[str, Any],
        feature_type: str = "latest"
    ):
        """
        Store features in online cache.
        
        Args:
            tenant_id: Tenant identifier
            asset_id: Asset identifier
            features: Feature dictionary
            feature_type: Feature type/version
        """
        cache_key = self._get_cache_key(tenant_id, asset_id, feature_type)
        
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    cache_key,
                    self.online_ttl,
                    json.dumps(features, default=str)
                )
                
                logger.info(
                    "features_stored",
                    cache_key=cache_key,
                    feature_count=len(features)
                )
            except Exception as e:
                logger.error("feature_store_failed", error=str(e))
                raise
    
    async def get_batch_features(
        self,
        tenant_id: str,
        asset_ids: List[str],
        timestamp: Optional[datetime] = None,
        lookback_hours: int = 168
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get features for multiple assets (batch inference).
        
        Args:
            tenant_id: Tenant identifier
            asset_ids: List of asset identifiers
            timestamp: Point-in-time for features
            lookback_hours: Historical lookback
        
        Returns:
            Dictionary of asset_id -> features
        """
        results = {}
        
        for asset_id in asset_ids:
            features = await self.get_features(
                tenant_id=tenant_id,
                asset_id=asset_id,
                timestamp=timestamp,
                lookback_hours=lookback_hours
            )
            results[asset_id] = features
        
        logger.info(
            "batch_features_computed",
            tenant_id=tenant_id,
            asset_count=len(asset_ids)
        )
        
        return results
    
    async def compute_feature_set(
        self,
        tenant_id: str,
        asset_id: str,
        feature_set_name: str,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Compute predefined feature set.
        
        Feature sets are collections of features for specific models.
        Examples: "forecast_basic", "forecast_advanced", "anomaly_detection"
        
        Args:
            tenant_id: Tenant identifier
            asset_id: Asset identifier
            feature_set_name: Name of feature set
            timestamp: Point-in-time for features
        
        Returns:
            Feature dictionary
        """
        # Define feature sets
        feature_sets = {
            "forecast_basic": [
                "hour_of_day",
                "day_of_week",
                "is_weekend",
                "historical_avg_24h",
                "lag_1h",
                "lag_24h"
            ],
            "forecast_advanced": [
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
            "anomaly_detection": [
                "hour_of_day",
                "day_of_week",
                "historical_avg_24h",
                "historical_std_24h",
                "historical_min_24h",
                "historical_max_24h",
                "lag_1h"
            ]
        }
        
        feature_names = feature_sets.get(feature_set_name)
        
        if not feature_names:
            logger.warning("unknown_feature_set", feature_set_name=feature_set_name)
            # Return all features as fallback
            feature_names = None
        
        return await self.get_features(
            tenant_id=tenant_id,
            asset_id=asset_id,
            timestamp=timestamp,
            feature_names=feature_names
        )
    
    async def invalidate_cache(self, tenant_id: str, asset_id: str):
        """
        Invalidate cached features for an asset.
        
        Args:
            tenant_id: Tenant identifier
            asset_id: Asset identifier
        """
        if self.redis_client:
            pattern = f"features:{tenant_id}:{asset_id}:*"
            
            try:
                # Note: This is a simplified version
                # In production, use SCAN for large key sets
                cache_key = self._get_cache_key(tenant_id, asset_id, "latest")
                await self.redis_client.delete(cache_key)
                
                logger.info(
                    "feature_cache_invalidated",
                    tenant_id=tenant_id,
                    asset_id=asset_id
                )
            except Exception as e:
                logger.error("feature_cache_invalidation_failed", error=str(e))
    
    async def export_features_to_parquet(
        self,
        tenant_id: str,
        feature_set: str,
        start_time: datetime,
        end_time: datetime,
        asset_ids: Optional[List[str]] = None,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Export features to Parquet format for offline training.
        
        This queries the appropriate feature materialized views and exports
        to Parquet files for batch model training.
        
        Args:
            tenant_id: Tenant identifier
            feature_set: Feature set name ('forecast_basic', 'anomaly_detection', etc.)
            start_time: Start of time range
            end_time: End of time range
            asset_ids: Optional list of specific assets (default: all)
            output_path: Optional output path (default: generated)
        
        Returns:
            Dictionary with export metadata (path, row_count, file_size)
        """
        import pandas as pd
        import uuid
        import os
        
        if not self.db_session:
            raise ValueError("Database session required for feature export")
        
        # Map feature sets to views
        view_mapping = {
            "forecast_basic": "forecast_basic_features",
            "forecast_advanced": "forecast_basic_features",  # Will add weather join
            "anomaly_detection": "anomaly_detection_features",
        }
        
        view_name = view_mapping.get(feature_set)
        if not view_name:
            raise ValueError(f"Unknown feature set: {feature_set}")
        
        try:
            # Build query
            query = f"""
                SELECT *
                FROM {view_name}
                WHERE tenant_id = :tenant_id
                AND timestamp BETWEEN :start_time AND :end_time
            """
            
            params = {
                "tenant_id": tenant_id,
                "start_time": start_time,
                "end_time": end_time
            }
            
            if asset_ids:
                query += " AND asset_id = ANY(:asset_ids)"
                params["asset_ids"] = asset_ids
            
            query += " ORDER BY asset_id, timestamp"
            
            # Execute query and load into DataFrame
            result = await self.db_session.execute(query, params)
            rows = result.fetchall()
            columns = result.keys()
            
            df = pd.DataFrame(rows, columns=columns)
            
            if df.empty:
                logger.warning(
                    "no_features_for_export",
                    tenant_id=tenant_id,
                    feature_set=feature_set,
                    start_time=start_time,
                    end_time=end_time
                )
                return {
                    "status": "no_data",
                    "row_count": 0,
                    "file_size_bytes": 0
                }
            
            # Generate output path if not provided
            if not output_path:
                export_id = str(uuid.uuid4())
                os.makedirs("./exports", exist_ok=True)
                output_path = f"./exports/{tenant_id}_{feature_set}_{export_id}.parquet"
            
            # Write to Parquet
            df.to_parquet(
                output_path,
                engine='pyarrow',
                compression='snappy',
                index=False
            )
            
            # Get file size
            file_size = os.path.getsize(output_path)
            
            # Store export metadata in database
            export_metadata = {
                "tenant_id": tenant_id,
                "feature_set": feature_set,
                "start_time": start_time,
                "end_time": end_time,
                "asset_ids": asset_ids,
                "storage_path": output_path,
                "row_count": len(df),
                "file_size_bytes": file_size,
                "status": "completed"
            }
            
            # Insert into feature_exports table
            insert_query = """
                INSERT INTO feature_exports (
                    tenant_id, feature_set, start_time, end_time,
                    asset_ids, export_format, storage_path, row_count,
                    file_size_bytes, status, completed_at
                ) VALUES (
                    :tenant_id, :feature_set, :start_time, :end_time,
                    :asset_ids, 'parquet', :storage_path, :row_count,
                    :file_size_bytes, 'completed', NOW()
                )
                RETURNING export_id
            """
            
            export_result = await self.db_session.execute(insert_query, export_metadata)
            export_id = export_result.fetchone()[0]
            export_metadata["export_id"] = str(export_id)
            
            await self.db_session.commit()
            
            logger.info(
                "features_exported_to_parquet",
                export_id=export_id,
                row_count=len(df),
                file_size_mb=file_size / (1024 * 1024),
                output_path=output_path
            )
            
            return export_metadata
            
        except Exception as e:
            logger.error(
                "feature_export_failed",
                error=str(e),
                tenant_id=tenant_id,
                feature_set=feature_set
            )
            
            # Update status to failed
            if self.db_session:
                try:
                    await self.db_session.execute(
                        """
                        INSERT INTO feature_exports (
                            tenant_id, feature_set, start_time, end_time,
                            status, error_message
                        ) VALUES (
                            :tenant_id, :feature_set, :start_time, :end_time,
                            'failed', :error
                        )
                        """,
                        {
                            "tenant_id": tenant_id,
                            "feature_set": feature_set,
                            "start_time": start_time,
                            "end_time": end_time,
                            "error": str(e)
                        }
                    )
                    await self.db_session.commit()
                except:
                    pass
            
            raise


# Singleton instance
_feature_store_instance: Optional[FeatureStore] = None


def get_feature_store() -> FeatureStore:
    """Get or create feature store singleton"""
    global _feature_store_instance
    
    if _feature_store_instance is None:
        # TODO: Initialize with actual Redis and DB connections
        _feature_store_instance = FeatureStore()
    
    return _feature_store_instance
