import logging
import queue
import re
import subprocess
from datetime import datetime

import croniter

from pg_dump.config import settings
from pg_dump.jobs import PgDumpJob

log = logging.getLogger(__name__)

PGDUMP_QUEUE: queue.Queue[PgDumpJob] = queue.Queue()


class CoreSubprocessError(Exception):
    pass


def get_next_backup_time() -> datetime:
    now = datetime.utcnow()
    cron = croniter.croniter(
        settings.PGDUMP_BACKUP_POLICY_CRON_EXPRESSION,
        start_time=now,
    )
    return cron.get_next(ret_type=datetime)


def get_new_backup_filename(now: datetime, db_version: str):
    number = str(
        len([f for f in settings.PGDUMP_BACKUP_FOLDER_PATH.iterdir() if f.is_file()])
    )
    while len(number) < 4:
        number = f"0{number}"

    return "{}_{}_{}_{}.sql".format(
        number,
        settings.PGDUMP_DATABASE_DB,
        now.strftime("%Y%m%d_%H%M"),
        db_version,
    )


def backup_folder_path(filename: str):
    return (settings.PGDUMP_BACKUP_FOLDER_PATH / filename).absolute()


def recreate_pgpass_file():
    log.info("Removing old pgpass file")
    settings.PGDUMP_PGPASS_FILE_PATH.unlink(missing_ok=True)

    log.info("Start creating pgpass file")
    text = settings.PGDUMP_DATABASE_HOSTNAME
    text += f":{settings.PGDUMP_DATABASE_PORT}"
    text += f":{settings.PGDUMP_DATABASE_USER}"
    text += f":{settings.PGDUMP_DATABASE_DB}"
    text += f":{settings.PGDUMP_DATABASE_PASSWORD}"

    log.info("Perform chmod 0600 on pgpass file")
    settings.PGDUMP_PGPASS_FILE_PATH.touch(0o600)

    log.info("Start saving pgpass file")
    with open(settings.PGDUMP_PGPASS_FILE_PATH, "w") as file:
        file.write(text)


def run_subprocess(shell_args: list[str]) -> str:
    p = subprocess.Popen(
        shell_args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    log.info("run_subprocess() Running: '%s'", " ".join(shell_args))
    output, err = p.communicate(timeout=settings.PGDUMP_POSTGRES_TIMEOUT_AFTER_SECS)

    if p.returncode != 0:
        log.error("run_subprocess() Fail with status %s", p.returncode)
        log.error("run_subprocess() stdout: %s", output)
        log.error("run_subprocess() stderr: %s", err)
        raise CoreSubprocessError(
            f"'{' '.join(shell_args)}' \n"
            f"Subprocess {p.pid} failed with code: {p.returncode} and shell args: {shell_args}"
        )
    else:
        log.info("run_subprocess(): Finished with status %s", p.returncode)
        log.debug("run_subprocess() stdout: %s", output)
        log.debug("run_subprocess() stderr: %s", err)
    return output


def run_pg_dump(output_file: str):
    log.info("Start pg_dump")
    run_subprocess(
        [
            "pg_dump",
            "-v",
            "-O",
            "-Fc",
            "-U",
            settings.PGDUMP_DATABASE_USER,
            "-p",
            settings.PGDUMP_DATABASE_PORT,
            "-h",
            settings.PGDUMP_DATABASE_HOSTNAME,
            settings.PGDUMP_DATABASE_DB,
            "-f",
            str(backup_folder_path(output_file)),
        ],
    )
    log.info("Finished pg_dump, output file: %s", output_file)


def get_postgres_version():
    log.info("Start postgres connection to get pg version")
    pg_version_regex = re.compile(r"PostgreSQL \d*\.\d* ")
    result = run_subprocess(
        [
            "psql",
            "-U",
            settings.PGDUMP_DATABASE_USER,
            "-p",
            settings.PGDUMP_DATABASE_PORT,
            "-h",
            settings.PGDUMP_DATABASE_HOSTNAME,
            settings.PGDUMP_DATABASE_DB,
            "-w",
            "--command",
            "SELECT version();",
        ],
    )
    version = None
    matches: list[str] = pg_version_regex.findall(result)

    for match in matches:
        version = match.strip()
        break
    if version is None:
        log.warning(
            "get_postgres_version() Error processing pg result, version is Unknown: %s",
            result,
        )
        return "unknown"
    log.info("Calculated PostgreSQL version: %s", version)
    return version.replace(" ", "_").lower()
