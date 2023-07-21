import logging
import logging.config
import os
import re
from enum import StrEnum
from functools import cached_property
from pathlib import Path
from typing import Any, Self, TypeVar

from croniter import croniter
from pydantic import (
    BaseModel,
    SecretStr,
    computed_field,
    field_validator,
    model_validator,
)

BASE_DIR = Path(__file__).resolve().parent.parent.absolute()

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:  # pragma: no cover
    pass

CONST_ENV_NAME_REGEX = re.compile(r"^[A-Za-z_0-9]{1,}$")
CONST_ZIP_BIN_7ZZ_PATH: Path = BASE_DIR / "bin/7zz"
CONST_BACKUP_FOLDER_PATH: Path = BASE_DIR / "data"
CONST_GOOGLE_SERVICE_ACCOUNT_PATH: Path = BASE_DIR / "google_auth.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(CONST_GOOGLE_SERVICE_ACCOUNT_PATH)
CONST_GOOGLE_SERVICE_ACCOUNT_PATH.touch(mode=0o700, exist_ok=True)
CONST_BACKUP_FOLDER_PATH.mkdir(mode=0o744, parents=True, exist_ok=True)
RUNTIME_SINGLE: bool = False
LOG_FOLDER_PATH: Path = Path(os.environ.get("LOG_FOLDER_PATH", BASE_DIR / "logs"))
LOG_FOLDER_PATH.mkdir(mode=0o700, parents=True, exist_ok=True)
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")


def logging_config(log_level: str) -> None:
    conf = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "{asctime} [{levelname}] {name}: {message}",
                "style": "{",
            },
        },
        "handlers": {
            "stream": {
                "class": "logging.StreamHandler",
                "formatter": "verbose",
                "level": "DEBUG",
            },
            "error": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": LOG_FOLDER_PATH / "backuper_error.log",
                "formatter": "verbose",
                "maxBytes": 10**5,
                "backupCount": 1,
                "level": "ERROR",
            },
            "warning": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": LOG_FOLDER_PATH / "backuper_warning.log",
                "formatter": "verbose",
                "maxBytes": 10**5,
                "backupCount": 1,
                "level": "WARNING",
            },
            "info": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": LOG_FOLDER_PATH / "backuper_info.log",
                "formatter": "verbose",
                "maxBytes": 10**5,
                "backupCount": 1,
                "level": "INFO",
            },
            "debug": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": LOG_FOLDER_PATH / "backuper_debug.log",
                "formatter": "verbose",
                "maxBytes": 10**5,
                "backupCount": 1,
                "level": "DEBUG",
            },
        },
        "loggers": {
            "": {
                "level": log_level,
                "handlers": ["debug", "info", "warning", "error", "stream"],
                "propagate": False,
            },
        },
    }
    logging.config.dictConfig(conf)


logging_config(LOG_LEVEL)

log = logging.getLogger(__name__)

log.info("Start configuring backuper")


class BackupProviderEnum(StrEnum):
    LOCAL_FILES = "local"
    GOOGLE_CLOUD_STORAGE = "gcs"


class BackupTargetEnum(StrEnum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MARIADB = "mariadb"
    FILE = "singlefile"
    FOLDER = "directory"


BACKUP_PROVIDER = os.environ.get("BACKUP_PROVIDER", BackupProviderEnum.LOCAL_FILES)
ZIP_ARCHIVE_PASSWORD = os.environ.get("ZIP_ARCHIVE_PASSWORD", "")
SUBPROCESS_TIMEOUT_SECS: int = int(os.environ.get("SUBPROCESS_TIMEOUT_SECS", 60 * 60))
BACKUPER_SIGTERM_TIMEOUT_SECS: float = float(
    os.environ.get("BACKUPER_SIGTERM_TIMEOUT_SECS", 30)
)
ZIP_ARCHIVE_LEVEL: int = int(os.environ.get("ZIP_ARCHIVE_LEVEL", 3))
BACKUP_MAX_NUMBER: int = int(os.environ.get("BACKUP_MAX_NUMBER", 7))
GOOGLE_BUCKET_NAME: str = os.environ.get("GOOGLE_BUCKET_NAME", "")
GOOGLE_BUCKET_UPLOAD_PATH: str = os.environ.get("GOOGLE_BUCKET_UPLOAD_PATH", "")
GOOGLE_SERVICE_ACCOUNT_BASE64: str = os.environ.get("GOOGLE_SERVICE_ACCOUNT_BASE64", "")
DISCORD_SUCCESS_WEBHOOK_URL: str = os.environ.get("DISCORD_SUCCESS_WEBHOOK_URL", "")
DISCORD_FAIL_WEBHOOK_URL: str = os.environ.get("DISCORD_FAIL_WEBHOOK_URL", "")


class TargetModel(BaseModel):
    env_name: str
    cron_rule: str
    max_backups: int = BACKUP_MAX_NUMBER
    archive_level: int = ZIP_ARCHIVE_LEVEL

    @field_validator("cron_rule")
    def cron_rule_is_valid(cls, cron_rule: str) -> str:
        if not croniter.is_valid(cron_rule):
            raise ValueError(
                f"Error in cron_rule expression: `{cron_rule}` is not valid"
            )
        return cron_rule

    @field_validator("env_name")
    def env_name_is_valid(cls, env_name: str) -> str:
        if not CONST_ENV_NAME_REGEX.match(env_name):
            raise ValueError(
                f"Env variable does not match regex {CONST_ENV_NAME_REGEX}: `{env_name}`"
            )
        return env_name

    @computed_field()
    @cached_property
    def target_type(self) -> BackupTargetEnum:
        cls_name = self.__class__.__name__.lower()
        target_name = cls_name.removesuffix("targetmodel")
        return BackupTargetEnum(target_name)


class PostgreSQLTargetModel(TargetModel):
    user: str = "postgres"
    host: str = "localhost"
    port: int = 5432
    db: str = "postgres"
    password: SecretStr


class MySQLTargetModel(TargetModel):
    user: str = "root"
    host: str = "localhost"
    port: int = 3306
    db: str = "mysql"
    password: SecretStr


class MariaDBTargetModel(TargetModel):
    user: str = "root"
    host: str = "localhost"
    port: int = 3306
    db: str = "mariadb"
    password: SecretStr


class SingleFileTargetModel(TargetModel):
    abs_path: Path

    @model_validator(mode="after")  # type: ignore [arg-type]
    def abs_path_is_valid(self) -> Self:
        if not self.abs_path.is_file() or not self.abs_path.exists():
            raise ValueError(
                f"Path {self.abs_path} is not a file or does not exist\n "
                f"Error validating environment variable: {self.env_name}"
            )
        return self


class DirectoryTargetModel(TargetModel):
    abs_path: Path

    @model_validator(mode="after")  # type: ignore [arg-type]
    def abs_path_is_valid(self) -> Self:
        if not self.abs_path.is_dir() or not self.abs_path.exists():
            raise ValueError(
                f"Path {self.abs_path} is not a dir or does not exist\n "
                f"Error validating environment variable: {self.env_name}"
            )
        return self


_BM = TypeVar("_BM", bound=BaseModel)


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
    target_map: dict[BackupTargetEnum, type[TargetModel]] = {}
    for target_model in TargetModel.__subclasses__():
        name = BackupTargetEnum(
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


def runtime_configuration() -> None:
    allowed_logs_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
    if LOG_LEVEL not in allowed_logs_levels:
        raise RuntimeError(
            f"LOG_LEVEL must be one of {allowed_logs_levels}, currently: `{LOG_LEVEL}`"
        )
    allowed_providers = [
        BackupProviderEnum.LOCAL_FILES,
        BackupProviderEnum.GOOGLE_CLOUD_STORAGE,
    ]
    if BACKUP_PROVIDER not in allowed_providers:
        raise RuntimeError(
            f"BACKUP_PROVIDER must be one of {allowed_providers}, currently: `{BACKUP_PROVIDER}`"
        )
    if BACKUP_PROVIDER == BackupProviderEnum.GOOGLE_CLOUD_STORAGE:
        if not GOOGLE_BUCKET_NAME:
            raise RuntimeError(
                f"For provider: `{BACKUP_PROVIDER}` you must use environment variable `GOOGLE_BUCKET_NAME`"
            )
        elif not GOOGLE_SERVICE_ACCOUNT_BASE64:
            raise RuntimeError(
                f"For provider: `{BACKUP_PROVIDER}` you must use environment variable `GOOGLE_SERVICE_ACCOUNT_BASE64`"
            )
        elif not GOOGLE_BUCKET_UPLOAD_PATH:
            raise RuntimeError(
                f"For provider: `{BACKUP_PROVIDER}` you must use environment variable `GOOGLE_BUCKET_UPLOAD_PATH`"
            )
    if ZIP_ARCHIVE_PASSWORD and not CONST_ZIP_BIN_7ZZ_PATH.exists():
        raise RuntimeError(
            f"`{ZIP_ARCHIVE_PASSWORD}` is set but `{CONST_ZIP_BIN_7ZZ_PATH}` binary does not exists, did you forget to create it?"
        )


runtime_configuration()
