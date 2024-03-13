import logging
from pathlib import Path
from typing import Any, TypedDict

import boto3
from boto3.s3.transfer import TransferConfig
from pydantic import SecretStr

from backuper import config, core
from backuper.models.upload_provider_models import AWSProviderModel
from backuper.upload_providers.base_provider import BaseUploadProvider

log = logging.getLogger(__name__)


class DeleteItemDict(TypedDict):
    Key: str


class UploadProviderAWS(BaseUploadProvider):
    """AWS S3 bucket for storing backups"""

    def __init__(self, target_provider: AWSProviderModel) -> None:
        self.bucket_upload_path = target_provider.bucket_upload_path
        self.max_bandwidth = target_provider.max_bandwidth

        s3: Any = boto3.resource(
            "s3",
            region_name=target_provider.region,
            aws_access_key_id=target_provider.key_id,
            aws_secret_access_key=target_provider.key_secret.get_secret_value(),
        )

        self.bucket = s3.Bucket(target_provider.bucket_name)
        self.transfer_config = TransferConfig(max_bandwidth=self.max_bandwidth)

    def _post_save(self, backup_file: Path) -> str:
        zip_backup_file = core.run_create_zip_archive(backup_file=backup_file)

        backup_dest_in_bucket = (
            f"{self.bucket_upload_path}/"
            f"{zip_backup_file.parent.name}/"
            f"{zip_backup_file.name}"
        )

        log.info("start uploading %s to %s", zip_backup_file, backup_dest_in_bucket)

        self.bucket.upload_file(
            Filename=zip_backup_file,
            Key=backup_dest_in_bucket,
            Config=self.transfer_config,
        )

        log.info("uploaded %s to %s", zip_backup_file, backup_dest_in_bucket)
        return backup_dest_in_bucket

    def _clean(
        self, backup_file: Path, max_backups: int, min_retention_days: int
    ) -> None:
        for backup_path in backup_file.parent.iterdir():
            core.remove_path(backup_path)
            log.info("removed %s from local disk", backup_path)

        backup_list_cloud: list[str] = []
        prefix = f"{self.bucket_upload_path}/{backup_file.parent.name}/"
        for bucket_obj in self.bucket.objects.filter(Delimiter="/", Prefix=prefix):
            backup_list_cloud.append(bucket_obj.key)

        # remove oldest
        backup_list_cloud.sort(reverse=True)
        items_to_delete: list[DeleteItemDict] = []

        while len(backup_list_cloud) > max_backups:
            backup_to_remove = backup_list_cloud.pop()
            file_name = backup_to_remove.split("/")[-1]
            if core.file_before_retention_period_ends(
                backup_name=file_name, min_retention_days=min_retention_days
            ):
                log.info(
                    "there are more backups than max_backups (%s/%s), "
                    "but oldest cannot be removed due to min retention days",
                    len(backup_list_cloud),
                    max_backups,
                )
                break

            items_to_delete.append({"Key": backup_to_remove})
            log.info("backup %s will be deleted from aws s3 bucket", backup_to_remove)

        if items_to_delete:
            delete_response = self.bucket.delete_objects(
                Delete={"Objects": items_to_delete, "Quiet": False}
            )
            if (
                "Errors" in delete_response and delete_response["Errors"]
            ):  # pragma: no cover
                raise RuntimeError(
                    "Fail to delete backups from aws s3: %s", delete_response["Errors"]
                )
            log.info(
                "%s backups were successfully deleted from aws s3 bucket",
                len(items_to_delete),
            )
