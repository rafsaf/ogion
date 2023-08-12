import logging
import re
import shlex
from pathlib import Path

from pydantic import SecretStr

from backuper import config, core
from backuper.backup_targets.base_target import BaseBackupTarget

log = logging.getLogger(__name__)

VERSION_REGEX = re.compile(r"\d*\.\d*\.\d*")


class MySQL(BaseBackupTarget, target_model_name=config.BackupTargetEnum.MYSQL):
    # https://dev.mysql.com/doc/refman/8.0/en/option-files.html
    # https://dev.mysql.com/doc/refman/8.0/en/mysqldump.html
    # https://dev.mysql.com/doc/refman/8.0/en/connecting.html

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
        **kwargs: str | int,
    ) -> None:
        super().__init__(
            cron_rule=cron_rule, env_name=env_name, max_backups=max_backups
        )
        self.cron_rule: str = cron_rule
        self.user: str = user
        self.db: str = db
        self.host: str = host
        self.port: int = port
        self.password: SecretStr = password
        self.option_file: Path = self._init_option_file()
        self.db_version: str = self._mysql_connection()

    def _init_option_file(self) -> Path:
        def escape(s: str) -> str:
            return s.replace("\\", "\\\\")

        name = f"{self.env_name}.my.cnf"
        path = config.BASE_DIR / name
        path.unlink(missing_ok=True)
        path.touch(0o600)
        with open(path, "w") as file:
            password = self.password.get_secret_value()
            file.write(
                "{}\n{}\n{}\n{}\n{}\n{}".format(
                    "[client]",
                    f'user="{escape(self.user)}"',
                    f'password="{escape(password)}"',
                    f"host={self.host}",
                    f"port={self.port}",
                    "protocol=TCP",
                )
            )
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
                "https://github.com/rafsaf/backuper/blob/main/scripts/install_mariadb_mysql_client.sh",
                version_err,
            )
            raise
        log.debug("start mysql connection")
        try:
            db = shlex.quote(self.db)
            result = core.run_subprocess(
                f"mysql --defaults-file={self.option_file} {db} "
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
            msg = f"mysql_connection error processing sql result, version unknown: {result}"
            log.error(msg)
            raise ValueError(msg)
        log.info("mysql_connection calculated version: %s", version)
        return version

    def _backup(self) -> Path:
        escaped_dbname = core.safe_text_version(self.db)
        name = f"{escaped_dbname}_{self.db_version}"
        out_file = core.get_new_backup_path(self.env_name, name, sql=True)

        db = shlex.quote(self.db)
        shell_args = (
            f"mysqldump --defaults-file={self.option_file} "
            f"--result-file={out_file} --verbose {db}"
        )
        log.debug("start mysqldump in subprocess: %s", shell_args)
        core.run_subprocess(shell_args)
        log.debug("finished mysqldump, output: %s", out_file)
        return out_file
