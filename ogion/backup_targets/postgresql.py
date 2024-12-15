# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import hashlib
import logging
import re
import shlex
import urllib.parse
from pathlib import Path
from typing import override

from ogion import config, core
from ogion.backup_targets.base_target import BaseBackupTarget
from ogion.models.backup_target_models import PostgreSQLTargetModel

log = logging.getLogger(__name__)

VERSION_REGEX = re.compile(r"PostgreSQL \d*\.\d* ")


class PostgreSQL(BaseBackupTarget):
    # https://www.postgresql.org/docs/current/app-pgdump.html
    # https://www.postgresql.org/docs/current/app-psql.html

    def __init__(self, target_model: PostgreSQLTargetModel) -> None:
        super().__init__(target_model)
        self.target_model: PostgreSQLTargetModel = target_model
        self.escaped_conn_uri: str = self._get_escaped_conn_uri()
        self.db_version: str = self._postgres_connection()

    def _init_pgpass_file(self) -> Path:
        # https://www.postgresql.org/docs/current/libpq-pgpass.html
        # If an entry needs to contain : or \, escape this character with \.

        def escape(s: str) -> str:
            return s.replace("\\", "\\\\").replace(":", "\\:")

        password = self.target_model.password.get_secret_value()
        text = (
            f"{self.target_model.host}:"
            f"{self.target_model.port}:"
            f"{escape(self.target_model.db)}:"
            f"{escape(self.target_model.user)}:"
            f"{escape(password)}\n"
        )

        md5_hash = hashlib.md5(text.encode(), usedforsecurity=False).hexdigest()
        name = f"{self.env_name}.{md5_hash}.pgpass"

        path = config.CONST_CONFIG_FOLDER_PATH / name
        path.touch(0o600)
        with open(path, "w") as file:
            file.write(text)
        log.debug("content of %s: %s", path, path.read_text())
        return path

    def _get_escaped_conn_uri(self) -> str:
        # https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING
        # The connection URI needs to be encoded with percent-encoding if
        # it includes symbols with special meaning in any of its parts.

        pgpass_file = self._init_pgpass_file()
        encoded_user = urllib.parse.quote_plus(self.target_model.user)
        encoded_db = urllib.parse.quote_plus(self.target_model.db)

        params = {"passfile": pgpass_file}
        if self.target_model.model_extra is not None:
            for param, value in self.target_model.model_extra.items():
                if not param.startswith("conn_"):
                    continue

                params[param.removeprefix("conn_")] = value

        log.debug("psql connection params: %s", params)

        uri = (
            f"postgresql://{encoded_user}@{self.target_model.host}:{self.target_model.port}/{encoded_db}?"
        ) + urllib.parse.urlencode(params)

        log.debug("psql connection url: %s", uri)

        escaped_uri = shlex.quote(uri)
        return escaped_uri

    def _postgres_connection(self) -> str:
        try:
            log.debug("check psql installation")
            psql_version = core.run_subprocess("psql -V")
            log.debug("output: %s", psql_version)
        except core.CoreSubprocessError as version_err:  # pragma: no cover
            log.critical(
                "psql postgres client is not detected on your system (%s)\n"
                "check out ready script: "
                "https://github.com/rafsaf/ogion/blob/main/scripts/install_postgresql_client.sh",
                version_err,
            )
            raise
        log.debug("start postgres connection")
        try:
            result = core.run_subprocess(
                f"psql -d {self.escaped_conn_uri} -w --command 'SELECT version();'",
            )
        except core.CoreSubprocessError as err:
            log.error(err, exc_info=True)
            log.error("unable to connect to database, exiting")
            raise

        version = None
        matches = VERSION_REGEX.finditer(result)

        for match in matches:
            version = match.group(0).strip().split(" ")[1]
            break
        if version is None:  # pragma: no cover
            msg = (
                f"postgres_connection error processing sql result, "
                f"version unknown: {result}"
            )
            log.error(msg)
            raise ValueError(msg)
        log.info("postgres_connection calculated version: %s", version)
        return version

    @override
    def backup(self) -> Path:
        escaped_dbname = core.safe_text_version(self.target_model.db)
        escaped_version = core.safe_text_version(self.db_version)
        name = f"{escaped_dbname}_{escaped_version}"

        out_file = core.get_new_backup_path(self.env_name, name).with_suffix(".sql")

        shell_pg_dump_db = (
            f"pg_dump --clean --if-exists -v -O -d "
            f"{self.escaped_conn_uri} -f {out_file}"
        )
        log.debug("start pg_dump in subprocess: %s", shell_pg_dump_db)
        core.run_subprocess(shell_pg_dump_db)
        log.debug("finished pg_dump, output: %s", out_file)
        return out_file

    @override
    def restore(self, path: str) -> None:
        shell_psql_restore = f"psql {self.escaped_conn_uri} < {path}"
        log.debug("start restore in subprocess: %s", shell_psql_restore)
        core.run_subprocess(shell_psql_restore)
        log.debug("finished restore")
