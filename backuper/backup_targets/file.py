import logging
from pathlib import Path

from backuper import core
from backuper.backup_targets.base_target import BaseBackupTarget
from backuper.models.backup_target_models import SingleFileTargetModel

log = logging.getLogger(__name__)


class File(BaseBackupTarget):
    def __init__(self, target_model: SingleFileTargetModel) -> None:
        self.target_model = target_model
        super().__init__(target_model)

    def _backup(self) -> Path:
        out_file = core.get_new_backup_path(
            self.env_name, self.target_model.abs_path.name
        )

        shell_create_file_symlink = f"ln -s {self.target_model.abs_path} {out_file}"
        log.debug("start ln in subprocess: %s", shell_create_file_symlink)
        core.run_subprocess(shell_create_file_symlink)
        log.debug("finished ln, output: %s", out_file)
        return out_file
