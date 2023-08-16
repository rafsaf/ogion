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


CONST_ENV_NAME_REGEX = re.compile(r"^[A-Za-z_0-9]{1,}$")
CONST_BIN_ZIP_PATH: Path = BASE_DIR / "bin/7zip"
CONST_BACKUP_FOLDER_PATH: Path = BASE_DIR / "data"
CONST_GOOGLE_SERVICE_ACCOUNT_PATH: Path = BASE_DIR / "google_auth.json"
CONST_BACKUP_FOLDER_PATH.mkdir(mode=0o744, parents=True, exist_ok=True)
LOG_FOLDER_PATH: Path = Path(os.environ.get("LOG_FOLDER_PATH", BASE_DIR / "logs"))
LOG_FOLDER_PATH.mkdir(mode=0o700, parents=True, exist_ok=True)
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
BACKUP_PROVIDER = os.environ.get("BACKUP_PROVIDER", "")
ZIP_ARCHIVE_PASSWORD = os.environ.get("ZIP_ARCHIVE_PASSWORD", "")
ZIP_SKIP_INTEGRITY_CHECK = os.environ.get("ZIP_SKIP_INTEGRITY_CHECK", "false")
SUBPROCESS_TIMEOUT_SECS: int = int(os.environ.get("SUBPROCESS_TIMEOUT_SECS", 60 * 60))
SIGTERM_TIMEOUT_SECS: float = float(os.environ.get("SIGTERM_TIMEOUT_SECS", 30))
ZIP_ARCHIVE_LEVEL: int = int(os.environ.get("ZIP_ARCHIVE_LEVEL", 3))
BACKUP_MAX_NUMBER: int = int(os.environ.get("BACKUP_MAX_NUMBER", 7))
DISCORD_SUCCESS_WEBHOOK_URL: str = os.environ.get("DISCORD_SUCCESS_WEBHOOK_URL", "")
DISCORD_FAIL_WEBHOOK_URL: str = os.environ.get("DISCORD_FAIL_WEBHOOK_URL", "")
DISCORD_NOTIFICATION_MAX_MSG_LEN: int = int(
    os.environ.get("DISCORD_NOTIFICATION_MAX_MSG_LEN", 1500)
)


def logging_config(log_level: str) -> None:
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
                "filename": LOG_FOLDER_PATH / "backuper_error.log",
                "formatter": "verbose",
                "maxBytes": 5 * 10**6,
                "backupCount": 1,
                "level": "ERROR",
            },
            "warning": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": LOG_FOLDER_PATH / "backuper_warning.log",
                "formatter": "verbose",
                "maxBytes": 5 * 10**6,
                "backupCount": 1,
                "level": "WARNING",
            },
            "info": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": LOG_FOLDER_PATH / "backuper_info.log",
                "formatter": "verbose",
                "maxBytes": 5 * 10**6,
                "backupCount": 1,
                "level": "INFO",
            },
            "debug": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": LOG_FOLDER_PATH / "backuper_debug.log",
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


logging_config(LOG_LEVEL)
