"""
Forecast router with forecasting endpoints.
"""
from datetime import datetime, timedelta
from uuid import uuid4
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status, Request
import structlog

from app.models import (
    ForecastRequest,
    ForecastResponse,
    ForecastMetrics,
    ForecastMetadata,
    TrainRequest,
    TrainResponse,
    ForecastModel as ForecastModelEnum
)
from app.services.forecast_service import ForecastService

logger = structlog.get_logger()
router = APIRouter()
forecast_service = ForecastService()


@router.post("/forecast", response_model=ForecastResponse, status_code=status.HTTP_200_OK)
async def request_forecast(req: Request, request: ForecastRequest):
    """
    Generate forecast for a time series.
    
    Supports multiple forecasting models:
    - **auto**: Automatically select best model
    - **arima**: AutoARIMA (classical statistical)
    - **ets**: Exponential Smoothing (classical statistical)
    - **xgboost**: Gradient boosting (ML)
    - **lightgbm**: Light gradient boosting (ML)
    - **seasonal_naive**: Simple seasonal baseline
    - **last_value**: Naive last-value baseline
    
    Returns point forecast and quantile predictions.
    """
    try:
        logger.info("forecast_request_received",
                    series_id=str(request.series_id),
                    horizon=request.horizon,
                    model=request.model.value)
        
        # Generate forecast
        result = await forecast_service.generate_forecast(request)
        
        logger.info("forecast_generated",
                    forecast_id=str(result.forecast_id),
                    series_id=str(request.series_id),
                    model_used=result.model_used,
                    points=len(result.point_forecast))
        
        # Save to database if available
        if hasattr(req.app.state, "forecast_db") and req.app.state.forecast_db:
            try:
                db = req.app.state.forecast_db
                
                # Save forecast job
                await db.save_forecast_job(
                    forecast_id=str(result.forecast_id),
                    series_id=str(request.series_id),
                    model_name=result.model_used,
                    horizon=request.horizon,
                    granularity=request.granularity,
                    training_samples=len(request.historical_data),
                    metrics={
                        "mae": result.metrics.mae if result.metrics else None,
                        "rmse": result.metrics.rmse if result.metrics else None,
                        "mape": result.metrics.mape if result.metrics else None
                    } if result.metrics else None
                )
                
                # Save forecast results
                timestamps = [datetime.fromisoformat(ts.replace('Z', '+00:00')) for ts in result.timestamps]
                values = result.point_forecast
                lower_bounds = result.quantiles.get("0.05", []) if result.quantiles else None
                upper_bounds = result.quantiles.get("0.95", []) if result.quantiles else None
                
                await db.save_forecast_results(
                    forecast_id=str(result.forecast_id),
                    timestamps=timestamps,
                    values=values,
                    lower_bounds=lower_bounds,
                    upper_bounds=upper_bounds
                )
                
                logger.info("forecast_saved_to_database", forecast_id=str(result.forecast_id))
            except Exception as e:
                # Don't fail the request if database save fails
                logger.error("forecast_database_save_failed", error=str(e), forecast_id=str(result.forecast_id))
        
        return result
        
    except ValueError as e:
        logger.error("forecast_validation_error",
                     series_id=str(request.series_id),
                     error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("forecast_generation_failed",
                     series_id=str(request.series_id),
                     error=str(e),
                     exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forecast generation failed: {str(e)}"
        )


@router.post("/train", response_model=TrainResponse, status_code=status.HTTP_201_CREATED)
async def train_model(request: TrainRequest):
    """
    Train a forecasting model for a specific series.
    
    This endpoint allows pre-training models that can be reused for multiple forecasts.
    The trained model is stored and can be referenced by model_id in subsequent requests.
    """
    try:
        logger.info("model_training_requested",
                    series_id=str(request.series_id),
                    model=request.model.value)
        
        result = await forecast_service.train_model(request)
        
        logger.info("model_trained",
                    model_id=result.model_id,
                    series_id=str(request.series_id),
                    training_time=result.training_time_seconds)
        
        return result
        
    except ValueError as e:
        logger.error("training_validation_error",
                     series_id=str(request.series_id),
                     error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("model_training_failed",
                     series_id=str(request.series_id),
                     error=str(e),
                     exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model training failed: {str(e)}"
        )


@router.get("/forecasts")
async def get_forecasts(req: Request, limit: int = 20, offset: int = 0):
    """Get list of saved forecasts."""
    try:
        if not hasattr(req.app.state, "forecast_db") or not req.app.state.forecast_db:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database not available"
            )
        
        db = req.app.state.forecast_db
        forecasts = await db.get_forecasts(limit=limit, offset=offset)
        
        return {
            "forecasts": forecasts,
            "limit": limit,
            "offset": offset,
            "count": len(forecasts)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_forecasts_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve forecasts: {str(e)}"
        )


@router.get("/forecasts/{forecast_id}")
async def get_forecast(req: Request, forecast_id: str):
    """Get a specific forecast with full results."""
    try:
        if not hasattr(req.app.state, "forecast_db") or not req.app.state.forecast_db:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database not available"
            )
        
        db = req.app.state.forecast_db
        forecast = await db.get_forecast(forecast_id)
        
        if not forecast:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Forecast {forecast_id} not found"
            )
        
        return forecast
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_forecast_failed", error=str(e), forecast_id=forecast_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve forecast: {str(e)}"
        )


@router.get("/models")
async def list_models():
    """List available forecasting models and their descriptions."""
    return {
        "models": [
            {
                "name": "auto",
                "description": "Automatically select best model based on data characteristics",
                "type": "ensemble",
                "supports_quantiles": True
            },
            {
                "name": "arima",
                "description": "AutoARIMA - Automatic ARIMA model selection",
                "type": "classical",
                "supports_quantiles": True
            },
            {
                "name": "ets",
                "description": "Exponential Smoothing State Space Model",
                "type": "classical",
                "supports_quantiles": True
            },
            {
                "name": "xgboost",
                "description": "XGBoost with time series features",
                "type": "machine_learning",
                "supports_quantiles": True
            },
            {
                "name": "lightgbm",
                "description": "LightGBM with time series features",
                "type": "machine_learning",
                "supports_quantiles": True
            },
            {
                "name": "seasonal_naive",
                "description": "Seasonal naive baseline (last year's value)",
                "type": "baseline",
                "supports_quantiles": False
            },
            {
                "name": "last_value",
                "description": "Simple persistence model (last observed value)",
                "type": "baseline",
                "supports_quantiles": False
            }
        ]
    }
