import logging
from pathlib import Path

import boto3
from typing import Any, TypedDict
from backuper import config, core
from backuper.upload_providers.base_provider import BaseUploadProvider
from boto3.s3.transfer import TransferConfig

log = logging.getLogger(__name__)


class DeleteItemDict(TypedDict):
    Key: str


class UploadProviderAWS(
    BaseUploadProvider,
    name=config.UploadProviderEnum.AWS_S3,
):
    """AWS S3 bucket for storing backups"""

    def __init__(
        self,
        bucket_name: str,
        bucket_upload_path: str,
        key_id: str,
        key_secret: str,
        region: str,
        max_bandwidth: int | None,
        **kwargs: str,
    ) -> None:
        self.bucket_upload_path = bucket_upload_path
        self.max_bandwidth = max_bandwidth

        s3: Any = boto3.resource(
            "s3",
            region_name=region,
            aws_access_key_id=key_id,
            aws_secret_access_key=key_secret,
        )

        self.bucket = s3.Bucket(bucket_name)
        self.transfer_config = TransferConfig(max_bandwidth=self.max_bandwidth)

    def _post_save(self, backup_file: Path) -> str:
        zip_backup_file = core.run_create_zip_archive(backup_file=backup_file)

        backup_dest_in_bucket = "{}/{}/{}".format(
            self.bucket_upload_path,
            zip_backup_file.parent.name,
            zip_backup_file.name,
        )

        log.info("start uploading %s to %s", zip_backup_file, backup_dest_in_bucket)

        self.bucket.upload_file(
            Filename=zip_backup_file,
            Key=backup_dest_in_bucket,
            Config=self.transfer_config,
        )

        log.info("uploaded %s to %s", zip_backup_file, backup_dest_in_bucket)
        return backup_dest_in_bucket

    def _clean(self, backup_file: Path, max_backups: int) -> None:
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
            items_to_delete.append({"Key": backup_to_remove})
            log.info("backup %s will be deleted from aws s3 bucket", backup_to_remove)

        if items_to_delete:
            delete_response = self.bucket.delete_objects(
                Delete={"Objects": items_to_delete, "Quiet": False}
            )
            if "Errors" in delete_response and delete_response["Errors"]:
                raise RuntimeError(
                    "Fail to delete backups from aws s3: %s", delete_response["Errors"]
                )
            log.info("backups were successfully deleted from aws s3 bucket")
