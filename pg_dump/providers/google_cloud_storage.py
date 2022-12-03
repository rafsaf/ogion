import logging
import time

from google.cloud import storage

from pg_dump import config
from pg_dump.providers import common

log = logging.getLogger(__name__)


class GoogleCloudStorage(common.Provider):
    """Represent GCS bucket for storing backups."""

    NAME = "gcs"
    MAX_UPLOAD_RETRY = 5

    def post_save(self, backup_file: str):
        backup_dest_in_bucket = "{}/{}".format(
            config.GOOGLE_BUCKET_UPLOAD_PATH,
            backup_file,
        )
        storage_client = storage.Client()
        bucket = storage_client.bucket(config.GOOGLE_BUCKET_NAME)

        log.debug("Start uploading %s to %s", backup_file, backup_dest_in_bucket)

        blob = bucket.blob(backup_dest_in_bucket)
        retry = 1
        while retry <= self.MAX_UPLOAD_RETRY:
            try:
                blob.upload_from_filename(backup_file)
                break
            except Exception as err:
                log.error(
                    "Error (try %s of %s) when uploading %s to gcs: %s",
                    retry,
                    self.MAX_UPLOAD_RETRY,
                    backup_file,
                    err,
                    exc_info=True,
                )
                time.sleep(2 ^ retry)
                retry += 1

        log.debug("Uploaded %s to %s", backup_file, backup_dest_in_bucket)
        return True

    def clean(self, success: bool):
        if success:
            for backup_path in config.BACKUP_FOLDER_PATH.iterdir():
                backup_path.unlink()
