import logging.config
import os
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, BaseSettings, ConstrainedStr, SecretStr

BASE_DIR = Path(__file__).resolve().parent.parent.absolute()
FRIENDLY_NAME_REGEX = re.compile(r"^[\w\.-]{1,}$")


class FirendlyName(ConstrainedStr):
    regex = FRIENDLY_NAME_REGEX
    max_length = 128


class Database(BaseModel):
    host: str
    user: str
    password: SecretStr
    port: str | int
    db: str
    cron_rule: str
    friendly_name: FirendlyName


class Settings(BaseSettings):
    PD_DATABASES: list[Database]
    PD_GPG_PUBLIC_KEY_BASE64: str

    PD_UPLOAD_PROVIDER: Literal["google"] = "google"
    PD_UPLOAD_GOOGLE_SERVICE_ACCOUNT_BASE64: str = ""
    PD_UPLOAD_GOOGLE_BUCKET_NAME = ""
    PD_UPLOAD_GOOGLE_BUCKET_DESTINATION_PATH = ""

    # Advanced settings
    PD_LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    PD_POSTGRES_TIMEOUT_AFTER_SECS: int = 60 * 60
    PD_COOLING_PERIOD_SECS: int = 60 * 5
    PD_COOLING_PERIOD_RETRIES: int = 2
    PD_NUMBER_PD_THREADS: int = 2
    PD_BACKUP_FOLDER_PATH: Path = BASE_DIR / "data"
    PD_LOG_FOLDER_PATH: Path = BASE_DIR / "logs"
    PD_PGPASS_FILE_PATH: Path = BASE_DIR / ".pgpass"
    PD_GPG_PUBLIC_KEY_PATH: Path = BASE_DIR / "gpg_public.key.pub"
    PD_UPLOAD_GOOGLE_SERVICE_ACCOUNT_PATH: Path = BASE_DIR / "google_auth.json"

    class Config:
        env_file = BASE_DIR / ".env"
        env_file_encoding = "utf-8"


settings = Settings()  # type: ignore


settings.PD_UPLOAD_GOOGLE_SERVICE_ACCOUNT_PATH.touch(mode=0o640, exist_ok=True)
settings.PD_GPG_PUBLIC_KEY_PATH.touch(mode=0o640, exist_ok=True)
settings.PD_PGPASS_FILE_PATH.touch(mode=0o640, exist_ok=True)
settings.PD_BACKUP_FOLDER_PATH.mkdir(mode=0o740, parents=True, exist_ok=True)
settings.PD_LOG_FOLDER_PATH.mkdir(mode=0o644, parents=True, exist_ok=True)
os.environ["PGPASSFILE"] = str(settings.PD_PGPASS_FILE_PATH)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(
    settings.PD_UPLOAD_GOOGLE_SERVICE_ACCOUNT_PATH
)


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
