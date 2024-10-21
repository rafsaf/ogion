# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import time
from pathlib import Path

import google.cloud.storage as storage_client
import pytest
from freezegun import freeze_time
from google.auth.credentials import AnonymousCredentials
from pydantic import SecretStr

from ogion.models.upload_provider_models import GCSProviderModel
from ogion.upload_providers.google_cloud_storage import UploadProviderGCS


@pytest.fixture
def bucket() -> storage_client.Bucket:
    return storage_client.Client(credentials=AnonymousCredentials()).create_bucket(  # type: ignore[no-untyped-call]
        str(time.time_ns())
    )


@pytest.fixture
def gcs_provider(bucket: storage_client.Bucket) -> UploadProviderGCS:
    return UploadProviderGCS(
        GCSProviderModel(
            bucket_name=bucket.name or "",
            bucket_upload_path="test",
            service_account_base64=SecretStr("Z29vZ2xlX3NlcnZpY2VfYWNjb3VudAo="),
            chunk_size_mb=100,
            chunk_timeout_secs=100,
        )
    )


@pytest.mark.parametrize("upload_path", [("test",), ("",), ("12345_xxx")])
def test_gcs_post_save(
    tmp_path: Path, gcs_provider: UploadProviderGCS, upload_path: str
) -> None:
    gcs_provider.bucket_upload_path = upload_path
    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_path = fake_backup_dir_path / "fake_backup"
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.age"

    with open(fake_backup_file_path, "w") as f:
        f.write("abcdefghijk\n12345")

    if gcs_provider.bucket_upload_path:
        assert (
            gcs_provider.post_save(fake_backup_file_path)
            == f"{gcs_provider.bucket_upload_path}/fake_env_name/fake_backup.age"
        )
    else:
        assert (
            gcs_provider.post_save(fake_backup_file_path)
            == "fake_env_name/fake_backup.age"
        )
    assert fake_backup_file_age_path.exists()


def test_gcs_clean_local_files(tmp_path: Path, gcs_provider: UploadProviderGCS) -> None:
    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.age"
    fake_backup_file_age_path.touch()
    fake_backup_file_age_path2 = fake_backup_dir_path / "fake_backup2.age"
    fake_backup_file_age_path2.touch()

    gcs_provider.clean(fake_backup_file_age_path, 2, 1)

    assert fake_backup_dir_path.exists()
    assert not fake_backup_file_age_path.exists()
    assert not fake_backup_file_age_path2.exists()


def test_gcs_clean_gcs_files_short(
    tmp_path: Path, gcs_provider: UploadProviderGCS, bucket: storage_client.Bucket
) -> None:
    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.age"

    bucket.blob(
        "test/fake_env_name/file_19990427_0108_dummy_xfcs.age"
    ).upload_from_string("")
    bucket.blob(
        "test/fake_env_name/file_20230427_0105_dummy_xfcs.age"
    ).upload_from_string("")
    bucket.blob(
        "test/fake_env_name/file_20230427_0108_dummy_xfcs.age"
    ).upload_from_string("")

    gcs_provider.clean(fake_backup_file_age_path, 2, 1)

    assert sorted(
        blob.name for blob in gcs_provider.storage_client.list_blobs(bucket)
    ) == [
        "test/fake_env_name/file_20230427_0105_dummy_xfcs.age",
        "test/fake_env_name/file_20230427_0108_dummy_xfcs.age",
    ]


def test_gcs_clean_gcs_files_long(
    tmp_path: Path, gcs_provider: UploadProviderGCS, bucket: storage_client.Bucket
) -> None:
    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.age"

    bucket.blob(
        "test/fake_env_name/file_20230127_0105_dummy_xfcs.age"
    ).upload_from_string("")
    bucket.blob(
        "test/fake_env_name/file_20230227_0105_dummy_xfcs.age"
    ).upload_from_string("")
    bucket.blob(
        "test/fake_env_name/file_20230327_0105_dummy_xfcs.age"
    ).upload_from_string("")
    bucket.blob(
        "test/fake_env_name/file_20230425_0105_dummy_xfcs.age"
    ).upload_from_string("")
    bucket.blob(
        "test/fake_env_name/file_20230426_0105_dummy_xfcs.age"
    ).upload_from_string("")
    bucket.blob(
        "test/fake_env_name/file_20230427_0105_dummy_xfcs.age"
    ).upload_from_string("")

    gcs_provider.clean(fake_backup_file_age_path, 2, 1)

    assert sorted(
        blob.name for blob in gcs_provider.storage_client.list_blobs(bucket)
    ) == [
        "test/fake_env_name/file_20230426_0105_dummy_xfcs.age",
        "test/fake_env_name/file_20230427_0105_dummy_xfcs.age",
    ]


@freeze_time("2023-08-27")
def test_gcs_clean_respects_max_backups_param_and_not_delete_old_files(
    tmp_path: Path, gcs_provider: UploadProviderGCS, bucket: storage_client.Bucket
) -> None:
    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.age"

    bucket.blob(
        "test/fake_env_name/file_20230426_0105_dummy_xfcs.age"
    ).upload_from_string("")
    bucket.blob(
        "test/fake_env_name/file_20230427_0105_dummy_xfcs.age"
    ).upload_from_string("")

    gcs_provider.clean(fake_backup_file_age_path, 2, 1)

    assert sorted(
        blob.name for blob in gcs_provider.storage_client.list_blobs(bucket)
    ) == [
        "test/fake_env_name/file_20230426_0105_dummy_xfcs.age",
        "test/fake_env_name/file_20230427_0105_dummy_xfcs.age",
    ]


@freeze_time("2023-08-27")
def test_gcs_clean_respects_min_retention_days_param_and_not_delete_any_backup(
    tmp_path: Path, gcs_provider: UploadProviderGCS, bucket: storage_client.Bucket
) -> None:
    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.age"

    bucket.blob(
        "test/fake_env_name/file_20230826_0105_dummy_xfcs.age"
    ).upload_from_string("")
    bucket.blob(
        "test/fake_env_name/file_20230825_0105_dummy_xfcs.age"
    ).upload_from_string("")
    bucket.blob(
        "test/fake_env_name/file_20230824_0105_dummy_xfcs.age"
    ).upload_from_string("")
    bucket.blob(
        "test/fake_env_name/file_20230823_0105_dummy_xfcs.age"
    ).upload_from_string("")
    bucket.blob(
        "test/fake_env_name/file_20230729_0105_dummy_xfcs.age"
    ).upload_from_string("")

    gcs_provider.clean(fake_backup_file_age_path, 2, 30)

    assert sorted(
        blob.name for blob in gcs_provider.storage_client.list_blobs(bucket)
    ) == [
        "test/fake_env_name/file_20230729_0105_dummy_xfcs.age",
        "test/fake_env_name/file_20230823_0105_dummy_xfcs.age",
        "test/fake_env_name/file_20230824_0105_dummy_xfcs.age",
        "test/fake_env_name/file_20230825_0105_dummy_xfcs.age",
        "test/fake_env_name/file_20230826_0105_dummy_xfcs.age",
    ]


def test_gcs_download_backup(
    gcs_provider: UploadProviderGCS, bucket: storage_client.Bucket
) -> None:
    bucket.blob(
        "test/fake_env_name/file_20230426_0105_dummy_xfcs.age"
    ).upload_from_string("abcdef")

    out = gcs_provider.download_backup(
        "test/fake_env_name/file_20230426_0105_dummy_xfcs.age"
    )

    assert out.is_file()
    assert out.read_text() == "abcdef"
