import logging
import re
import secrets
import shlex
import subprocess
from datetime import datetime
from pathlib import Path

from backuper import config

log = logging.getLogger(__name__)

SAFE_LETTER_PATTERN = r"[^A-Za-z0-9_]*"


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


def get_new_backup_path(env_name: str, name: str, sql: bool = False) -> Path:
    base_dir_path = config.CONST_BACKUP_FOLDER_PATH / env_name
    base_dir_path.mkdir(mode=0o700, exist_ok=True, parents=True)
    random_string = secrets.token_urlsafe(3)
    new_file = "{}_{}_{}_{}".format(
        env_name,
        datetime.utcnow().strftime("%Y%m%d_%H%M"),
        name,
        random_string,
    )
    if sql:
        new_file += ".sql"
    return base_dir_path / new_file


def run_create_zip_archive(backup_file: Path) -> Path:
    out_file = Path(f"{backup_file}.zip")
    log.debug("run_create_zip_archive start creating in subprocess: %s", backup_file)
    zip_escaped_password = shlex.quote(config.ZIP_ARCHIVE_PASSWORD)
    shell_args_create = (
        f"{config.CONST_ZIP_BIN_7ZZ_PATH} a -p{zip_escaped_password} "
        f"-mx={config.ZIP_ARCHIVE_LEVEL} {out_file} {backup_file}"
    )
    run_subprocess(shell_args_create)
    log.debug("run_create_zip_archive finished, output: %s", out_file)

    log.debug("run_create_zip_archive start integriy test in subprocess: %s", out_file)
    shell_args_integriy = (
        f"{config.CONST_ZIP_BIN_7ZZ_PATH} t -p{zip_escaped_password} {out_file}"
    )
    integrity_check_result = run_subprocess(shell_args_integriy)
    if "Everything is Ok" not in integrity_check_result:  # pragma: no cover
        raise AssertionError("zip arichive integrity fatal error")
    log.debug("run_create_zip_archive finish integriy test in subprocess: %s", out_file)
    return out_file


def safe_text_version(text: str) -> str:
    return re.sub(SAFE_LETTER_PATTERN, "", text)
