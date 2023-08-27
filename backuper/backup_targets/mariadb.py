import hashlib
import logging
import re
import shlex
from pathlib import Path

from pydantic import SecretStr

from backuper import config, core
from backuper.backup_targets.base_target import BaseBackupTarget

log = logging.getLogger(__name__)

VERSION_REGEX = re.compile(r"\d*\.\d*\.\d*")


class MariaDB(BaseBackupTarget, target_model_name=config.BackupTargetEnum.MARIADB):
    # https://mariadb.com/kb/en/configuring-mariadb-with-option-files/
    # https://mariadb.com/kb/en/mariadb-dump/
    # https://mariadb.com/kb/en/connecting-to-mariadb/

    def __init__(
        self,
        user: str,
        password: SecretStr,
        port: int,
        host: str,
        db: str,
        cron_rule: str,
        env_name: str,
        max_backups: int,
        min_retention_days: int,
        **kwargs: str | int,
    ) -> None:
        super().__init__(
            cron_rule=cron_rule,
            env_name=env_name,
            max_backups=max_backups,
            min_retention_days=min_retention_days,
        )
        self.cron_rule: str = cron_rule
        self.user: str = user
        self.db: str = db
        self.host: str = host
        self.port: int = port
        self.password: SecretStr = password
        self.option_file: Path = self._init_option_file()
        self.db_version: str = self._mariadb_connection()

    def _init_option_file(self) -> Path:
        def escape(s: str) -> str:
            return s.replace("\\", "\\\\")

        password = self.password.get_secret_value()
        text = "{}\n{}\n{}\n{}\n{}\n{}".format(
            "[client]",
            f'user="{escape(self.user)}"',
            f"host={self.host}",
            f"port={self.port}",
            "protocol=TCP",
            f'password="{escape(password)}"' if self.password else "",
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
                "https://github.com/rafsaf/backuper/blob/main/scripts/install_mariadb_mysql_client.sh",
                version_err,
            )
            raise
        log.debug("start mariadb connection")
        try:
            db = shlex.quote(self.db)
            result = core.run_subprocess(
                f"mariadb --defaults-file={self.option_file} {db} "
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
            msg = f"mariadb_connection error processing sql result, version unknown: {result}"
            log.error(msg)
            raise ValueError(msg)
        log.info("mariadb_connection calculated version: %s", version)
        return version

    def _backup(self) -> Path:
        escaped_dbname = core.safe_text_version(self.db)
        name = f"{escaped_dbname}_{self.db_version}"
        out_file = core.get_new_backup_path(self.env_name, name, sql=True)
        db = shlex.quote(self.db)
        shell_mariadb_dump_db = (
            f"mariadb-dump --defaults-file={self.option_file} "
            f"--result-file={out_file} --verbose {db}"
        )
        log.debug("start mariadbdump in subprocess: %s", shell_mariadb_dump_db)
        core.run_subprocess(shell_mariadb_dump_db)
        log.debug("finished mariadbdump, output: %s", out_file)
        return out_file
