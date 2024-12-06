# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import logging
from pathlib import Path
from typing import override

from ogion import config, core
from ogion.models.upload_provider_models import AzureProviderModel
from ogion.upload_providers.base_provider import BaseUploadProvider

log = logging.getLogger(__name__)


class UploadProviderAzure(BaseUploadProvider):
    """Azure blob storage for storing backups"""

    def __init__(self, target_provider: AzureProviderModel) -> None:
        from azure.storage.blob import BlobServiceClient

        self.container_name = target_provider.container_name

        blob_service_client = BlobServiceClient.from_connection_string(
            target_provider.connect_string.get_secret_value()
        )
        self.container_client = blob_service_client.get_container_client(
            container=self.container_name
        )

    @override
    def post_save(self, backup_file: Path) -> str:
        age_backup_file = core.run_create_age_archive(backup_file=backup_file)

        backup_dest_in_azure_container = (
            f"{age_backup_file.parent.name}/{age_backup_file.name}"
        )
        blob_client = self.container_client.get_blob_client(
            blob=backup_dest_in_azure_container
        )

        log.info(
            "start uploading %s to %s", age_backup_file, backup_dest_in_azure_container
        )

        with open(file=age_backup_file, mode="rb") as data:
            blob_client.upload_blob(data=data)

        log.info(
            "uploaded %s to %s in %s",
            age_backup_file,
            backup_dest_in_azure_container,
            self.container_name,
        )
        return backup_dest_in_azure_container

    @override
    def all_target_backups(self, env_name: str) -> list[str]:
        backups: list[str] = []
        for blob in self.container_client.list_blobs(name_starts_with=env_name):
            backups.append(blob.name)

        backups.sort(reverse=True)
        return backups

    @override
    def download_backup(self, path: str) -> Path:
        backup_file = config.CONST_DOWNLOADS_FOLDER_PATH / path
        backup_file.parent.mkdir(parents=True, exist_ok=True)

        with open(backup_file, mode="wb") as file:
            stream = self.container_client.download_blob(path)
            stream.readinto(file)

        return backup_file

    @override
    def clean(
        self, backup_file: Path, max_backups: int, min_retention_days: int
    ) -> None:
        for backup_path in backup_file.parent.iterdir():
            core.remove_path(backup_path)
            log.info("removed %s from local disk", backup_path)

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

            self.container_client.delete_blob(blob=backup_to_remove)
            log.info("deleted backup %s from azure blob storage", backup_to_remove)
