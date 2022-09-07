import logging.config
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.absolute()


class Settings(BaseSettings):
    PD_DATABASE_HOSTNAME: str = "localhost"
    PD_DATABASE_USER: str = "postgres"
    PD_DATABASE_PASSWORD: str = "postgres"
    PD_DATABASE_PORT: str = "5432"
    PD_DATABASE_DB: str = "postgres"

    PD_BACKUP_POLICY_CRON_EXPRESSION: str = "0 5 * * *"
    PD_GPG_PUBLIC_KEY_BASE64: str = ""
    PD_UPLOAD_GOOGLE_SERVICE_ACCOUNT_BASE64: str = ""
    PD_UPLOAD_GOOGLE_BUCKET_NAME = ""
    PD_UPLOAD_GOOGLE_BUCKET_DESTINATION_PATH = ""
    PD_UPLOAD_PROVIDER: Literal["", "google"] = ""
    PD_NUMBER_PD_THREADS: int = 1
    PD_POSTGRES_TIMEOUT_AFTER_SECS: int = 60 * 60
    PD_COOLING_PERIOD_SECS: int = 60 * 5
    PD_COOLING_PERIOD_RETRIES: int = 2
    PD_LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "DEBUG"
    PD_MAX_NUMBER_BACKUPS_LOCAL = 7

    PD_BACKUP_FOLDER_PATH: Path = BASE_DIR / "data/backup"
    PD_LOG_FOLDER_PATH: Path = BASE_DIR / "logs"
    PD_PGPASS_FILE_PATH: Path = BASE_DIR / ".pgpass"
    PD_GPG_PUBLIC_KEY_BASE64_PATH: Path = BASE_DIR / "gpg_public.key.pub"
    PD_UPLOAD_GOOGLE_SERVICE_ACCOUNT_BASE64_PATH: Path = BASE_DIR / "google_auth.json"
    PD_PICKLE_PD_QUEUE_NAME: Path = BASE_DIR / "data/pg_queue.pickle"

    PRIV_PD_GPG_PUBLIC_KEY_RECIPIENT: str = ""
    PRIV_PD_DB_VERSION: str = ""

    class Config:  # type: ignore
        env_file = BASE_DIR / ".env"
        env_file_encoding = "utf-8"


settings = Settings()

os.environ["PGPASSFILE"] = str(settings.PD_PGPASS_FILE_PATH)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(
    settings.PD_UPLOAD_GOOGLE_SERVICE_ACCOUNT_BASE64_PATH
)
os.makedirs(settings.PD_BACKUP_FOLDER_PATH, exist_ok=True)
os.makedirs(settings.PD_LOG_FOLDER_PATH, exist_ok=True)


LOGGING = {
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
            "class": "logging.FileHandler",
            "filename": settings.PD_LOG_FOLDER_PATH / "pg_dump_error.log",
            "formatter": "verbose",
            "level": "ERROR",
        },
        "warning": {
            "class": "logging.FileHandler",
            "filename": settings.PD_LOG_FOLDER_PATH / "pg_dump_warning.log",
            "formatter": "verbose",
            "level": "WARNING",
        },
        "info": {
            "class": "logging.FileHandler",
            "filename": settings.PD_LOG_FOLDER_PATH / "pg_dump_info.log",
            "formatter": "verbose",
            "level": "INFO",
        },
        "debug": {
            "class": "logging.FileHandler",
            "filename": settings.PD_LOG_FOLDER_PATH / "pg_dump_debug.log",
            "formatter": "verbose",
            "level": "DEBUG",
        },
    },
    "loggers": {
        "": {
            "level": settings.PD_LOG_LEVEL,
            "handlers": ["debug", "info", "warning", "error", "stream"],
            "propagate": False,
        },
    },
}

logging.config.dictConfig(LOGGING)
