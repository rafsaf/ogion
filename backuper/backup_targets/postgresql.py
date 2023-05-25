import logging
import re
import shlex
import sys
import urllib.parse

from pydantic import SecretStr

from backuper import config, core
from backuper.backup_targets.base_target import BaseBackupTarget

log = logging.getLogger(__name__)

VERSION_REGEX = re.compile(r"PostgreSQL \d*\.\d* ")


class PostgreSQL(BaseBackupTarget):
    # https://www.postgresql.org/docs/current/app-pgdump.html
    # https://www.postgresql.org/docs/current/app-psql.html

    def __init__(
        self,
        user: str,
        password: SecretStr,
        port: int,
        host: str,
        db: str,
        cron_rule: str,
        env_name: str,
        **kwargs,
    ) -> None:
        super().__init__(cron_rule=cron_rule, env_name=env_name)
        self.cron_rule = cron_rule
        self.user = user
        self.db = db
        self.host = host
        self.port = port
        self.password = password
        self.escaped_conn_uri = self._get_escaped_conn_uri()
        self.db_version = self._postgres_connection()

    def _init_pgpass_file(self):
        # https://www.postgresql.org/docs/current/libpq-pgpass.html
        # If an entry needs to contain : or \, escape this character with \.

        def escape(s: str):
            return s.replace("\\", "\\\\").replace(":", "\\:")

        name = f"{self.env_name}.pgpass"
        path = config.BASE_DIR / name
        path.unlink(missing_ok=True)
        path.touch(0o600)
        with open(path, "w") as file:
            password = self.password.get_secret_value()
            file.write(
                "{}:{}:{}:{}:{}\n".format(
                    self.host,
                    self.port,
                    escape(self.db),
                    escape(self.user),
                    escape(password),
                )
            )
        log.debug("content of %s: %s", path, path.read_text())
        return path

    def _get_escaped_conn_uri(self):
        # https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING
        # The connection URI needs to be encoded with percent-encoding if
        # it includes symbols with special meaning in any of its parts.

        pgpass_file = self._init_pgpass_file()
        encoded_user = urllib.parse.quote_plus(self.user)
        encoded_db = urllib.parse.quote_plus(self.db)
        uri = (
            f"postgresql://{encoded_user}@{self.host}:{self.port}/{encoded_db}?"
            f"passfile={pgpass_file}"
        )
        escaped_uri = shlex.quote(uri)
        return escaped_uri

    def _postgres_connection(self):
        log.debug("postgres_connection start postgres connection")

        try:
            result = core.run_subprocess(
                f"psql -d {self.escaped_conn_uri} -w --command 'SELECT version();'",
            )
        except core.CoreSubprocessError as err:
            log.error(err, exc_info=True)
            log.error("postgres_connection unable to connect to database, exiting")
            sys.exit(1)

        version = None
        matches = VERSION_REGEX.finditer(result)

        for match in matches:
            version = match.group(0).strip().split(" ")[1]
            break
        if version is None:  # pragma: no cover
            log.error(
                "postgres_connection error processing pg result, version unknown: %s",
                result,
            )
            sys.exit(1)
        log.debug("postgres_connection calculated version: %s", version)
        return version

    def _backup(self):
        escaped_dbname = core.safe_text_version(self.db)
        name = f"{escaped_dbname}_{self.db_version}"
        out_file = core.get_new_backup_path(self.env_name, name, sql=True)
        shell_args = f"pg_dump -v -O -d {self.escaped_conn_uri} -f {out_file}"
        log.debug("start pg_dump in subprocess: %s", shell_args)
        core.run_subprocess(shell_args)
        log.debug("finished pg_dump, output: %s", out_file)
        return out_file
