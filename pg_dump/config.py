import logging.config
import os
import pathlib
from typing import Literal

from pydantic import BaseSettings

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.absolute()


class Settings(BaseSettings):
    PGDUMP_DATABASE_HOSTNAME: str
    PGDUMP_DATABASE_USER: str
    PGDUMP_DATABASE_PASSWORD: str
    PGDUMP_DATABASE_PORT: str
    PGDUMP_DATABASE_DB: str

    PGDUMP_BACKUP_POLICY_CRON_EXPRESSION: str = "0 5 * * *"
    PGDUMP_POSTGRES_TIMEOUT_AFTER_SECS: int = 60 * 2
    PGDUMP_COOLING_PERIOD_AFTER_TIMEOUT: int = 60 * 5
    PGDUMP_BACKUP_FOLDER_PATH: pathlib.Path = BASE_DIR / "backup"
    PGDUMP_LOGS_FOLDER_PATH: pathlib.Path = BASE_DIR / "logs"
    PGDUMP_PGPASS_FILE_PATH: pathlib.Path = BASE_DIR / ".pgpass"
    PGDUMP_LOGS_MIN_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "DEBUG"

    POSTGRESQL_VERSION: str = "Unknown"

    class Config:
        env_file = BASE_DIR / ".env"
        env_file_encoding = "utf-8"


settings = Settings()  # type: ignore

os.makedirs(settings.PGDUMP_BACKUP_FOLDER_PATH, exist_ok=True)
os.makedirs(settings.PGDUMP_LOGS_FOLDER_PATH, exist_ok=True)

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
            "level": "INFO",
        },
        "error": {
            "class": "logging.FileHandler",
            "filename": settings.PGDUMP_LOGS_FOLDER_PATH / "pg_dump_error.log",
            "formatter": "verbose",
            "level": "ERROR",
        },
        "warning": {
            "class": "logging.FileHandler",
            "filename": settings.PGDUMP_LOGS_FOLDER_PATH / "pg_dump_warning.log",
            "formatter": "verbose",
            "level": "WARNING",
        },
        "info": {
            "class": "logging.FileHandler",
            "filename": settings.PGDUMP_LOGS_FOLDER_PATH / "pg_dump_info.log",
            "formatter": "verbose",
            "level": "INFO",
        },
        "debug": {
            "class": "logging.FileHandler",
            "filename": settings.PGDUMP_LOGS_FOLDER_PATH / "pg_dump_debug.log",
            "formatter": "verbose",
            "level": "DEBUG",
        },
    },
    "loggers": {
        "": {
            "level": settings.PGDUMP_LOGS_MIN_LEVEL,
            "handlers": ["error", "info", "debug", "warning", "stream"],
            "propagate": False,
        },
    },
}

logging.config.dictConfig(LOGGING)
