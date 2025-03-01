# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import logging
import logging.config
import os
import re
import secrets
import subprocess
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from ogion import config
from ogion.models import backup_target_models, models_mapping, upload_provider_models

log = logging.getLogger(__name__)

SAFE_LETTER_PATTERN = re.compile(r"[^A-Za-z0-9_]*")
DATETIME_BACKUP_FILE_PATTERN = re.compile(r"_[0-9]{8}_[0-9]{4}_")
MODEL_SPLIT_EQUATION_PATTERN = re.compile(r"( (\w|\-)*\=|^(\w|\-)*\=)")

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
        path.unlink()


def get_new_backup_path(env_name: str, name: str) -> Path:
    base_dir_path = config.CONST_BACKUP_FOLDER_PATH / env_name
    base_dir_path.mkdir(mode=0o700, exist_ok=True, parents=True)
    new_file = (
        f"{env_name}_"
        f"{datetime.now(UTC).strftime('%Y%m%d_%H%M')}_"
        f"{name}_"
        f"{secrets.token_urlsafe(6)}"
    )
    return base_dir_path / new_file


def run_decrypt_age_archive(backup_file: Path) -> Path:
    log.info("start age decrypt archive in subprocess: %s", backup_file)

    out = Path(str(backup_file).removesuffix(".age"))

    if config.options.DEBUG_AGE_SECRET_KEY:
        secret = config.options.DEBUG_AGE_SECRET_KEY
    else:  # pragma: no cover
        secret = input("please input age private key to decrypt\n")

    with tempfile.NamedTemporaryFile("w") as identity_file:
        identity_file.write(secret)
        identity_file.flush()

        shell_age_decrypt_archive = (
            f"age -d -o {out} -i {identity_file.name} {backup_file}"
        )
        run_subprocess(shell_age_decrypt_archive)
        log.info("finished age archive decrypt")

    return out


def run_create_age_archive(backup_file: Path) -> Path:
    if not backup_file.is_file():
        raise ValueError(f"backup_file must be file, not dir: {backup_file}")

    log.info("start creating age archive in subprocess: %s", backup_file)
    out_file = Path(f"{backup_file}.age")

    recipients = config.options.age_recipients_file

    shell_create_age_archive = f"age -R {recipients} -o {out_file} {backup_file}"
    run_subprocess(shell_create_age_archive)
    log.info("finished age archive creating")

    return out_file


def safe_text_version(text: str) -> str:
    return re.sub(SAFE_LETTER_PATTERN, "", text)


def _validate_model(
    env_name: str,
    env_value: str,
    target: type[_BM],
) -> _BM:
    target_name: str = target.__name__.lower()
    log.info("validating %s variable: `%s`", target_name, env_name)
    log.debug("%s=%s", target_name, env_value)
    try:
        env_value_parts = env_value.strip()
        fields_matches = [
            match.group()
            for match in MODEL_SPLIT_EQUATION_PATTERN.finditer(env_value_parts)
        ]
        target_kwargs: dict[str, Any] = {"env_name": env_name}

        while fields_matches:
            field_match = fields_matches.pop()
            rest, value = env_value_parts.split(field_match, maxsplit=1)
            env_value_parts = rest.rstrip()
            target_kwargs[field_match.removesuffix("=").strip()] = value

        log.debug("calculated arguments: %s", target_kwargs)
        validated_target = target.model_validate(target_kwargs)
    except Exception:
        log.critical("error validating environment variable: `%s`", env_name)
        raise
    log.info("%s variable ok: `%s`", target_name, env_name)
    return validated_target


def create_target_models() -> list[backup_target_models.TargetModel]:
    target_map = models_mapping.get_target_map()

    targets: list[backup_target_models.TargetModel] = []
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


def create_provider_model() -> upload_provider_models.ProviderModel:
    provider_map = models_mapping.get_provider_map()

    log.info("start validating BACKUP_PROVIDER environment variable")
    log.debug("BACKUP_PROVIDER: %s", config.options.BACKUP_PROVIDER)

    base_provider = _validate_model(
        "backup_provider",
        config.options.BACKUP_PROVIDER,
        upload_provider_models.ProviderModel,
    )
    target_model_cls = provider_map[base_provider.name]
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
