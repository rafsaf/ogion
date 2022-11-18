import logging

from google.cloud import storage

from pg_dump import config
from pg_dump.providers import common

log = logging.getLogger(__name__)


class GoogleCloudStorage(common.Provider):
    """Represent GCS bucket for storing backups."""

    @staticmethod
    def post_save(backup_file: str):
        backup_dest_in_bucket = "{}/{}".format(
            config.GOOGLE_BUCKET_UPLOAD_PATH,
            backup_file,
        )
        storage_client = storage.Client()
        bucket = storage_client.bucket(config.GOOGLE_BUCKET_NAME)

        log.debug("Start uploading %s to %s", backup_file, backup_dest_in_bucket)
        try:
            blob = bucket.blob(backup_dest_in_bucket)
            blob.upload_from_filename(backup_file)
            log.debug("Uploaded %s to %s", backup_file, backup_dest_in_bucket)
            return True
        except Exception as err:
            log.error(
                "Error during google bucket uploading %s: %s",
                backup_file,
                err,
                exc_info=True,
            )
            return False

    @staticmethod
    def clean(success: bool):
        if success:
            for backup_path in config.BACKUP_FOLDER_PATH.iterdir():
                backup_path.unlink()
