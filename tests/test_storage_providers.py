# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from pathlib import Path
from unittest.mock import Mock

import pytest
from azure.core.exceptions import ResourceNotFoundError
from google.cloud.exceptions import NotFound
from pydantic import SecretStr

from ogion import config
from ogion.models.upload_provider_models import (
    AzureProviderModel,
    DebugProviderModel,
    GCSProviderModel,
    S3ProviderModel,
)
from ogion.upload_providers.azure import UploadProviderAzure
from ogion.upload_providers.base_provider import BaseUploadProvider
from ogion.upload_providers.debug import UploadProviderLocalDebug
from ogion.upload_providers.google_cloud_storage import UploadProviderGCS
from ogion.upload_providers.s3 import UploadProviderS3


def test_gcs_post_save(provider: BaseUploadProvider, provider_prefix: str) -> None:
    fake_backup_dir_path = config.CONST_DATA_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_path = fake_backup_dir_path / "fake_backup"
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.lz.age"

    with open(fake_backup_file_path, "w") as f:
        f.write("abcdefghijk\n12345")

    assert (
        provider.post_save(fake_backup_file_path)
        == f"{provider_prefix}fake_env_name/fake_backup.lz.age"
    )
    # Files are cleaned up immediately after upload in post_save()
    assert not fake_backup_file_age_path.exists()
    assert not fake_backup_file_path.exists()


def test_gcs_clean_local_files(provider: BaseUploadProvider) -> None:
    """Test that clean() doesn't fail when local files don't exist.

    Local files are now cleaned up in post_save(), so clean() only
    handles remote storage cleanup.
    """
    fake_backup_dir_path = config.CONST_DATA_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()

    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup"

    # clean() should work even when local files don't exist
    # (they're already cleaned in post_save())
    provider.clean(fake_backup_file_age_path, 2, 1)

    # Directory should still exist
    assert fake_backup_dir_path.exists()


def test_gcs_clean_gcs_files_short(
    provider: BaseUploadProvider, provider_prefix: str
) -> None:
    fake_backup_dir_path = config.CONST_DATA_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.lz.age"

    (fake_backup_dir_path / "file_19990427_0108_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_19990427_0108_dummy_xfcs")
    (fake_backup_dir_path / "file_20230427_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230427_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230427_0108_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230427_0108_dummy_xfcs")

    assert provider.all_target_backups("fake_env_name") == [
        f"{provider_prefix}fake_env_name/file_20230427_0108_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230427_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_19990427_0108_dummy_xfcs.lz.age",
    ]

    provider.clean(fake_backup_file_age_path, 2, 1)

    assert provider.all_target_backups("fake_env_name") == [
        f"{provider_prefix}fake_env_name/file_20230427_0108_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230427_0105_dummy_xfcs.lz.age",
    ]


def test_gcs_clean_gcs_files_long(
    provider: BaseUploadProvider, provider_prefix: str
) -> None:
    fake_backup_dir_path = config.CONST_DATA_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.lz.age"

    (fake_backup_dir_path / "file_20230127_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230127_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230227_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230227_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230327_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230327_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230425_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230425_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230426_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230426_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230427_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230427_0105_dummy_xfcs")

    assert provider.all_target_backups("fake_env_name") == [
        f"{provider_prefix}fake_env_name/file_20230427_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230426_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230425_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230327_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230227_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230127_0105_dummy_xfcs.lz.age",
    ]

    provider.clean(fake_backup_file_age_path, 2, 1)

    assert provider.all_target_backups("fake_env_name") == [
        f"{provider_prefix}fake_env_name/file_20230427_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230426_0105_dummy_xfcs.lz.age",
    ]


def test_gcs_clean_respects_max_backups_param_and_not_delete_old_files(
    provider: BaseUploadProvider, provider_prefix: str
) -> None:
    fake_backup_dir_path = config.CONST_DATA_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.lz.age"

    (fake_backup_dir_path / "file_20230426_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230426_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230427_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230427_0105_dummy_xfcs")

    assert provider.all_target_backups("fake_env_name") == [
        f"{provider_prefix}fake_env_name/file_20230427_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230426_0105_dummy_xfcs.lz.age",
    ]

    provider.clean(fake_backup_file_age_path, 2, 1)

    assert provider.all_target_backups("fake_env_name") == [
        f"{provider_prefix}fake_env_name/file_20230427_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230426_0105_dummy_xfcs.lz.age",
    ]


def test_gcs_clean_respects_min_retention_days_param_and_not_delete_any_backup(
    provider: BaseUploadProvider, provider_prefix: str
) -> None:
    fake_backup_dir_path = config.CONST_DATA_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.lz.age"

    (fake_backup_dir_path / "file_20230826_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230826_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230825_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230825_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230824_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230824_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230823_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230823_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230729_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230729_0105_dummy_xfcs")

    assert provider.all_target_backups("fake_env_name") == [
        f"{provider_prefix}fake_env_name/file_20230826_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230825_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230824_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230823_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230729_0105_dummy_xfcs.lz.age",
    ]

    provider.clean(fake_backup_file_age_path, 2, 300000)

    assert provider.all_target_backups("fake_env_name") == [
        f"{provider_prefix}fake_env_name/file_20230826_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230825_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230824_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230823_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230729_0105_dummy_xfcs.lz.age",
    ]


def test_gcs_download_backup(
    provider: BaseUploadProvider, provider_prefix: str
) -> None:
    fake_backup_dir_path = config.CONST_DATA_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()

    (fake_backup_dir_path / "file_20230426_0105_dummy_xfcs").write_text("abcdef")
    provider.post_save(fake_backup_dir_path / "file_20230426_0105_dummy_xfcs")

    out = provider.download_backup(
        f"{provider_prefix}fake_env_name/file_20230426_0105_dummy_xfcs.lz.age"
    )

    assert out.is_file()


def test_all_target_backups_edge_cases_with_similar_names(
    provider: BaseUploadProvider, provider_prefix: str
) -> None:
    """Test various edge cases with similar env_names to ensure exact matching.

    Covers cases like:
    - 'db' and 'db_2'
    - 'app' and 'application'
    - 'test' and 'test_env' and 'testing'
    """

    env_names = [
        "db",
        "db_2",
        "db_backup",
        "app",
        "application",
        "test",
        "test_env",
        "testing",
    ]

    for env_name in env_names:
        backup_dir = config.CONST_DATA_FOLDER_PATH / env_name
        backup_dir.mkdir()
        backup_file = backup_dir / f"backup_20230427_0105_{env_name}"
        backup_file.touch()
        provider.post_save(backup_file)

    expected_backup_count = 1
    for env_name in env_names:
        backups = provider.all_target_backups(env_name)
        assert len(backups) == expected_backup_count, (
            f"Expected {expected_backup_count} backup for {env_name}, "
            f"got {len(backups)}: {backups}"
        )
        assert env_name in backups[0], (
            f"Backup path {backups[0]} doesn't contain {env_name}"
        )

        expected_prefix = f"{provider_prefix}{env_name}/"
        assert backups[0].startswith(expected_prefix), (
            f"Backup {backups[0]} doesn't start with expected prefix {expected_prefix}"
        )


def test_gcs_clean_handles_already_deleted_blob(
    provider: BaseUploadProvider,
    provider_prefix: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test clean() handles gracefully when blob already deleted (concurrent)."""
    fake_backup_dir_path = config.CONST_DATA_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.lz.age"

    (fake_backup_dir_path / "file_20230425_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230425_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230426_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230426_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230427_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230427_0105_dummy_xfcs")

    expected_backups_count = 3
    assert len(provider.all_target_backups("fake_env_name")) == expected_backups_count

    # Simulate concurrent deletion by manually deleting one backup
    backups = provider.all_target_backups("fake_env_name")
    oldest_backup = backups[-1]

    # Delete the oldest backup manually to simulate another thread deleting it
    provider_type = type(provider).__name__
    if provider_type == "UploadProviderGCS":
        client = provider.storage_client  # type: ignore[attr-defined]
        bucket = client.bucket(provider.bucket.name)  # type: ignore[attr-defined]
        blob = bucket.blob(oldest_backup)
        blob.delete()
    elif provider_type == "UploadProviderAzure":
        provider.container_client.delete_blob(blob=oldest_backup)  # type: ignore[attr-defined]
    elif provider_type == "UploadProviderS3":
        provider.client.remove_object(provider.bucket, oldest_backup)  # type: ignore[attr-defined]
    elif provider_type == "UploadProviderLocalDebug":
        # For debug provider, manually delete the file
        Path(oldest_backup).unlink(missing_ok=True)

    # Now clean should handle the already-deleted blob gracefully
    # This should not raise an exception even though the oldest backup is gone
    provider.clean(fake_backup_file_age_path, 2, 1)

    # Should still end up with 2 backups
    expected_final_count = 2
    assert len(provider.all_target_backups("fake_env_name")) == expected_final_count


def test_azure_clean_handles_resource_not_found_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test Azure clean() handles ResourceNotFoundError during deletion."""
    # Create a mock Azure provider
    mock_container_client = Mock()
    mock_blob_service_client = Mock()
    mock_blob_service_client.get_container_client.return_value = mock_container_client

    # Mock list_blobs to return 3 backups
    mock_blob_1 = Mock()
    mock_blob_1.name = "fake_env/file_20230425_0105_dummy.lz.age"
    mock_blob_2 = Mock()
    mock_blob_2.name = "fake_env/file_20230426_0105_dummy.lz.age"
    mock_blob_3 = Mock()
    mock_blob_3.name = "fake_env/file_20230427_0105_dummy.lz.age"
    mock_container_client.list_blobs.return_value = [
        mock_blob_1,
        mock_blob_2,
        mock_blob_3,
    ]

    # Mock delete_blob to raise ResourceNotFoundError (concurrent deletion)
    mock_container_client.delete_blob.side_effect = ResourceNotFoundError(
        "Blob not found"
    )

    # Patch BlobServiceClient
    mock_blob_service_client_class = Mock(return_value=mock_blob_service_client)
    mock_blob_service_client_class.from_connection_string = Mock(
        return_value=mock_blob_service_client
    )

    monkeypatch.setattr(
        "azure.storage.blob.BlobServiceClient",
        mock_blob_service_client_class,
    )

    provider_model = AzureProviderModel(
        name="azure",
        container_name="test-container",
        connect_string=SecretStr(
            "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=test=="
        ),
    )
    provider = UploadProviderAzure(provider_model)

    fake_backup_dir_path = config.CONST_DATA_FOLDER_PATH / "fake_env"
    fake_backup_dir_path.mkdir(parents=True, exist_ok=True)
    fake_backup_file = fake_backup_dir_path / "file_20230427_0105_dummy.lz.age"

    # Should not raise exception with ResourceNotFoundError
    provider.clean(fake_backup_file, max_backups=2, min_retention_days=1)

    # Verify delete_blob was called (trying to delete the oldest backup)
    assert mock_container_client.delete_blob.called


def test_gcs_clean_handles_not_found_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test GCS clean() handles NotFound error during deletion."""
    # Create mock GCS components
    mock_blob_1 = Mock()
    mock_blob_1.name = "backups/fake_env/file_20230425_0105_dummy.lz.age"
    mock_blob_2 = Mock()
    mock_blob_2.name = "backups/fake_env/file_20230426_0105_dummy.lz.age"
    mock_blob_3 = Mock()
    mock_blob_3.name = "backups/fake_env/file_20230427_0105_dummy.lz.age"

    # Mock blob.delete() to raise NotFound
    mock_blob_to_delete = Mock()
    mock_blob_to_delete.delete.side_effect = NotFound("Blob not found")  # type: ignore[no-untyped-call]

    mock_bucket = Mock()
    mock_bucket.blob.return_value = mock_blob_to_delete

    mock_storage_client = Mock()
    mock_storage_client.bucket.return_value = mock_bucket
    # Mock list_blobs on storage_client (not bucket)
    mock_storage_client.list_blobs.return_value = [
        mock_blob_1,
        mock_blob_2,
        mock_blob_3,
    ]

    # Patch storage.Client
    mock_client_class = Mock(return_value=mock_storage_client)
    monkeypatch.setattr(
        "google.cloud.storage.Client",
        mock_client_class,
    )

    provider_model = GCSProviderModel(
        name="gcs",
        bucket_name="test-bucket",
        bucket_upload_path="backups",
        service_account_base64=SecretStr("dGVzdA=="),  # base64 "test"
    )
    provider = UploadProviderGCS(provider_model)

    fake_backup_dir_path = config.CONST_DATA_FOLDER_PATH / "fake_env"
    fake_backup_dir_path.mkdir(parents=True, exist_ok=True)
    fake_backup_file = fake_backup_dir_path / "file_20230427_0105_dummy.lz.age"

    # This should not raise an exception even though blob.delete() raises NotFound
    provider.clean(fake_backup_file, max_backups=2, min_retention_days=1)

    # Verify delete was attempted
    assert mock_blob_to_delete.delete.called


def test_s3_clean_filters_no_such_key_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test S3 clean() filters out NoSuchKey errors from delete responses."""
    # Create mock S3 components
    mock_obj_1 = Mock()
    mock_obj_1.object_name = "fake_env/file_20230425_0105_dummy.lz.age"
    mock_obj_2 = Mock()
    mock_obj_2.object_name = "fake_env/file_20230426_0105_dummy.lz.age"
    mock_obj_3 = Mock()
    mock_obj_3.object_name = "fake_env/file_20230427_0105_dummy.lz.age"

    mock_client = Mock()
    mock_client.list_objects.return_value = [mock_obj_1, mock_obj_2, mock_obj_3]

    # Mock remove_objects to return an error with code "NoSuchKey"
    mock_error = Mock()
    mock_error.code = "NoSuchKey"
    mock_client.remove_objects.return_value = [mock_error]

    # Patch Minio
    mock_minio_class = Mock(return_value=mock_client)
    monkeypatch.setattr(
        "minio.Minio",
        mock_minio_class,
    )

    provider_model = S3ProviderModel(
        name="s3",
        bucket_name="test-bucket",
        bucket_upload_path="backups",
        access_key="test",
        secret_key=SecretStr("test"),
    )
    provider = UploadProviderS3(provider_model)

    fake_backup_dir_path = config.CONST_DATA_FOLDER_PATH / "fake_env"
    fake_backup_dir_path.mkdir(parents=True, exist_ok=True)
    fake_backup_file = fake_backup_dir_path / "file_20230427_0105_dummy.lz.age"

    # This should not raise an exception even though NoSuchKey is in the errors
    provider.clean(fake_backup_file, max_backups=2, min_retention_days=1)

    # Verify remove_objects was called
    assert mock_client.remove_objects.called


def test_s3_clean_raises_on_non_no_such_key_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test S3 clean() raises RuntimeError for non-NoSuchKey errors."""
    # Create mock S3 components
    mock_obj_1 = Mock()
    mock_obj_1.object_name = "backups/fake_env/file_20230425_0105_dummy.lz.age"
    mock_obj_2 = Mock()
    mock_obj_2.object_name = "backups/fake_env/file_20230426_0105_dummy.lz.age"
    mock_obj_3 = Mock()
    mock_obj_3.object_name = "backups/fake_env/file_20230427_0105_dummy.lz.age"

    mock_client = Mock()
    mock_client.list_objects.return_value = [mock_obj_1, mock_obj_2, mock_obj_3]

    # Mock remove_objects to return an error with a different code
    mock_error = Mock()
    mock_error.code = "AccessDenied"  # Different error code
    mock_client.remove_objects.return_value = [mock_error]

    # Patch Minio
    mock_minio_class = Mock(return_value=mock_client)
    monkeypatch.setattr(
        "minio.Minio",
        mock_minio_class,
    )

    provider_model = S3ProviderModel(
        name="s3",
        bucket_name="test-bucket",
        bucket_upload_path="backups",
        access_key="test",
        secret_key=SecretStr("test"),
    )
    provider = UploadProviderS3(provider_model)

    fake_backup_dir_path = config.CONST_DATA_FOLDER_PATH / "fake_env"
    fake_backup_dir_path.mkdir(parents=True, exist_ok=True)
    fake_backup_file = fake_backup_dir_path / "file_20230427_0105_dummy.lz.age"

    # This should raise RuntimeError for non-NoSuchKey errors
    with pytest.raises(RuntimeError):
        provider.clean(fake_backup_file, max_backups=2, min_retention_days=1)


def test_provider_close(provider: BaseUploadProvider) -> None:
    """Test that close() method can be called without errors on all providers."""
    # close() should work for all providers
    provider.close()
    # Calling close() multiple times should be safe
    provider.close()


def test_debug_provider_close() -> None:
    """Test debug provider close() method has no side effects."""
    provider = UploadProviderLocalDebug(DebugProviderModel())
    # Should not raise any exception
    provider.close()
    provider.close()  # Multiple calls should be safe


def test_gcs_provider_close(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test GCS provider close() properly closes the storage client."""
    mock_storage_client = Mock()
    mock_bucket = Mock()
    mock_storage_client.bucket.return_value = mock_bucket

    # Mock the Client class
    mock_client_class = Mock(return_value=mock_storage_client)
    monkeypatch.setattr(
        "google.cloud.storage.Client",
        mock_client_class,
    )

    # Mock AnonymousCredentials
    mock_anon_creds = Mock()
    monkeypatch.setattr(
        "google.oauth2.service_account.Credentials.from_service_account_info",
        Mock(return_value=mock_anon_creds),
    )

    provider_model = GCSProviderModel(
        bucket_name="test-bucket",
        bucket_upload_path="test",
        service_account_base64=SecretStr("Z29vZ2xlX3NlcnZpY2VfYWNjb3VudAo="),
        chunk_size_mb=100,
        chunk_timeout_secs=100,
    )
    provider = UploadProviderGCS(provider_model)

    # Verify storage_client exists
    assert hasattr(provider, "storage_client")

    # Call close
    provider.close()

    # Verify close was called on storage_client
    mock_storage_client.close.assert_called_once()

    # Multiple calls should be safe
    provider.close()
    expected_calls = 2
    assert mock_storage_client.close.call_count == expected_calls


def test_azure_provider_close(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test Azure provider close() properly closes the container client."""
    mock_container_client = Mock()
    mock_blob_service_client = Mock()
    mock_blob_service_client.get_container_client.return_value = mock_container_client

    # Mock BlobServiceClient
    mock_blob_service_class = Mock()
    mock_blob_service_class.from_connection_string.return_value = (
        mock_blob_service_client
    )
    monkeypatch.setattr(
        "azure.storage.blob.BlobServiceClient",
        mock_blob_service_class,
    )

    provider_model = AzureProviderModel(
        container_name="test-container",
        connect_string=SecretStr("DefaultEndpointsProtocol=http;AccountName=test;"),
    )
    provider = UploadProviderAzure(provider_model)

    # Verify container_client exists
    assert hasattr(provider, "container_client")

    # Call close
    provider.close()

    # Verify close was called on container_client
    mock_container_client.close.assert_called_once()

    # Multiple calls should be safe
    provider.close()
    expected_calls = 2
    assert mock_container_client.close.call_count == expected_calls


def test_s3_provider_close(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test S3 provider close() properly clears the HTTP connection pool."""
    mock_http = Mock()
    mock_client = Mock()
    mock_client._http = mock_http

    # Mock Minio class
    mock_minio_class = Mock(return_value=mock_client)
    monkeypatch.setattr(
        "minio.Minio",
        mock_minio_class,
    )

    provider_model = S3ProviderModel(
        bucket_name="test-bucket",
        bucket_upload_path="test",
        access_key="test",
        secret_key=SecretStr("test"),
    )
    provider = UploadProviderS3(provider_model)

    # Verify client exists
    assert hasattr(provider, "client")
    assert hasattr(provider.client, "_http")

    # Call close
    provider.close()

    # Verify clear was called on _http
    mock_http.clear.assert_called_once()

    # Multiple calls should be safe
    provider.close()
    expected_calls = 2
    assert mock_http.clear.call_count == expected_calls


def test_s3_provider_close_no_http_attribute(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test S3 provider close() handles missing _http attribute gracefully."""
    mock_client = Mock(spec=[])  # Client without _http attribute

    # Mock Minio class
    mock_minio_class = Mock(return_value=mock_client)
    monkeypatch.setattr(
        "minio.Minio",
        mock_minio_class,
    )

    provider_model = S3ProviderModel(
        bucket_name="test-bucket",
        bucket_upload_path="test",
        access_key="test",
        secret_key=SecretStr("test"),
    )
    provider = UploadProviderS3(provider_model)

    # Should not raise exception even without _http attribute
    provider.close()


def test_gcs_provider_close_no_storage_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test GCS provider close() handles missing storage_client gracefully."""
    mock_storage_client = Mock()
    mock_bucket = Mock()
    mock_storage_client.bucket.return_value = mock_bucket

    # Mock the Client class
    mock_client_class = Mock(return_value=mock_storage_client)
    monkeypatch.setattr(
        "google.cloud.storage.Client",
        mock_client_class,
    )

    # Mock AnonymousCredentials
    mock_anon_creds = Mock()
    monkeypatch.setattr(
        "google.oauth2.service_account.Credentials.from_service_account_info",
        Mock(return_value=mock_anon_creds),
    )

    provider_model = GCSProviderModel(
        bucket_name="test-bucket",
        bucket_upload_path="test",
        service_account_base64=SecretStr("Z29vZ2xlX3NlcnZpY2VfYWNjb3VudAo="),
        chunk_size_mb=100,
        chunk_timeout_secs=100,
    )
    provider = UploadProviderGCS(provider_model)

    # Remove storage_client attribute
    delattr(provider, "storage_client")

    # Should not raise exception
    provider.close()


def test_azure_provider_close_no_container_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test Azure provider close() handles missing container_client gracefully."""
    mock_container_client = Mock()
    mock_blob_service_client = Mock()
    mock_blob_service_client.get_container_client.return_value = mock_container_client

    # Mock BlobServiceClient
    mock_blob_service_class = Mock()
    mock_blob_service_class.from_connection_string.return_value = (
        mock_blob_service_client
    )
    monkeypatch.setattr(
        "azure.storage.blob.BlobServiceClient",
        mock_blob_service_class,
    )

    provider_model = AzureProviderModel(
        container_name="test-container",
        connect_string=SecretStr("DefaultEndpointsProtocol=http;AccountName=test;"),
    )
    provider = UploadProviderAzure(provider_model)

    # Remove container_client attribute
    delattr(provider, "container_client")

    # Should not raise exception
    provider.close()
