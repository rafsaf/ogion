# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import logging
import shutil
from pathlib import Path
from typing import override

from ogion import core
from ogion.backup_targets.base_target import BaseBackupTarget
from ogion.models.backup_target_models import SingleFileTargetModel

log = logging.getLogger(__name__)


class File(BaseBackupTarget):
    def __init__(self, target_model: SingleFileTargetModel) -> None:
        super().__init__(target_model)
        self.target_model: SingleFileTargetModel = target_model

    @override
    def backup(self) -> Path:
        escaped_filename = core.safe_text_version(self.target_model.abs_path.name)

        out_file = core.get_new_backup_path(self.env_name, escaped_filename)

        log.debug("start copy of %s to %s", self.target_model.abs_path, out_file)
        shutil.copy2(self.target_model.abs_path, out_file)
        log.debug("finished ln, output: %s", out_file)
        return out_file

    @override
    def restore(self, path: str) -> None:
        log.info("start restore of %s", path)
        log.debug("start copy of %s to %s", path, self.target_model.abs_path)
        shutil.copy2(path, self.target_model.abs_path)
        log.debug("finished cp to %s", self.target_model.abs_path)
        log.info("success restore of %s", path)
