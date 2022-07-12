import logging.config
import os
import pathlib

from pydantic import BaseSettings

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.absolute()

os.environ["PGDUMP_DATABASE_HOSTNAME"] = "localhost"
os.environ["PGDUMP_DATABASE_USER"] = "postgres"
os.environ["PGDUMP_DATABASE_PASSWORD"] = "postgres"
os.environ["PGDUMP_DATABASE_PORT"] = "15432"
os.environ["PGDUMP_DATABASE_DB"] = "postgres"


class Settings(BaseSettings):
    PGDUMP_DATABASE_HOSTNAME: str
    PGDUMP_DATABASE_USER: str
    PGDUMP_DATABASE_PASSWORD: str
    PGDUMP_DATABASE_PORT: str
    PGDUMP_DATABASE_DB: str

    PGDUMP_BACKUP_POLICY_CRON_EXPRESSION: str = "30 4 * * *"
    PGDUMP_BACKUP_POLICY_REMOVE_AFTER_DAYS: int = 14

    POSTGRESQL_VERSION: str = "Unknown"


os.makedirs(BASE_DIR / "logs", exist_ok=True)
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
            "filename": BASE_DIR / "logs/pg_dump_error.log",
            "formatter": "verbose",
            "level": "ERROR",
        },
        "warning": {
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs/pg_dump_warning.log",
            "formatter": "verbose",
            "level": "WARNING",
        },
        "info": {
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs/pg_dump_info.log",
            "formatter": "verbose",
            "level": "INFO",
        },
    },
    "loggers": {
        "": {
            "level": "INFO",
            "handlers": ["error", "info", "warning", "stream"],
            "propagate": False,
        },
    },
}

logging.config.dictConfig(LOGGING)
settings = Settings()  # type: ignore
