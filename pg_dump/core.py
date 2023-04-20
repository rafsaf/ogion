import logging
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


def get_new_backup_path(name: str):
    random_string = secrets.token_urlsafe(3)
    new_file = "{}_{}_{}".format(
        datetime.utcnow().strftime("%Y%m%d_%H%M"),
        name,
        random_string,
    )
    return config.CONST_BACKUP_FOLDER_PATH / new_file


def run_create_zip_archive(backup_file: str):
    out_file = f"{backup_file}.zip"
    shell_args = (
        f"{config.CONST_ZIP_BIN_7ZZ_PATH} a -p{config.ZIP_ARCHIVE_PASSWORD} -mx=5 "
        f"{out_file} {backup_file}"
    )
    log.debug("run_create_zip_archive start in subprocess: %s", backup_file)
    run_subprocess(shell_args)
    log.debug("run_create_zip_archive finished, output: %s", out_file)
    return out_file
