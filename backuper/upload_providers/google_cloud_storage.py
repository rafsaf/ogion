import base64
import logging
import os
import shutil
import time
from pathlib import Path

import google.cloud.storage as storage
from google.api_core.retry import Retry
from backuper import config, core
from backuper.upload_providers.base_provider import BaseUploadProvider

log = logging.getLogger(__name__)


class UploadProviderGCS(
    BaseUploadProvider,
    name=config.UploadProviderEnum.GOOGLE_CLOUD_STORAGE,
):
    """GCS bucket for storing backups"""

    def __init__(
        self,
        bucket_name: str,
        bucket_upload_path: str,
        service_account_base64: str,
        chunk_size_mb: int,
        chunk_timeout_secs: int,
        **kwargs: str,
    ) -> None:
        service_account_bytes = base64.b64decode(service_account_base64)
        with open(config.CONST_GOOGLE_SERVICE_ACCOUNT_PATH, "wb") as f:
            f.write(service_account_bytes)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(
            config.CONST_GOOGLE_SERVICE_ACCOUNT_PATH
        )
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(bucket_name)
        self.bucket_upload_path = bucket_upload_path
        self.chunk_size_bytes = chunk_size_mb * 1024 * 1024
        self.chunk_timeout_secs = chunk_timeout_secs
        self._retry = Retry()

    def _post_save(self, backup_file: Path) -> str:
        zip_backup_file = core.run_create_zip_archive(backup_file=backup_file)

        backup_dest_in_bucket = "{}/{}/{}".format(
            self.bucket_upload_path,
            zip_backup_file.parent.name,
            zip_backup_file.name,
        )

        log.info("start uploading %s to %s", zip_backup_file, backup_dest_in_bucket)

        blob = self.bucket.blob(backup_dest_in_bucket, chunk_size=self.chunk_size_bytes)
        blob.upload_from_filename(
            zip_backup_file, timeout=self.chunk_timeout_secs, retry=self._retry  # type: ignore
        )

        log.info("uploaded %s to %s", zip_backup_file, backup_dest_in_bucket)
        return backup_dest_in_bucket

    def _clean(self, backup_file: Path) -> None:
        for backup_path in backup_file.parent.iterdir():
            if backup_path.is_dir():
                shutil.rmtree(backup_path)
            else:
                backup_path.unlink()
            log.info("removed %s from local disk", backup_path)

        backup_list_cloud: list[str] = []
        prefix = f"{self.bucket_upload_path}/{backup_file.parent.name}"
        for blob in self.storage_client.list_blobs(self.bucket, prefix=prefix):
            backup_list_cloud.append(blob.name)

        # remove oldest
        backup_list_cloud.sort(reverse=True)
        while len(backup_list_cloud) > config.BACKUP_MAX_NUMBER:
            backup_to_remove = backup_list_cloud.pop()
            blob = self.bucket.blob(backup_to_remove)
            blob.delete()
            log.info("deleted backup %s from google cloud storage", backup_to_remove)
