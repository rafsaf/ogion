import json
import logging.config
import os
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent.absolute()
CONST_ZIP_BIN_7ZZ_PATH: Path = BASE_DIR / "bin/7zz"
CONST_BACKUP_FOLDER_PATH: Path = BASE_DIR / "data"
CONST_PGPASS_FILE_PATH: Path = BASE_DIR / ".pgpass"
CONST_GOOGLE_SERVICE_ACCOUNT_PATH: Path = BASE_DIR / "google_auth.json"
os.environ["PGPASSFILE"] = str(CONST_PGPASS_FILE_PATH)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(CONST_GOOGLE_SERVICE_ACCOUNT_PATH)
CONST_GOOGLE_SERVICE_ACCOUNT_PATH.touch(mode=0o700, exist_ok=True)
CONST_PGPASS_FILE_PATH.unlink(missing_ok=True)
CONST_PGPASS_FILE_PATH.touch(mode=0o700)
CONST_BACKUP_FOLDER_PATH.mkdir(mode=0o700, parents=True, exist_ok=True)

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:  # pragma: no cover
    pass


class Provider(StrEnum):
    LOCAL_FILES = "local"
    GOOGLE_CLOUD_STORAGE = "gcs"


CRON_RULE = os.environ.get("PD_CRON_RULE", "0 5 * * *")
BACKUP_PROVIDER = os.environ.get("PD_BACKUP_PROVIDER", Provider.LOCAL_FILES)
LOG_LEVEL = os.environ.get("PD_LOG_LEVEL", "INFO")
assert LOG_LEVEL in [
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
], f"invalid log level {LOG_LEVEL}"
ZIP_ARCHIVE_PASSWORD = os.environ.get("PD_ZIP_ARCHIVE_PASSWORD", "")
SUBPROCESS_TIMEOUT_SECS: int = int(
    os.environ.get("PD_SUBPROCESS_TIMEOUT_SECS", 60 * 60)
)
BACKUP_COOLING_SECS: int = int(os.environ.get("PD_BACKUP_COOLING_SECS", 60))
BACKUP_COOLING_RETRIES: int = int(os.environ.get("PD_BACKUP_COOLING_RETRIES", 1))
BACKUP_MAX_NUMBER: int = int(os.environ.get("PD_BACKUP_MAX_NUMBER", 7))
GOOGLE_BUCKET_NAME: str = os.environ.get("PD_GOOGLE_BUCKET_NAME", "")
GOOGLE_BUCKET_UPLOAD_PATH: str | None = os.environ.get(
    "PD_GOOGLE_BUCKET_UPLOAD_PATH", None
)
GOOGLE_SERVICE_ACCOUNT_BASE64: str = os.environ.get(
    "PD_GOOGLE_SERVICE_ACCOUNT_BASE64", ""
)


class PostgreSQLBackupTarget(BaseModel):
    user: str = "postgres"
    host: str = "localhost"
    port: int = 5432
    db: str = "postgres"
    password: str
    cron_rule: str = CRON_RULE


POSTGRESQL_DBS: list[PostgreSQLBackupTarget] = []
for env_name, val in os.environ.items():
    if env_name.startswith("POSTGRESQL"):
        db_data_from_env = json.loads(val)
        POSTGRESQL_DBS.append(PostgreSQLBackupTarget(**db_data_from_env))


def runtime_configuration():
    if BACKUP_PROVIDER == Provider.GOOGLE_CLOUD_STORAGE:
        if not ZIP_ARCHIVE_PASSWORD:
            raise RuntimeError(
                f"For provider: `{BACKUP_PROVIDER}` you must use environment variable `ZIP_ARCHIVE_PASSWORD`"
            )
        elif not GOOGLE_BUCKET_NAME:
            raise RuntimeError(
                f"For provider: `{BACKUP_PROVIDER}` you must use environment variable `GOOGLE_BUCKET_NAME`"
            )
        elif not GOOGLE_SERVICE_ACCOUNT_BASE64:
            raise RuntimeError(
                f"For provider: `{BACKUP_PROVIDER}` you must use environment variable `GOOGLE_SERVICE_ACCOUNT_BASE64`"
            )
    if ZIP_ARCHIVE_PASSWORD and not CONST_ZIP_BIN_7ZZ_PATH.exists():
        raise RuntimeError(
            f"`{ZIP_ARCHIVE_PASSWORD}` is set but `{CONST_ZIP_BIN_7ZZ_PATH}` binary does not exists, did you forget to create it?"
        )


runtime_configuration()


logging.config.dictConfig(
    {
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
        },
        "loggers": {
            "": {
                "level": LOG_LEVEL,
                "handlers": ["stream"],
                "propagate": False,
            },
        },
    }
)
