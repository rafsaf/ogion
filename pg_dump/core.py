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

from pg_dump.config import Database, settings
from pg_dump.jobs import DeleteFolderJob, PgDumpJob, UploaderJob

log = logging.getLogger(__name__)

PD_QUEUE: queue.Queue["PgDumpJob"] = queue.Queue()
UPLOADER_QUEUE: queue.Queue["UploaderJob"] = queue.Queue()
CLEANUP_QUEUE: queue.Queue["DeleteFolderJob"] = queue.Queue()

_MB_TO_BYTES = 1048576
_GB_TO_BYTES = 1073741824


class CoreSubprocessError(Exception):
    pass


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


def run_subprocess(shell_args: str) -> str:
    p = subprocess.Popen(
        shell_args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=True,
    )
    log.debug("run_subprocess running: '%s'", shell_args)
    output, err = p.communicate(timeout=settings.PD_POSTGRES_TIMEOUT_AFTER_SECS)

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
        log.debug("run_subprocess finished with status %s", p.returncode)
        log.debug("run_subprocess stdout: %s", output)
        log.debug("run_subprocess stderr: %s", err)
    return output


class PgDumpDatabase:
    def __init__(self, pg_dump: "PgDump", database: Database) -> None:
        self.pg_dump = pg_dump
        self.db = database
        self.database_version: str = self.init_postgres_connection()
        self.backup_folder: pathlib.Path = self.init_backup_folder()
        self.next_backup = self.get_next_backup_time()

    def init_postgres_connection(self):
        log.debug(
            "init_postgres_connection start postgres connection to %s get pg version",
            self.db,
        )
        pg_version_regex = re.compile(r"PostgreSQL \d*\.\d* ")
        try:
            result = run_subprocess(
                f"psql -U {self.db.user} "
                f"-p {self.db.port} "
                f"-h {self.db.host} "
                f"{self.db.db} "
                f"-w --command 'SELECT version();'",
            )
        except CoreSubprocessError as err:
            log.error(err, exc_info=True)
            log.error(
                "init_postgres_connection unable to connect to database %s, exiting",
                self.db,
            )
            exit(1)

        version = None
        matches: list[str] = pg_version_regex.findall(result)

        for match in matches:
            version = match.strip().split(" ")[1]
            break
        if version is None:
            log.error(
                "init_postgres_connection error processing pg result from %s, db version is unknown: %s",
                self.db,
                result,
            )
            exit(1)
        log.debug(
            "init_postgres_connection calculated database %s version: %s",
            self.db,
            version,
        )
        return version

    def init_backup_folder(self):
        log.debug("init_backup_folder start %s", self.db)
        backup_folder_path = settings.PD_BACKUP_FOLDER_PATH / self.db.friendly_name
        log.debug(
            "init_backup_folder creating folder backup_folder_path %s",
            backup_folder_path,
        )
        backup_folder_path.mkdir(mode=0o740, parents=True, exist_ok=True)
        log.debug("init_backup_folder created %s", backup_folder_path)
        return backup_folder_path

    def get_next_backup_time(self) -> datetime:
        now = datetime.utcnow()
        cron = croniter.croniter(
            self.db.cron_rule,
            start_time=now,
        )
        next_backup = cron.get_next(ret_type=datetime)
        log.info("%s: next backup time %s.", self.db, next_backup)
        return next_backup

    def get_new_backup_full_path(self):
        log.debug("get_new_backup_full_path calculating new backup path")
        random_string = secrets.token_urlsafe(3)
        new_file = "{}_{}_{}_{}".format(
            datetime.utcnow().strftime("%Y%m%d_%H%M"),
            self.db.db,
            self.database_version,
            random_string,
        )
        new_folder = self.backup_folder / new_file
        log.debug(
            "get_new_backup_full_path calculated new backup folder: %s", new_folder
        )
        return new_folder

    def run_pg_dump(self, out: pathlib.Path):
        log.debug("run_pg_dump start")
        shell_args = (
            f"pg_dump -v -O -Fd -j {multiprocessing.cpu_count()} "
            f"-U {self.db.user} "
            f"-p {self.db.port} "
            f"-h {self.db.host} "
            f"{self.db.db} "
            f"-f {out}"
        )
        log.info("run_pg_dump start pg_dump in subprocess: %s", shell_args)
        run_subprocess(shell_args)
        log.debug(
            "run_pg_dump finished pg_dump, output folder: %s, size: %s",
            out,
            _get_human_folder_size_msg(out),
        )
        log.debug(
            "run_pg_dump start encryption of folder: %s",
            out,
        )
        run_subprocess(
            "gpg --encrypt-files --trust-model always "
            f"-r {self.pg_dump.gpg_recipient} "
            f"{out / '*'}",
        )
        gpg_out = pathlib.Path(f"{out}.gpg")
        gpg_out.mkdir(mode=0o740, parents=True, exist_ok=True)
        run_subprocess(f"mv {out / '*.gpg'} {gpg_out}")
        log.info(
            "run_pg_dump finished encryption, out folder: %s, size: %s",
            gpg_out,
            _get_human_folder_size_msg(gpg_out),
        )
        CLEANUP_QUEUE.put(DeleteFolderJob(foldername=out))
        UPLOADER_QUEUE.put(UploaderJob(foldername=gpg_out, cleanup_queue=CLEANUP_QUEUE))


class PgDump:
    def __init__(self) -> None:
        self.gpg_recipient = self.init_gpg_public_key()
        self.init_pgpass_file()
        self.init_google_auth_account()

        self.pg_dump_databases: list[PgDumpDatabase] = []
        for database in settings.PD_DATABASES:
            self.pg_dump_databases.append(
                PgDumpDatabase(
                    pg_dump=self,
                    database=database,
                )
            )

        UploaderJob.test_gcs_upload()

    def init_pgpass_file(self):
        log.debug("init_pgpass_file start creating pgpass file")
        pgpass_text = ""
        for database in settings.PD_DATABASES:
            pgpass_text += "{}:{}:{}:{}:{}\n".format(
                database.host,
                database.port,
                database.user,
                database.db,
                database.password.get_secret_value(),
            )

        log.debug("init_pgpass_file saving pgpass file")
        with open(settings.PD_PGPASS_FILE_PATH, "w") as file:
            file.write(pgpass_text)

        log.debug("init_pgpass_file pgpass file saved")

    def init_gpg_public_key(self):
        log.debug("init_gpg_public_key starting")
        if not settings.PD_GPG_PUBLIC_KEY_BASE64:
            log.error("init_gpg_public_key no GPG public key provided, skipped")
            exit(1)
        try:
            gpg_pub_cert = base64.standard_b64decode(
                settings.PD_GPG_PUBLIC_KEY_BASE64
            ).decode()
        except (binascii.Error, UnicodeDecodeError) as err:
            log.error("init_gpg_public_key base64 error: %s", err, exc_info=True)
            log.error(
                "init_gpg_public_key set correct PD_GPG_PUBLIC_KEY_BASE64, exiting"
            )
            exit(1)
        with open(settings.PD_GPG_PUBLIC_KEY_PATH, "w") as gpg_pub_file:
            gpg_pub_file.write(gpg_pub_cert)
        log.debug(
            "init_gpg_public_key saved gpg public key to %s:\n%s",
            settings.PD_GPG_PUBLIC_KEY_PATH,
            gpg_pub_cert,
        )
        log.debug("init_gpg_public_key start gpg key import")
        try:
            run_subprocess(
                f"gpg --import {settings.PD_GPG_PUBLIC_KEY_PATH}",
            )
        except CoreSubprocessError as err:
            log.error(
                "init_gpg_public_key invalid gpg key error: %s", err, exc_info=True
            )
            log.error(
                "init_gpg_public_key set correct PD_GPG_PUBLIC_KEY_BASE64, exiting"
            )
            exit(1)

        log.debug("init_gpg_public_key start gpg list keys")
        result = run_subprocess(
            "gpg --list-keys",
        )
        log.debug("init_gpg_public_key gpg list keys result: %s", result)

        gpg_recipient = result.split("\n")[3].strip()
        log.debug(
            "init_gpg_public_key found gpg public key recipient %s",
            gpg_recipient,
        )
        log.debug("recreate_gpg_public_key successfully finished")
        return gpg_recipient

    def init_google_auth_account(self):
        log.debug("init_google_auth_account starting")
        try:
            google_auth_service = base64.standard_b64decode(
                settings.PD_UPLOAD_GOOGLE_SERVICE_ACCOUNT_BASE64
            ).decode()
        except (binascii.Error, UnicodeDecodeError) as err:
            log.error("init_google_auth_account base64 error: %s", err, exc_info=True)
            log.error(
                "init_google_auth_account set correct PD_UPLOAD_GOOGLE_SERVICE_ACCOUNT_BASE64, exiting"
            )
            exit(1)
        log.debug(
            "init_google_auth_account saving google_auth_service to %s",
            settings.PD_UPLOAD_GOOGLE_SERVICE_ACCOUNT_PATH,
        )
        with open(
            settings.PD_UPLOAD_GOOGLE_SERVICE_ACCOUNT_PATH, "w"
        ) as google_auth_file:
            google_auth_file.write(google_auth_service)
        log.debug("init_google_auth_account successfully finished")
