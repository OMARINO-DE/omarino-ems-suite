"""
Model Cache Service

Handles loading, caching, and serving ML models.
Uses Redis for metadata caching and local filesystem for model storage.
"""
import os
import joblib
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import structlog
from pathlib import Path

logger = structlog.get_logger(__name__)


class ModelCache:
    """
    Service for caching and managing ML models.
    
    Features:
    - LRU cache for model objects
    - Redis metadata caching
    - Filesystem model storage
    - Automatic cache eviction
    """
    
    def __init__(
        self,
        storage_path: str = "./models",
        cache_size: int = 5,
        cache_ttl: int = 3600,
        redis_client = None
    ):
        """
        Initialize model cache.
        
        Args:
            storage_path: Path to model storage directory
            cache_size: Maximum number of models to cache in memory
            cache_ttl: Cache TTL in seconds
            redis_client: Optional Redis client for metadata caching
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.cache_size = cache_size
        self.cache_ttl = cache_ttl
        self.redis_client = redis_client
        
        # In-memory LRU cache
        self._model_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        
        logger.info(
            "model_cache_initialized",
            storage_path=str(self.storage_path),
            cache_size=cache_size,
            cache_ttl=cache_ttl
        )
    
    def _get_model_path(self, tenant_id: str, model_name: str, model_version: str) -> Path:
        """Get filesystem path for model file"""
        return self.storage_path / tenant_id / model_name / f"{model_version}.joblib"
    
    def _get_metadata_path(self, tenant_id: str, model_name: str, model_version: str) -> Path:
        """Get filesystem path for metadata file"""
        return self.storage_path / tenant_id / model_name / f"{model_version}_metadata.json"
    
    def _get_cache_key(self, tenant_id: str, model_name: str, model_version: str) -> str:
        """Generate cache key"""
        return f"{tenant_id}:{model_name}:{model_version}"
    
    def _evict_lru(self):
        """Evict least recently used model from cache"""
        if len(self._model_cache) >= self.cache_size:
            # Find oldest entry
            oldest_key = min(self._cache_timestamps, key=self._cache_timestamps.get)
            
            logger.info("model_cache_eviction", cache_key=oldest_key)
            
            del self._model_cache[oldest_key]
            del self._cache_timestamps[oldest_key]
    
    def _is_cache_expired(self, cache_key: str) -> bool:
        """Check if cached model has expired"""
        if cache_key not in self._cache_timestamps:
            return True
        
        timestamp = self._cache_timestamps[cache_key]
        age = (datetime.utcnow() - timestamp).total_seconds()
        
        return age > self.cache_ttl
    
    async def get_model(
        self,
        tenant_id: str,
        model_name: str,
        model_version: str = "latest"
    ) -> Optional[Any]:
        """
        Get model from cache or load from storage.
        
        Args:
            tenant_id: Tenant identifier
            model_name: Model name
            model_version: Model version (default: "latest")
        
        Returns:
            Model object or None if not found
        """
        cache_key = self._get_cache_key(tenant_id, model_name, model_version)
        
        # Check in-memory cache
        if cache_key in self._model_cache and not self._is_cache_expired(cache_key):
            logger.info("model_cache_hit", cache_key=cache_key)
            self._cache_timestamps[cache_key] = datetime.utcnow()  # Update LRU
            return self._model_cache[cache_key]["model"]
        
        # Load from filesystem
        logger.info("model_cache_miss", cache_key=cache_key)
        model = await self.load_model(tenant_id, model_name, model_version)
        
        if model:
            await self.cache_model(tenant_id, model_name, model_version, model)
        
        return model
    
    async def load_model(
        self,
        tenant_id: str,
        model_name: str,
        model_version: str
    ) -> Optional[Any]:
        """
        Load model from filesystem.
        
        Args:
            tenant_id: Tenant identifier
            model_name: Model name
            model_version: Model version
        
        Returns:
            Model object or None if not found
        """
        model_path = self._get_model_path(tenant_id, model_name, model_version)
        
        if not model_path.exists():
            logger.warning(
                "model_not_found",
                tenant_id=tenant_id,
                model_name=model_name,
                model_version=model_version,
                path=str(model_path)
            )
            return None
        
        try:
            model = joblib.load(model_path)
            
            logger.info(
                "model_loaded",
                tenant_id=tenant_id,
                model_name=model_name,
                model_version=model_version
            )
            
            return model
            
        except Exception as e:
            logger.error(
                "model_load_failed",
                tenant_id=tenant_id,
                model_name=model_name,
                model_version=model_version,
                error=str(e)
            )
            return None
    
    async def cache_model(
        self,
        tenant_id: str,
        model_name: str,
        model_version: str,
        model: Any
    ):
        """
        Cache model in memory.
        
        Args:
            tenant_id: Tenant identifier
            model_name: Model name
            model_version: Model version
            model: Model object to cache
        """
        cache_key = self._get_cache_key(tenant_id, model_name, model_version)
        
        # Evict LRU if cache is full
        self._evict_lru()
        
        self._model_cache[cache_key] = {
            "model": model,
            "tenant_id": tenant_id,
            "model_name": model_name,
            "model_version": model_version
        }
        self._cache_timestamps[cache_key] = datetime.utcnow()
        
        logger.info("model_cached", cache_key=cache_key)
    
    async def save_model(
        self,
        tenant_id: str,
        model_name: str,
        model_version: str,
        model: Any,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Save model to filesystem.
        
        Args:
            tenant_id: Tenant identifier
            model_name: Model name
            model_version: Model version
            model: Model object to save
            metadata: Optional model metadata
        """
        model_path = self._get_model_path(tenant_id, model_name, model_version)
        model_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Save model
            joblib.dump(model, model_path)
            
            # Save metadata
            if metadata:
                metadata_path = self._get_metadata_path(tenant_id, model_name, model_version)
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2, default=str)
            
            logger.info(
                "model_saved",
                tenant_id=tenant_id,
                model_name=model_name,
                model_version=model_version,
                path=str(model_path)
            )
            
        except Exception as e:
            logger.error(
                "model_save_failed",
                tenant_id=tenant_id,
                model_name=model_name,
                model_version=model_version,
                error=str(e)
            )
            raise
    
    async def get_metadata(
        self,
        tenant_id: str,
        model_name: str,
        model_version: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get model metadata.
        
        Args:
            tenant_id: Tenant identifier
            model_name: Model name
            model_version: Model version
        
        Returns:
            Metadata dict or None if not found
        """
        metadata_path = self._get_metadata_path(tenant_id, model_name, model_version)
        
        if not metadata_path.exists():
            return None
        
        try:
            with open(metadata_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(
                "metadata_load_failed",
                tenant_id=tenant_id,
                model_name=model_name,
                model_version=model_version,
                error=str(e)
            )
            return None
    
    async def list_models(self, tenant_id: str) -> List[Dict[str, Any]]:
        """
        List all models for a tenant.
        
        Args:
            tenant_id: Tenant identifier
        
        Returns:
            List of model metadata dicts
        """
        tenant_path = self.storage_path / tenant_id
        
        if not tenant_path.exists():
            return []
        
        models = []
        
        for model_dir in tenant_path.iterdir():
            if not model_dir.is_dir():
                continue
            
            for metadata_file in model_dir.glob("*_metadata.json"):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        models.append(metadata)
                except Exception as e:
                    logger.error(
                        "metadata_read_failed",
                        file=str(metadata_file),
                        error=str(e)
                    )
        
        return models
    
    async def clear_cache(self):
        """Clear all cached models from memory"""
        self._model_cache.clear()
        self._cache_timestamps.clear()
        
        logger.info("model_cache_cleared")
    
    async def warmup(self, models: List[Dict[str, str]]):
        """
        Warmup cache by preloading models.
        
        Args:
            models: List of dicts with tenant_id, model_name, model_version
        """
        logger.info("model_cache_warmup_started", count=len(models))
        
        for model_info in models:
            await self.get_model(
                tenant_id=model_info["tenant_id"],
                model_name=model_info["model_name"],
                model_version=model_info.get("model_version", "latest")
            )
        
        logger.info("model_cache_warmup_completed", count=len(models))


# Singleton instance
_model_cache_instance: Optional[ModelCache] = None


def get_model_cache() -> ModelCache:
    """Get or create model cache singleton"""
    global _model_cache_instance
    
    if _model_cache_instance is None:
        from app.config import get_settings
        settings = get_settings()
        
        _model_cache_instance = ModelCache(
            storage_path=settings.MODEL_STORAGE_PATH,
            cache_size=settings.MODEL_CACHE_SIZE,
            cache_ttl=settings.MODEL_CACHE_TTL
        )
    
    return _model_cache_instance
