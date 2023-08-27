from pathlib import Path
from unittest.mock import Mock

import google.cloud.storage as storage
import pytest
from freezegun import freeze_time
from pydantic import SecretStr

from backuper.upload_providers import UploadProviderGCS


@pytest.fixture(autouse=True)
def mock_google_storage_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(storage, "Client", Mock())


def get_test_gcs() -> UploadProviderGCS:
    return UploadProviderGCS(
        bucket_name="name",
        bucket_upload_path="test",
        service_account_base64=SecretStr("Z29vZ2xlX3NlcnZpY2VfYWNjb3VudAo="),
        chunk_size_mb=100,
        chunk_timeout_secs=100,
    )


def test_gcs_post_save_fails_on_fail_upload(tmp_path: Path) -> None:
    gcs = get_test_gcs()
    bucket_mock = Mock()
    single_blob_mock = Mock()
    single_blob_mock.upload_from_filename.side_effect = ValueError()
    bucket_mock.blob.return_value = single_blob_mock
    gcs.bucket = bucket_mock

    fake_backup_file_path = tmp_path / "fake_backup"
    fake_backup_file_path.touch()
    with pytest.raises(ValueError):
        assert gcs.post_save(fake_backup_file_path)


@pytest.mark.parametrize("gcs_method_name", ["_post_save", "post_save"])
def test_gcs_post_save_with_google_bucket_upload_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, gcs_method_name: str
) -> None:
    gcs = get_test_gcs()
    bucket_mock = Mock()

    single_blob_mock = Mock()
    bucket_mock.blob.return_value = single_blob_mock
    gcs.bucket = bucket_mock

    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_path = fake_backup_dir_path / "fake_backup"
    fake_backup_file_zip_path = fake_backup_dir_path / "fake_backup.zip"
    with open(fake_backup_file_path, "w") as f:
        f.write("abcdefghijk\n12345")

    monkeypatch.setattr(gcs, "bucket_upload_path", "test123")
    assert (
        getattr(gcs, gcs_method_name)(fake_backup_file_path)
        == "test123/fake_env_name/fake_backup.zip"
    )
    assert fake_backup_file_zip_path.exists()
    bucket_mock.blob.assert_called_once_with(
        "test123/fake_env_name/fake_backup.zip",
        chunk_size=gcs.chunk_size_bytes,
    )
    single_blob_mock.upload_from_filename.assert_called_once_with(
        fake_backup_file_zip_path,
        timeout=gcs.chunk_timeout_secs,
        if_generation_match=0,
        checksum="crc32c",
    )


class BlobInCloudStorage:
    def __init__(self, blob_name: str) -> None:
        self.name = blob_name


list_blobs_short_with_upload_path: list[BlobInCloudStorage] = [
    BlobInCloudStorage("test123/fake_env_name/file_20230427_0105_dummy_xfcs.zip"),
    BlobInCloudStorage("test123/fake_env_name/file_20230427_0108_dummy_xfcs.zip"),
    BlobInCloudStorage("test123/fake_env_name/file_19990427_0108_dummy_xfcs.zip"),
]
list_blobs_long_no_upload_path: list[BlobInCloudStorage] = [
    BlobInCloudStorage("test123/fake_env_name/file_20230427_0105_dummy_xfcs.zip"),
    BlobInCloudStorage("test123/fake_env_name/file_20230127_0105_dummy_xfcs.zip"),
    BlobInCloudStorage("test123/fake_env_name/file_20230426_0105_dummy_xfcs.zip"),
    BlobInCloudStorage("test123/fake_env_name/file_20230227_0105_dummy_xfcs.zip.zip"),
    BlobInCloudStorage("test123/fake_env_name/file_20230425_0105_dummy_xfcs.zip.zip"),
    BlobInCloudStorage("test123/fake_env_name/file_20230327_0105_dummy_xfcs.zip.zip"),
]


@pytest.mark.parametrize("gcs_method_name", ["_clean", "clean"])
def test_gcs_clean_file_and_short_blob_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, gcs_method_name: str
) -> None:
    gcs = get_test_gcs()

    bucket_mock = Mock()
    storage_client_mock = Mock()
    single_blob_mock = Mock()

    storage_client_mock.list_blobs.return_value = list_blobs_short_with_upload_path
    bucket_mock.blob.return_value = single_blob_mock

    gcs.storage_client = storage_client_mock
    gcs.bucket = bucket_mock

    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_zip_path = fake_backup_dir_path / "fake_backup.zip"
    fake_backup_file_zip_path.touch()
    fake_backup_file_zip_path2 = fake_backup_dir_path / "fake_backup2.zip"
    fake_backup_file_zip_path2.touch()

    monkeypatch.setattr(gcs, "bucket_upload_path", "test123")

    getattr(gcs, gcs_method_name)(fake_backup_file_zip_path, 2, 1)
    assert fake_backup_dir_path.exists()
    assert not fake_backup_file_zip_path.exists()
    assert not fake_backup_file_zip_path2.exists()

    bucket_mock.blob.assert_called_once_with(
        "test123/fake_env_name/file_19990427_0108_dummy_xfcs.zip"
    )
    single_blob_mock.delete.assert_called_once_with()


@pytest.mark.parametrize("gcs_method_name", ["_clean", "clean"])
def test_gcs_clean_directory_and_long_blob_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, gcs_method_name: str
) -> None:
    gcs = get_test_gcs()

    bucket_mock = Mock()
    storage_client_mock = Mock()
    single_blob_mock = Mock()

    storage_client_mock.list_blobs.return_value = list_blobs_long_no_upload_path
    bucket_mock.blob.return_value = single_blob_mock

    gcs.storage_client = storage_client_mock
    gcs.bucket = bucket_mock

    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_zip_path = fake_backup_dir_path / "fake_backup.zip"
    fake_backup_file_zip_path.touch()
    fake_backup_file_zip_path2 = fake_backup_dir_path / "fake_backup2.zip"
    fake_backup_file_zip_path2.touch()
    fake_backup_dir_path2 = tmp_path / "fake_env_name2"
    fake_backup_dir_path2.mkdir()
    fake_backup_file_zip_path3 = fake_backup_dir_path2 / "fake_backup.zip"
    fake_backup_file_zip_path3.touch()
    fake_backup_file_zip_path4 = fake_backup_dir_path2 / "fake_backup2.zip"
    fake_backup_file_zip_path4.touch()

    monkeypatch.setattr(gcs, "bucket_upload_path", None)

    getattr(gcs, gcs_method_name)(fake_backup_dir_path, 2, 1)
    assert not fake_backup_dir_path.exists()
    assert not fake_backup_file_zip_path.exists()
    assert not fake_backup_file_zip_path2.exists()
    assert not fake_backup_dir_path2.exists()
    assert not fake_backup_file_zip_path3.exists()
    assert not fake_backup_file_zip_path4.exists()

    bucket_mock.blob.assert_any_call(
        "test123/fake_env_name/file_20230127_0105_dummy_xfcs.zip"
    )
    bucket_mock.blob.assert_any_call(
        "test123/fake_env_name/file_20230227_0105_dummy_xfcs.zip.zip"
    )
    bucket_mock.blob.assert_any_call(
        "test123/fake_env_name/file_20230425_0105_dummy_xfcs.zip.zip"
    )
    bucket_mock.blob.assert_any_call(
        "test123/fake_env_name/file_20230327_0105_dummy_xfcs.zip.zip"
    )
    single_blob_mock.delete.assert_called()


@freeze_time("2023-08-27")
@pytest.mark.parametrize("gcs_method_name", ["_clean", "clean"])
def test_gcs_clean_respects_min_retention_days_param_and_not_delete_any_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, gcs_method_name: str
) -> None:
    gcs = get_test_gcs()

    bucket_mock = Mock()
    storage_client_mock = Mock()
    single_blob_mock = Mock()

    storage_client_mock.list_blobs.return_value = list_blobs_short_with_upload_path
    bucket_mock.blob.return_value = single_blob_mock

    gcs.storage_client = storage_client_mock
    gcs.bucket = bucket_mock

    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_zip_path = fake_backup_dir_path / "fake_backup"
    fake_backup_file_zip_path.touch()

    monkeypatch.setattr(gcs, "bucket_upload_path", "test123")

    getattr(gcs, gcs_method_name)(fake_backup_file_zip_path, 2, 30 * 365)

    bucket_mock.blob.assert_not_called()
    single_blob_mock.delete.assert_not_called()
