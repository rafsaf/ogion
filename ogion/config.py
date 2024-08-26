# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import logging
import logging.config
import socket
from enum import StrEnum
from functools import cached_property
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, HttpUrl, SecretStr, computed_field, model_validator
from pydantic_settings import BaseSettings

_log_levels = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

CONST_BASE_DIR = Path(__file__).resolve().parent.parent.absolute()
CONST_BACKUP_FOLDER_PATH: Path = CONST_BASE_DIR / "data"
CONST_CONFIG_FOLDER_PATH: Path = CONST_BASE_DIR / "conf"
CONST_DOWNLOADS_FOLDER_PATH: Path = CONST_BACKUP_FOLDER_PATH / "downloads"
CONST_BACKUP_FOLDER_PATH.mkdir(mode=0o700, parents=True, exist_ok=True)
CONST_CONFIG_FOLDER_PATH.mkdir(mode=0o700, parents=True, exist_ok=True)
CONST_DOWNLOADS_FOLDER_PATH.mkdir(mode=0o700, exist_ok=True)

try:
    from dotenv import load_dotenv

    load_dotenv(CONST_BASE_DIR / ".env")
except ImportError:  # pragma: no cover
    pass


class UploadProviderEnum(StrEnum):
    LOCAL_FILES_DEBUG = "debug"
    GCS = "gcs"
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
    INSTANCE_NAME: str = socket.gethostname()
    ZIP_SKIP_INTEGRITY_CHECK: bool = False
    CPU_ARCH: Literal["amd64", "arm64"] = Field(
        default="amd64", alias_priority=2, alias="OGION_CPU_ARCHITECTURE"
    )
    SUBPROCESS_TIMEOUT_SECS: float = Field(ge=5, le=3600 * 24, default=3600)
    SIGTERM_TIMEOUT_SECS: float = Field(ge=0, le=3600 * 24, default=3600)
    ZIP_ARCHIVE_LEVEL: int = Field(ge=1, le=9, default=3)
    BACKUP_MAX_NUMBER: int = Field(ge=1, le=998, default=7)
    BACKUP_MIN_RETENTION_DAYS: int = Field(ge=0, le=36600, default=3)
    DISCORD_WEBHOOK_URL: HttpUrl | None = None
    DISCORD_MAX_MSG_LEN: int = Field(ge=150, le=10000, default=1500)
    SLACK_WEBHOOK_URL: HttpUrl | None = None
    SLACK_MAX_MSG_LEN: int = Field(ge=150, le=10000, default=1500)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_FROM_ADDR: str = ""
    SMTP_PASSWORD: SecretStr = SecretStr("")
    SMTP_TO_ADDRS: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @cached_property
    def seven_zip_bin_path(self) -> Path:
        return CONST_BASE_DIR / f"ogion/bin/7zip/{self.CPU_ARCH}/7zzs"

    @computed_field  # type: ignore[prop-decorator]
    @cached_property
    def smtp_addresses(self) -> list[str]:
        return self.SMTP_TO_ADDRS.split(",")

    @model_validator(mode="after")
    def check_smtp_setup(self) -> Self:
        smtp_settings = [self.SMTP_HOST, self.SMTP_FROM_ADDR, self.SMTP_TO_ADDRS]
        if any(smtp_settings) != all(smtp_settings):  # pragma: no cover
            raise ValueError(
                "parameters SMTP_HOST, SMTP_FROM_ADDR, SMTP_TO_ADDRS "
                "must be all either set or not."
            )
        return self


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
                "filename": options.LOG_FOLDER_PATH / "ogion_error.log",
                "formatter": "verbose",
                "maxBytes": 5 * 10**6,
                "backupCount": 1,
                "level": "ERROR",
            },
            "warning": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": options.LOG_FOLDER_PATH / "ogion_warning.log",
                "formatter": "verbose",
                "maxBytes": 5 * 10**6,
                "backupCount": 1,
                "level": "WARNING",
            },
            "info": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": options.LOG_FOLDER_PATH / "ogion_info.log",
                "formatter": "verbose",
                "maxBytes": 5 * 10**6,
                "backupCount": 1,
                "level": "INFO",
            },
            "debug": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": options.LOG_FOLDER_PATH / "ogion_debug.log",
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
