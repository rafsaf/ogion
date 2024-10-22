# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import logging
from pathlib import Path
from typing import override

from minio import Minio
from minio.deleteobjects import DeleteObject

from ogion import config, core
from ogion.models.upload_provider_models import S3ProviderModel
from ogion.upload_providers.base_provider import BaseUploadProvider

log = logging.getLogger(__name__)


class UploadProviderS3(BaseUploadProvider):
    """S3 compatibile storage bucket for storing backups"""

    def __init__(self, target_provider: S3ProviderModel) -> None:
        self.bucket_upload_path = target_provider.bucket_upload_path
        self.max_bandwidth = target_provider.max_bandwidth

        self.client = Minio(
            target_provider.endpoint,
            access_key=target_provider.access_key,
            secret_key=target_provider.secret_key.get_secret_value()
            if target_provider.secret_key
            else None,
            region=target_provider.region,
            secure=target_provider.secure,
        )

        self.bucket = target_provider.bucket_name

    @override
    def post_save(self, backup_file: Path) -> str:
        age_backup_file = core.run_create_age_archive(backup_file=backup_file)

        backup_dest_in_bucket = (
            f"{self.bucket_upload_path}/"
            f"{age_backup_file.parent.name}/"
            f"{age_backup_file.name}"
        )

        log.info("start uploading %s to %s", age_backup_file, backup_dest_in_bucket)

        self.client.fput_object(
            bucket_name=self.bucket,
            object_name=backup_dest_in_bucket,
            file_path=str(age_backup_file),
        )

        log.info("uploaded %s to %s", age_backup_file, backup_dest_in_bucket)
        return backup_dest_in_bucket

    @override
    def all_target_backups(self, env_name: str) -> list[str]:
        backups: list[str] = []
        prefix = f"{self.bucket_upload_path}/{env_name}/"

        for bucket_obj in self.client.list_objects(self.bucket, prefix=prefix):
            backups.append(bucket_obj.object_name or "")

        backups.sort(reverse=True)
        return backups

    @override
    def download_backup(self, path: str) -> Path:
        backup_file = config.CONST_DOWNLOADS_FOLDER_PATH / path
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        backup_file.touch(exist_ok=True)

        self.client.fget_object(
            self.bucket, object_name=path, file_path=str(backup_file)
        )

        return backup_file

    @override
    def clean(
        self, backup_file: Path, max_backups: int, min_retention_days: int
    ) -> None:
        for backup_path in backup_file.parent.iterdir():
            core.remove_path(backup_path)
            log.info("removed %s from local disk", backup_path)

        items_to_delete: list[DeleteObject] = []
        backups = self.all_target_backups(env_name=backup_file.parent.name)

        while len(backups) > max_backups:
            backup_to_remove = backups.pop()
            file_name = backup_to_remove.split("/")[-1]
            if core.file_before_retention_period_ends(
                backup_name=file_name, min_retention_days=min_retention_days
            ):
                log.info(
                    "there are more backups than max_backups (%s/%s), "
                    "but oldest cannot be removed due to min retention days",
                    len(backups),
                    max_backups,
                )
                break

            items_to_delete.append(DeleteObject(name=backup_to_remove))
            log.info("backup %s will be deleted from s3 bucket", backup_to_remove)

        if items_to_delete:
            delete_response = self.client.remove_objects(
                self.bucket, delete_object_list=items_to_delete
            )
            if len([error for error in delete_response]):
                raise RuntimeError(
                    "Fail to delete backups from s3: %s", delete_response
                )
            log.info(
                "%s backups were successfully deleted from s3 bucket",
                len(items_to_delete),
            )
