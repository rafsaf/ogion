import logging
import logging.config
import os
import re
from enum import StrEnum
from pathlib import Path
from typing import Any, TypeVar

from croniter import croniter
from pydantic import BaseModel, SecretStr, validator

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


class BackupTarget(BaseModel):
    env_name: str
    type: BackupTargetEnum
    cron_rule: str
    max_backups: int = BACKUP_MAX_NUMBER
    archive_level: int = ZIP_ARCHIVE_LEVEL

    @validator("cron_rule")
    def cron_rule_is_valid(cls, cron_rule: str) -> str:
        if not croniter.is_valid(cron_rule):
            raise ValueError(
                f"Error in cron_rule expression: `{cron_rule}` is not valid"
            )
        return cron_rule

    @validator("env_name")
    def env_name_is_valid(cls, env_name: str) -> str:
        if not CONST_ENV_NAME_REGEX.match(env_name):
            raise ValueError(
                f"Env variable does not match regex {CONST_ENV_NAME_REGEX}: `{env_name}`"
            )
        return env_name


class PostgreSQLBackupTarget(BackupTarget):
    user: str = "postgres"
    host: str = "localhost"
    port: int = 5432
    db: str = "postgres"
    password: SecretStr
    type = BackupTargetEnum.POSTGRESQL


class MySQLBackupTarget(BackupTarget):
    user: str = "root"
    host: str = "localhost"
    port: int = 3306
    db: str = "mysql"
    password: SecretStr
    type = BackupTargetEnum.MYSQL


class MariaDBBackupTarget(BackupTarget):
    user: str = "root"
    host: str = "localhost"
    port: int = 3306
    db: str = "mariadb"
    password: SecretStr
    type = BackupTargetEnum.MARIADB


class FileBackupTarget(BackupTarget):
    abs_path: Path
    type = BackupTargetEnum.FILE

    @validator("abs_path")
    def abs_path_is_valid(cls, abs_path: Path, values: dict[str, Any]) -> Path:
        if not abs_path.is_file() or not abs_path.exists():
            raise ValueError(
                f"Path {abs_path} is not a file or does not exist\n "
                f"Error validating environment variable: {values['env_name']}"
            )
        return abs_path


class FolderBackupTarget(BackupTarget):
    abs_path: Path
    type = BackupTargetEnum.FOLDER

    @validator("abs_path")
    def abs_path_is_valid(cls, abs_path: Path, values: dict[str, Any]) -> Path:
        if not abs_path.is_dir() or not abs_path.exists():
            raise ValueError(
                f"Path {abs_path} is not a dir or does not exist\n "
                f"Error validating environment variable: {values['env_name']}"
            )
        return abs_path


_BT = TypeVar("_BT", bound=BackupTarget)


def _validate_backup_target(env_name: str, env_value: str, target: type[_BT]) -> _BT:
    target_type = target.__name__.lower()
    log.info("validating %s variable: `%s`", target_type, env_name)
    log.debug("%s=%s", target_type, env_value)
    try:
        env_value_parts = env_value.strip()
        target_kwargs: dict[str, Any] = {}
        for field_name in target.__fields__.keys():
            if env_value_parts.startswith(f"{field_name}="):
                f = f"{field_name}="
            else:
                f = f" {field_name}="
            if f in env_value_parts:
                _, val = env_value_parts.split(f, maxsplit=1)
                for other_field in target.__fields__.keys():
                    val = val.split(f" {other_field}=")[0]
                target_kwargs[field_name] = val
        log.debug("calculated arguments: %s", target_kwargs)
        res = target(env_name=env_name, **target_kwargs)  # mypy: ignore
    except Exception:
        log.critical("error validating environment variable: `%s`", env_name)
        raise
    log.info("%s variable ok: `%s`", target_type, env_name)
    return res


_targets_lst = list[
    PostgreSQLBackupTarget
    | MySQLBackupTarget
    | FileBackupTarget
    | FolderBackupTarget
    | MariaDBBackupTarget
]


def create_backup_targets() -> _targets_lst:
    targets: _targets_lst = []
    for env_name, env_value in os.environ.items():
        env_name = env_name.lower()
        if env_name.startswith(BackupTargetEnum.POSTGRESQL):
            targets.append(
                _validate_backup_target(env_name, env_value, PostgreSQLBackupTarget)
            )
        elif env_name.startswith(BackupTargetEnum.MYSQL):
            targets.append(
                _validate_backup_target(env_name, env_value, MySQLBackupTarget)
            )
        elif env_name.startswith(BackupTargetEnum.FILE):
            targets.append(
                _validate_backup_target(env_name, env_value, FileBackupTarget)
            )
        elif env_name.startswith(BackupTargetEnum.FOLDER):
            targets.append(
                _validate_backup_target(env_name, env_value, FolderBackupTarget)
            )
        elif env_name.startswith(BackupTargetEnum.MARIADB):
            targets.append(
                _validate_backup_target(env_name, env_value, MariaDBBackupTarget)
            )

    return targets


BACKUP_TARGETS = create_backup_targets()


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
        log.error(GOOGLE_BUCKET_UPLOAD_PATH)
    if ZIP_ARCHIVE_PASSWORD and not CONST_ZIP_BIN_7ZZ_PATH.exists():
        raise RuntimeError(
            f"`{ZIP_ARCHIVE_PASSWORD}` is set but `{CONST_ZIP_BIN_7ZZ_PATH}` binary does not exists, did you forget to create it?"
        )


runtime_configuration()
