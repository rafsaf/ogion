import time
from pathlib import Path
from unittest.mock import Mock

import pytest
from pytest import MonkeyPatch

from backuper import config
from backuper.storage_providers import GoogleCloudStorage


def test_gcs_safe_post_fail_gracefully_on_fail_upload(
    tmp_path: Path, monkeypatch: MonkeyPatch
):
    sleep_mock = Mock()
    monkeypatch.setattr(time, "sleep", sleep_mock)
    gcs = GoogleCloudStorage()
    bucket_mock = Mock()
    single_blob_mock = Mock()
    single_blob_mock.upload_from_filename.side_effect = ValueError()
    bucket_mock.blob.return_value = single_blob_mock
    gcs.bucket = bucket_mock

    fake_backup_file_path = tmp_path / "fake_backup"
    fake_backup_file_path.touch()

    assert gcs.safe_post_save(fake_backup_file_path) is None
    sleep_mock.assert_any_call(1)
    sleep_mock.assert_any_call(2)
    sleep_mock.assert_any_call(4)
    sleep_mock.assert_called_with(8)


def test_gcs_post_save_runtime_error_on_fail_upload(
    tmp_path: Path, monkeypatch: MonkeyPatch
):
    sleep_mock = Mock()
    monkeypatch.setattr(time, "sleep", sleep_mock)
    gcs = GoogleCloudStorage()
    bucket_mock = Mock()
    single_blob_mock = Mock()
    single_blob_mock.upload_from_filename.side_effect = ValueError()
    bucket_mock.blob.return_value = single_blob_mock
    gcs.bucket = bucket_mock

    fake_backup_file_path = tmp_path / "fake_backup"
    fake_backup_file_path.touch()
    with pytest.raises(RuntimeError):
        assert gcs._post_save(fake_backup_file_path)
    sleep_mock.assert_any_call(1)
    sleep_mock.assert_any_call(2)
    sleep_mock.assert_any_call(4)
    sleep_mock.assert_called_with(8)


@pytest.mark.parametrize("gcs_method_name", ["_post_save", "safe_post_save"])
def test_gcs_post_save_with_google_bucket_upload_path(
    tmp_path: Path, monkeypatch: MonkeyPatch, gcs_method_name
):
    gcs = GoogleCloudStorage()
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

    monkeypatch.setattr(config, "GOOGLE_BUCKET_UPLOAD_PATH", "test123")
    assert (
        getattr(gcs, gcs_method_name)(fake_backup_file_path)
        == "test123/fake_env_name/fake_backup.zip"
    )
    assert fake_backup_file_zip_path.exists()
    bucket_mock.blob.assert_called_once_with("test123/fake_env_name/fake_backup.zip")
    single_blob_mock.upload_from_filename.assert_called_once_with(
        fake_backup_file_zip_path
    )


class BlobInCloudStorage:
    def __init__(self, blob_name: str) -> None:
        self.name = blob_name


list_blobs_short_with_upload_path = [
    BlobInCloudStorage("test123/fake_env_name/file_20230427_0105.zip"),
    BlobInCloudStorage("test123/fake_env_name/file_20230427_0108.zip"),
    BlobInCloudStorage("test123/fake_env_name/file_19990427_0108.zip"),
]
list_blobs_long_no_upload_path = [
    BlobInCloudStorage("test123/fake_env_name/file_20230427_0105.zip"),
    BlobInCloudStorage("test123/fake_env_name/file_20230127_0105.zip"),
    BlobInCloudStorage("test123/fake_env_name/file_20230426_0105.zip"),
    BlobInCloudStorage("test123/fake_env_name/file_20230227_0105.zip"),
    BlobInCloudStorage("test123/fake_env_name/file_20230425_0105.zip"),
    BlobInCloudStorage("test123/fake_env_name/file_20230327_0105.zip"),
]


@pytest.mark.parametrize("gcs_method_name", ["_clean", "safe_clean"])
def test_gcs_clean_file_and_short_blob_list(
    tmp_path: Path, monkeypatch: MonkeyPatch, gcs_method_name
):
    gcs = GoogleCloudStorage()

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

    monkeypatch.setattr(config, "GOOGLE_BUCKET_UPLOAD_PATH", "test123")
    monkeypatch.setattr(config, "BACKUP_MAX_NUMBER", 2)

    getattr(gcs, gcs_method_name)(fake_backup_file_zip_path)
    assert fake_backup_dir_path.exists()
    assert not fake_backup_file_zip_path.exists()
    assert not fake_backup_file_zip_path2.exists()

    bucket_mock.blob.assert_called_once_with(
        "test123/fake_env_name/file_19990427_0108.zip"
    )
    single_blob_mock.delete.assert_called_once_with()


@pytest.mark.parametrize("gcs_method_name", ["_clean", "safe_clean"])
def test_gcs_clean_directory_and_long_blob_list(
    tmp_path: Path, monkeypatch: MonkeyPatch, gcs_method_name
):
    gcs = GoogleCloudStorage()

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

    monkeypatch.setattr(config, "GOOGLE_BUCKET_UPLOAD_PATH", None)
    monkeypatch.setattr(config, "BACKUP_MAX_NUMBER", 2)

    getattr(gcs, gcs_method_name)(fake_backup_dir_path)
    assert not fake_backup_dir_path.exists()
    assert not fake_backup_file_zip_path.exists()
    assert not fake_backup_file_zip_path2.exists()
    assert not fake_backup_dir_path2.exists()
    assert not fake_backup_file_zip_path3.exists()
    assert not fake_backup_file_zip_path4.exists()

    bucket_mock.blob.assert_any_call("test123/fake_env_name/file_20230127_0105.zip")
    bucket_mock.blob.assert_any_call("test123/fake_env_name/file_20230227_0105.zip")
    bucket_mock.blob.assert_any_call("test123/fake_env_name/file_20230425_0105.zip")
    bucket_mock.blob.assert_any_call("test123/fake_env_name/file_20230327_0105.zip")
    single_blob_mock.delete.assert_called()
