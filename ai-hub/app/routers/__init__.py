"""
API Routers for AI Hub service.

Available routers:
- health: Health check endpoints
- forecast: Time series forecasting
- anomaly: Anomaly detection
- explain: Model explainability
- model_registry: Model lifecycle management
- features: Feature engineering and exports
- training: Model training pipeline and job management
- hpo: Hyperparameter optimization with Optuna
- experiments: Experiment tracking with MLflow
"""

from .health import router as health_router
from .forecast import router as forecast_router
from .anomaly import router as anomaly_router
from .explain import router as explain_router
from .model_registry import router as model_registry_router
from .features import router as features_router
from .training import router as training_router
from .hpo import router as hpo_router
from .experiments import router as experiments_router

__all__ = [
    "health_router",
    "forecast_router",
    "anomaly_router",
    "explain_router",
    "model_registry_router",
    "features_router",
    "training_router",
    "hpo_router",
    "experiments_router",
]
