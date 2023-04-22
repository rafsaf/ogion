import os
import secrets
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from google.cloud import storage
from pytest import MonkeyPatch

from pg_dump import config
from pg_dump.config import BackupTargetEnum, PostgreSQLBackupTarget

DOCKER_TESTS: bool = os.environ.get("DOCKER_TESTS", None) is not None
CONST_TOKEN_URLSAFE = "mock"
POSTGRES_15 = PostgreSQLBackupTarget(
    env_name="postgresql_db_15",
    type=BackupTargetEnum.POSTGRESQL,
    cron_rule="* * * * *",
    host="postgres_15" if DOCKER_TESTS else "localhost",
    password="postgres",
    port=5432 if DOCKER_TESTS else 10015,
)
POSTGRES_14 = PostgreSQLBackupTarget(
    env_name="postgresql_db_14",
    type=BackupTargetEnum.POSTGRESQL,
    cron_rule="* * * * *",
    host="postgres_14" if DOCKER_TESTS else "localhost",
    password="postgres",
    port=5432 if DOCKER_TESTS else 10014,
)
POSTGRES_13 = PostgreSQLBackupTarget(
    env_name="postgresql_db_13",
    type=BackupTargetEnum.POSTGRESQL,
    cron_rule="* * * * *",
    host="postgres_13" if DOCKER_TESTS else "localhost",
    password="postgres",
    port=5432 if DOCKER_TESTS else 10013,
)
POSTGRES_12 = PostgreSQLBackupTarget(
    env_name="postgresql_db_12",
    type=BackupTargetEnum.POSTGRESQL,
    cron_rule="* * * * *",
    host="postgres_12" if DOCKER_TESTS else "localhost",
    password="postgres",
    port=5432 if DOCKER_TESTS else 10012,
)
POSTGRES_11 = PostgreSQLBackupTarget(
    env_name="postgresql_db_11",
    type=BackupTargetEnum.POSTGRESQL,
    cron_rule="* * * * *",
    host="postgres_11" if DOCKER_TESTS else "localhost",
    password="postgres",
    port=5432 if DOCKER_TESTS else 10011,
)

POSTGRES_VERSION_BY_ENV: dict[str, str] = {
    "postgresql_db_15": "15.1",
    "postgresql_db_14": "14.6",
    "postgresql_db_13": "13.8",
    "postgresql_db_12": "12.12",
    "postgresql_db_11": "11.16",
}
ALL_POSTGRES_DBS_TARGETS: list[PostgreSQLBackupTarget] = [
    POSTGRES_11,
    POSTGRES_12,
    POSTGRES_13,
    POSTGRES_14,
    POSTGRES_15,
]


@pytest.fixture(autouse=True)
def fixed_config_setup(tmp_path: Path, monkeypatch: MonkeyPatch):
    monkeypatch.setattr(config, "SUBPROCESS_TIMEOUT_SECS", 1)
    monkeypatch.setattr(config, "LOG_LEVEL", "DEBUG")
    monkeypatch.setattr(config, "BACKUP_COOLING_SECS", 1)
    monkeypatch.setattr(config, "BACKUP_COOLING_RETRIES", 0)
    monkeypatch.setattr(config, "BACKUP_MAX_NUMBER", 1)
    monkeypatch.setattr(config, "ZIP_ARCHIVE_PASSWORD", "test")
    monkeypatch.setattr(config, "GOOGLE_BUCKET_UPLOAD_PATH", "test")
    CONST_BACKUP_FOLDER_PATH = tmp_path / "pytest_data"
    monkeypatch.setattr(config, "CONST_BACKUP_FOLDER_PATH", CONST_BACKUP_FOLDER_PATH)
    CONST_PGPASS_FILE_PATH = tmp_path / "pytest_pgpass"
    CONST_PGPASS_FILE_PATH.touch(0o600, exist_ok=True)
    monkeypatch.setattr(config, "CONST_PGPASS_FILE_PATH", CONST_PGPASS_FILE_PATH)
    google_serv_acc_path = tmp_path / "pytest_google_auth"
    monkeypatch.setattr(
        config, "CONST_GOOGLE_SERVICE_ACCOUNT_PATH", google_serv_acc_path
    )
    monkeypatch.setenv("PGPASSFILE", str(CONST_PGPASS_FILE_PATH))
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(google_serv_acc_path))
    config.runtime_configuration()
    config.logging_config("DEBUG")


@pytest.fixture(autouse=True)
def fixed_secrets_token_urlsafe(monkeypatch: MonkeyPatch):
    def mock_token_urlsafe(nbytes: int):
        return CONST_TOKEN_URLSAFE

    monkeypatch.setattr(secrets, "token_urlsafe", mock_token_urlsafe)


@pytest.fixture(autouse=True)
def mock_google_cloud_storage(monkeypatch: MonkeyPatch):
    class Blob:
        def __init__(self) -> None:
            self.name = "test_blob"

    class TestClient:
        def bucket(self, *args, **kwargs):
            return MagicMock()

        def list_blobs(self, *args, **kwargs):
            return [Blob()]

    monkeypatch.setattr(storage, "Client", TestClient)
