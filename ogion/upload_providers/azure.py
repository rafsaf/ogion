# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import contextlib
import hashlib
import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, override

from ogion import config, core
from ogion.models.upload_provider_models import AzureProviderModel
from ogion.upload_providers.base_provider import BaseUploadProvider

log = logging.getLogger(__name__)


@dataclass
class _AzureClientCacheEntry:
    blob_service_client: Any
    container_client: Any
    refcount: int


class UploadProviderAzure(BaseUploadProvider):
    """Azure blob storage for storing backups"""

    _cache_lock: ClassVar[threading.Lock] = threading.Lock()
    _client_cache: ClassVar[dict[str, _AzureClientCacheEntry]] = {}

    def __init__(self, target_provider: AzureProviderModel) -> None:
        from azure.storage.blob import BlobServiceClient  # noqa: PLC0415

        self.container_name = target_provider.container_name
        self._closed = False

        connect_string = target_provider.connect_string.get_secret_value()
        connect_hash = hashlib.sha256(connect_string.encode()).hexdigest()
        self._cache_key = f"{connect_hash}::{self.container_name}"

        with self._cache_lock:
            cache_entry = self._client_cache.get(self._cache_key)

            if cache_entry is None:
                blob_service_client = BlobServiceClient.from_connection_string(
                    connect_string
                )
                container_client = blob_service_client.get_container_client(
                    container=self.container_name
                )
                cache_entry = _AzureClientCacheEntry(
                    blob_service_client=blob_service_client,
                    container_client=container_client,
                    refcount=0,
                )
                self._client_cache[self._cache_key] = cache_entry

            cache_entry.refcount += 1
            self.blob_service_client = cache_entry.blob_service_client
            self.container_client = cache_entry.container_client

    @override
    def post_save(self, backup_file: Path) -> str:
        age_backup_file = core.run_create_age_archive(backup_file=backup_file)

        backup_dest_in_azure_container = (
            f"{age_backup_file.parent.name}/{age_backup_file.name}"
        )
        with self.container_client.get_blob_client(
            blob=backup_dest_in_azure_container
        ) as blob_client:
            log.info(
                "start uploading %s to %s",
                age_backup_file,
                backup_dest_in_azure_container,
            )

            with open(file=age_backup_file, mode="rb") as data:
                blob_client.upload_blob(data=data)

            log.info(
                "uploaded %s to %s in %s",
                age_backup_file,
                backup_dest_in_azure_container,
                self.container_name,
            )

        core.remove_path(age_backup_file)
        core.remove_path(backup_file)

        log.info("removed %s and %s from local disk", backup_file, age_backup_file)

        return backup_dest_in_azure_container

    @override
    def all_target_backups(self, env_name: str) -> list[str]:
        backups: list[str] = []
        for blob in self.container_client.list_blobs(name_starts_with=f"{env_name}/"):
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
        from azure.core.exceptions import ResourceNotFoundError  # noqa: PLC0415

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

            try:
                self.container_client.delete_blob(blob=backup_to_remove)
                log.info("deleted backup %s from azure blob storage", backup_to_remove)
            except ResourceNotFoundError:
                log.info(
                    "backup %s already deleted (concurrent cleanup)", backup_to_remove
                )

    @override
    def close(self) -> None:
        if self._closed:
            return

        with self._cache_lock:
            cache_entry = self._client_cache.get(self._cache_key)

            if cache_entry is None:
                self._closed = True
                return

            cache_entry.refcount -= 1

            if cache_entry.refcount <= 0:
                cache_entry.container_client.close()
                log.debug("closed Azure container client")

                cache_entry.blob_service_client.close()
                log.debug("closed Azure blob service client")

                del self._client_cache[self._cache_key]

        self._closed = True

    @classmethod
    def _clear_cache_for_tests(cls) -> None:  # pragma: no cover
        with cls._cache_lock:
            for entry in cls._client_cache.values():
                with contextlib.suppress(Exception):  # pragma: no cover
                    entry.container_client.close()
                with contextlib.suppress(Exception):  # pragma: no cover
                    entry.blob_service_client.close()

            cls._client_cache.clear()
