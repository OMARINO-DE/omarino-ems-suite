"""
Unit tests for forecast models.
"""
import numpy as np
import pandas as pd
import pytest

from app.models import ForecastRequest, ForecastModel
from app.services.forecast_service import ForecastService
from uuid import uuid4


@pytest.fixture
def sample_time_series():
    """Create sample time series data."""
    dates = pd.date_range(start='2024-01-01', periods=1000, freq='15min')
    
    # Create seasonal pattern with trend and noise
    t = np.arange(len(dates))
    seasonal = 10 * np.sin(2 * np.pi * t / 96)  # Daily seasonality
    trend = 0.01 * t
    noise = np.random.normal(0, 2, len(dates))
    values = 100 + trend + seasonal + noise
    
    return pd.Series(values, index=dates)


@pytest.fixture
def forecast_service():
    """Create forecast service instance."""
    return ForecastService()


class TestForecastService:
    """Tests for ForecastService."""
    
    @pytest.mark.asyncio
    async def test_generate_forecast_last_value(self, forecast_service):
        """Test last value forecast."""
        request = ForecastRequest(
            series_id=uuid4(),
            horizon=24,
            granularity="PT15M",
            model=ForecastModel.LAST_VALUE,
            quantiles=[0.1, 0.5, 0.9]
        )
        
        # Mock the data fetch
        dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
        test_data = pd.Series(np.random.randn(100) + 100, index=dates)
        forecast_service._fetch_historical_data = lambda **kwargs: test_data
        
        response = await forecast_service.generate_forecast(request)
        
        assert response.series_id == request.series_id
        assert len(response.point_forecast) == request.horizon
        assert len(response.timestamps) == request.horizon
        assert response.model_used == "last_value"
        assert all(val == test_data.iloc[-1] for val in response.point_forecast)
    
    def test_create_features(self, forecast_service, sample_time_series):
        """Test feature creation for ML models."""
        lags = [1, 2, 3, 96]
        X, y = forecast_service._create_features(sample_time_series, lags)
        
        # Should have lag features + time features (hour, day_of_week, month)
        assert X.shape[1] == len(lags) + 3
        
        # Should drop NaN rows (max lag = 96)
        assert len(X) == len(sample_time_series) - max(lags)
        assert len(y) == len(X)
    
    def test_seasonal_naive_forecast(self, forecast_service, sample_time_series):
        """Test seasonal naive forecast."""
        request = ForecastRequest(
            series_id=uuid4(),
            horizon=96,
            granularity="PT15M",
            model=ForecastModel.SEASONAL_NAIVE,
            quantiles=[0.5]
        )
        
        forecast, quantiles = forecast_service._forecast_seasonal_naive(
            sample_time_series,
            request
        )
        
        assert len(forecast) == request.horizon
        # First 96 values should match last 96 values of input
        last_season = sample_time_series.values[-96:]
        np.testing.assert_array_equal(forecast[:96], last_season)
    
    def test_parse_granularity(self, forecast_service):
        """Test granularity parsing."""
        assert forecast_service._parse_granularity("PT15M") == "15min"
        assert forecast_service._parse_granularity("PT1H") == "1h"
        assert forecast_service._parse_granularity("P1D") == "1D"
        assert forecast_service._parse_granularity("PT30M") == "30min"
        assert forecast_service._parse_granularity("UNKNOWN") == "15min"  # Default
    
    def test_select_best_model(self, forecast_service):
        """Test automatic model selection."""
        # Short series -> last_value
        short_series = pd.Series(np.random.randn(50))
        assert forecast_service._select_best_model(short_series) == "last_value"
        
        # Medium series -> ets
        medium_series = pd.Series(np.random.randn(300))
        assert forecast_service._select_best_model(medium_series) == "ets"
        
        # Long series -> xgboost
        long_series = pd.Series(np.random.randn(1000))
        assert forecast_service._select_best_model(long_series) == "xgboost"


class TestForecastModels:
    """Tests for individual forecasting models."""
    
    def test_last_value_forecast(self):
        """Test last value persistence model."""
        service = ForecastService()
        data = pd.Series([1, 2, 3, 4, 5])
        request = ForecastRequest(
            series_id=uuid4(),
            horizon=10,
            granularity="PT15M",
            model=ForecastModel.LAST_VALUE
        )
        
        forecast, quantiles = service._forecast_last_value(data, request)
        
        assert len(forecast) == 10
        assert all(val == 5 for val in forecast)
        assert quantiles == {}
    
    def test_generate_quantiles_from_normal(self):
        """Test quantile generation from normal distribution."""
        service = ForecastService()
        point_forecast = np.array([100, 101, 102])
        std_error = 5.0
        quantile_levels = [0.1, 0.5, 0.9]
        
        quantiles = service._generate_quantiles_from_normal(
            point_forecast,
            std_error,
            quantile_levels
        )
        
        assert "p10" in quantiles
        assert "p50" in quantiles
        assert "p90" in quantiles
        
        # p50 should be close to point forecast (median of normal)
        np.testing.assert_array_almost_equal(
            quantiles["p50"],
            point_forecast.tolist(),
            decimal=1
        )
        
        # p10 should be lower than p50, p90 should be higher
        assert all(p10 < p50 < p90 
                   for p10, p50, p90 in zip(quantiles["p10"], 
                                             quantiles["p50"], 
                                             quantiles["p90"]))
