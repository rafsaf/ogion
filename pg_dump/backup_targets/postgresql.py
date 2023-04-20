import logging
import re

from pg_dump import config, core
from pg_dump.backup_targets.base_target import BaseBackupTarget

log = logging.getLogger(__name__)

VERSION_REGEX = re.compile(r"PostgreSQL \d*\.\d* ")


class PostgreSQL(BaseBackupTarget):
    def __init__(
        self,
        user: str,
        password: str,
        port: int,
        host: str,
        db: str,
        cron_rule: str,
        **kwargs,
    ) -> None:
        self.cron_rule = cron_rule
        self.user = user
        self.port = port
        self.db = db
        self.host = host
        self.password = password
        self._init_pgpass_file()
        self.db_version = self._postgres_connection()
        super().__init__(cron_rule=cron_rule)

    def _init_pgpass_file(self):
        pgpass_text = "{}:{}:{}:{}:{}\n".format(
            self.host,
            self.port,
            self.user,
            self.db,
            self.password,
        )
        with open(config.CONST_PGPASS_FILE_PATH, "a") as file:
            file.write(pgpass_text)

    def _postgres_connection(self):
        log.debug("postgres_connection start postgres connection")

        try:
            result = core.run_subprocess(
                f"psql -U {self.user} "
                f"-p {self.port} "
                f"-h {self.host} "
                f"{self.db} "
                "-w --command 'SELECT version();'",
            )
        except core.CoreSubprocessError as err:
            log.error(err, exc_info=True)
            log.error("postgres_connection unable to connect to database, exiting")
            exit(1)

        version = None
        matches: list[str] = VERSION_REGEX.findall(result)

        for match in matches:
            version = match.strip().split(" ")[1]
            break
        if version is None:  # pragma: no cover
            log.error(
                "postgres_connection error processing pg result, version unknown: %s",
                result,
            )
            exit(1)
        log.debug("postgres_connection calculated version: %s", version)
        return version

    def _backup(self):
        name = f"{self.db}_{self.db_version}"
        out_file = core.get_new_backup_path(name)

        shell_args = (
            f"pg_dump -v -O -Fc "
            f"-U {self.user} "
            f"-p {self.port} "
            f"-h {self.host} "
            f"{self.db} "
            f"-f {out_file}"
        )
        log.debug("start pg_dump in subprocess: %s", shell_args)
        core.run_subprocess(shell_args)
        log.debug("finished pg_dump, output: %s", out_file)
        return out_file
