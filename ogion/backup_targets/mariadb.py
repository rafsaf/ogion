# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import hashlib
import logging
import re
import shlex
from pathlib import Path
from typing import override

from ogion import config, core
from ogion.backup_targets.base_target import BaseBackupTarget
from ogion.models.backup_target_models import MariaDBTargetModel

log = logging.getLogger(__name__)

VERSION_REGEX = re.compile(r"\d*\.\d*\.\d*")


class MariaDB(BaseBackupTarget):
    # https://mariadb.com/kb/en/configuring-mariadb-with-option-files/
    # https://mariadb.com/kb/en/mariadb-dump/
    # https://mariadb.com/kb/en/connecting-to-mariadb/

    def __init__(self, target_model: MariaDBTargetModel) -> None:
        super().__init__(target_model)
        self.target_model: MariaDBTargetModel = target_model
        self.db_name = shlex.quote(self.target_model.db)
        self.option_file: Path = self._init_option_file()
        self.db_version: str = self._mariadb_connection()

    def _init_option_file(self) -> Path:
        def escape(s: str) -> str:
            return s.replace("\\", "\\\\")

        password = self.target_model.password.get_secret_value()
        text = "{}\n{}\n{}\n{}\n{}\n{}".format(
            "[client]",
            f'user="{escape(self.target_model.user)}"',
            f"host={self.target_model.host}",
            f"port={self.target_model.port}",
            "protocol=TCP",
            f'password="{escape(password)}"' if self.target_model.password else "",
        )
        md5_hash = hashlib.md5(text.encode(), usedforsecurity=False).hexdigest()
        name = f"{self.env_name}.{md5_hash}.mariadb.cnf"

        path = config.CONST_CONFIG_FOLDER_PATH / name
        path.touch(0o600)
        with open(path, "w") as file:
            file.write(text)

        return path

    def _mariadb_connection(self) -> str:
        try:
            log.debug("check mariadb installation")
            mariadb_version = core.run_subprocess("mariadb -V")
            log.debug("output: %s", mariadb_version)
        except core.CoreSubprocessError as version_err:  # pragma: no cover
            log.critical(
                "mariadb client is not detected on your system (%s)\n"
                "check out ready script: "
                "https://github.com/rafsaf/ogion/blob/main/scripts/install_mariadb_mysql_client.sh",
                version_err,
            )
            raise
        log.debug("start mariadb connection")
        try:
            result = core.run_subprocess(
                f"mariadb --defaults-file={self.option_file} {self.db_name} "
                f"--execute='SELECT version();'",
            )
        except core.CoreSubprocessError as conn_err:
            log.error(conn_err, exc_info=True)
            log.error("unable to connect to database, exiting")
            raise

        version = None
        matches = VERSION_REGEX.finditer(result)

        for match in matches:
            version = match.group(0)
            break
        if version is None:  # pragma: no cover
            msg = (
                f"mariadb_connection error processing sql result, "
                f"version unknown: {result}"
            )
            log.error(msg)
            raise ValueError(msg)
        log.info("mariadb_connection calculated version: %s", version)
        return version

    @override
    def _backup(self) -> Path:
        escaped_dbname = core.safe_text_version(self.target_model.db)
        escaped_version = core.safe_text_version(self.db_version)
        name = f"{escaped_dbname}_{escaped_version}"

        out_file = core.get_new_backup_path(self.env_name, name).with_suffix(".sql")

        shell_mariadb_dump_db = (
            f"mariadb-dump --defaults-file={self.option_file} "
            f"--result-file={out_file} --verbose {self.db_name}"
        )
        log.debug("start mariadbdump in subprocess: %s", shell_mariadb_dump_db)
        core.run_subprocess(shell_mariadb_dump_db)
        log.debug("finished mariadbdump, output: %s", out_file)
        return out_file

    @override
    def restore(self, path: Path) -> None:
        return None
