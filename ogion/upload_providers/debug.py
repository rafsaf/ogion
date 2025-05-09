# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import logging
from pathlib import Path
from typing import override

from ogion import config, core
from ogion.models.upload_provider_models import DebugProviderModel
from ogion.upload_providers.base_provider import BaseUploadProvider

log = logging.getLogger(__name__)


class UploadProviderLocalDebug(BaseUploadProvider):
    """Represent local folder `data` for storing backups.

    If docker volume/persistant volume is lost, so are backups.
    """

    def __init__(self, target_provider: DebugProviderModel) -> None:
        pass

    @override
    def post_save(self, backup_file: Path) -> str:
        age_file = core.run_create_age_archive(backup_file=backup_file)

        out_path = config.CONST_DEBUG_FOLDER_PATH / age_file.parent.name / age_file.name
        out_path.parent.mkdir(mode=0o700, exist_ok=True)

        shell_copy_to_debug_dir = f"cp {age_file} {out_path}"
        core.run_subprocess(shell_copy_to_debug_dir)

        return str(out_path)

    @override
    def all_target_backups(self, env_name: str) -> list[str]:
        backups: list[str] = []
        path = config.CONST_DEBUG_FOLDER_PATH / env_name
        path.mkdir(mode=0o700, exist_ok=True)
        for backup_path in path.iterdir():
            backups.append(str(backup_path.absolute()))
        backups.sort(reverse=True)
        return backups

    @override
    def download_backup(self, path: str) -> Path:
        log.debug(
            "concate %s and %s",
            config.CONST_DOWNLOADS_FOLDER_PATH,
            path.removeprefix("/"),
        )
        backup_file = config.CONST_DOWNLOADS_FOLDER_PATH / path.removeprefix("/")
        log.debug("debug provider download backup file %s", backup_file)
        backup_file.parent.mkdir(parents=True, exist_ok=True)

        p = Path(path)

        backup_file.write_bytes(p.read_bytes())

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
            backup_to_remove = Path(backups.pop())
            if core.file_before_retention_period_ends(
                backup_name=backup_to_remove.name, min_retention_days=min_retention_days
            ):
                log.info(
                    "there are more backups than max_backups (%s/%s), "
                    "but oldest cannot be removed due to min retention days",
                    len(backups),
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
