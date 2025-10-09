"""
Model Storage Service

Handles ML model artifact storage in MinIO/S3.
Provides versioning, metadata management, and model lifecycle operations.
"""
from typing import Dict, Any, List, Optional, BinaryIO
from datetime import datetime
import structlog
import json
import boto3
from botocore.exceptions import ClientError
import joblib
import io
import os

logger = structlog.get_logger(__name__)


class ModelStorage:
    """
    Service for storing and retrieving ML models from S3-compatible storage.
    
    Features:
    - Model artifact upload/download
    - Model versioning
    - Metadata management
    - Lifecycle management (staging, production, archived)
    - Integration with MinIO or AWS S3
    """
    
    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        bucket_name: str = "ml-models",
        region_name: str = "us-east-1"
    ):
        """
        Initialize model storage.
        
        Args:
            endpoint_url: S3 endpoint URL (for MinIO, e.g., http://minio:9000)
            aws_access_key_id: AWS access key or MinIO access key
            aws_secret_access_key: AWS secret key or MinIO secret key
            bucket_name: S3 bucket name for model storage
            region_name: AWS region name
        """
        self.bucket_name = bucket_name
        
        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name
        )
        
        # Ensure bucket exists
        self._ensure_bucket_exists()
        
        logger.info(
            "model_storage_initialized",
            bucket=bucket_name,
            endpoint=endpoint_url
        )
    
    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Bucket doesn't exist, create it
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                    logger.info("bucket_created", bucket=self.bucket_name)
                except ClientError as create_error:
                    logger.error(
                        "bucket_creation_failed",
                        error=str(create_error),
                        bucket=self.bucket_name
                    )
            else:
                logger.error("bucket_check_failed", error=str(e))
    
    def _get_model_key(
        self,
        tenant_id: str,
        model_name: str,
        version: str,
        file_type: str = "model"
    ) -> str:
        """
        Generate S3 key for model artifact or metadata.
        
        Args:
            tenant_id: Tenant identifier
            model_name: Model name
            version: Model version
            file_type: 'model', 'metadata', or 'metrics'
        
        Returns:
            S3 object key
        """
        if file_type == "model":
            return f"{tenant_id}/{model_name}/{version}/model.joblib"
        elif file_type == "metadata":
            return f"{tenant_id}/{model_name}/{version}/metadata.json"
        elif file_type == "metrics":
            return f"{tenant_id}/{model_name}/{version}/metrics.json"
        else:
            return f"{tenant_id}/{model_name}/{version}/{file_type}"
    
    async def upload_model(
        self,
        tenant_id: str,
        model_name: str,
        version: str,
        model: Any,
        metadata: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload model artifact and metadata to S3.
        
        Args:
            tenant_id: Tenant identifier
            model_name: Model name (e.g., 'forecast_lgb', 'anomaly_if')
            version: Model version (e.g., 'v1.0.0', '2024-01-15-001')
            model: Trained model object (must be joblib-serializable)
            metadata: Model metadata (hyperparameters, training config, etc.)
            metrics: Model performance metrics (accuracy, RMSE, etc.)
        
        Returns:
            Dictionary with upload results
        """
        try:
            # Serialize model to bytes
            model_buffer = io.BytesIO()
            joblib.dump(model, model_buffer)
            model_buffer.seek(0)
            
            # Upload model artifact
            model_key = self._get_model_key(tenant_id, model_name, version, "model")
            self.s3_client.upload_fileobj(
                model_buffer,
                self.bucket_name,
                model_key,
                ExtraArgs={'ContentType': 'application/octet-stream'}
            )
            
            model_size = model_buffer.getbuffer().nbytes
            
            # Prepare metadata
            full_metadata = {
                "tenant_id": tenant_id,
                "model_name": model_name,
                "version": version,
                "uploaded_at": datetime.utcnow().isoformat(),
                "model_size_bytes": model_size,
                "model_type": type(model).__name__,
                "status": "uploaded",
                **(metadata or {})
            }
            
            # Upload metadata
            metadata_key = self._get_model_key(tenant_id, model_name, version, "metadata")
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=metadata_key,
                Body=json.dumps(full_metadata, default=str),
                ContentType='application/json'
            )
            
            # Upload metrics if provided
            if metrics:
                metrics_key = self._get_model_key(tenant_id, model_name, version, "metrics")
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=metrics_key,
                    Body=json.dumps(metrics, default=str),
                    ContentType='application/json'
                )
            
            logger.info(
                "model_uploaded",
                tenant_id=tenant_id,
                model_name=model_name,
                version=version,
                size_mb=model_size / (1024 * 1024)
            )
            
            return {
                "status": "success",
                "model_key": model_key,
                "metadata_key": metadata_key,
                "model_size_bytes": model_size,
                "version": version
            }
            
        except Exception as e:
            logger.error(
                "model_upload_failed",
                error=str(e),
                tenant_id=tenant_id,
                model_name=model_name,
                version=version
            )
            raise
    
    async def download_model(
        self,
        tenant_id: str,
        model_name: str,
        version: str
    ) -> Any:
        """
        Download model artifact from S3 and deserialize.
        
        Args:
            tenant_id: Tenant identifier
            model_name: Model name
            version: Model version
        
        Returns:
            Deserialized model object
        """
        try:
            model_key = self._get_model_key(tenant_id, model_name, version, "model")
            
            # Download model bytes
            model_buffer = io.BytesIO()
            self.s3_client.download_fileobj(
                self.bucket_name,
                model_key,
                model_buffer
            )
            model_buffer.seek(0)
            
            # Deserialize model
            model = joblib.load(model_buffer)
            
            logger.info(
                "model_downloaded",
                tenant_id=tenant_id,
                model_name=model_name,
                version=version
            )
            
            return model
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.warning(
                    "model_not_found",
                    tenant_id=tenant_id,
                    model_name=model_name,
                    version=version
                )
                raise FileNotFoundError(f"Model not found: {model_key}")
            else:
                logger.error("model_download_failed", error=str(e))
                raise
        except Exception as e:
            logger.error(
                "model_deserialization_failed",
                error=str(e),
                tenant_id=tenant_id,
                model_name=model_name,
                version=version
            )
            raise
    
    async def get_metadata(
        self,
        tenant_id: str,
        model_name: str,
        version: str
    ) -> Dict[str, Any]:
        """
        Get model metadata from S3.
        
        Args:
            tenant_id: Tenant identifier
            model_name: Model name
            version: Model version
        
        Returns:
            Model metadata dictionary
        """
        try:
            metadata_key = self._get_model_key(tenant_id, model_name, version, "metadata")
            
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=metadata_key
            )
            
            metadata = json.loads(response['Body'].read())
            
            return metadata
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.warning("metadata_not_found", key=metadata_key)
                return {}
            else:
                logger.error("metadata_download_failed", error=str(e))
                raise
    
    async def get_metrics(
        self,
        tenant_id: str,
        model_name: str,
        version: str
    ) -> Dict[str, Any]:
        """
        Get model performance metrics from S3.
        
        Args:
            tenant_id: Tenant identifier
            model_name: Model name
            version: Model version
        
        Returns:
            Model metrics dictionary
        """
        try:
            metrics_key = self._get_model_key(tenant_id, model_name, version, "metrics")
            
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=metrics_key
            )
            
            metrics = json.loads(response['Body'].read())
            
            return metrics
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.warning("metrics_not_found", key=metrics_key)
                return {}
            else:
                logger.error("metrics_download_failed", error=str(e))
                raise
    
    async def list_versions(
        self,
        tenant_id: str,
        model_name: str
    ) -> List[Dict[str, Any]]:
        """
        List all versions of a model.
        
        Args:
            tenant_id: Tenant identifier
            model_name: Model name
        
        Returns:
            List of version metadata dictionaries
        """
        try:
            prefix = f"{tenant_id}/{model_name}/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                Delimiter='/'
            )
            
            versions = []
            
            # Get version directories
            if 'CommonPrefixes' in response:
                for prefix_obj in response['CommonPrefixes']:
                    version_prefix = prefix_obj['Prefix']
                    # Extract version from path: tenant/model/version/
                    version = version_prefix.rstrip('/').split('/')[-1]
                    
                    # Get metadata for this version
                    try:
                        metadata = await self.get_metadata(tenant_id, model_name, version)
                        metadata['version'] = version
                        versions.append(metadata)
                    except:
                        # If metadata doesn't exist, add basic info
                        versions.append({
                            "version": version,
                            "model_name": model_name,
                            "tenant_id": tenant_id
                        })
            
            # Sort by version (descending)
            versions.sort(key=lambda x: x.get('uploaded_at', ''), reverse=True)
            
            return versions
            
        except Exception as e:
            logger.error(
                "list_versions_failed",
                error=str(e),
                tenant_id=tenant_id,
                model_name=model_name
            )
            return []
    
    async def delete_model(
        self,
        tenant_id: str,
        model_name: str,
        version: str
    ) -> Dict[str, Any]:
        """
        Delete model artifact and metadata from S3.
        
        Args:
            tenant_id: Tenant identifier
            model_name: Model name
            version: Model version
        
        Returns:
            Deletion result dictionary
        """
        try:
            # Delete all files for this version
            prefix = f"{tenant_id}/{model_name}/{version}/"
            
            # List all objects with this prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            deleted_keys = []
            
            if 'Contents' in response:
                # Delete each object
                for obj in response['Contents']:
                    key = obj['Key']
                    self.s3_client.delete_object(
                        Bucket=self.bucket_name,
                        Key=key
                    )
                    deleted_keys.append(key)
            
            logger.info(
                "model_deleted",
                tenant_id=tenant_id,
                model_name=model_name,
                version=version,
                files_deleted=len(deleted_keys)
            )
            
            return {
                "status": "deleted",
                "version": version,
                "files_deleted": deleted_keys
            }
            
        except Exception as e:
            logger.error(
                "model_deletion_failed",
                error=str(e),
                tenant_id=tenant_id,
                model_name=model_name,
                version=version
            )
            raise
    
    async def copy_model(
        self,
        tenant_id: str,
        model_name: str,
        source_version: str,
        target_version: str
    ) -> Dict[str, Any]:
        """
        Copy model to a new version (useful for promoting staging -> production).
        
        Args:
            tenant_id: Tenant identifier
            model_name: Model name
            source_version: Source version to copy from
            target_version: Target version to copy to
        
        Returns:
            Copy result dictionary
        """
        try:
            source_prefix = f"{tenant_id}/{model_name}/{source_version}/"
            target_prefix = f"{tenant_id}/{model_name}/{target_version}/"
            
            # List all objects in source
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=source_prefix
            )
            
            copied_keys = []
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    source_key = obj['Key']
                    # Generate target key
                    relative_path = source_key[len(source_prefix):]
                    target_key = target_prefix + relative_path
                    
                    # Copy object
                    self.s3_client.copy_object(
                        Bucket=self.bucket_name,
                        CopySource={'Bucket': self.bucket_name, 'Key': source_key},
                        Key=target_key
                    )
                    copied_keys.append(target_key)
                
                # Update metadata with new version
                metadata = await self.get_metadata(tenant_id, model_name, target_version)
                metadata['version'] = target_version
                metadata['copied_from'] = source_version
                metadata['copied_at'] = datetime.utcnow().isoformat()
                
                metadata_key = self._get_model_key(tenant_id, model_name, target_version, "metadata")
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=metadata_key,
                    Body=json.dumps(metadata, default=str),
                    ContentType='application/json'
                )
            
            logger.info(
                "model_copied",
                tenant_id=tenant_id,
                model_name=model_name,
                source_version=source_version,
                target_version=target_version,
                files_copied=len(copied_keys)
            )
            
            return {
                "status": "copied",
                "source_version": source_version,
                "target_version": target_version,
                "files_copied": copied_keys
            }
            
        except Exception as e:
            logger.error(
                "model_copy_failed",
                error=str(e),
                tenant_id=tenant_id,
                model_name=model_name,
                source_version=source_version,
                target_version=target_version
            )
            raise


# Singleton instance
_model_storage_instance: Optional[ModelStorage] = None


def get_model_storage() -> ModelStorage:
    """Get or create model storage singleton"""
    global _model_storage_instance
    
    if _model_storage_instance is None:
        # Get configuration from environment variables
        endpoint_url = os.getenv("MINIO_ENDPOINT_URL")
        access_key = os.getenv("MINIO_ACCESS_KEY", os.getenv("AWS_ACCESS_KEY_ID"))
        secret_key = os.getenv("MINIO_SECRET_KEY", os.getenv("AWS_SECRET_ACCESS_KEY"))
        bucket_name = os.getenv("MODEL_STORAGE_BUCKET", "ml-models")
        
        _model_storage_instance = ModelStorage(
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            bucket_name=bucket_name
        )
    
    return _model_storage_instance
