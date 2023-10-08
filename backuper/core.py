import logging
import logging.config
import os
import re
import secrets
import shlex
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from backuper import config
from backuper.models.backup_target_models import TargetModel
from backuper.models.upload_provider_models import ProviderModel

log = logging.getLogger(__name__)

SAFE_LETTER_PATTERN = re.compile(r"[^A-Za-z0-9_]*")
DATETIME_BACKUP_FILE_PATTERN = re.compile(r"_[0-9]{8}_[0-9]{4}_")

_BM = TypeVar("_BM", bound=BaseModel)


class CoreSubprocessError(Exception):
    pass


def run_subprocess(shell_args: str) -> str:
    log.debug("run_subprocess running: '%s'", shell_args)
    try:
        p = subprocess.run(
            shell_args,
            capture_output=True,
            text=True,
            shell=True,
            timeout=config.options.SUBPROCESS_TIMEOUT_SECS,
            check=True,
        )
    except subprocess.CalledProcessError as process_error:
        log.error("run_subprocess failed with status %s", process_error.returncode)
        log.error("run_subprocess stdout: %s", process_error.stdout)
        log.error("run_subprocess stderr: %s", process_error.stderr)
        raise CoreSubprocessError(process_error.stderr)

    log.debug("run_subprocess finished with status %s", p.returncode)
    log.debug("run_subprocess stdout: %s", p.stdout)
    log.debug("run_subprocess stderr: %s", p.stderr)
    return p.stdout


def remove_path(path: Path) -> None:
    if path.exists():
        if path.is_file() or path.is_symlink():
            path.unlink()
        else:
            shutil.rmtree(path=path)


def get_new_backup_path(env_name: str, name: str, sql: bool = False) -> Path:
    base_dir_path = config.CONST_BACKUP_FOLDER_PATH / env_name
    base_dir_path.mkdir(mode=0o700, exist_ok=True, parents=True)
    new_file = (
        f"{env_name}_"
        f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}_"
        f"{name}_"
        f"{secrets.token_urlsafe(3)}"
    )
    if sql:
        new_file += ".sql"
    return base_dir_path / new_file


def run_create_zip_archive(backup_file: Path) -> Path:
    out_file = Path(f"{backup_file}.zip")
    log.info("start creating zip archive in subprocess: %s", backup_file)
    zip_escaped_password = shlex.quote(
        config.options.ZIP_ARCHIVE_PASSWORD.get_secret_value()
    )
    shell_create_7zip_archive = (
        f"{config.options.seven_zip_bin_path} a -p{zip_escaped_password} "
        f"-mx={config.options.ZIP_ARCHIVE_LEVEL} {out_file} {backup_file}"
    )
    run_subprocess(shell_create_7zip_archive)
    log.info("finished zip archive creating")

    if config.options.ZIP_SKIP_INTEGRITY_CHECK:
        return out_file

    log.info(
        (
            "start zip archive integriy test on %s in subprocess, "
            "you can control it using ZIP_SKIP_INTEGRITY_CHECK"
        ),
        out_file,
    )
    shell_7zip_archive_integriy_check = (
        f"{config.options.seven_zip_bin_path} t -p{zip_escaped_password} {out_file}"
    )
    integrity_check_result = run_subprocess(shell_7zip_archive_integriy_check)
    if "Everything is Ok" not in integrity_check_result:  # pragma: no cover
        raise AssertionError(
            "zip arichive integrity test on %s: %s", out_file, integrity_check_result
        )
    log.info("finished zip archive integriy test")
    return out_file


def safe_text_version(text: str) -> str:
    return re.sub(SAFE_LETTER_PATTERN, "", text)


def _validate_model(
    env_name: str,
    env_value: str,
    target: type[_BM],
    value_whitespace_split: bool = False,
) -> _BM:
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
                if value_whitespace_split:
                    val = val.split()[0]
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
        env_name_lowercase = env_name.lower()
        log.debug("processing env variable %s", env_name_lowercase)
        for target_model_name in target_map:
            if env_name_lowercase.startswith(target_model_name):
                target_model_cls = target_map[target_model_name]
                targets.append(
                    _validate_model(env_name_lowercase, env_value, target_model_cls)
                )
                break

    return targets


def create_provider_model() -> ProviderModel:
    target_map: dict[config.UploadProviderEnum, type[ProviderModel]] = {}
    for target_model in ProviderModel.__subclasses__():
        name = config.UploadProviderEnum(
            target_model.__name__.lower().removesuffix("providermodel")
        )
        target_map[name] = target_model
    log.info("start validating BACKUP_PROVIDER environment variable")

    base_provider = _validate_model(
        "backup_provider",
        config.options.BACKUP_PROVIDER,
        ProviderModel,
        value_whitespace_split=True,
    )
    target_model_cls = target_map[base_provider.name]
    return _validate_model(
        "backup_provider", config.options.BACKUP_PROVIDER, target_model_cls
    )


def file_before_retention_period_ends(
    backup_name: str, min_retention_days: int
) -> bool:
    now = datetime.now()
    matches = DATETIME_BACKUP_FILE_PATTERN.finditer(backup_name)

    datetime_str = ""
    for match in matches:
        datetime_str = match.group(0)
        break
    if not datetime_str:  # pragma: no cover
        raise ValueError(
            f"unexpected backup file name, could not parse datetime: {backup_name}"
        )
    backup_datetime = datetime.strptime(datetime_str, "_%Y%m%d_%H%M_")
    delete_not_before = backup_datetime + timedelta(days=min_retention_days)

    if now < delete_not_before:
        return True
    return False
