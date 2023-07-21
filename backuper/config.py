import logging
import logging.config
import os
import re
from enum import StrEnum
from pathlib import Path

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

log.info("Finish logging configuring")


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
