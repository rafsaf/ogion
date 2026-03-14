# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import getpass
import logging
import os
import re
import secrets
import shlex
import subprocess
import tempfile
import typing
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any

import tenacity
from pydantic import BaseModel

from ogion import config
from ogion.models import backup_target_models, models_mapping, upload_provider_models

log = logging.getLogger(__name__)

SAFE_LETTER_PATTERN = re.compile(r"[^A-Za-z0-9_]*")
DATETIME_BACKUP_FILE_PATTERN = re.compile(r"_[0-9]{8}_[0-9]{4}_")
MODEL_SPLIT_EQUATION_PATTERN = re.compile(r"( (\w|\-)*\=|^(\w|\-)*\=)")


class CoreSubprocessError(Exception):
    pass


def is_network_error(exception: BaseException) -> bool:
    """Check if exception is a network-related error that should be retried."""
    if not isinstance(exception, CoreSubprocessError):
        return False

    error_msg = str(exception).lower()
    network_error_patterns = [
        "temporary failure in name resolution",
        "can't connect to server",
        "connection refused",
        "network is unreachable",
        "host is unreachable",
        "timeout",
    ]

    return any(pattern in error_msg for pattern in network_error_patterns)


def retry_before_sleep(retry_state: tenacity.RetryCallState) -> None:
    log.warning(
        "Network error detected, retrying in %s seconds (attempt %s): %s",
        retry_state.next_action.sleep if retry_state.next_action else "unknown",
        retry_state.attempt_number,
        retry_state.outcome.exception() if retry_state.outcome else "No outcome",
    )


def retry_on_network_errors(attempts: int = 3) -> typing.Callable:  # type: ignore
    return tenacity.retry(
        retry=tenacity.retry_if_exception(is_network_error),
        stop=tenacity.stop_after_attempt(attempts),
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=16),
        before_sleep=retry_before_sleep,
        reraise=True,
    )


def run_subprocess(
    shell_args: list[str],
    *,
    stdin_path: Path | None = None,
) -> str:
    display_args = shlex.join(str(arg) for arg in shell_args)

    log.debug("run_subprocess running: '%s'", display_args)
    try:
        with (
            open(stdin_path, encoding="utf-8")
            if stdin_path is not None
            else nullcontext(None)
        ) as stdin_file:
            p = subprocess.run(
                shell_args,
                capture_output=True,
                text=True,
                stdin=stdin_file,
                timeout=config.options.SUBPROCESS_TIMEOUT_SECS,
                check=True,
            )
    except subprocess.CalledProcessError as process_error:
        log.error("run_subprocess failed with status %s", process_error.returncode)
        log.error("run_subprocess stdout: %s", process_error.stdout)
        log.error("run_subprocess stderr: %s", process_error.stderr)
        raise CoreSubprocessError(process_error.stderr or process_error.stdout)

    log.debug("run_subprocess finished with status %s", p.returncode)
    log.debug("run_subprocess stdout: %s", p.stdout)
    log.debug("run_subprocess stderr: %s", p.stderr)
    return p.stdout


def remove_path(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def get_new_backup_path(env_name: str, name: str) -> Path:
    base_dir_path = config.CONST_DATA_FOLDER_PATH / env_name
    base_dir_path.mkdir(mode=0o700, exist_ok=True, parents=True)
    new_file = (
        f"{env_name}_"
        f"{datetime.now(UTC).strftime('%Y%m%d_%H%M')}_"
        f"{name}_"
        f"{secrets.token_urlsafe(6)}"
    )
    return base_dir_path / new_file


def size(path: Path) -> str:
    file_size = round(path.stat().st_size / 1024 / 1024, 2)
    return f"{file_size} MB"


def get_safe_download_path(path: str) -> Path:
    raw_parts = path.lstrip("/").split("/")
    if not raw_parts or raw_parts == [""]:
        raise ValueError("backup path cannot be empty")
    if any(part in {"", ".", ".."} for part in raw_parts):
        raise ValueError(f"unsafe backup path: {path}")
    relative_path = PurePosixPath(*raw_parts)
    return config.CONST_DOWNLOADS_FOLDER_PATH.joinpath(*relative_path.parts)


def get_safe_debug_download_paths(path: str) -> tuple[Path, Path]:
    source = Path(path).resolve(strict=False)
    debug_root = config.CONST_DEBUG_FOLDER_PATH.resolve(strict=False)
    try:
        source.relative_to(debug_root)
    except ValueError as err:
        raise ValueError(f"unsafe debug backup path: {path}") from err
    return source, get_safe_download_path(path.removeprefix("/"))


def run_lzip_compression(backup_file: Path) -> Path:
    log.info("start lzip compression on %s: %s", backup_file, size(backup_file))
    out = Path(f"{backup_file}.lz")

    args = ["plzip", f"-{config.options.LZIP_LEVEL}"]
    if config.options.LZIP_THREADS:
        args.extend(["-n", str(config.options.LZIP_THREADS)])
    args.extend(["-o", str(out), str(backup_file)])

    run_subprocess(args)

    log.info("created compressed file %s: %s", out, size(out))

    return out


def run_lzip_decrypt(backup_file: Path) -> Path:
    if not backup_file.name.endswith(".lz"):
        return backup_file

    log.info(
        "start lzip decompression on %s: %s",
        backup_file,
        size(backup_file),
    )
    out = Path(str(backup_file).removesuffix(".lz"))

    args = ["plzip", "-d"]
    if config.options.LZIP_THREADS:
        args.extend(["-n", str(config.options.LZIP_THREADS)])
    args.extend(["-o", str(out), str(backup_file)])

    run_subprocess(args)

    log.info("created decompressed file %s: %s", out, size(out))

    return out


def run_decrypt_age_archive(backup_file: Path) -> Path:
    log.info("start age decrypt archive in subprocess: %s", backup_file)

    out = Path(str(backup_file).removesuffix(".age"))

    if config.options.DEBUG_AGE_SECRET_KEY:
        secret = config.options.DEBUG_AGE_SECRET_KEY
    else:  # pragma: no cover
        secret = getpass.getpass("please input age private key to decrypt:\n")

    with tempfile.NamedTemporaryFile(
        "w", dir=config.CONST_CONFIG_FOLDER_PATH
    ) as identity_file:
        identity_file.write(secret)
        identity_file.flush()

        run_subprocess(
            [
                "age",
                "-d",
                "-o",
                str(out),
                "-i",
                identity_file.name,
                str(backup_file),
            ]
        )
        log.info("finished age archive decrypt")

    return run_lzip_decrypt(out)


def run_create_age_archive(backup_file: Path) -> Path:
    if not backup_file.is_file():
        raise ValueError(f"backup_file must be file, not dir: {backup_file}")

    backup_file = run_lzip_compression(backup_file)

    log.info("start creating age archive in subprocess: %s", backup_file)
    out_file = Path(f"{backup_file}.age")

    recipients = config.options.age_recipients_file

    run_subprocess(
        [
            "age",
            "-R",
            str(recipients),
            "-o",
            str(out_file),
            str(backup_file),
        ]
    )
    log.info("finished age archive creating")

    remove_path(backup_file)
    log.info("removed unencrypted compressed file: %s", backup_file)

    return out_file


def safe_text_version(text: str) -> str:
    return re.sub(SAFE_LETTER_PATTERN, "", text)


def _validate_model[BM: BaseModel](
    env_name: str,
    env_value: str,
    target: type[BM],
) -> BM:
    target_name: str = target.__name__.lower()
    log.info("validating %s variable: `%s`", target_name, env_name)
    try:
        env_value_parts = env_value.strip()
        fields_matches = [
            match.group()
            for match in MODEL_SPLIT_EQUATION_PATTERN.finditer(env_value_parts)
        ]
        if not fields_matches:
            raise ValueError(f"could not parse any fields from: {env_value!r}")

        target_kwargs: dict[str, Any] = {"env_name": env_name}
        seen_fields: set[str] = set()

        while fields_matches:
            field_match = fields_matches.pop()
            rest, value = env_value_parts.split(field_match, maxsplit=1)
            env_value_parts = rest.rstrip()
            field_name = field_match.removesuffix("=").strip()
            if field_name in seen_fields:
                raise ValueError(f"duplicate field in config: {field_name!r}")
            seen_fields.add(field_name)
            target_kwargs[field_name] = value

        if env_value_parts:
            raise ValueError(f"unexpected unparsed text in config: {env_value_parts!r}")

        log.debug("calculated arguments keys: %s", sorted(target_kwargs))
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
            if (
                env_name_lowercase != target_model_name
                and not env_name_lowercase.startswith(f"{target_model_name}_")
            ):
                continue

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
