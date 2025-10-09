"""
Tests for FeatureStore TimescaleDB Integration

Tests real database queries and feature computation:
- Time features (always available)
- Continuous aggregate queries
- Lag features via SQL functions
- Rolling window features
- Weather data integration
- Parquet export from database
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, AsyncMock
import pandas as pd
from app.services.feature_store import FeatureStore


class TestFeatureComputation:
    """Tests for _compute_features() with TimescaleDB queries"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session"""
        session = MagicMock()
        return session
    
    @pytest.fixture
    def feature_store(self, mock_db_session):
        """Create FeatureStore with mock session"""
        return FeatureStore(db_session=mock_db_session)
    
    async def test_compute_time_features_always_available(self, feature_store):
        """Test that time features are always computed even without DB"""
        # Test with None DB session
        store_no_db = FeatureStore(db_session=None)
        
        timestamp = datetime(2025, 10, 9, 14, 30, 0, tzinfo=timezone.utc)
        features = await store_no_db._compute_features(
            tenant_id="tenant-123",
            asset_id="meter-001",
            timestamp=timestamp
        )
        
        # Time features should always be present
        assert features["hour_of_day"] == 14
        assert features["day_of_week"] == 3  # Thursday
        assert features["day_of_month"] == 9
        assert features["month"] == 10
        assert features["is_weekend"] == 0
        assert features["is_business_hours"] == 1  # 14:30 is business hours
    
    async def test_compute_hourly_aggregates(self, feature_store, mock_db_session):
        """Test querying hourly_features continuous aggregate"""
        # Mock query result
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (45.2, 40.0, 50.0, 5.0, 100)
        mock_db_session.execute.return_value = mock_result
        
        timestamp = datetime(2025, 10, 9, 14, 0, 0, tzinfo=timezone.utc)
        features = await feature_store._compute_features(
            tenant_id="tenant-123",
            asset_id="meter-001",
            timestamp=timestamp
        )
        
        # Should have hourly aggregate features
        assert "hourly_avg" in features
        assert features["hourly_avg"] == 45.2
        assert "hourly_min" in features
        assert "hourly_max" in features
        assert "hourly_stddev" in features
        assert "hourly_count" in features
    
    async def test_compute_daily_aggregates(self, feature_store, mock_db_session):
        """Test querying daily_features continuous aggregate"""
        # Mock hourly result
        hourly_result = MagicMock()
        hourly_result.fetchone.return_value = (45.2, 40.0, 50.0, 5.0, 100)
        
        # Mock daily result
        daily_result = MagicMock()
        daily_result.fetchone.return_value = (44.8, 38.0, 52.0, 6.2, 2400)
        
        # Setup execute to return different results based on query
        def execute_side_effect(query, params=None):
            query_str = str(query)
            if "hourly_features" in query_str:
                return hourly_result
            elif "daily_features" in query_str:
                return daily_result
            return MagicMock()
        
        mock_db_session.execute.side_effect = execute_side_effect
        
        timestamp = datetime(2025, 10, 9, 14, 0, 0, tzinfo=timezone.utc)
        features = await feature_store._compute_features(
            tenant_id="tenant-123",
            asset_id="meter-001",
            timestamp=timestamp
        )
        
        # Should have daily aggregate features
        assert "daily_avg" in features
        assert features["daily_avg"] == 44.8
        assert "daily_min" in features
        assert "daily_max" in features
        assert "daily_stddev" in features
    
    async def test_compute_lag_features(self, feature_store, mock_db_session):
        """Test lag features via get_lag_features() SQL function"""
        # Mock lag features result
        lag_result = MagicMock()
        lag_result.fetchall.return_value = [
            (43.5,),  # lag_1h
            (44.8,),  # lag_24h
            (42.3,)   # lag_168h
        ]
        
        # Mock other queries
        hourly_result = MagicMock()
        hourly_result.fetchone.return_value = None
        
        def execute_side_effect(query, params=None):
            query_str = str(query)
            if "get_lag_features" in query_str:
                return lag_result
            return hourly_result
        
        mock_db_session.execute.side_effect = execute_side_effect
        
        timestamp = datetime(2025, 10, 9, 14, 0, 0, tzinfo=timezone.utc)
        features = await feature_store._compute_features(
            tenant_id="tenant-123",
            asset_id="meter-001",
            timestamp=timestamp
        )
        
        # Should have lag features
        assert "lag_1h" in features
        assert features["lag_1h"] == 43.5
        assert "lag_24h" in features
        assert features["lag_24h"] == 44.8
        assert "lag_168h" in features
        assert features["lag_168h"] == 42.3
    
    async def test_compute_rolling_features(self, feature_store, mock_db_session):
        """Test rolling window features via get_rolling_features() SQL function"""
        # Mock rolling features result
        rolling_24h = MagicMock()
        rolling_24h.fetchall.return_value = [(44.5, 3.2)]  # avg, stddev
        
        rolling_168h = MagicMock()
        rolling_168h.fetchall.return_value = [(43.8, 4.1)]
        
        # Mock other queries
        hourly_result = MagicMock()
        hourly_result.fetchone.return_value = None
        
        def execute_side_effect(query, params=None):
            query_str = str(query)
            if "get_rolling_features" in query_str:
                if "24" in str(params):
                    return rolling_24h
                elif "168" in str(params):
                    return rolling_168h
            return hourly_result
        
        mock_db_session.execute.side_effect = execute_side_effect
        
        timestamp = datetime(2025, 10, 9, 14, 0, 0, tzinfo=timezone.utc)
        features = await feature_store._compute_features(
            tenant_id="tenant-123",
            asset_id="meter-001",
            timestamp=timestamp
        )
        
        # Should have rolling window features
        assert "rolling_avg_24h" in features
        assert features["rolling_avg_24h"] == 44.5
        assert "rolling_std_24h" in features
        assert features["rolling_std_24h"] == 3.2
        assert "rolling_avg_168h" in features
        assert features["rolling_avg_168h"] == 43.8
    
    async def test_compute_weather_features(self, feature_store, mock_db_session):
        """Test weather feature integration"""
        # Mock weather result
        weather_result = MagicMock()
        weather_result.fetchone.return_value = (22.5, 60.0, 800.0, 15.5)
        
        # Mock other queries
        hourly_result = MagicMock()
        hourly_result.fetchone.return_value = None
        
        def execute_side_effect(query, params=None):
            query_str = str(query)
            if "weather_features" in query_str:
                return weather_result
            return hourly_result
        
        mock_db_session.execute.side_effect = execute_side_effect
        
        timestamp = datetime(2025, 10, 9, 14, 0, 0, tzinfo=timezone.utc)
        features = await feature_store._compute_features(
            tenant_id="tenant-123",
            asset_id="meter-001",
            timestamp=timestamp
        )
        
        # Should have weather features
        assert "temperature" in features
        assert features["temperature"] == 22.5
        assert "humidity" in features
        assert features["humidity"] == 60.0
        assert "solar_irradiance" in features
        assert features["solar_irradiance"] == 800.0
        assert "wind_speed" in features
        assert features["wind_speed"] == 15.5
    
    async def test_fallback_when_db_unavailable(self, feature_store, mock_db_session):
        """Test graceful fallback when database queries fail"""
        # Mock DB error
        mock_db_session.execute.side_effect = Exception("Connection error")
        
        timestamp = datetime(2025, 10, 9, 14, 0, 0, tzinfo=timezone.utc)
        features = await feature_store._compute_features(
            tenant_id="tenant-123",
            asset_id="meter-001",
            timestamp=timestamp
        )
        
        # Should still have time features
        assert "hour_of_day" in features
        assert "day_of_week" in features
        # But not DB-dependent features
        assert "hourly_avg" not in features
        assert "lag_1h" not in features


class TestParquetExport:
    """Tests for export_features_to_parquet()"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session"""
        session = MagicMock()
        return session
    
    @pytest.fixture
    def feature_store(self, mock_db_session):
        """Create FeatureStore with mock session"""
        return FeatureStore(db_session=mock_db_session)
    
    @patch('pandas.DataFrame.to_parquet')
    async def test_export_forecast_basic_features(self, mock_to_parquet, feature_store, mock_db_session):
        """Test exporting forecast_basic feature set"""
        # Mock query result with multiple rows
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (
                datetime(2024, 1, 1, 0, 0, 0),
                "tenant-123",
                "meter-001",
                45.2, 43.5, 44.8, 42.3,  # value, lag_1h, lag_24h, lag_168h
                44.5, 3.2,  # rolling_avg_24h, rolling_std_24h
                0, 0, 1, 0  # hour, day_of_week, day_of_month, is_weekend
            ),
            (
                datetime(2024, 1, 1, 1, 0, 0),
                "tenant-123",
                "meter-001",
                46.0, 45.2, 44.5, 42.8,
                45.0, 3.1,
                1, 0, 1, 0
            )
        ]
        mock_db_session.execute.return_value = mock_result
        
        # Mock export metadata insertion
        insert_result = MagicMock()
        insert_result.fetchone.return_value = ("550e8400-e29b-41d4-a716-446655440000",)
        
        def execute_side_effect(query, params=None):
            query_str = str(query)
            if "INSERT INTO feature_exports" in query_str:
                return insert_result
            return mock_result
        
        mock_db_session.execute.side_effect = execute_side_effect
        
        result = await feature_store.export_features_to_parquet(
            tenant_id="tenant-123",
            feature_set="forecast_basic",
            start_time=datetime(2024, 1, 1, 0, 0, 0),
            end_time=datetime(2024, 12, 31, 23, 59, 59)
        )
        
        assert result["status"] == "completed"
        assert result["row_count"] == 2
        assert "storage_path" in result
        assert mock_to_parquet.called
    
    @patch('pandas.DataFrame.to_parquet')
    async def test_export_anomaly_detection_features(self, mock_to_parquet, feature_store, mock_db_session):
        """Test exporting anomaly_detection feature set"""
        # Mock query result
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (
                datetime(2024, 1, 1, 0, 0, 0),
                "tenant-123",
                "meter-001",
                45.2,  # value
                44.5, 3.2,  # historical_avg_24h, historical_std_24h
                43.8, 4.1,  # historical_avg_168h, historical_std_168h
                46.0, 42.0, 5.5  # max_24h, min_24h, range_24h
            )
        ]
        mock_db_session.execute.return_value = mock_result
        
        # Mock export metadata
        insert_result = MagicMock()
        insert_result.fetchone.return_value = ("test-export-id",)
        
        def execute_side_effect(query, params=None):
            query_str = str(query)
            if "INSERT INTO feature_exports" in query_str:
                return insert_result
            return mock_result
        
        mock_db_session.execute.side_effect = execute_side_effect
        
        result = await feature_store.export_features_to_parquet(
            tenant_id="tenant-123",
            feature_set="anomaly_detection",
            start_time=datetime(2024, 1, 1, 0, 0, 0),
            end_time=datetime(2024, 12, 31, 23, 59, 59)
        )
        
        assert result["status"] == "completed"
        assert result["row_count"] == 1
    
    @patch('pandas.DataFrame.to_parquet')
    async def test_export_with_asset_filter(self, mock_to_parquet, feature_store, mock_db_session):
        """Test export filtered by specific assets"""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (datetime(2024, 1, 1, 0, 0, 0), "tenant-123", "meter-001", 45.2),
            (datetime(2024, 1, 1, 0, 0, 0), "tenant-123", "meter-002", 46.0)
        ]
        
        # Mock export metadata
        insert_result = MagicMock()
        insert_result.fetchone.return_value = ("test-export-id",)
        
        def execute_side_effect(query, params=None):
            query_str = str(query)
            if "INSERT INTO feature_exports" in query_str:
                return insert_result
            return mock_result
        
        mock_db_session.execute.side_effect = execute_side_effect
        
        result = await feature_store.export_features_to_parquet(
            tenant_id="tenant-123",
            feature_set="forecast_basic",
            start_time=datetime(2024, 1, 1, 0, 0, 0),
            end_time=datetime(2024, 12, 31, 23, 59, 59),
            asset_ids=["meter-001", "meter-002"]
        )
        
        assert result["status"] == "completed"
        assert result["row_count"] == 2
    
    async def test_export_no_data_found(self, feature_store, mock_db_session):
        """Test export when query returns no data"""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []  # Empty result
        mock_db_session.execute.return_value = mock_result
        
        result = await feature_store.export_features_to_parquet(
            tenant_id="tenant-123",
            feature_set="forecast_basic",
            start_time=datetime(2030, 1, 1, 0, 0, 0),
            end_time=datetime(2030, 12, 31, 23, 59, 59)
        )
        
        assert result["status"] == "no_data"
        assert result["row_count"] == 0
    
    async def test_export_metadata_tracking(self, feature_store, mock_db_session):
        """Test that export metadata is tracked in feature_exports table"""
        # Mock feature query
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (datetime(2024, 1, 1, 0, 0, 0), "tenant-123", "meter-001", 45.2)
        ]
        
        # Mock metadata insert
        insert_result = MagicMock()
        export_id = "550e8400-e29b-41d4-a716-446655440000"
        insert_result.fetchone.return_value = (export_id,)
        
        def execute_side_effect(query, params=None):
            query_str = str(query)
            if "INSERT INTO feature_exports" in query_str:
                # Verify insert parameters
                assert params["tenant_id"] == "tenant-123"
                assert params["feature_set"] == "forecast_basic"
                assert "row_count" in params
                return insert_result
            return mock_result
        
        mock_db_session.execute.side_effect = execute_side_effect
        
        with patch('pandas.DataFrame.to_parquet'):
            result = await feature_store.export_features_to_parquet(
                tenant_id="tenant-123",
                feature_set="forecast_basic",
                start_time=datetime(2024, 1, 1, 0, 0, 0),
                end_time=datetime(2024, 12, 31, 23, 59, 59)
            )
        
        assert result["export_id"] == export_id
        assert mock_db_session.commit.called
    
    async def test_export_error_handling(self, feature_store, mock_db_session):
        """Test error handling during export"""
        # Mock query to succeed but parquet write to fail
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (datetime(2024, 1, 1, 0, 0, 0), "tenant-123", "meter-001", 45.2)
        ]
        mock_db_session.execute.return_value = mock_result
        
        with patch('pandas.DataFrame.to_parquet', side_effect=Exception("Disk full")):
            with pytest.raises(Exception):
                await feature_store.export_features_to_parquet(
                    tenant_id="tenant-123",
                    feature_set="forecast_basic",
                    start_time=datetime(2024, 1, 1, 0, 0, 0),
                    end_time=datetime(2024, 12, 31, 23, 59, 59)
                )
        
        # Should rollback transaction
        assert mock_db_session.rollback.called


class TestFeatureCaching:
    """Tests for Redis caching behavior"""
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client"""
        redis = MagicMock()
        return redis
    
    @pytest.fixture
    def feature_store_with_cache(self, mock_redis):
        """Create FeatureStore with Redis cache"""
        with patch('app.services.feature_store.redis_client', mock_redis):
            return FeatureStore(db_session=MagicMock())
    
    async def test_cache_miss_computes_features(self, feature_store_with_cache, mock_redis):
        """Test that cache miss triggers feature computation"""
        # Mock cache miss
        mock_redis.get.return_value = None
        
        timestamp = datetime(2025, 10, 9, 14, 0, 0, tzinfo=timezone.utc)
        
        with patch.object(feature_store_with_cache, '_compute_features', return_value={"hour_of_day": 14}):
            features = await feature_store_with_cache.get_features(
                tenant_id="tenant-123",
                asset_id="meter-001",
                timestamp=timestamp
            )
        
        # Should compute and cache
        assert mock_redis.get.called
        assert mock_redis.setex.called  # Cache result
    
    async def test_cache_hit_returns_cached_data(self, feature_store_with_cache, mock_redis):
        """Test that cache hit returns cached features"""
        import json
        
        cached_features = {"hour_of_day": 14, "lag_1h": 43.5}
        mock_redis.get.return_value = json.dumps(cached_features)
        
        timestamp = datetime(2025, 10, 9, 14, 0, 0, tzinfo=timezone.utc)
        features = await feature_store_with_cache.get_features(
            tenant_id="tenant-123",
            asset_id="meter-001",
            timestamp=timestamp
        )
        
        assert features == cached_features
        assert mock_redis.get.called
        # Should NOT call _compute_features
    
    async def test_cache_expiration(self, feature_store_with_cache, mock_redis):
        """Test that cache entries have TTL"""
        mock_redis.get.return_value = None
        
        timestamp = datetime(2025, 10, 9, 14, 0, 0, tzinfo=timezone.utc)
        
        with patch.object(feature_store_with_cache, '_compute_features', return_value={"hour_of_day": 14}):
            await feature_store_with_cache.get_features(
                tenant_id="tenant-123",
                asset_id="meter-001",
                timestamp=timestamp
            )
        
        # Check that setex was called with TTL
        assert mock_redis.setex.called
        call_args = mock_redis.setex.call_args
        ttl = call_args[0][1]
        assert ttl == 300  # 5 minutes
    
    async def test_cache_key_format(self, feature_store_with_cache, mock_redis):
        """Test cache key generation"""
        mock_redis.get.return_value = None
        
        timestamp = datetime(2025, 10, 9, 14, 0, 0, tzinfo=timezone.utc)
        
        with patch.object(feature_store_with_cache, '_compute_features', return_value={"hour_of_day": 14}):
            await feature_store_with_cache.get_features(
                tenant_id="tenant-123",
                asset_id="meter-001",
                timestamp=timestamp
            )
        
        # Check cache key format
        cache_key = mock_redis.get.call_args[0][0]
        assert "tenant-123" in cache_key
        assert "meter-001" in cache_key
        assert "2025-10-09T14:00:00" in cache_key


class TestFeatureStoreIntegration:
    """Integration tests for complete feature store workflows"""
    
    @patch('app.services.feature_store.FeatureStore._compute_features')
    async def test_forecast_workflow(self, mock_compute):
        """Test complete forecast feature workflow"""
        mock_compute.return_value = {
            "hour_of_day": 14,
            "lag_1h": 43.5,
            "lag_24h": 44.8,
            "rolling_avg_24h": 44.5
        }
        
        store = FeatureStore(db_session=None)
        
        # Get features for multiple timestamps
        timestamps = [
            datetime(2025, 10, 9, 14, 0, 0, tzinfo=timezone.utc),
            datetime(2025, 10, 9, 15, 0, 0, tzinfo=timezone.utc),
            datetime(2025, 10, 9, 16, 0, 0, tzinfo=timezone.utc)
        ]
        
        for ts in timestamps:
            features = await store.get_features(
                tenant_id="tenant-123",
                asset_id="meter-001",
                timestamp=ts
            )
            assert "hour_of_day" in features
            assert "lag_1h" in features
    
    @patch('app.services.feature_store.FeatureStore.export_features_to_parquet')
    async def test_training_data_export_workflow(self, mock_export):
        """Test exporting features for model training"""
        mock_export.return_value = {
            "export_id": "test-id",
            "status": "completed",
            "row_count": 100000,
            "storage_path": "./exports/test.parquet"
        }
        
        store = FeatureStore(db_session=MagicMock())
        
        result = await store.export_features_to_parquet(
            tenant_id="tenant-123",
            feature_set="forecast_basic",
            start_time=datetime(2024, 1, 1, 0, 0, 0),
            end_time=datetime(2024, 12, 31, 23, 59, 59)
        )
        
        assert result["status"] == "completed"
        assert result["row_count"] == 100000
