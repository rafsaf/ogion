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

        out_file = core.get_new_backup_path(
            self.env_name, escaped_foldername
        ).with_suffix(".tar")

        tar_args = [
            "tar",
            "-C",
            str(self.target_model.abs_path.parent),
            "-cf",
            str(out_file),
            self.target_model.abs_path.name,
        ]
        log.debug(
            "start tar in subprocess: %s",
            tar_args,
        )
        core.run_subprocess(tar_args)
        log.debug("finished tar, output: %s", out_file)
        return out_file

    @override
    def restore(self, path: str) -> None:
        log.info("start restore of %s", path)
        self.target_model.abs_path.mkdir(parents=True, exist_ok=True)

        untar_args = [
            "tar",
            "xf",
            path,
            "-C",
            str(self.target_model.abs_path),
            "--strip-components=1",
        ]
        log.debug(
            "start tar extract in subprocess: %s",
            untar_args,
        )
        core.run_subprocess(untar_args)
        log.debug("finished tar extract to %s", self.target_model.abs_path)
        log.info("success restore of %s", path)
