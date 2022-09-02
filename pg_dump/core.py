import base64
import binascii
import logging
import multiprocessing
import queue
import re
import secrets
import subprocess
from datetime import datetime

import croniter

from pg_dump.config import settings
from pg_dump.jobs import PgDumpJob

log = logging.getLogger(__name__)

PGDUMP_QUEUE: queue.Queue[PgDumpJob] = queue.Queue(
    maxsize=settings.PGDUMP_NUMBER_PGDUMP_THREADS
)


class CoreSubprocessError(Exception):
    pass


def get_next_backup_time() -> datetime:
    now = datetime.utcnow()
    cron = croniter.croniter(
        settings.PGDUMP_BACKUP_POLICY_CRON_EXPRESSION,
        start_time=now,
    )
    return cron.get_next(ret_type=datetime)


def get_new_backup_foldername(now: datetime, db_version: str):
    random_string = secrets.token_urlsafe(3)
    return "{}_{}_{}_{}".format(
        settings.PGDUMP_DATABASE_DB,
        now.strftime("%Y%m%d_%H%M"),
        db_version,
        random_string,
    )


def backup_folder_path(foldername: str):
    return (settings.PGDUMP_BACKUP_FOLDER_PATH / foldername).absolute()


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
        log.info("run_subprocess() stdout: %s", output)
        log.info("run_subprocess() stderr: %s", err)
    return output


def run_pg_dump(output_folder: str):
    log.info("Start pg_dump")
    out = backup_folder_path(output_folder)
    run_subprocess(
        [
            "pg_dump",
            "-v",
            "-O",
            "-Fd",
            "-j",
            f"{multiprocessing.cpu_count()}",
            "-U",
            settings.PGDUMP_DATABASE_USER,
            "-p",
            settings.PGDUMP_DATABASE_PORT,
            "-h",
            settings.PGDUMP_DATABASE_HOSTNAME,
            settings.PGDUMP_DATABASE_DB,
            "-f",
            str(out),
        ],
    )
    log.info("Finished pg_dump, output folder: %s", output_folder)


def recreate_gpg_public_key():
    log.info("Starting recreate_gpg_public_key")
    if not settings.PGDUMP_GPG_PUBLIC_KEY_BASE64:
        log.info("No GPG public key provided, skipped recreate_gpg_public_key")
        return
    try:
        gpg_pub_cert = base64.standard_b64decode(settings.PGDUMP_GPG_PUBLIC_KEY_BASE64)
    except binascii.Error as err:
        log.error("recreate_gpg_public_key base64 error: %s", err, exc_info=True)
        log.error("Set correct PGDUMP_GPG_PUBLIC_KEY_BASE64, exiting")
        exit(1)
    with open(settings.PGDUMP_GPG_PUBLIC_KEY_BASE64_PATH, "wb") as gpg_pub_file:
        gpg_pub_file.write(gpg_pub_cert)
    log.debug("Saved gpg public key: %s", gpg_pub_cert.decode())
    log.info("Successfully finished recreate_gpg_public_key")


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
