import base64
import binascii
import logging
import multiprocessing
import os
import queue
import re
import secrets
import subprocess
from datetime import datetime

import croniter

from pg_dump.config import settings
from pg_dump.jobs import PgDumpJob

log = logging.getLogger(__name__)

PG_DUMP_QUEUE: queue.Queue[PgDumpJob] = queue.Queue(
    maxsize=settings.PG_DUMP_NUMBER_PG_DUMP_THREADS
)
_MB_TO_BYTES = 1048576
_GB_TO_BYTES = 1073741824


class CoreSubprocessError(Exception):
    pass


def get_next_backup_time() -> datetime:
    now = datetime.utcnow()
    cron = croniter.croniter(
        settings.PG_DUMP_BACKUP_POLICY_CRON_EXPRESSION,
        start_time=now,
    )
    return cron.get_next(ret_type=datetime)


def get_new_backup_foldername(now: datetime, db_version: str):
    random_string = secrets.token_urlsafe(3)
    new_foldername = "{}_{}_{}_{}".format(
        settings.PG_DUMP_DATABASE_DB,
        now.strftime("%Y%m%d_%H%M"),
        db_version,
        random_string,
    )
    log.debug(
        "get_new_backup_foldername calculated new backup folder: %s", new_foldername
    )
    return new_foldername


def _get_folder_size(folder):
    total_size = os.path.getsize(folder)
    for item in os.listdir(folder):
        itempath = os.path.join(folder, item)
        if os.path.isfile(itempath):
            total_size += os.path.getsize(itempath)
        elif os.path.isdir(itempath):
            total_size += _get_folder_size(itempath)
    return total_size


def backup_folder_path(foldername: str):
    return (settings.PG_DUMP_BACKUP_FOLDER_PATH / foldername).absolute()


def recreate_pgpass_file():
    log.info("recreate_pgpass_file removing old pgpass file")
    settings.PG_DUMP_PGPASS_FILE_PATH.unlink(missing_ok=True)

    log.info("recreate_pgpass_file start creating pgpass file")
    text = settings.PG_DUMP_DATABASE_HOSTNAME
    text += f":{settings.PG_DUMP_DATABASE_PORT}"
    text += f":{settings.PG_DUMP_DATABASE_USER}"
    text += f":{settings.PG_DUMP_DATABASE_DB}"
    text += f":{settings.PG_DUMP_DATABASE_PASSWORD}"

    log.info("recreate_pgpass_file perform chmod 0600 on pgpass file")
    settings.PG_DUMP_PGPASS_FILE_PATH.touch(0o600)

    log.info("recreate_pgpass_file saving pgpass file")
    with open(settings.PG_DUMP_PGPASS_FILE_PATH, "w") as file:
        file.write(text)


def run_subprocess(shell_args: list[str]) -> str:
    p = subprocess.Popen(
        shell_args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    log.info("run_subprocess running: '%s'", " ".join(shell_args))
    output, err = p.communicate(timeout=settings.PG_DUMP_POSTGRES_TIMEOUT_AFTER_SECS)

    if p.returncode != 0:
        log.error("run_subprocess fail with status %s", p.returncode)
        log.error("run_subprocess stdout: %s", output)
        log.error("run_subprocess stderr: %s", err)
        raise CoreSubprocessError(
            f"'{' '.join(shell_args)}' \n"
            f"recreate_pgpass_file subprocess {p.pid} failed with code: {p.returncode} and shell args: {shell_args}"
        )
    else:
        log.info("run_subprocess finished with status %s", p.returncode)
        log.info("run_subprocess stdout: %s", output)
        log.info("run_subprocess stderr: %s", err)
    return output


def run_pg_dump(output_folder: str):
    log.info("run_pg_dump start pg_dump in subprocess")
    out = str(backup_folder_path(output_folder))
    run_subprocess(
        [
            "pg_dump",
            "-v",
            "-O",
            "-Fd",
            "-j",
            f"{multiprocessing.cpu_count()}",
            "-U",
            settings.PG_DUMP_DATABASE_USER,
            "-p",
            settings.PG_DUMP_DATABASE_PORT,
            "-h",
            settings.PG_DUMP_DATABASE_HOSTNAME,
            settings.PG_DUMP_DATABASE_DB,
            "-f",
            out,
        ],
    )
    output_folder_size = _get_folder_size(out)
    log.debug("run_pg_dump calculated size of %s: %s bytes", out, output_folder_size)
    if output_folder_size < _MB_TO_BYTES:
        size_msg = f"{output_folder_size} bytes ({round(output_folder_size / _MB_TO_BYTES, 4)} mb)"
    elif output_folder_size < _GB_TO_BYTES:
        size_msg = f"{round(output_folder_size / _MB_TO_BYTES, 4)} mb"
    else:
        size_msg = f"{round(output_folder_size / _GB_TO_BYTES, 4)} gb"

    log.info(
        "run_pg_dump finished pg_dump, output folder: %s, size: %s",
        output_folder,
        size_msg,
    )


def recreate_gpg_public_key():
    log.info("recreate_gpg_public_key starting")
    if not settings.PG_DUMP_GPG_PUBLIC_KEY_BASE64:
        log.info("recreate_gpg_public_key no GPG public key provided, skipped")
        return
    try:
        gpg_pub_cert = base64.standard_b64decode(settings.PG_DUMP_GPG_PUBLIC_KEY_BASE64)
    except binascii.Error as err:
        log.error("recreate_gpg_public_key base64 error: %s", err, exc_info=True)
        log.error(
            "recreate_gpg_public_key set correct PG_DUMP_GPG_PUBLIC_KEY_BASE64, exiting"
        )
        exit(1)
    with open(settings.PG_DUMP_GPG_PUBLIC_KEY_BASE64_PATH, "wb") as gpg_pub_file:
        gpg_pub_file.write(gpg_pub_cert)
    log.debug(
        "recreate_gpg_public_key saved gpg public key to %s:\n%s",
        settings.PG_DUMP_GPG_PUBLIC_KEY_BASE64_PATH,
        gpg_pub_cert.decode(),
    )
    log.info("recreate_gpg_public_key start gpg key import")
    run_subprocess(
        ["gpg", "--import", str(settings.PG_DUMP_GPG_PUBLIC_KEY_BASE64_PATH)],
    )
    log.info("recreate_gpg_public_key start gpg list keys")
    result = run_subprocess(
        ["gpg", "--list-keys"],
    )
    log.info("recreate_gpg_public_key gpg list keys result: %s", result)
    pub_line = False
    for output_line in result.split("\n"):
        if pub_line:
            gpg_key_recipient = output_line.strip()
            log.info(
                "recreate_gpg_public_key found gpg public key recipient %s",
                gpg_key_recipient,
            )
            settings.PRIV_PG_DUMP_GPG_PUBLIC_KEY_RECIPIENT = gpg_key_recipient
            break
        if output_line.startswith("pub"):
            pub_line = True  # next line will be recipient

    log.info("recreate_gpg_public_key successfully finished")


def get_postgres_version():
    log.info("get_postgres_version start postgres connection to get pg version")
    pg_version_regex = re.compile(r"PostgreSQL \d*\.\d* ")
    result = run_subprocess(
        [
            "psql",
            "-U",
            settings.PG_DUMP_DATABASE_USER,
            "-p",
            settings.PG_DUMP_DATABASE_PORT,
            "-h",
            settings.PG_DUMP_DATABASE_HOSTNAME,
            settings.PG_DUMP_DATABASE_DB,
            "-w",
            "--command",
            "SELECT version();",
        ],
    )
    version = None
    matches: list[str] = pg_version_regex.findall(result)

    for match in matches:
        version = match.strip().replace(" ", "_").lower()
        break
    if version is None:
        log.warning(
            "get_postgres_version error processing pg result, version is unknown: %s",
            result,
        )
        exit(1)
    log.info("get_postgres_version calculated database version: %s", version)
    return version
