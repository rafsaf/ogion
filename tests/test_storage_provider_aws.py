from pathlib import Path
from unittest.mock import Mock

import boto3
import pytest
from freezegun import freeze_time

from backuper.upload_providers import UploadProviderAWS


@pytest.fixture(autouse=True)
def mock_google_storage_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(boto3, "resource", Mock())


def get_test_aws() -> UploadProviderAWS:
    return UploadProviderAWS(
        bucket_name="name",
        bucket_upload_path="test123",
        key_id="id",
        key_secret="secret",
        region="fake region",
        max_bandwidth=None,
    )


def test_aws_post_save_fails_on_fail_upload(tmp_path: Path) -> None:
    aws = get_test_aws()
    bucket_mock = Mock()
    bucket_mock.upload_file.side_effect = ValueError()
    aws.bucket = bucket_mock

    fake_backup_file_path = tmp_path / "fake_backup"
    fake_backup_file_path.touch()
    with pytest.raises(ValueError):
        assert aws.post_save(fake_backup_file_path)


@pytest.mark.parametrize("aws_method_name", ["_post_save", "post_save"])
def test_aws_post_save_with_bucket_upload_path(
    tmp_path: Path, aws_method_name: str
) -> None:
    aws = get_test_aws()
    bucket_mock = Mock()
    aws.bucket = bucket_mock

    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_path = fake_backup_dir_path / "fake_backup"
    fake_backup_file_zip_path = fake_backup_dir_path / "fake_backup.zip"
    with open(fake_backup_file_path, "w") as f:
        f.write("abcdefghijk\n12345")

    assert (
        getattr(aws, aws_method_name)(fake_backup_file_path)
        == "test123/fake_env_name/fake_backup.zip"
    )
    assert fake_backup_file_zip_path.exists()

    bucket_mock.upload_file.assert_called_once_with(
        Filename=fake_backup_file_zip_path,
        Key="test123/fake_env_name/fake_backup.zip",
        Config=aws.transfer_config,
    )


class ItemInS3:
    def __init__(self, name: str) -> None:
        self.key = name


items_lst: list[ItemInS3] = [
    ItemInS3("test123/fake_env_name/file_20230427_0105_dummy_xfcs.zip"),
    ItemInS3("test123/fake_env_name/file_20230127_0105_dummy_xfcs.zip"),
    ItemInS3("test123/fake_env_name/file_20230426_0105_dummy_xfcs.zip"),
    ItemInS3("test123/fake_env_name/file_20230227_0105_dummy_xfcs.zip.zip"),
    ItemInS3("test123/fake_env_name/file_20230425_0105_dummy_xfcs.zip.zip"),
    ItemInS3("test123/fake_env_name/file_20230327_0105_dummy_xfcs.zip.zip"),
]


@pytest.mark.parametrize("aws_method_name", ["_clean", "clean"])
def test_aws_clean_method_with_file_list(tmp_path: Path, aws_method_name: str) -> None:
    aws = get_test_aws()

    bucket_mock = Mock()
    aws.bucket = bucket_mock
    bucket_mock.objects.filter.return_value = items_lst
    bucket_mock.delete_objects.return_value = {
        "Deleted": [
            {
                "Key": "string",
                "VersionId": "string",
                "DeleteMarker": True,
                "DeleteMarkerVersionId": "string",
            },
        ],
        "RequestCharged": "requester",
    }

    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_zip_path = fake_backup_dir_path / "fake_backup.zip"
    fake_backup_file_zip_path.touch()
    fake_backup_file_zip_path2 = fake_backup_dir_path / "fake_backup2.zip"
    fake_backup_file_zip_path2.touch()

    getattr(aws, aws_method_name)(fake_backup_file_zip_path, 2, 1)
    assert fake_backup_dir_path.exists()
    assert not fake_backup_file_zip_path.exists()
    assert not fake_backup_file_zip_path2.exists()

    aws.bucket.delete_objects.assert_called_once_with(
        Delete={
            "Objects": [
                {"Key": "test123/fake_env_name/file_20230127_0105_dummy_xfcs.zip"},
                {"Key": "test123/fake_env_name/file_20230227_0105_dummy_xfcs.zip.zip"},
                {"Key": "test123/fake_env_name/file_20230327_0105_dummy_xfcs.zip.zip"},
                {"Key": "test123/fake_env_name/file_20230425_0105_dummy_xfcs.zip.zip"},
            ],
            "Quiet": False,
        }
    )


@freeze_time("2023-08-27")
@pytest.mark.parametrize("aws_method_name", ["_clean", "clean"])
def test_aws_clean_respects_min_retention_days_param_and_not_delete_any_file(
    tmp_path: Path, aws_method_name: str
) -> None:
    aws = get_test_aws()

    bucket_mock = Mock()
    aws.bucket = bucket_mock
    bucket_mock.objects.filter.return_value = items_lst
    bucket_mock.delete_objects.return_value = {}

    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_path = fake_backup_dir_path / "fake_backup"
    fake_backup_file_path.touch()

    getattr(aws, aws_method_name)(fake_backup_file_path, 2, 3650)

    aws.bucket.delete_objects.assert_not_called()
