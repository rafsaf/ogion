import os
import secrets
from pathlib import Path

import pytest
import responses
from pydantic import SecretStr
from pytest import MonkeyPatch

from backuper import config
from backuper.config import (
    BackupTargetEnum,
    FileBackupTarget,
    FolderBackupTarget,
    MariaDBBackupTarget,
    MySQLBackupTarget,
    PostgreSQLBackupTarget,
)

DOCKER_TESTS: bool = os.environ.get("DOCKER_TESTS", None) is not None
CONST_TOKEN_URLSAFE = "mock"
FILE_1 = FileBackupTarget(
    env_name="singlefile_1",
    cron_rule="* * * * *",
    type=BackupTargetEnum.FILE,
    abs_path=Path(__file__).absolute().parent / "const/testfile.txt",
)
FOLDER_1 = FolderBackupTarget(
    env_name="directory_1",
    cron_rule="* * * * *",
    type=BackupTargetEnum.FOLDER,
    abs_path=Path(__file__).absolute().parent / "const/testfolder",
)
POSTGRES_15 = PostgreSQLBackupTarget(
    env_name="postgresql_db_15",
    type=BackupTargetEnum.POSTGRESQL,
    cron_rule="* * * * *",
    host="postgres_15" if DOCKER_TESTS else "localhost",
    port=5432 if DOCKER_TESTS else 10015,
    password=SecretStr('password-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""'),
    db='database-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""',
    user="user",
)
POSTGRES_14 = PostgreSQLBackupTarget(
    env_name="postgresql_db_14",
    type=BackupTargetEnum.POSTGRESQL,
    cron_rule="* * * * *",
    host="postgres_14" if DOCKER_TESTS else "localhost",
    port=5432 if DOCKER_TESTS else 10014,
    password=SecretStr('password-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""'),
    db='database-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""',
    user="user",
)
POSTGRES_13 = PostgreSQLBackupTarget(
    env_name="postgresql_db_13",
    type=BackupTargetEnum.POSTGRESQL,
    cron_rule="* * * * *",
    host="postgres_13" if DOCKER_TESTS else "localhost",
    port=5432 if DOCKER_TESTS else 10013,
    password=SecretStr('password-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""'),
    db='database-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""',
    user="user",
)
POSTGRES_12 = PostgreSQLBackupTarget(
    env_name="postgresql_db_12",
    type=BackupTargetEnum.POSTGRESQL,
    cron_rule="* * * * *",
    host="postgres_12" if DOCKER_TESTS else "localhost",
    port=5432 if DOCKER_TESTS else 10012,
    password=SecretStr('password-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""'),
    db='database-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""',
    user="user",
)
POSTGRES_11 = PostgreSQLBackupTarget(
    env_name="postgresql_db_11",
    type=BackupTargetEnum.POSTGRESQL,
    cron_rule="* * * * *",
    host="postgres_11" if DOCKER_TESTS else "localhost",
    port=5432 if DOCKER_TESTS else 10011,
    password=SecretStr('password-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""'),
    db='database-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""',
    user="user",
)
MYSQL_57 = MySQLBackupTarget(
    env_name="mysql_db_57",
    type=BackupTargetEnum.MYSQL,
    cron_rule="* * * * *",
    host="mysql_57" if DOCKER_TESTS else "localhost",
    port=3306 if DOCKER_TESTS else 10057,
    password=SecretStr('password-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""'),
    db='database-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""',
    user='user-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""',
)
MYSQL_80 = MySQLBackupTarget(
    env_name="mysql_db_80",
    type=BackupTargetEnum.MYSQL,
    cron_rule="* * * * *",
    host="mysql_80" if DOCKER_TESTS else "localhost",
    port=3306 if DOCKER_TESTS else 10080,
    password=SecretStr('password-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""'),
    db='database-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""',
    user='user-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""',
)
MARIADB_1011 = MariaDBBackupTarget(
    env_name="mariadb_1011",
    type=BackupTargetEnum.MARIADB,
    cron_rule="* * * * *",
    host="mariadb_1011" if DOCKER_TESTS else "localhost",
    port=3306 if DOCKER_TESTS else 11011,
    password=SecretStr('password-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""'),
    db='database-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""',
    user='user-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""',
)
MARIADB_1006 = MariaDBBackupTarget(
    env_name="mariadb_1006",
    type=BackupTargetEnum.MARIADB,
    cron_rule="* * * * *",
    host="mariadb_1006" if DOCKER_TESTS else "localhost",
    port=3306 if DOCKER_TESTS else 11006,
    password=SecretStr('password-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""'),
    db='database-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""',
    user='user-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""',
)
MARIADB_1005 = MariaDBBackupTarget(
    env_name="mariadb_1005",
    type=BackupTargetEnum.MARIADB,
    cron_rule="* * * * *",
    host="mariadb_1005" if DOCKER_TESTS else "localhost",
    port=3306 if DOCKER_TESTS else 11005,
    password=SecretStr('password-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""'),
    db='database-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""',
    user='user-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""',
)
MARIADB_1004 = MariaDBBackupTarget(
    env_name="mariadb_1004",
    type=BackupTargetEnum.MARIADB,
    cron_rule="* * * * *",
    host="mariadb_1004" if DOCKER_TESTS else "localhost",
    port=3306 if DOCKER_TESTS else 11004,
    password=SecretStr('password-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""'),
    db='database-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""',
    user='user-_-12!@#$%^&*()/;><.,]}{[\\]}`~\'"\'"\'""',
)

DB_VERSION_BY_ENV_VAR: dict[str, str] = {
    "postgresql_db_15": "15.1",
    "postgresql_db_14": "14.6",
    "postgresql_db_13": "13.8",
    "postgresql_db_12": "12.12",
    "postgresql_db_11": "11.16",
    "mysql_db_80": "8.0.33",
    "mysql_db_57": "5.7.42",
    "mariadb_1011": "10.11.2",
    "mariadb_1006": "10.6.12",
    "mariadb_1005": "10.5.19",
    "mariadb_1004": "10.4.28",
}
ALL_POSTGRES_DBS_TARGETS: list[PostgreSQLBackupTarget] = [
    POSTGRES_11,
    POSTGRES_12,
    POSTGRES_13,
    POSTGRES_14,
    POSTGRES_15,
]
ALL_MYSQL_DBS_TARGETS: list[MySQLBackupTarget] = [
    MYSQL_57,
    MYSQL_80,
]
ALL_MARIADB_DBS_TARGETS: list[MariaDBBackupTarget] = [
    MARIADB_1011,
    MARIADB_1006,
    MARIADB_1005,
    MARIADB_1004,
]


@pytest.fixture(autouse=True)
def fixed_config_setup(tmp_path: Path, monkeypatch: MonkeyPatch):
    monkeypatch.setattr(config, "SUBPROCESS_TIMEOUT_SECS", 1)
    monkeypatch.setattr(config, "LOG_LEVEL", "DEBUG")
    monkeypatch.setattr(config, "BACKUP_COOLING_SECS", 1)
    monkeypatch.setattr(config, "BACKUP_COOLING_RETRIES", 0)
    monkeypatch.setattr(config, "BACKUP_MAX_NUMBER", 1)
    monkeypatch.setattr(
        config,
        "ZIP_ARCHIVE_PASSWORD",
        'very_unpleasant:password-_-12!@#$%^&*()/;><.,]}{[\\`~\'"\'"\'""',
    )
    monkeypatch.setattr(config, "GOOGLE_BUCKET_UPLOAD_PATH", "test")
    LOG_FOLDER_PATH = tmp_path / "pytest_logs"
    LOG_FOLDER_PATH.mkdir(mode=0o700, parents=True, exist_ok=True)
    monkeypatch.setattr(config, "LOG_FOLDER_PATH", LOG_FOLDER_PATH)
    CONST_BACKUP_FOLDER_PATH = tmp_path / "pytest_data"
    monkeypatch.setattr(config, "CONST_BACKUP_FOLDER_PATH", CONST_BACKUP_FOLDER_PATH)
    CONST_BACKUP_FOLDER_PATH.mkdir(mode=0o700, parents=True, exist_ok=True)
    google_serv_acc_path = tmp_path / "pytest_google_auth"
    monkeypatch.setattr(
        config, "CONST_GOOGLE_SERVICE_ACCOUNT_PATH", google_serv_acc_path
    )
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(google_serv_acc_path))
    config.runtime_configuration()
    config.logging_config("DEBUG")


@pytest.fixture(autouse=True)
def fixed_secrets_token_urlsafe(monkeypatch: MonkeyPatch):
    def mock_token_urlsafe(nbytes: int):
        return CONST_TOKEN_URLSAFE

    monkeypatch.setattr(secrets, "token_urlsafe", mock_token_urlsafe)


@pytest.fixture(autouse=True)
def responses_activate_mock_to_prevent_accidential_requests():
    r_mock = responses.RequestsMock()
    r_mock.start()
    yield
    r_mock.stop()
