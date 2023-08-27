import logging
from pathlib import Path

from backuper import config, core
from backuper.upload_providers.base_provider import BaseUploadProvider

log = logging.getLogger(__name__)


class UploadProviderLocalDebug(
    BaseUploadProvider,
    name=config.UploadProviderEnum.LOCAL_FILES_DEBUG,
):
    """Represent local folder `data` for storing backups.

    If docker volume/persistant volume is lost, so are backups.
    """

    def __init__(self, **kwargs: str) -> None:
        pass

    def _post_save(self, backup_file: Path) -> str:
        zip_file = core.run_create_zip_archive(backup_file=backup_file)
        return str(zip_file)

    def _clean(
        self, backup_file: Path, max_backups: int, min_retention_days: int
    ) -> None:
        core.remove_path(backup_file)
        files: list[str] = []
        for backup_path in backup_file.parent.iterdir():
            files.append(str(backup_path.absolute()))
        files.sort(reverse=True)
        while len(files) > max_backups:
            backup_to_remove = Path(files.pop())
            if core.file_before_retention_period_ends(
                backup_name=backup_to_remove.name, min_retention_days=min_retention_days
            ):
                log.info(
                    "there are more backups than max_backups (%s/%s), "
                    "but oldest cannot be removed due to min retention days",
                    len(files),
                    max_backups,
                )
                break
            try:
                core.remove_path(backup_to_remove)
                log.info("removed path %s", backup_to_remove)
            except Exception as e:  # pragma: no cover
                log.error(
                    "could not remove path %s: %s", backup_to_remove, e, exc_info=True
                )
