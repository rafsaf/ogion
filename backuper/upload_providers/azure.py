import logging
from pathlib import Path

from azure.storage.blob import BlobServiceClient
from pydantic import SecretStr

from backuper import config, core
from backuper.upload_providers.base_provider import BaseUploadProvider

log = logging.getLogger(__name__)


class UploadProviderAzure(
    BaseUploadProvider,
    name=config.UploadProviderEnum.AZURE,
):
    """Azure blob storage for storing backups"""

    def __init__(
        self,
        container_name: str,
        connect_string: SecretStr,
        **kwargs: str,
    ) -> None:
        self.container_name = container_name
        self.connect_str = connect_string

        self.blob_service_client = BlobServiceClient.from_connection_string(
            connect_string.get_secret_value()
        )
        self.container_client = self.blob_service_client.get_container_client(
            container=self.container_name
        )

    def _post_save(self, backup_file: Path) -> str:
        zip_backup_file = core.run_create_zip_archive(backup_file=backup_file)

        backup_dest_in_bucket = "{}/{}".format(
            zip_backup_file.parent.name,
            zip_backup_file.name,
        )
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name, blob=backup_dest_in_bucket
        )

        log.info("start uploading %s to %s", zip_backup_file, backup_dest_in_bucket)

        with open(file=zip_backup_file, mode="rb") as data:
            blob_client.upload_blob(data=data)

        log.info(
            "uploaded %s to %s in %s",
            zip_backup_file,
            backup_dest_in_bucket,
            self.container_name,
        )
        return backup_dest_in_bucket

    def _clean(self, backup_file: Path, max_backups: int) -> None:
        for backup_path in backup_file.parent.iterdir():
            core.remove_path(backup_path)
            log.info("removed %s from local disk", backup_path)

        backup_list_cloud: list[str] = []
        for blob in self.container_client.list_blobs(
            name_starts_with=backup_file.parent.name
        ):
            backup_list_cloud.append(blob.name)

        # remove oldest
        backup_list_cloud.sort(reverse=True)

        while len(backup_list_cloud) > max_backups:
            backup_to_remove = backup_list_cloud.pop()
            self.container_client.delete_blob(blob=backup_to_remove)
            log.info("deleted backup %s from azure blob storage", backup_to_remove)
