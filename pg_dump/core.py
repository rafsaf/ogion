import logging
import re
import secrets
import subprocess
from datetime import datetime

from pg_dump import config

log = logging.getLogger(__name__)


class CoreSubprocessError(Exception):
    pass


def run_subprocess(shell_args: str) -> str:
    log.debug("run_subprocess running: '%s'", shell_args)
    p = subprocess.run(
        shell_args,
        capture_output=True,
        text=True,
        shell=True,
        timeout=config.SUBPROCESS_TIMEOUT_SECS,
    )
    if p.returncode:
        log.error("run_subprocess failed with status %s", p.returncode)
        log.error("run_subprocess stdout: %s", p.stdout)
        log.error("run_subprocess stderr: %s", p.stderr)
        raise CoreSubprocessError()

    log.debug("run_subprocess finished with status %s", p.returncode)
    log.debug("run_subprocess stdout: %s", p.stdout)
    log.debug("run_subprocess stderr: %s", p.stderr)
    return p.stdout


def get_new_backup_path(db_version: str):
    random_string = secrets.token_urlsafe(3)
    new_file = "{}/{}_{}_{}_{}".format(
        config.BACKUP_FOLDER_PATH,
        datetime.utcnow().strftime("%Y%m%d_%H%M"),
        config.POSTGRES_DB,
        db_version,
        random_string,
    )
    return new_file


def run_create_zip_archive(backup_file: str):
    out_file = f"{backup_file}.zip"
    shell_args = (
        f"{config.ZIP_BIN_7ZZ_PATH} a -p{config.ZIP_ARCHIVE_PASSWORD} -mx=5 "
        f"{out_file} {backup_file}"
    )
    log.debug("run_create_zip_archive start in subprocess: %s", backup_file)
    run_subprocess(shell_args)
    log.debug("run_create_zip_archive finished, output: %s", out_file)
    return out_file


def run_pg_dump(db_version: str):
    out_file = get_new_backup_path(db_version)

    shell_args = (
        f"pg_dump -v -O -Fc "
        f"-U {config.POSTGRES_USER} "
        f"-p {config.POSTGRES_PORT} "
        f"-h {config.POSTGRES_HOST} "
        f"{config.POSTGRES_DB} "
        f"-f {out_file}"
    )
    log.debug("run_pg_dump start pg_dump in subprocess: %s", shell_args)
    run_subprocess(shell_args)
    log.debug("run_pg_dump finished pg_dump, output: %s", out_file)
    return out_file


def postgres_connection():
    log.debug("postgres_connection start postgres connection")
    pg_version_regex = re.compile(r"PostgreSQL \d*\.\d* ")
    try:
        result = run_subprocess(
            f"psql -U {config.POSTGRES_USER} "
            f"-p {config.POSTGRES_PORT} "
            f"-h {config.POSTGRES_HOST} "
            f"{config.POSTGRES_DB} "
            f"-w --command 'SELECT version();'",
        )
    except CoreSubprocessError as err:
        log.error(err, exc_info=True)
        log.error("postgres_connection unable to connect to database, exiting")
        exit(1)

    version = None
    matches: list[str] = pg_version_regex.findall(result)

    for match in matches:
        version = match.strip().split(" ")[1]
        break
    if version is None:
        log.error(
            "postgres_connection error processing pg result, version unknown: %s",
            result,
        )
        exit(1)
    log.debug("postgres_connection calculated version: %s", version)
    return version


def init_pgpass_file():
    pgpass_text = "{}:{}:{}:{}:{}".format(
        config.POSTGRES_HOST,
        config.POSTGRES_PORT,
        config.POSTGRES_USER,
        config.POSTGRES_DB,
        config.POSTGRES_PASSWORD,
    )
    with open(config.PGPASS_FILE_PATH, "w") as file:
        file.write(pgpass_text)
