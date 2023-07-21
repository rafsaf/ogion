import logging
import logging.config
import os
import re
import secrets
import shlex
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from backuper import config
from backuper.models.target_models import TargetModel

log = logging.getLogger(__name__)

SAFE_LETTER_PATTERN = r"[^A-Za-z0-9_]*"
_BM = TypeVar("_BM", bound=BaseModel)


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


def _validate_model(env_name: str, env_value: str, target: type[_BM]) -> _BM:
    target_name: str = target.__name__.lower()
    log.info("validating %s variable: `%s`", target_name, env_name)
    log.debug("%s=%s", target_name, env_value)
    try:
        env_value_parts = env_value.strip()
        target_kwargs: dict[str, Any] = {"env_name": env_name}
        for field_name in target.model_fields.keys():
            if env_value_parts.startswith(f"{field_name}="):
                f = f"{field_name}="
            else:
                f = f" {field_name}="
            if f in env_value_parts:
                _, val = env_value_parts.split(f, maxsplit=1)
                for other_field in target.model_fields.keys():
                    val = val.split(f" {other_field}=")[0]
                target_kwargs[field_name] = val
        log.debug("calculated arguments: %s", target_kwargs)
        validated_target = target.model_validate(target_kwargs)
    except Exception:
        log.critical("error validating environment variable: `%s`", env_name)
        raise
    log.info("%s variable ok: `%s`", target_name, env_name)
    return validated_target


def create_target_models() -> list[TargetModel]:
    target_map: dict[config.BackupTargetEnum, type[TargetModel]] = {}
    for target_model in TargetModel.__subclasses__():
        name = config.BackupTargetEnum(
            target_model.__name__.lower().removesuffix("targetmodel")
        )
        target_map[name] = target_model

    targets: list[TargetModel] = []
    for env_name, env_value in os.environ.items():
        env_name = env_name.lower()
        log.debug("processing env variable %s", env_name)
        for target_model_name in target_map:
            if env_name.startswith(target_model_name):
                target_model_cls = target_map[target_model_name]
                targets.append(_validate_model(env_name, env_value, target_model_cls))
                break

    return targets
