import logging
import logging.config
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings

_log_levels = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

CONST_BASE_DIR = Path(__file__).resolve().parent.parent.absolute()
CONST_BACKUP_FOLDER_PATH: Path = CONST_BASE_DIR / "data"
CONST_CONFIG_FOLDER_PATH: Path = CONST_BASE_DIR / "conf"
CONST_BACKUP_FOLDER_PATH.mkdir(mode=0o700, parents=True, exist_ok=True)
CONST_CONFIG_FOLDER_PATH.mkdir(mode=0o700, parents=True, exist_ok=True)

try:
    from dotenv import load_dotenv

    load_dotenv(CONST_BASE_DIR / ".env")
except ImportError:  # pragma: no cover
    pass


class UploadProviderEnum(StrEnum):
    LOCAL_FILES_DEBUG = "debug"
    GOOGLE_CLOUD_STORAGE = "gcs"
    AWS_S3 = "aws"


class BackupTargetEnum(StrEnum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MARIADB = "mariadb"
    FILE = "singlefile"
    FOLDER = "directory"


class Settings(BaseSettings):
    LOG_FOLDER_PATH: Path = CONST_BASE_DIR / "logs"
    LOG_LEVEL: _log_levels = "INFO"
    BACKUP_PROVIDER: str
    ZIP_ARCHIVE_PASSWORD: SecretStr
    ZIP_SKIP_INTEGRITY_CHECK: bool = False
    SUBPROCESS_TIMEOUT_SECS: float = Field(ge=5, le=3600 * 24, default=3600)
    SIGTERM_TIMEOUT_SECS: float = Field(ge=0, le=3600 * 24, default=30)
    ZIP_ARCHIVE_LEVEL: int = Field(ge=1, le=9, default=3)
    BACKUP_MAX_NUMBER: int = Field(ge=1, le=998, default=7)
    BACKUP_MIN_RETENTION_DAYS: int = Field(ge=0, le=36600, default=3)
    DISCORD_SUCCESS_WEBHOOK_URL: HttpUrl | None = None
    DISCORD_FAIL_WEBHOOK_URL: HttpUrl | None = None
    DISCORD_NOTIFICATION_MAX_MSG_LEN: int = Field(ge=150, le=10000, default=1500)


options = Settings()  # type: ignore


def logging_config(log_level: _log_levels) -> None:
    options.LOG_FOLDER_PATH.mkdir(0o700, parents=True, exist_ok=True)
    conf = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "{asctime} {threadName} [{levelname}] {name}: {message}",
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
                "filename": options.LOG_FOLDER_PATH / "backuper_error.log",
                "formatter": "verbose",
                "maxBytes": 5 * 10**6,
                "backupCount": 1,
                "level": "ERROR",
            },
            "warning": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": options.LOG_FOLDER_PATH / "backuper_warning.log",
                "formatter": "verbose",
                "maxBytes": 5 * 10**6,
                "backupCount": 1,
                "level": "WARNING",
            },
            "info": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": options.LOG_FOLDER_PATH / "backuper_info.log",
                "formatter": "verbose",
                "maxBytes": 5 * 10**6,
                "backupCount": 1,
                "level": "INFO",
            },
            "debug": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": options.LOG_FOLDER_PATH / "backuper_debug.log",
                "formatter": "verbose",
                "maxBytes": 5 * 10**7,
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


logging_config(options.LOG_LEVEL)
