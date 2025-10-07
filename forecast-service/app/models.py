"""
Pydantic models for forecast service API contracts.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ForecastModel(str, Enum):
    """Available forecasting models."""
    AUTO = "auto"
    ARIMA = "arima"
    ETS = "ets"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    SEASONAL_NAIVE = "seasonal_naive"
    LAST_VALUE = "last_value"
    # NHITS = "nhits"  # Uncomment if using neuralforecast


class ExternalFeatures(BaseModel):
    """External regressors for forecasting."""
    weather: Optional[Dict[str, List[float]]] = Field(
        None, description="Weather features (temperature, humidity, irradiance)"
    )
    calendar: Optional[Dict[str, List[bool]]] = Field(
        None, description="Calendar features (is_holiday, is_weekend)"
    )


class ForecastRequest(BaseModel):
    """Request for time series forecasting."""
    series_id: UUID = Field(..., description="ID of the time series to forecast")
    horizon: int = Field(..., ge=1, le=8760, description="Number of periods to forecast")
    granularity: str = Field(..., description="Forecast granularity (ISO 8601 duration)", pattern=r"^PT?\d+[HMS]$|^P\d+D$")
    start_time: Optional[datetime] = Field(None, description="Start time for forecast")
    model: ForecastModel = Field(ForecastModel.AUTO, description="Forecasting model to use")
    quantiles: List[float] = Field([0.1, 0.5, 0.9], description="Quantiles for probabilistic forecasting")
    external_features: Optional[ExternalFeatures] = None
    training_window: Optional[int] = Field(None, ge=1, description="Number of historical periods for training")
    confidence_level: float = Field(0.95, ge=0.0, le=1.0, description="Confidence level for prediction intervals")

    @field_validator("quantiles")
    @classmethod
    def validate_quantiles(cls, v: List[float]) -> List[float]:
        """Ensure quantiles are between 0 and 1."""
        if not all(0 <= q <= 1 for q in v):
            raise ValueError("All quantiles must be between 0 and 1")
        return sorted(v)


class ForecastMetrics(BaseModel):
    """Forecast quality metrics."""
    mae: Optional[float] = Field(None, description="Mean Absolute Error")
    mape: Optional[float] = Field(None, description="Mean Absolute Percentage Error")
    rmse: Optional[float] = Field(None, description="Root Mean Squared Error")
    pinball_loss: Optional[float] = Field(None, description="Pinball loss for quantile forecasts")


class ForecastMetadata(BaseModel):
    """Additional forecast metadata."""
    training_samples: Optional[int] = None
    training_time_seconds: Optional[float] = None
    feature_importance: Optional[Dict[str, float]] = None


class ForecastResponse(BaseModel):
    """Time series forecast with point predictions and quantiles."""
    forecast_id: UUID = Field(..., description="Unique forecast identifier")
    series_id: UUID = Field(..., description="ID of the forecasted series")
    model_used: str = Field(..., description="Model that produced the forecast")
    created_at: datetime = Field(..., description="When the forecast was generated")
    timestamps: List[datetime] = Field(..., description="Forecast timestamps")
    point_forecast: List[float] = Field(..., description="Point forecast values (median or mean)")
    quantiles: Dict[str, List[float]] = Field(
        default_factory=dict,
        description="Quantile forecasts keyed by quantile level (e.g., 'p10', 'p50', 'p90')"
    )
    metrics: Optional[ForecastMetrics] = None
    metadata: Optional[ForecastMetadata] = None


class TrainRequest(BaseModel):
    """Request to train a model for a specific series."""
    series_id: UUID = Field(..., description="ID of the time series")
    model: ForecastModel = Field(..., description="Model to train")
    training_window: Optional[int] = Field(None, description="Number of historical periods")
    hyperparameters: Optional[Dict[str, Any]] = Field(None, description="Model hyperparameters")


class TrainResponse(BaseModel):
    """Response from model training."""
    model_id: str = Field(..., description="Unique identifier for trained model")
    series_id: UUID
    model_type: str
    training_samples: int
    training_time_seconds: float
    metrics: Optional[ForecastMetrics] = None
    created_at: datetime


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Error response."""
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
