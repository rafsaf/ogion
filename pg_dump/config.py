import logging.config
import os
import pathlib
from typing import Literal

from pydantic import BaseSettings

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.absolute()


class Settings(BaseSettings):
    PG_DUMP_DATABASE_HOSTNAME: str = "localhost"
    PG_DUMP_DATABASE_USER: str = "postgres"
    PG_DUMP_DATABASE_PASSWORD: str = "postgres"
    PG_DUMP_DATABASE_PORT: str = "5432"
    PG_DUMP_DATABASE_DB: str = "postgres"

    PG_DUMP_BACKUP_POLICY_CRON_EXPRESSION: str = "0 5 * * *"
    PG_DUMP_GPG_PUBLIC_KEY_BASE64: str = ""
    PG_DUMP_NUMBER_PG_DUMP_THREADS: int = 1
    PG_DUMP_POSTGRES_TIMEOUT_AFTER_SECS: int = 60 * 60
    PG_DUMP_COOLING_PERIOD_SECS: int = 60 * 5
    PG_DUMP_COOLING_PERIOD_RETRIES: int = 2

    PG_DUMP_BACKUP_FOLDER_PATH: pathlib.Path = BASE_DIR / "data/backup"
    PG_DUMP_LOG_FOLDER_PATH: pathlib.Path = BASE_DIR / "logs"
    PG_DUMP_PGPASS_FILE_PATH: pathlib.Path = BASE_DIR / ".pgpass"
    PG_DUMP_GPG_PUBLIC_KEY_BASE64_PATH: pathlib.Path = BASE_DIR / "gpg_public.key.pub"
    PG_DUMP_PICKLE_PG_DUMP_QUEUE_NAME: pathlib.Path = BASE_DIR / "data/pg_queue.pickle"
    PG_DUMP_LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "DEBUG"

    PRIV_PG_DUMP_GPG_PUBLIC_KEY_RECIPIENT: str = ""

    class Config:
        env_file = BASE_DIR / ".env"
        env_file_encoding = "utf-8"


settings = Settings()  # type: ignore

os.environ["PGPASSFILE"] = str(settings.PG_DUMP_PGPASS_FILE_PATH)
os.makedirs(settings.PG_DUMP_BACKUP_FOLDER_PATH, exist_ok=True)
os.makedirs(settings.PG_DUMP_LOG_FOLDER_PATH, exist_ok=True)

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
            "filename": settings.PG_DUMP_LOG_FOLDER_PATH / "pg_dump_error.log",
            "formatter": "verbose",
            "level": "ERROR",
        },
        "warning": {
            "class": "logging.FileHandler",
            "filename": settings.PG_DUMP_LOG_FOLDER_PATH / "pg_dump_warning.log",
            "formatter": "verbose",
            "level": "WARNING",
        },
        "info": {
            "class": "logging.FileHandler",
            "filename": settings.PG_DUMP_LOG_FOLDER_PATH / "pg_dump_info.log",
            "formatter": "verbose",
            "level": "INFO",
        },
        "debug": {
            "class": "logging.FileHandler",
            "filename": settings.PG_DUMP_LOG_FOLDER_PATH / "pg_dump_debug.log",
            "formatter": "verbose",
            "level": "DEBUG",
        },
    },
    "loggers": {
        "": {
            "level": settings.PG_DUMP_LOG_LEVEL,
            "handlers": ["debug", "info", "warning", "error", "stream"],
            "propagate": False,
        },
    },
}

logging.config.dictConfig(LOGGING)
