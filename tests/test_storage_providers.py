# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import time
from pathlib import Path

import google.cloud.storage as storage_client
import pytest
from google.auth.credentials import AnonymousCredentials
from pydantic import SecretStr

from ogion.models.upload_provider_models import (
    AzureProviderModel,
    GCSProviderModel,
    S3ProviderModel,
)
from ogion.upload_providers.azure import UploadProviderAzure
from ogion.upload_providers.base_provider import BaseUploadProvider
from ogion.upload_providers.google_cloud_storage import UploadProviderGCS
from ogion.upload_providers.s3 import UploadProviderS3


@pytest.fixture(params=["gcs", "s3", "azure"])
def provider(request: pytest.FixtureRequest) -> BaseUploadProvider:  # type: ignore
    if request.param == "gcs":
        bucket = storage_client.Client(
            credentials=AnonymousCredentials()  # type: ignore[no-untyped-call]
        ).create_bucket(str(time.time_ns()))
        return UploadProviderGCS(
            GCSProviderModel(
                bucket_name=bucket.name or "",
                bucket_upload_path="test",
                service_account_base64=SecretStr("Z29vZ2xlX3NlcnZpY2VfYWNjb3VudAo="),
                chunk_size_mb=100,
                chunk_timeout_secs=100,
            )
        )

    elif request.param == "s3":
        bucket = str(time.time_ns())
        provider_s3 = UploadProviderS3(
            S3ProviderModel(
                endpoint="localhost:9000",
                bucket_name=bucket,
                access_key="minioadmin",
                secret_key=SecretStr("minioadmin"),
                bucket_upload_path="test",
                secure=False,
            )
        )
        provider_s3.client.make_bucket(bucket)
        return provider_s3

    elif request.param == "azure":
        provider_azure = UploadProviderAzure(
            # https://github.com/Azure/Azurite?tab=readme-ov-file#connection-strings
            AzureProviderModel(
                container_name=str(time.time_ns()),
                connect_string=SecretStr(
                    "DefaultEndpointsProtocol=http;"
                    "AccountName=devstoreaccount1;"
                    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
                    "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
                    "QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;"
                    "TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
                ),
            )
        )
        provider_azure.container_client.create_container()
        return provider_azure


def test_gcs_post_save(tmp_path: Path, provider: BaseUploadProvider) -> None:
    prefix = "test/" if provider.__class__ != UploadProviderAzure else ""

    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_path = fake_backup_dir_path / "fake_backup"
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.age"

    with open(fake_backup_file_path, "w") as f:
        f.write("abcdefghijk\n12345")

    assert (
        provider.post_save(fake_backup_file_path)
        == f"{prefix}fake_env_name/fake_backup.age"
    )
    assert fake_backup_file_age_path.exists()


def test_gcs_clean_local_files(tmp_path: Path, provider: BaseUploadProvider) -> None:
    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.age"
    fake_backup_file_age_path.touch()
    fake_backup_file_age_path2 = fake_backup_dir_path / "fake_backup2.age"
    fake_backup_file_age_path2.touch()

    provider.clean(fake_backup_file_age_path, 2, 1)

    assert fake_backup_dir_path.exists()
    assert not fake_backup_file_age_path.exists()
    assert not fake_backup_file_age_path2.exists()


def test_gcs_clean_gcs_files_short(
    tmp_path: Path, provider: BaseUploadProvider
) -> None:
    prefix = "test/" if provider.__class__ != UploadProviderAzure else ""

    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.age"

    (fake_backup_dir_path / "file_19990427_0108_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_19990427_0108_dummy_xfcs")
    (fake_backup_dir_path / "file_20230427_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230427_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230427_0108_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230427_0108_dummy_xfcs")

    assert provider.all_target_backups("fake_env_name") == [
        f"{prefix}fake_env_name/file_20230427_0108_dummy_xfcs.age",
        f"{prefix}fake_env_name/file_20230427_0105_dummy_xfcs.age",
        f"{prefix}fake_env_name/file_19990427_0108_dummy_xfcs.age",
    ]

    provider.clean(fake_backup_file_age_path, 2, 1)

    assert provider.all_target_backups("fake_env_name") == [
        f"{prefix}fake_env_name/file_20230427_0108_dummy_xfcs.age",
        f"{prefix}fake_env_name/file_20230427_0105_dummy_xfcs.age",
    ]


def test_gcs_clean_gcs_files_long(tmp_path: Path, provider: BaseUploadProvider) -> None:
    prefix = "test/" if provider.__class__ != UploadProviderAzure else ""

    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.age"

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
        f"{prefix}fake_env_name/file_20230427_0105_dummy_xfcs.age",
        f"{prefix}fake_env_name/file_20230426_0105_dummy_xfcs.age",
        f"{prefix}fake_env_name/file_20230425_0105_dummy_xfcs.age",
        f"{prefix}fake_env_name/file_20230327_0105_dummy_xfcs.age",
        f"{prefix}fake_env_name/file_20230227_0105_dummy_xfcs.age",
        f"{prefix}fake_env_name/file_20230127_0105_dummy_xfcs.age",
    ]

    provider.clean(fake_backup_file_age_path, 2, 1)

    assert provider.all_target_backups("fake_env_name") == [
        f"{prefix}fake_env_name/file_20230427_0105_dummy_xfcs.age",
        f"{prefix}fake_env_name/file_20230426_0105_dummy_xfcs.age",
    ]


def test_gcs_clean_respects_max_backups_param_and_not_delete_old_files(
    tmp_path: Path, provider: BaseUploadProvider
) -> None:
    prefix = "test/" if provider.__class__ != UploadProviderAzure else ""

    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.age"

    (fake_backup_dir_path / "file_20230426_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230426_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230427_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230427_0105_dummy_xfcs")

    assert provider.all_target_backups("fake_env_name") == [
        f"{prefix}fake_env_name/file_20230427_0105_dummy_xfcs.age",
        f"{prefix}fake_env_name/file_20230426_0105_dummy_xfcs.age",
    ]

    provider.clean(fake_backup_file_age_path, 2, 1)

    assert provider.all_target_backups("fake_env_name") == [
        f"{prefix}fake_env_name/file_20230427_0105_dummy_xfcs.age",
        f"{prefix}fake_env_name/file_20230426_0105_dummy_xfcs.age",
    ]


def test_gcs_clean_respects_min_retention_days_param_and_not_delete_any_backup(
    tmp_path: Path, provider: BaseUploadProvider
) -> None:
    prefix = "test/" if provider.__class__ != UploadProviderAzure else ""

    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.age"

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
        f"{prefix}fake_env_name/file_20230826_0105_dummy_xfcs.age",
        f"{prefix}fake_env_name/file_20230825_0105_dummy_xfcs.age",
        f"{prefix}fake_env_name/file_20230824_0105_dummy_xfcs.age",
        f"{prefix}fake_env_name/file_20230823_0105_dummy_xfcs.age",
        f"{prefix}fake_env_name/file_20230729_0105_dummy_xfcs.age",
    ]

    provider.clean(fake_backup_file_age_path, 2, 300000)

    assert provider.all_target_backups("fake_env_name") == [
        f"{prefix}fake_env_name/file_20230826_0105_dummy_xfcs.age",
        f"{prefix}fake_env_name/file_20230825_0105_dummy_xfcs.age",
        f"{prefix}fake_env_name/file_20230824_0105_dummy_xfcs.age",
        f"{prefix}fake_env_name/file_20230823_0105_dummy_xfcs.age",
        f"{prefix}fake_env_name/file_20230729_0105_dummy_xfcs.age",
    ]


def test_gcs_download_backup(
    tmp_path: Path,
    provider: BaseUploadProvider,
) -> None:
    prefix = "test/" if provider.__class__ != UploadProviderAzure else ""

    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()

    (fake_backup_dir_path / "file_20230426_0105_dummy_xfcs").write_text("abcdef")
    provider.post_save(fake_backup_dir_path / "file_20230426_0105_dummy_xfcs")

    out = provider.download_backup(
        f"{prefix}fake_env_name/file_20230426_0105_dummy_xfcs.age"
    )

    assert out.is_file()
