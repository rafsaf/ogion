import logging
from pathlib import Path

from backuper import core
from backuper.backup_targets.base_target import BaseBackupTarget

log = logging.getLogger(__name__)


class File(BaseBackupTarget):
    def __init__(
        self,
        abs_path: Path,
        cron_rule: str,
        env_name: str,
        **kwargs: str | int,
    ) -> None:
        self.cron_rule: str = cron_rule
        self.file: Path = abs_path
        super().__init__(cron_rule=cron_rule, env_name=env_name)

    def _backup(self) -> Path:
        out_file = core.get_new_backup_path(self.env_name, self.file.name)

        shell_args = f"cp -f {self.file} {out_file}"
        log.debug("start cp -f in subprocess: %s", shell_args)
        core.run_subprocess(shell_args)
        log.debug("finished cp -f, output: %s", out_file)
        return out_file
