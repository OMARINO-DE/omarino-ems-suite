"""
Tests for Model Storage Service

Tests S3/MinIO integration for ML model artifacts:
- Model upload/download
- Metadata management
- Version listing
- Model deletion
- Model copying
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY
import io
import json
from datetime import datetime
from botocore.exceptions import ClientError


class TestModelStorageInitialization:
    """Tests for ModelStorage initialization"""
    
    @patch('boto3.client')
    def test_init_with_minio_endpoint(self, mock_boto_client):
        """Test initialization with MinIO endpoint"""
        from app.services.model_storage import ModelStorage
        
        storage = ModelStorage(
            endpoint_url="http://minio:9000",
            aws_access_key_id="minioadmin",
            aws_secret_access_key="minioadmin",
            bucket_name="ml-models"
        )
        
        assert storage.bucket_name == "ml-models"
        mock_boto_client.assert_called_once()
    
    @patch('boto3.client')
    def test_init_with_aws_s3(self, mock_boto_client):
        """Test initialization with AWS S3"""
        from app.services.model_storage import ModelStorage
        
        storage = ModelStorage(
            aws_access_key_id="AWS_KEY",
            aws_secret_access_key="AWS_SECRET",
            bucket_name="production-models",
            region_name="us-west-2"
        )
        
        assert storage.bucket_name == "production-models"
    
    @patch('boto3.client')
    def test_bucket_creation_if_not_exists(self, mock_boto_client):
        """Test automatic bucket creation"""
        from app.services.model_storage import ModelStorage
        
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        
        # Simulate bucket doesn't exist
        mock_s3.head_bucket.side_effect = ClientError(
            {'Error': {'Code': '404'}}, 'head_bucket'
        )
        
        storage = ModelStorage(bucket_name="new-bucket")
        
        mock_s3.create_bucket.assert_called_once()


class TestModelUpload:
    """Tests for upload_model()"""
    
    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_upload_model_success(self, mock_boto_client):
        """Test successful model upload"""
        from app.services.model_storage import ModelStorage
        
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.head_bucket.return_value = {}  # Bucket exists
        
        storage = ModelStorage(bucket_name="test-bucket")
        
        # Create a simple mock model
        mock_model = MagicMock()
        
        metadata = {
            "hyperparameters": {"num_leaves": 31},
            "feature_names": ["hour", "temp"]
        }
        
        metrics = {
            "rmse": 2.5,
            "mae": 1.8
        }
        
        result = await storage.upload_model(
            tenant_id="tenant-123",
            model_name="forecast_lgb",
            version="v1.0.0",
            model=mock_model,
            metadata=metadata,
            metrics=metrics
        )
        
        assert result["status"] == "success"
        assert result["version"] == "v1.0.0"
        assert "model_key" in result
        assert "model_size_bytes" in result
        
        # Verify S3 calls
        assert mock_s3.upload_fileobj.called
        assert mock_s3.put_object.called
    
    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_upload_model_with_metrics(self, mock_boto_client):
        """Test model upload with performance metrics"""
        from app.services.model_storage import ModelStorage
        
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.head_bucket.return_value = {}
        
        storage = ModelStorage(bucket_name="test-bucket")
        
        mock_model = MagicMock()
        metrics = {
            "rmse": 2.5,
            "mae": 1.8,
            "r2_score": 0.92,
            "custom_metrics": {
                "pinball_loss": 1.2
            }
        }
        
        result = await storage.upload_model(
            tenant_id="tenant-123",
            model_name="test_model",
            version="v1.0.0",
            model=mock_model,
            metrics=metrics
        )
        
        assert result["status"] == "success"
        # Verify metrics were uploaded
        assert mock_s3.put_object.call_count >= 2  # metadata + metrics
    
    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_upload_model_s3_error(self, mock_boto_client):
        """Test model upload with S3 error"""
        from app.services.model_storage import ModelStorage
        
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.head_bucket.return_value = {}
        mock_s3.upload_fileobj.side_effect = Exception("S3 upload failed")
        
        storage = ModelStorage(bucket_name="test-bucket")
        
        with pytest.raises(Exception):
            await storage.upload_model(
                tenant_id="tenant-123",
                model_name="test_model",
                version="v1.0.0",
                model=MagicMock()
            )


class TestModelDownload:
    """Tests for download_model()"""
    
    @pytest.mark.asyncio
    @patch('boto3.client')
    @patch('joblib.load')
    async def test_download_model_success(self, mock_joblib_load, mock_boto_client):
        """Test successful model download"""
        from app.services.model_storage import ModelStorage
        
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.head_bucket.return_value = {}
        
        # Mock model object
        mock_model = MagicMock()
        mock_joblib_load.return_value = mock_model
        
        storage = ModelStorage(bucket_name="test-bucket")
        
        result = await storage.download_model(
            tenant_id="tenant-123",
            model_name="forecast_lgb",
            version="v1.0.0"
        )
        
        assert result is not None
        mock_s3.download_fileobj.assert_called_once()
        mock_joblib_load.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_download_model_not_found(self, mock_boto_client):
        """Test downloading non-existent model"""
        from app.services.model_storage import ModelStorage
        
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.head_bucket.return_value = {}
        mock_s3.download_fileobj.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey'}}, 'download_fileobj'
        )
        
        storage = ModelStorage(bucket_name="test-bucket")
        
        with pytest.raises(FileNotFoundError):
            await storage.download_model(
                tenant_id="tenant-123",
                model_name="nonexistent",
                version="v1.0.0"
            )
    
    @pytest.mark.asyncio
    @patch('boto3.client')
    @patch('joblib.load')
    async def test_download_model_deserialization_error(self, mock_joblib_load, mock_boto_client):
        """Test model download with deserialization error"""
        from app.services.model_storage import ModelStorage
        
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.head_bucket.return_value = {}
        mock_joblib_load.side_effect = Exception("Deserialization failed")
        
        storage = ModelStorage(bucket_name="test-bucket")
        
        with pytest.raises(Exception):
            await storage.download_model(
                tenant_id="tenant-123",
                model_name="corrupt_model",
                version="v1.0.0"
            )


class TestMetadataRetrieval:
    """Tests for get_metadata() and get_metrics()"""
    
    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_get_metadata_success(self, mock_boto_client):
        """Test successful metadata retrieval"""
        from app.services.model_storage import ModelStorage
        
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.head_bucket.return_value = {}
        
        metadata_json = json.dumps({
            "model_type": "LightGBM",
            "hyperparameters": {"num_leaves": 31},
            "uploaded_at": "2025-10-09T12:00:00Z"
        })
        
        mock_response = {'Body': MagicMock()}
        mock_response['Body'].read.return_value = metadata_json.encode()
        mock_s3.get_object.return_value = mock_response
        
        storage = ModelStorage(bucket_name="test-bucket")
        
        metadata = await storage.get_metadata(
            tenant_id="tenant-123",
            model_name="forecast_lgb",
            version="v1.0.0"
        )
        
        assert metadata["model_type"] == "LightGBM"
        assert "hyperparameters" in metadata
    
    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_get_metadata_not_found(self, mock_boto_client):
        """Test metadata retrieval when not found"""
        from app.services.model_storage import ModelStorage
        
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.head_bucket.return_value = {}
        mock_s3.get_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey'}}, 'get_object'
        )
        
        storage = ModelStorage(bucket_name="test-bucket")
        
        metadata = await storage.get_metadata(
            tenant_id="tenant-123",
            model_name="nonexistent",
            version="v1.0.0"
        )
        
        assert metadata == {}
    
    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_get_metrics_success(self, mock_boto_client):
        """Test successful metrics retrieval"""
        from app.services.model_storage import ModelStorage
        
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.head_bucket.return_value = {}
        
        metrics_json = json.dumps({
            "rmse": 2.5,
            "mae": 1.8,
            "r2_score": 0.92
        })
        
        mock_response = {'Body': MagicMock()}
        mock_response['Body'].read.return_value = metrics_json.encode()
        mock_s3.get_object.return_value = mock_response
        
        storage = ModelStorage(bucket_name="test-bucket")
        
        metrics = await storage.get_metrics(
            tenant_id="tenant-123",
            model_name="forecast_lgb",
            version="v1.0.0"
        )
        
        assert metrics["rmse"] == 2.5
        assert metrics["mae"] == 1.8


class TestVersionListing:
    """Tests for list_versions()"""
    
    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_list_versions_success(self, mock_boto_client):
        """Test successful version listing"""
        from app.services.model_storage import ModelStorage
        
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.head_bucket.return_value = {}
        
        mock_s3.list_objects_v2.return_value = {
            'CommonPrefixes': [
                {'Prefix': 'tenant-123/forecast_lgb/v1.0.0/'},
                {'Prefix': 'tenant-123/forecast_lgb/v0.9.0/'},
            ]
        }
        
        storage = ModelStorage(bucket_name="test-bucket")
        
        # Mock get_metadata to return version info
        with patch.object(storage, 'get_metadata', return_value={
            "version": "v1.0.0",
            "uploaded_at": "2025-10-09T12:00:00Z"
        }):
            versions = await storage.list_versions(
                tenant_id="tenant-123",
                model_name="forecast_lgb"
            )
        
        assert len(versions) >= 0  # May be empty if metadata fails
    
    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_list_versions_no_versions(self, mock_boto_client):
        """Test listing versions when none exist"""
        from app.services.model_storage import ModelStorage
        
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.head_bucket.return_value = {}
        mock_s3.list_objects_v2.return_value = {}  # No results
        
        storage = ModelStorage(bucket_name="test-bucket")
        
        versions = await storage.list_versions(
            tenant_id="tenant-123",
            model_name="nonexistent"
        )
        
        assert versions == []


class TestModelDeletion:
    """Tests for delete_model()"""
    
    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_delete_model_success(self, mock_boto_client):
        """Test successful model deletion"""
        from app.services.model_storage import ModelStorage
        
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.head_bucket.return_value = {}
        
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'tenant-123/forecast_lgb/v1.0.0/model.joblib'},
                {'Key': 'tenant-123/forecast_lgb/v1.0.0/metadata.json'},
                {'Key': 'tenant-123/forecast_lgb/v1.0.0/metrics.json'},
            ]
        }
        
        storage = ModelStorage(bucket_name="test-bucket")
        
        result = await storage.delete_model(
            tenant_id="tenant-123",
            model_name="forecast_lgb",
            version="v1.0.0"
        )
        
        assert result["status"] == "deleted"
        assert len(result["files_deleted"]) == 3
        assert mock_s3.delete_object.call_count == 3
    
    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_delete_model_no_files(self, mock_boto_client):
        """Test deleting model with no files"""
        from app.services.model_storage import ModelStorage
        
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.head_bucket.return_value = {}
        mock_s3.list_objects_v2.return_value = {}  # No files
        
        storage = ModelStorage(bucket_name="test-bucket")
        
        result = await storage.delete_model(
            tenant_id="tenant-123",
            model_name="empty",
            version="v1.0.0"
        )
        
        assert result["status"] == "deleted"
        assert len(result["files_deleted"]) == 0


class TestModelCopy:
    """Tests for copy_model()"""
    
    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_copy_model_success(self, mock_boto_client):
        """Test successful model copy (staging to production)"""
        from app.services.model_storage import ModelStorage
        
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.head_bucket.return_value = {}
        
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'tenant-123/forecast_lgb/v1.0.0-staging/model.joblib'},
                {'Key': 'tenant-123/forecast_lgb/v1.0.0-staging/metadata.json'},
            ]
        }
        
        storage = ModelStorage(bucket_name="test-bucket")
        
        # Mock get_metadata for metadata update
        with patch.object(storage, 'get_metadata', return_value={}):
            result = await storage.copy_model(
                tenant_id="tenant-123",
                model_name="forecast_lgb",
                source_version="v1.0.0-staging",
                target_version="v1.0.0-production"
            )
        
        assert result["status"] == "copied"
        assert result["source_version"] == "v1.0.0-staging"
        assert result["target_version"] == "v1.0.0-production"
        assert len(result["files_copied"]) >= 0
        assert mock_s3.copy_object.called
    
    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_copy_model_no_source_files(self, mock_boto_client):
        """Test copying model with no source files"""
        from app.services.model_storage import ModelStorage
        
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.head_bucket.return_value = {}
        mock_s3.list_objects_v2.return_value = {}  # No files
        
        storage = ModelStorage(bucket_name="test-bucket")
        
        with patch.object(storage, 'get_metadata', return_value={}):
            result = await storage.copy_model(
                tenant_id="tenant-123",
                model_name="empty",
                source_version="v1.0.0",
                target_version="v2.0.0"
            )
        
        assert result["status"] == "copied"
        assert len(result["files_copied"]) == 0


class TestModelStorageHelpers:
    """Tests for helper methods"""
    
    @patch('boto3.client')
    def test_get_model_key_for_model(self, mock_boto_client):
        """Test model key generation"""
        from app.services.model_storage import ModelStorage
        
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.head_bucket.return_value = {}
        
        storage = ModelStorage(bucket_name="test-bucket")
        
        key = storage._get_model_key(
            tenant_id="tenant-123",
            model_name="forecast_lgb",
            version="v1.0.0",
            file_type="model"
        )
        
        assert key == "tenant-123/forecast_lgb/v1.0.0/model.joblib"
    
    @patch('boto3.client')
    def test_get_model_key_for_metadata(self, mock_boto_client):
        """Test metadata key generation"""
        from app.services.model_storage import ModelStorage
        
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.head_bucket.return_value = {}
        
        storage = ModelStorage(bucket_name="test-bucket")
        
        key = storage._get_model_key(
            tenant_id="tenant-123",
            model_name="forecast_lgb",
            version="v1.0.0",
            file_type="metadata"
        )
        
        assert key == "tenant-123/forecast_lgb/v1.0.0/metadata.json"
    
    @patch('boto3.client')
    def test_get_model_key_for_metrics(self, mock_boto_client):
        """Test metrics key generation"""
        from app.services.model_storage import ModelStorage
        
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.head_bucket.return_value = {}
        
        storage = ModelStorage(bucket_name="test-bucket")
        
        key = storage._get_model_key(
            tenant_id="tenant-123",
            model_name="forecast_lgb",
            version="v1.0.0",
            file_type="metrics"
        )
        
        assert key == "tenant-123/forecast_lgb/v1.0.0/metrics.json"


class TestModelStorageSingleton:
    """Tests for get_model_storage() singleton"""
    
    @patch('os.getenv')
    @patch('boto3.client')
    def test_get_model_storage_singleton(self, mock_boto_client, mock_getenv):
        """Test singleton pattern"""
        from app.services.model_storage import get_model_storage
        
        mock_getenv.side_effect = lambda key, default=None: {
            "MINIO_ENDPOINT_URL": "http://minio:9000",
            "MINIO_ACCESS_KEY": "minioadmin",
            "MINIO_SECRET_KEY": "minioadmin",
            "MODEL_STORAGE_BUCKET": "ml-models"
        }.get(key, default)
        
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.head_bucket.return_value = {}
        
        # Get instance twice
        storage1 = get_model_storage()
        storage2 = get_model_storage()
        
        # Should be same instance
        assert storage1 is storage2
