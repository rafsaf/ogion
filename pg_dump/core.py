import base64
import binascii
import logging
import multiprocessing
import os
import pathlib
import queue
import re
import secrets
import subprocess
from datetime import datetime

import croniter

from pg_dump.config import settings
from pg_dump.jobs import DeleteFolderJob, PgDumpJob, UploaderJob

log = logging.getLogger(__name__)

PG_DUMP_QUEUE: queue.Queue[PgDumpJob] = queue.Queue(maxsize=1)
UPLOADER_QUEUE: queue.Queue[UploaderJob] = queue.Queue()
CLEANUP_QUEUE: queue.Queue[DeleteFolderJob] = queue.Queue()

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


def get_new_backup_foldername():
    random_string = secrets.token_urlsafe(3)
    new_foldername = "{}_{}_{}_{}".format(
        datetime.utcnow().strftime("%Y%m%d_%H%M"),
        settings.PG_DUMP_DATABASE_DB,
        settings.PRIV_PG_DUMP_DB_VERSION,
        random_string,
    )
    log.debug(
        "get_new_backup_foldername calculated new backup folder: %s", new_foldername
    )
    return new_foldername


def _get_human_folder_size_msg(folder_path: pathlib.Path):
    def get_folder_size_bytes(folder: str):
        total_size = os.path.getsize(folder)
        for item in os.listdir(folder):
            itempath = os.path.join(folder, item)
            if os.path.isfile(itempath):
                total_size += os.path.getsize(itempath)
            elif os.path.isdir(itempath):
                total_size += get_folder_size_bytes(itempath)
        return total_size

    folder_size = get_folder_size_bytes(str(folder_path))
    log.debug("get_folder_size_bytes size of %s: %s", folder_path, folder_size)

    if folder_size < _MB_TO_BYTES:
        size_msg = f"{folder_size} bytes ({round(folder_size / _MB_TO_BYTES, 3)} mb)"
    elif folder_size < _GB_TO_BYTES:
        size_msg = f"{round(folder_size / _MB_TO_BYTES, 3)} mb"
    else:
        size_msg = f"{round(folder_size / _GB_TO_BYTES, 3)} gb"
    return size_msg


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

    log.info("recreate_pgpass_file perform chmod 600 on pgpass file")
    settings.PG_DUMP_PGPASS_FILE_PATH.touch(0o600)

    log.info("recreate_pgpass_file saving pgpass file")
    with open(settings.PG_DUMP_PGPASS_FILE_PATH, "w") as file:
        file.write(text)


def run_subprocess(shell_args: str) -> str:
    p = subprocess.Popen(
        shell_args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=True,
    )
    log.info("run_subprocess running: '%s'", shell_args)
    output, err = p.communicate(timeout=settings.PG_DUMP_POSTGRES_TIMEOUT_AFTER_SECS)

    if p.returncode != 0:
        log.error("run_subprocess failed with status %s", p.returncode)
        log.error("run_subprocess stdout: %s", output)
        log.error("run_subprocess stderr: %s", err)
        raise CoreSubprocessError(
            f"run_subprocess '{shell_args}'\n"
            f"subprocess {p.pid} "
            f"failed with code: {p.returncode}"
        )
    else:
        log.info("run_subprocess finished with status %s", p.returncode)
        log.info("run_subprocess stdout: %s", output)
        log.info("run_subprocess stderr: %s", err)
    return output


def gpg_encrypt_folder_for_upload_and_delete_it(encrypt_folder: pathlib.Path):
    log.info(
        "gpg_encrypt_folder_for_upload_and_delete_it start encryption of folder: %s",
        encrypt_folder,
    )
    run_subprocess(
        "gpg --encrypt-files --trust-model always "
        f"-r {settings.PRIV_PG_DUMP_GPG_PUBLIC_KEY_RECIPIENT} "
        f"{encrypt_folder / '*'}",
    )
    gpg_out = pathlib.Path(f"{encrypt_folder}.gpg")
    gpg_out.mkdir(exist_ok=True)
    run_subprocess(f"mv {encrypt_folder / '*.gpg'} {gpg_out}")
    log.info(
        "gpg_encrypt_folder_for_upload_and_delete_it finished encryption, out folder: %s, size: %s",
        gpg_out,
        _get_human_folder_size_msg(gpg_out),
    )
    CLEANUP_QUEUE.put(DeleteFolderJob(foldername=encrypt_folder))
    UPLOADER_QUEUE.put(UploaderJob(foldername=gpg_out))


def run_pg_dump(output_folder: str):
    log.info("run_pg_dump start pg_dump in subprocess")
    out = backup_folder_path(output_folder)
    run_subprocess(
        f"pg_dump -v -O -Fd -j {multiprocessing.cpu_count()} "
        f"-U {settings.PG_DUMP_DATABASE_USER} "
        f"-p {settings.PG_DUMP_DATABASE_PORT} "
        f"-h {settings.PG_DUMP_DATABASE_HOSTNAME} "
        f"{settings.PG_DUMP_DATABASE_DB} "
        f"-f {out}"
    )
    log.info(
        "run_pg_dump finished pg_dump, output folder: %s, size: %s",
        out,
        _get_human_folder_size_msg(out),
    )
    return out


def recreate_gpg_public_key():
    log.info("recreate_gpg_public_key starting")
    if not settings.PG_DUMP_GPG_PUBLIC_KEY_BASE64:
        log.info("recreate_gpg_public_key no GPG public key provided, skipped")
        return
    try:
        gpg_pub_cert = base64.standard_b64decode(
            settings.PG_DUMP_GPG_PUBLIC_KEY_BASE64
        ).decode()
    except (binascii.Error, UnicodeDecodeError) as err:
        log.error("recreate_gpg_public_key base64 error: %s", err, exc_info=True)
        log.error(
            "recreate_gpg_public_key set correct PG_DUMP_GPG_PUBLIC_KEY_BASE64, exiting"
        )
        exit(1)
    with open(settings.PG_DUMP_GPG_PUBLIC_KEY_BASE64_PATH, "w") as gpg_pub_file:
        gpg_pub_file.write(gpg_pub_cert)
    log.debug(
        "recreate_gpg_public_key saved gpg public key to %s:\n%s",
        settings.PG_DUMP_GPG_PUBLIC_KEY_BASE64_PATH,
        gpg_pub_cert,
    )
    log.info("recreate_gpg_public_key start gpg key import")
    try:
        run_subprocess(
            f"gpg --import {settings.PG_DUMP_GPG_PUBLIC_KEY_BASE64_PATH}",
        )
    except CoreSubprocessError as err:
        log.error(
            "recreate_gpg_public_key invalid gpg key error: %s", err, exc_info=True
        )
        log.error(
            "recreate_gpg_public_key set correct PG_DUMP_GPG_PUBLIC_KEY_BASE64, exiting"
        )
        exit(1)

    log.info("recreate_gpg_public_key start gpg list keys")
    result = run_subprocess(
        "gpg --list-keys",
    )
    log.info("recreate_gpg_public_key gpg list keys result: %s", result)

    gpg_key_recipient = result.split("\n")[3].strip()
    log.info(
        "recreate_gpg_public_key found gpg public key recipient %s",
        gpg_key_recipient,
    )
    settings.PRIV_PG_DUMP_GPG_PUBLIC_KEY_RECIPIENT = gpg_key_recipient
    log.info("recreate_gpg_public_key successfully finished")


def setup_google_auth_account():
    log.info("setup_google_auth_account starting")
    try:
        google_auth_service = base64.standard_b64decode(
            settings.PG_DUMP_UPLOAD_GOOGLE_SERVICE_ACCOUNT_BASE64
        ).decode()
    except (binascii.Error, UnicodeDecodeError) as err:
        log.error("setup_google_auth_account base64 error: %s", err, exc_info=True)
        log.error(
            "setup_google_auth_account set correct PG_DUMP_UPLOAD_GOOGLE_SERVICE_ACCOUNT_BASE64, exiting"
        )
        exit(1)
    with open(
        settings.PG_DUMP_UPLOAD_GOOGLE_SERVICE_ACCOUNT_BASE64_PATH, "w"
    ) as google_auth_file:
        google_auth_file.write(google_auth_service)
    log.info("setup_google_auth_account successfully finished")


def get_postgres_version():
    log.info("get_postgres_version start postgres connection to get pg version")
    pg_version_regex = re.compile(r"PostgreSQL \d*\.\d* ")
    try:
        result = run_subprocess(
            f"psql -U {settings.PG_DUMP_DATABASE_USER} "
            f"-p {settings.PG_DUMP_DATABASE_PORT} "
            f"-h {settings.PG_DUMP_DATABASE_HOSTNAME} "
            f"{settings.PG_DUMP_DATABASE_DB} "
            f"-w --command 'SELECT version();'",
        )
    except CoreSubprocessError as err:
        log.error(err, exc_info=True)
        log.error("check_postgres_connection unable to connect to database, exiting")
        exit(1)

    version = None
    matches: list[str] = pg_version_regex.findall(result)

    for match in matches:
        version = match.strip().split(" ")[1]
        break
    if version is None:
        log.error(
            "get_postgres_version error processing pg result, version is unknown: %s",
            result,
        )
        exit(1)
    settings.PRIV_PG_DUMP_DB_VERSION = version
    log.info("get_postgres_version calculated database version: %s", version)
