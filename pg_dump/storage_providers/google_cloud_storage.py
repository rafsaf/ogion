import base64
import logging
import time

from google.cloud import storage

from pg_dump import config, core
from pg_dump.storage_providers import common

log = logging.getLogger(__name__)


class GoogleCloudStorage(common.BaseBackupProvider):
    """Represent GCS bucket for storing backups."""

    NAME = config.BackupProviderEnum.GOOGLE_CLOUD_STORAGE
    MAX_UPLOAD_RETRY = 5

    def __init__(self) -> None:
        service_account_bytes = base64.b64decode(config.GOOGLE_SERVICE_ACCOUNT_BASE64)
        with open(config.CONST_GOOGLE_SERVICE_ACCOUNT_PATH, "wb") as f:
            f.write(service_account_bytes)

        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(config.GOOGLE_BUCKET_NAME)

    def post_save(self, backup_file: str):
        try:
            zip_backup_file = core.run_create_zip_archive(backup_file=backup_file)
        except core.CoreSubprocessError:
            log.error("Could not create zip_backup_file from %s", backup_file)
            raise

        if config.GOOGLE_BUCKET_UPLOAD_PATH is not None:
            backup_dest_in_bucket = "{}/{}".format(
                config.GOOGLE_BUCKET_UPLOAD_PATH,
                zip_backup_file.split("/")[-1],
            )
        else:
            backup_dest_in_bucket = zip_backup_file.split("/")[-1]

        log.debug("Start uploading %s to %s", zip_backup_file, backup_dest_in_bucket)

        blob = self.bucket.blob(backup_dest_in_bucket)
        retry = 1
        while retry <= self.MAX_UPLOAD_RETRY:
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

        log.debug("Uploaded %s to %s", zip_backup_file, backup_dest_in_bucket)
        return True

    def clean(self, success: bool):
        if success:
            for backup_path in config.CONST_BACKUP_FOLDER_PATH.iterdir():
                backup_path.unlink()
                log.info("Removed %s from local disk", backup_path)

            backup_list_cloud: list[str] = []
            for blob in self.storage_client.list_blobs(
                self.bucket, prefix=config.GOOGLE_BUCKET_UPLOAD_PATH
            ):
                backup_list_cloud.append(blob.name)

            backup_list_cloud.sort(reverse=True)
            while len(backup_list_cloud) > config.BACKUP_MAX_NUMBER:
                backup_to_remove = backup_list_cloud.pop()
                blob = self.bucket.blob(backup_to_remove)
                blob.delete()
                log.info("Deleted backup %s from Google Cloud Storage")
