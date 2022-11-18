import logging.config
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.absolute()

POSTGRES_USER = os.environ.get("PD_POSTGRES_USER", "postgres")
POSTGRES_HOST = os.environ.get("PD_POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.environ.get("PD_POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ.get("PD_POSTGRES_DB", "postgres")
POSTGRES_PASSWORD = os.environ.get("PD_POSTGRES_PASSWORD", "postgres")

CRON_RULE = os.environ.get("PD_CRON_RULE", "0 5 * * *")

LOG_LEVEL = os.environ.get("PD_LOG_LEVEL", "INFO")
assert LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR"]

SUBPROCESS_TIMEOUT_SECS: int = int(
    os.environ.get("PD_SUBPROCESS_TIMEOUT_SECS", 60 * 60)
)
BACKUP_COOLING_SECS: int = int(os.environ.get("PD_BACKUP_COOLING_SECS", 60))
BACKUP_COOLING_RETRIES: int = int(os.environ.get("PD_BACKUP_COOLING_RETRIES", 1))
BACKUP_MAX_NUMBER: int = int(os.environ.get("PD_BACKUP_NUMBER", 5))
BACKUP_FOLDER_PATH: Path = BASE_DIR / "data"
PGPASS_FILE_PATH: Path = BASE_DIR / ".pgpass"
GOOGLE_SERVICE_ACCOUNT_PATH: Path = BASE_DIR / "google_auth.json"
GOOGLE_BUCKET_NAME: str | None = os.environ.get("PD_GOOGLE_BUCKET_NAME")
GOOGLE_BUCKET_UPLOAD_PATH: str | None = os.environ.get("PD_GOOGLE_BUCKET_UPLOAD_PATH")
GOOGLE_SERVICE_ACCOUNT_BASE64: str | None = os.environ.get(
    "PD_GOOGLE_SERVICE_ACCOUNT_BASE64"
)
GOOGLE_SERVICE_ACCOUNT_PATH: Path = BASE_DIR / "google_auth.json"


GOOGLE_SERVICE_ACCOUNT_PATH.touch(mode=0o700, exist_ok=True)
PGPASS_FILE_PATH.touch(mode=0o700, exist_ok=True)
BACKUP_FOLDER_PATH.mkdir(mode=0o700, parents=True, exist_ok=True)
os.environ["PGPASSFILE"] = str(PGPASS_FILE_PATH)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(GOOGLE_SERVICE_ACCOUNT_PATH)

LOGGING = {
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

logging.config.dictConfig(LOGGING)
