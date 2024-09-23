# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from pathlib import Path
from unittest.mock import Mock

import pytest
from azure.storage.blob import BlobServiceClient
from freezegun import freeze_time
from pydantic import SecretStr

from ogion.models.upload_provider_models import AzureProviderModel
from ogion.upload_providers.azure import UploadProviderAzure


@pytest.fixture(autouse=True)
def mock_azure_service_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(BlobServiceClient, "from_connection_string", Mock())


def get_test_azure() -> UploadProviderAzure:
    return UploadProviderAzure(
        AzureProviderModel(container_name="test", connect_string=SecretStr("any"))
    )


def test_azure_post_save_fails_on_fail_upload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    azure = get_test_azure()
    blob_client_mock = Mock()
    blob_client_mock.upload_blob.side_effect = ValueError()
    container_client_mock = Mock()
    container_client_mock.get_blob_client.return_value = blob_client_mock
    monkeypatch.setattr(azure, "container_client", container_client_mock)

    fake_backup_file_path = tmp_path / "fake_backup"
    fake_backup_file_path.touch()
    with pytest.raises(ValueError):
        assert azure.post_save(fake_backup_file_path)


def test_azure_post_save_with_bucket_upload_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    azure = get_test_azure()
    blob_client_mock = Mock()
    container_client_mock = Mock()
    container_client_mock.get_blob_client.return_value = blob_client_mock
    monkeypatch.setattr(azure, "container_client", container_client_mock)

    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_path = fake_backup_dir_path / "fake_backup"
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.age"
    with open(fake_backup_file_path, "w") as f:
        f.write("abcdefghijk\n12345")

    assert azure.post_save(fake_backup_file_path) == "fake_env_name/fake_backup.age"
    assert fake_backup_file_age_path.exists()

    blob_client_mock.upload_blob.assert_called_once()


class AzureBlob:
    def __init__(self, blob_name: str) -> None:
        self.name = blob_name


list_blobs_short: list[AzureBlob] = [
    AzureBlob("fake_env_name/file_20230427_0105_dummy_xfcs.age"),
    AzureBlob("fake_env_name/file_20230427_0108_dummy_xfcs.age"),
    AzureBlob("fake_env_name/file_19990427_0108_dummy_xfcs.age"),
]
list_blobs_long: list[AzureBlob] = [
    AzureBlob("fake_env_name/file_20230427_0105_dummy_xfcs.age"),
    AzureBlob("fake_env_name/file_20230127_0105_dummy_xfcs.age"),
    AzureBlob("fake_env_name/file_20230426_0105_dummy_xfcs.age"),
    AzureBlob("fake_env_name/file_20230227_0105_dummy_xfcs.age.age"),
    AzureBlob("fake_env_name/file_20230425_0105_dummy_xfcs.age.age"),
    AzureBlob("fake_env_name/file_20230327_0105_dummy_xfcs.age.age"),
]


def test_azure_clean_file_and_short_blob_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    azure = get_test_azure()
    container_client_mock = Mock()
    container_client_mock.list_blobs.return_value = list_blobs_short
    monkeypatch.setattr(azure, "container_client", container_client_mock)

    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.age"
    fake_backup_file_age_path.touch()
    fake_backup_file_age_path2 = fake_backup_dir_path / "fake_backup2.age"
    fake_backup_file_age_path2.touch()

    azure.clean(fake_backup_file_age_path, 2, 1)
    assert fake_backup_dir_path.exists()
    assert not fake_backup_file_age_path.exists()
    assert not fake_backup_file_age_path2.exists()

    container_client_mock.delete_blob.assert_called_once_with(
        blob="fake_env_name/file_19990427_0108_dummy_xfcs.age"
    )


def test_azure_clean_directory_and_long_blob_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    azure = get_test_azure()
    container_client_mock = Mock()
    container_client_mock.list_blobs.return_value = list_blobs_long
    monkeypatch.setattr(azure, "container_client", container_client_mock)

    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.age"
    fake_backup_file_age_path.touch()

    azure.clean(fake_backup_dir_path, 2, 1)

    assert not fake_backup_dir_path.exists()
    assert not fake_backup_file_age_path.exists()

    container_client_mock.delete_blob.assert_any_call(
        blob="fake_env_name/file_20230127_0105_dummy_xfcs.age"
    )
    container_client_mock.delete_blob.assert_any_call(
        blob="fake_env_name/file_20230227_0105_dummy_xfcs.age.age"
    )
    container_client_mock.delete_blob.assert_any_call(
        blob="fake_env_name/file_20230425_0105_dummy_xfcs.age.age"
    )
    container_client_mock.delete_blob.assert_any_call(
        blob="fake_env_name/file_20230327_0105_dummy_xfcs.age.age"
    )


@freeze_time("2023-08-27")
def test_azure_clean_respects_min_retention_days_param_and_not_delete_any_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    azure = get_test_azure()
    container_client_mock = Mock()
    container_client_mock.list_blobs.return_value = list_blobs_long
    monkeypatch.setattr(azure, "container_client", container_client_mock)

    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.age"
    fake_backup_file_age_path.touch()

    azure.clean(fake_backup_dir_path, 2, 30 * 365)

    container_client_mock.delete_blob.assert_not_called()
