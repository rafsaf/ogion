import logging
import shutil
from pathlib import Path

from backuper import config, core
from backuper.storage_providers import base_provider

log = logging.getLogger(__name__)


class LocalFiles(base_provider.BaseBackupProvider):
    """Represent local folder `data` for storing backups.

    If docker volume/persistant volume is lost, so are backups.
    """

    NAME = config.BackupProviderEnum.LOCAL_FILES

    def _post_save(self, backup_file: Path) -> str:
        try:
            zip_file = core.run_create_zip_archive(backup_file=backup_file)
        except core.CoreSubprocessError:
            log.error("could not create zip_backup_file from %s", backup_file)
            raise
        return str(zip_file)

    def _clean(self, backup_file: Path):
        if backup_file.is_file():
            backup_file.unlink()
        else:
            shutil.rmtree(backup_file)
        files: list[str] = []
        for backup_path in backup_file.parent.iterdir():
            files.append(str(backup_path.absolute()))
        files.sort(reverse=True)
        while len(files) > config.BACKUP_MAX_NUMBER:
            backup_to_remove = Path(files.pop())
            try:
                if backup_to_remove.is_file():
                    backup_to_remove.unlink()
                else:
                    shutil.rmtree(backup_to_remove)
                log.info("removed path %s", backup_to_remove)
            except Exception as e:
                log.error(
                    "could not remove path %s: %s", backup_to_remove, e, exc_info=True
                )
