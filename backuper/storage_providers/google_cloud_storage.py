import base64
import logging
import shutil
import time
from pathlib import Path

from google.cloud import storage

from backuper import config, core
from backuper.storage_providers import base_provider

log = logging.getLogger(__name__)


class GoogleCloudStorage(base_provider.BaseBackupProvider):
    """Represent GCS bucket for storing backups."""

    NAME = config.BackupProviderEnum.GOOGLE_CLOUD_STORAGE
    MAX_UPLOAD_RETRY = 5

    def __init__(self) -> None:
        service_account_bytes = base64.b64decode(config.GOOGLE_SERVICE_ACCOUNT_BASE64)
        with open(config.CONST_GOOGLE_SERVICE_ACCOUNT_PATH, "wb") as f:
            f.write(service_account_bytes)

        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(config.GOOGLE_BUCKET_NAME)

    def _post_save(self, backup_file: Path) -> str:
        try:
            zip_backup_file = core.run_create_zip_archive(backup_file=backup_file)
        except core.CoreSubprocessError:
            log.error("could not create zip_backup_file from %s", backup_file)
            raise

        backup_dest_in_bucket = "{}/{}".format(
            zip_backup_file.parent.name,
            zip_backup_file.name,
        )
        if config.GOOGLE_BUCKET_UPLOAD_PATH is not None:
            backup_dest_in_bucket = "{}/{}".format(
                config.GOOGLE_BUCKET_UPLOAD_PATH,
                backup_dest_in_bucket,
            )

        log.info("start uploading %s to %s", zip_backup_file, backup_dest_in_bucket)

        blob = self.bucket.blob(backup_dest_in_bucket)
        retry = 0
        while retry < self.MAX_UPLOAD_RETRY:
            try:
                blob.upload_from_filename(zip_backup_file)
                break
            except Exception as err:
                log.error(
                    "Error (try %s of %s) when uploading %s to gcs: %s",
                    retry,
                    self.MAX_UPLOAD_RETRY,
                    zip_backup_file,
                    err,
                    exc_info=True,
                )
                time.sleep(2 ^ retry)
                retry += 1
        if retry == self.MAX_UPLOAD_RETRY:
            raise RuntimeError("failed upload %s file to gcs", zip_backup_file)
        log.info("uploaded %s to %s", zip_backup_file, backup_dest_in_bucket)
        return backup_dest_in_bucket

    def _clean(self, backup_file: Path):
        for backup_path in backup_file.parent.iterdir():
            if backup_path.is_dir():
                shutil.rmtree(backup_path)
            else:
                backup_path.unlink()
            log.info("removed %s from local disk", backup_path)

        backup_list_cloud: list[str] = []
        prefix = backup_file.parent.name
        if config.GOOGLE_BUCKET_UPLOAD_PATH:
            prefix = f"{config.GOOGLE_BUCKET_UPLOAD_PATH}/{prefix}"
        for blob in self.storage_client.list_blobs(self.bucket, prefix=prefix):
            backup_list_cloud.append(blob.name)

        backup_list_cloud.sort(reverse=True)
        while len(backup_list_cloud) > config.BACKUP_MAX_NUMBER:
            backup_to_remove = backup_list_cloud.pop()
            blob = self.bucket.blob(backup_to_remove)
            blob.delete()
            log.info("deleted backup %s from google cloud storage", backup_to_remove)
