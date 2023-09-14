import logging
import logging.config
import socket
from enum import StrEnum
from functools import cached_property
from pathlib import Path
from typing import Literal

from pydantic import Field, HttpUrl, SecretStr, computed_field
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
    AZURE = "azure"


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
    INSTANCE_NAME: str = ""
    ZIP_SKIP_INTEGRITY_CHECK: bool = False
    CPU_ARCH: Literal["amd64", "arm64"] = Field(
        default="amd64", alias_priority=2, alias="BACKUPER_CPU_ARCHITECTURE"
    )
    SUBPROCESS_TIMEOUT_SECS: float = Field(ge=5, le=3600 * 24, default=3600)
    SIGTERM_TIMEOUT_SECS: float = Field(ge=0, le=3600 * 24, default=30)
    ZIP_ARCHIVE_LEVEL: int = Field(ge=1, le=9, default=3)
    BACKUP_MAX_NUMBER: int = Field(ge=1, le=998, default=7)
    BACKUP_MIN_RETENTION_DAYS: int = Field(ge=0, le=36600, default=3)
    DISCORD_WEBHOOK_URL: HttpUrl | None = None
    DISCORD_NOTIFICATION_MAX_MSG_LEN: int = Field(ge=150, le=10000, default=1500)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_FROM_ADDR: str = ""
    SMTP_PASSWORD: SecretStr = SecretStr("")
    SMTP_TO_ADDRS: str = ""

    @computed_field  # type: ignore[misc]
    @cached_property
    def seven_zip_bin_path(self) -> Path:
        return CONST_BASE_DIR / f"backuper/bin/7zip/{self.CPU_ARCH}/7zzs"

    @computed_field  # type: ignore[misc]
    @cached_property
    def backuper_instance(self) -> str:
        if self.INSTANCE_NAME:
            return self.INSTANCE_NAME
        return socket.gethostname()

    @computed_field  # type: ignore[misc]
    @cached_property
    def smtp_addresses(self) -> list[str]:
        return self.SMTP_TO_ADDRS.split(",")


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
