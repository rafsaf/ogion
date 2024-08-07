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
from ogion.models.backup_target_models import MySQLTargetModel

log = logging.getLogger(__name__)

VERSION_REGEX = re.compile(r"\d*\.\d*\.\d*")


class MySQL(BaseBackupTarget):
    # https://dev.mysql.com/doc/refman/8.0/en/option-files.html
    # https://dev.mysql.com/doc/refman/8.0/en/mysqldump.html
    # https://dev.mysql.com/doc/refman/8.0/en/connecting.html

    def __init__(self, target_model: MySQLTargetModel) -> None:
        super().__init__(target_model)
        self.target_model: MySQLTargetModel = target_model
        self.db_name = shlex.quote(self.target_model.db)
        self.option_file: Path = self._init_option_file()
        self.db_version: str = self._mysql_connection()

    def _init_option_file(self) -> Path:
        def escape(s: str) -> str:
            return s.replace("\\", "\\\\")

        password = self.target_model.password.get_secret_value()
        text = "{}\n{}\n{}\n{}\n{}\n{}".format(
            "[client]",
            f'user="{escape(self.target_model.user)}"',
            f'password="{escape(password)}"',
            f"host={self.target_model.host}",
            f"port={self.target_model.port}",
            "protocol=TCP",
        )
        md5_hash = hashlib.md5(text.encode(), usedforsecurity=False).hexdigest()
        name = f"{self.env_name}.{md5_hash}.mysql.cnf"

        path = config.CONST_CONFIG_FOLDER_PATH / name
        path.touch(0o600)
        with open(path, "w") as file:
            file.write(text)

        return path

    def _mysql_connection(self) -> str:
        try:
            log.debug("check mysql installation")
            mysql_version = core.run_subprocess("mysql -V")
            log.debug("output: %s", mysql_version)
        except core.CoreSubprocessError as version_err:  # pragma: no cover
            log.critical(
                "mysql client is not detected on your system (%s)\n"
                "check out ready script: "
                "https://github.com/rafsaf/ogion/blob/main/scripts/install_mariadb_mysql_client.sh",
                version_err,
            )
            raise
        log.debug("start mysql connection")
        try:
            result = core.run_subprocess(
                f"mariadb --defaults-file={self.option_file} {self.db_name} "
                "--execute='SELECT version();'",
            )
        except core.CoreSubprocessError as err:
            log.error(err, exc_info=True)
            log.error("unable to connect to database, exiting")
            raise

        version = None
        matches = VERSION_REGEX.finditer(result)

        for match in matches:
            version = match.group(0)
            break
        if version is None:  # pragma: no cover
            msg = (
                f"mysql_connection error processing sql result, "
                f"version unknown: {result}"
            )
            log.error(msg)
            raise ValueError(msg)
        log.info("mysql_connection calculated version: %s", version)
        return version

    @override
    def backup(self) -> Path:
        escaped_dbname = core.safe_text_version(self.target_model.db)
        escaped_version = core.safe_text_version(self.db_version)
        name = f"{escaped_dbname}_{escaped_version}"

        out_file = core.get_new_backup_path(self.env_name, name).with_suffix(".sql")

        shell_mysqldump_db = (
            f"mariadb-dump --defaults-file={self.option_file} "
            f"--result-file={out_file} --verbose {self.db_name}"
        )
        log.debug("start mysqldump in subprocess: %s", shell_mysqldump_db)
        core.run_subprocess(shell_mysqldump_db)
        log.debug("finished mysqldump, output: %s", out_file)
        return out_file

    @override
    def restore(self, path: str) -> None:
        shell_mysql_restore = (
            f"mariadb --defaults-file={self.option_file} {self.db_name} < {path}"
        )
        log.debug("start restore in subprocess: %s", shell_mysql_restore)
        core.run_subprocess(shell_mysql_restore)
        log.debug("finished restore")
