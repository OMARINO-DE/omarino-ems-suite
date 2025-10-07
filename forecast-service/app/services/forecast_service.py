"""
Core forecasting service with multiple model implementations.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import uuid4
import time

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from sklearn.ensemble import GradientBoostingRegressor
import xgboost as xgb
import lightgbm as lgb
import structlog

from app.models import (
    ForecastRequest,
    ForecastResponse,
    ForecastMetrics,
    ForecastMetadata,
    ForecastModel,
    TrainRequest,
    TrainResponse
)
from app.services.timeseries_client import TimeSeriesClient

logger = structlog.get_logger()


class ForecastService:
    """Service for generating time series forecasts."""
    
    def __init__(self):
        self.ts_client = TimeSeriesClient()
        self.models_cache: Dict[str, any] = {}
    
    async def generate_forecast(self, request: ForecastRequest) -> ForecastResponse:
        """
        Generate forecast for a time series.
        
        Args:
            request: Forecast request parameters
            
        Returns:
            ForecastResponse with point forecast and quantiles
        """
        start_time = time.time()
        
        # Fetch historical data
        historical_data = await self._fetch_historical_data(
            series_id=request.series_id,
            training_window=request.training_window
        )
        
        if len(historical_data) < 10:
            raise ValueError(f"Insufficient historical data: {len(historical_data)} points. Need at least 10.")
        
        # Select and train model
        model_name = request.model.value
        if model_name == "auto":
            model_name = self._select_best_model(historical_data)
        
        logger.info("model_selected", model=model_name, data_points=len(historical_data))
        
        # Generate forecast based on model type
        if model_name == "arima":
            point_forecast, quantiles = self._forecast_arima(historical_data, request)
        elif model_name == "ets":
            point_forecast, quantiles = self._forecast_ets(historical_data, request)
        elif model_name == "xgboost":
            point_forecast, quantiles = self._forecast_xgboost(historical_data, request)
        elif model_name == "lightgbm":
            point_forecast, quantiles = self._forecast_lightgbm(historical_data, request)
        elif model_name == "seasonal_naive":
            point_forecast, quantiles = self._forecast_seasonal_naive(historical_data, request)
        elif model_name == "last_value":
            point_forecast, quantiles = self._forecast_last_value(historical_data, request)
        else:
            raise ValueError(f"Unknown model: {model_name}")
        
        # Generate timestamps
        last_timestamp = historical_data.index[-1]
        freq = self._parse_granularity(request.granularity)
        timestamps = pd.date_range(
            start=last_timestamp,
            periods=request.horizon + 1,
            freq=freq
        )[1:].tolist()  # Skip the first timestamp as it's the last historical point
        
        training_time = time.time() - start_time
        
        # Calculate metrics if we have test data
        metrics = self._calculate_metrics(historical_data, point_forecast)
        
        return ForecastResponse(
            forecast_id=uuid4(),
            series_id=request.series_id,
            model_used=model_name,
            created_at=datetime.utcnow(),
            timestamps=timestamps,
            point_forecast=point_forecast.tolist(),
            quantiles=quantiles,
            metrics=metrics,
            metadata=ForecastMetadata(
                training_samples=len(historical_data),
                training_time_seconds=round(training_time, 3)
            )
        )
    
    async def train_model(self, request: TrainRequest) -> TrainResponse:
        """Train a model for a specific series."""
        start_time = time.time()
        
        # Fetch historical data
        historical_data = await self._fetch_historical_data(
            series_id=request.series_id,
            training_window=request.training_window
        )
        
        if len(historical_data) < 10:
            raise ValueError(f"Insufficient historical data: {len(historical_data)} points")
        
        # Train model (implementation depends on model type)
        model_id = f"{request.series_id}_{request.model.value}_{int(time.time())}"
        
        training_time = time.time() - start_time
        
        return TrainResponse(
            model_id=model_id,
            series_id=request.series_id,
            model_type=request.model.value,
            training_samples=len(historical_data),
            training_time_seconds=round(training_time, 3),
            created_at=datetime.utcnow()
        )
    
    async def _fetch_historical_data(
        self,
        series_id,
        training_window: Optional[int] = None
    ) -> pd.Series:
        """Fetch historical data from timeseries service."""
        # TODO: Implement actual API call to timeseries-service
        # For now, return dummy data
        logger.info("fetching_historical_data", series_id=str(series_id))
        
        # Generate dummy time series for testing
        periods = training_window if training_window else 1000
        dates = pd.date_range(end=datetime.utcnow(), periods=periods, freq='15min')
        
        # Create seasonal pattern with noise
        t = np.arange(len(dates))
        seasonal = 10 * np.sin(2 * np.pi * t / 96)  # Daily seasonality
        trend = 0.01 * t
        noise = np.random.normal(0, 2, len(dates))
        values = 100 + trend + seasonal + noise
        
        return pd.Series(values, index=dates)
    
    def _select_best_model(self, data: pd.Series) -> str:
        """Select best model based on data characteristics."""
        # Simple heuristics for model selection
        if len(data) < 100:
            return "last_value"
        elif len(data) < 500:
            return "ets"
        else:
            return "xgboost"
    
    def _forecast_arima(
        self,
        data: pd.Series,
        request: ForecastRequest
    ) -> Tuple[np.ndarray, Dict[str, List[float]]]:
        """Generate ARIMA forecast."""
        try:
            model = ARIMA(data, order=(1, 1, 1), seasonal_order=(1, 0, 1, 96))
            fitted = model.fit()
            forecast = fitted.forecast(steps=request.horizon)
            
            # Generate prediction intervals (approximation of quantiles)
            std_error = np.std(fitted.resid) if hasattr(fitted, 'resid') else data.std()
            quantiles = self._generate_quantiles_from_normal(
                forecast,
                std_error,
                request.quantiles
            )
            
            return forecast.values, quantiles
        except Exception as e:
            logger.warning("arima_failed", error=str(e))
            # Fallback to simpler model
            return self._forecast_last_value(data, request)
    
    def _forecast_ets(
        self,
        data: pd.Series,
        request: ForecastRequest
    ) -> Tuple[np.ndarray, Dict[str, List[float]]]:
        """Generate Exponential Smoothing forecast."""
        try:
            model = ExponentialSmoothing(
                data,
                seasonal_periods=96,  # Daily seasonality for 15-min data
                trend='add',
                seasonal='add'
            )
            fitted = model.fit()
            forecast = fitted.forecast(steps=request.horizon)
            
            std_error = np.std(fitted.resid) if hasattr(fitted, 'resid') else data.std()
            quantiles = self._generate_quantiles_from_normal(
                forecast,
                std_error,
                request.quantiles
            )
            
            return forecast.values, quantiles
        except Exception as e:
            logger.warning("ets_failed", error=str(e))
            return self._forecast_last_value(data, request)
    
    def _forecast_xgboost(
        self,
        data: pd.Series,
        request: ForecastRequest
    ) -> Tuple[np.ndarray, Dict[str, List[float]]]:
        """Generate XGBoost forecast with time series features."""
        # Create lagged features
        X, y = self._create_features(data, lags=[1, 2, 3, 96, 672])
        
        # Train model
        model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            objective='reg:squarederror'
        )
        model.fit(X, y)
        
        # Recursive forecasting
        forecast = self._recursive_forecast(model, data, request.horizon, lags=[1, 2, 3, 96, 672])
        
        # Quantile forecasts (train separate models for quantiles)
        quantiles = {}
        for q in request.quantiles:
            q_model = xgb.XGBRegressor(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                objective=f'reg:quantileerror',
                quantile_alpha=q
            )
            q_model.fit(X, y)
            q_forecast = self._recursive_forecast(q_model, data, request.horizon, lags=[1, 2, 3, 96, 672])
            quantiles[f"p{int(q*100)}"] = q_forecast.tolist()
        
        return forecast, quantiles
    
    def _forecast_lightgbm(
        self,
        data: pd.Series,
        request: ForecastRequest
    ) -> Tuple[np.ndarray, Dict[str, List[float]]]:
        """Generate LightGBM forecast."""
        X, y = self._create_features(data, lags=[1, 2, 3, 96, 672])
        
        model = lgb.LGBMRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1
        )
        model.fit(X, y)
        
        forecast = self._recursive_forecast(model, data, request.horizon, lags=[1, 2, 3, 96, 672])
        
        # Generate quantiles
        std_error = np.std(y - model.predict(X))
        quantiles = self._generate_quantiles_from_normal(
            forecast,
            std_error,
            request.quantiles
        )
        
        return forecast, quantiles
    
    def _forecast_seasonal_naive(
        self,
        data: pd.Series,
        request: ForecastRequest
    ) -> Tuple[np.ndarray, Dict[str, List[float]]]:
        """Seasonal naive forecast (last year's values)."""
        seasonal_period = 96  # Daily seasonality for 15-min data
        
        # Repeat the last seasonal period
        last_season = data.values[-seasonal_period:]
        n_repeats = (request.horizon // seasonal_period) + 1
        forecast = np.tile(last_season, n_repeats)[:request.horizon]
        
        return forecast, {}
    
    def _forecast_last_value(
        self,
        data: pd.Series,
        request: ForecastRequest
    ) -> Tuple[np.ndarray, Dict[str, List[float]]]:
        """Naive forecast (last value repeated)."""
        last_value = data.values[-1]
        forecast = np.full(request.horizon, last_value)
        
        return forecast, {}
    
    def _create_features(self, data: pd.Series, lags: List[int]) -> Tuple[np.ndarray, np.ndarray]:
        """Create lagged features for ML models."""
        df = pd.DataFrame({'y': data.values})
        
        # Lagged features
        for lag in lags:
            df[f'lag_{lag}'] = df['y'].shift(lag)
        
        # Time features
        df['hour'] = data.index.hour
        df['day_of_week'] = data.index.dayofweek
        df['month'] = data.index.month
        
        # Drop NaN rows
        df = df.dropna()
        
        X = df.drop('y', axis=1).values
        y = df['y'].values
        
        return X, y
    
    def _recursive_forecast(
        self,
        model,
        data: pd.Series,
        horizon: int,
        lags: List[int]
    ) -> np.ndarray:
        """Generate recursive forecast for ML models."""
        forecast = []
        history = data.values.tolist()
        
        for i in range(horizon):
            # Create features for next step
            features = []
            for lag in lags:
                if lag <= len(history):
                    features.append(history[-lag])
                else:
                    features.append(history[0])
            
            # Add time features (simplified)
            features.extend([0, 0, 0])  # hour, day_of_week, month placeholders
            
            # Predict
            pred = model.predict([features])[0]
            forecast.append(pred)
            history.append(pred)
        
        return np.array(forecast)
    
    def _generate_quantiles_from_normal(
        self,
        point_forecast: np.ndarray,
        std_error: float,
        quantile_levels: List[float]
    ) -> Dict[str, List[float]]:
        """Generate quantile forecasts assuming normal distribution."""
        from scipy.stats import norm
        
        quantiles = {}
        for q in quantile_levels:
            z_score = norm.ppf(q)
            quantile_forecast = point_forecast + z_score * std_error
            quantiles[f"p{int(q*100)}"] = quantile_forecast.tolist()
        
        return quantiles
    
    def _calculate_metrics(
        self,
        historical_data: pd.Series,
        forecast: np.ndarray
    ) -> Optional[ForecastMetrics]:
        """Calculate forecast metrics (if test data available)."""
        # This would be used for backtesting
        # For now, return None as we don't have test data
        return None
    
    def _parse_granularity(self, granularity: str) -> str:
        """Parse ISO 8601 duration to pandas frequency."""
        # Simple mapping for common granularities
        mapping = {
            "PT15M": "15min",
            "PT1H": "1H",
            "P1D": "1D",
            "PT30M": "30min",
            "PT5M": "5min"
        }
        return mapping.get(granularity, "15min")
