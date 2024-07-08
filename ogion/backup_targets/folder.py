# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import logging
from pathlib import Path
from typing import override

from ogion import core
from ogion.backup_targets.base_target import BaseBackupTarget
from ogion.models.backup_target_models import DirectoryTargetModel

log = logging.getLogger(__name__)


class Folder(BaseBackupTarget):
    def __init__(self, target_model: DirectoryTargetModel) -> None:
        super().__init__(target_model)
        self.target_model: DirectoryTargetModel = target_model

    @override
    def backup(self) -> Path:
        escaped_foldername = core.safe_text_version(self.target_model.abs_path.name)

        out_file = core.get_new_backup_path(self.env_name, escaped_foldername)

        shell_create_dir_symlink = f"ln -s {self.target_model.abs_path} {out_file}"
        log.debug("start ln in subprocess: %s", shell_create_dir_symlink)
        core.run_subprocess(shell_create_dir_symlink)
        log.debug("finished ln, output: %s", out_file)
        return out_file

    @override
    def restore(self, path: str) -> None:
        shell_cp_file = f"cp -r {path} {self.target_model.abs_path.parent}"
        log.debug("start cp in subprocess: %s", shell_cp_file)
        core.run_subprocess(shell_cp_file)
        log.debug("finished cp to %s", self.target_model.abs_path)
