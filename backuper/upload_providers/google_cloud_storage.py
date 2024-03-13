import base64
import logging
import os
from pathlib import Path

import google.cloud.storage as cloud_storage
from pydantic import SecretStr

from backuper import config, core
from backuper.models.upload_provider_models import GCSProviderModel
from backuper.upload_providers.base_provider import BaseUploadProvider

log = logging.getLogger(__name__)


class UploadProviderGCS(BaseUploadProvider):
    """GCS bucket for storing backups"""

    def __init__(self, target_provider: GCSProviderModel) -> None:
        service_account_bytes = base64.b64decode(
            target_provider.service_account_base64.get_secret_value()
        )
        sa_path = config.CONST_CONFIG_FOLDER_PATH / "google_auth.json"
        with open(sa_path, "wb") as f:
            f.write(service_account_bytes)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(sa_path)

        self.storage_client = cloud_storage.Client()
        self.bucket = self.storage_client.bucket(target_provider.bucket_name)
        self.bucket_upload_path = target_provider.bucket_upload_path
        self.chunk_size_bytes = target_provider.chunk_size_mb * 1024 * 1024
        self.chunk_timeout_secs = target_provider.chunk_timeout_secs

    def _post_save(self, backup_file: Path) -> str:
        zip_backup_file = core.run_create_zip_archive(backup_file=backup_file)

        backup_dest_in_bucket = (
            f"{self.bucket_upload_path}/"
            f"{zip_backup_file.parent.name}/"
            f"{zip_backup_file.name}"
        )

        log.info("start uploading %s to %s", zip_backup_file, backup_dest_in_bucket)

        blob = self.bucket.blob(backup_dest_in_bucket, chunk_size=self.chunk_size_bytes)
        blob.upload_from_filename(
            zip_backup_file,
            timeout=self.chunk_timeout_secs,
            if_generation_match=0,
            checksum="crc32c",
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
        prefix = f"{self.bucket_upload_path}/{backup_file.parent.name}"
        for blob in self.storage_client.list_blobs(self.bucket, prefix=prefix):
            backup_list_cloud.append(blob.name)

        # remove oldest
        backup_list_cloud.sort(reverse=True)
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

            blob = self.bucket.blob(backup_to_remove)
            blob.delete()
            log.info("deleted backup %s from google cloud storage", backup_to_remove)
