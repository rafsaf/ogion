import os
import secrets
from collections.abc import Generator
from pathlib import Path

import pytest
import responses
from pydantic import SecretStr

from backuper import config
from backuper.models.backup_target_models import (
    DirectoryTargetModel,
    MariaDBTargetModel,
    MySQLTargetModel,
    PostgreSQLTargetModel,
    SingleFileTargetModel,
)

DOCKER_TESTS: bool = os.environ.get("DOCKER_TESTS", None) is not None
CONST_TOKEN_URLSAFE = "mock"
FILE_1 = SingleFileTargetModel(
    env_name="singlefile_1",
    cron_rule="* * * * *",
    abs_path=Path(__file__).absolute().parent / "const/testfile.txt",
)
FOLDER_1 = DirectoryTargetModel(
    env_name="directory_1",
    cron_rule="* * * * *",
    abs_path=Path(__file__).absolute().parent / "const/testfolder",
)
POSTGRES_16 = PostgreSQLTargetModel(
    env_name="postgresql_db_16",
    cron_rule="* * * * *",
    host="postgres_16" if DOCKER_TESTS else "localhost",
    port=5432 if DOCKER_TESTS else 10016,
    password=SecretStr("password-_-12!@#%^&*()/;><.,]}{["),
    db="database-_-12!@#%^&*()/;><.,]}{[",
    user="user-_-12!@#%^&*()/;><.,]}{[",
)
POSTGRES_15 = PostgreSQLTargetModel(
    env_name="postgresql_db_15",
    cron_rule="* * * * *",
    host="postgres_15" if DOCKER_TESTS else "localhost",
    port=5432 if DOCKER_TESTS else 10015,
    password=SecretStr("password-_-12!@#%^&*()/;><.,]}{["),
    db="database-_-12!@#%^&*()/;><.,]}{[",
    user="user-_-12!@#%^&*()/;><.,]}{[",
)
POSTGRES_14 = PostgreSQLTargetModel(
    env_name="postgresql_db_14",
    cron_rule="* * * * *",
    host="postgres_14" if DOCKER_TESTS else "localhost",
    port=5432 if DOCKER_TESTS else 10014,
    password=SecretStr("password-_-12!@#%^&*()/;><.,]}{["),
    db="database-_-12!@#%^&*()/;><.,]}{[",
    user="user-_-12!@#%^&*()/;><.,]}{[",
)
POSTGRES_13 = PostgreSQLTargetModel(
    env_name="postgresql_db_13",
    cron_rule="* * * * *",
    host="postgres_13" if DOCKER_TESTS else "localhost",
    port=5432 if DOCKER_TESTS else 10013,
    password=SecretStr("password-_-12!@#%^&*()/;><.,]}{["),
    db="database-_-12!@#%^&*()/;><.,]}{[",
    user="user-_-12!@#%^&*()/;><.,]}{[",
)
POSTGRES_12 = PostgreSQLTargetModel(
    env_name="postgresql_db_12",
    cron_rule="* * * * *",
    host="postgres_12" if DOCKER_TESTS else "localhost",
    port=5432 if DOCKER_TESTS else 10012,
    password=SecretStr("password-_-12!@#%^&*()/;><.,]}{["),
    db="database-_-12!@#%^&*()/;><.,]}{[",
    user="user-_-12!@#%^&*()/;><.,]}{[",
)
POSTGRES_11 = PostgreSQLTargetModel(
    env_name="postgresql_db_11",
    cron_rule="* * * * *",
    host="postgres_11" if DOCKER_TESTS else "localhost",
    port=5432 if DOCKER_TESTS else 10011,
    password=SecretStr("password-_-12!@#%^&*()/;><.,]}{["),
    db="database-_-12!@#%^&*()/;><.,]}{[",
    user="user-_-12!@#%^&*()/;><.,]}{[",
)
MYSQL_57 = MySQLTargetModel(
    env_name="mysql_db_57",
    cron_rule="* * * * *",
    host="mysql_57" if DOCKER_TESTS else "localhost",
    port=3306 if DOCKER_TESTS else 10057,
    password=SecretStr("password-_-12!@#%^&*()/;><.,]}{["),
    db="database-_-12!@#%^&*()/;><.,]}{[",
    user="user-_-12!@#%^&*()/;><.,]}{[",
)
MYSQL_80 = MySQLTargetModel(
    env_name="mysql_db_80",
    cron_rule="* * * * *",
    host="mysql_80" if DOCKER_TESTS else "localhost",
    port=3306 if DOCKER_TESTS else 10080,
    password=SecretStr("password-_-12!@#%^&*()/;><.,]}{["),
    db="database-_-12!@#%^&*()/;><.,]}{[",
    user="user-_-12!@#%^&*()/;><.,]}{[",
)
MYSQL_81 = MySQLTargetModel(
    env_name="mysql_db_81",
    cron_rule="* * * * *",
    host="mysql_81" if DOCKER_TESTS else "localhost",
    port=3306 if DOCKER_TESTS else 10081,
    password=SecretStr("password-_-12!@#%^&*()/;><.,]}{["),
    db="database-_-12!@#%^&*()/;><.,]}{[",
    user="user-_-12!@#%^&*()/;><.,]}{[",
)
MARIADB_1011 = MariaDBTargetModel(
    env_name="mariadb_1011",
    cron_rule="* * * * *",
    host="mariadb_1011" if DOCKER_TESTS else "localhost",
    port=3306 if DOCKER_TESTS else 11011,
    password=SecretStr("password-_-12!@#%^&*()/;><.,]}{["),
    db="database-_-12!@#%^&*()/;><.,]}{[",
    user="user-_-12!@#%^&*()/;><.,]}{[",
)
MARIADB_1006 = MariaDBTargetModel(
    env_name="mariadb_1006",
    cron_rule="* * * * *",
    host="mariadb_1006" if DOCKER_TESTS else "localhost",
    port=3306 if DOCKER_TESTS else 11006,
    password=SecretStr("password-_-12!@#%^&*()/;><.,]}{["),
    db="database-_-12!@#%^&*()/;><.,]}{[",
    user="user-_-12!@#%^&*()/;><.,]}{[",
)
MARIADB_1005 = MariaDBTargetModel(
    env_name="mariadb_1005",
    cron_rule="* * * * *",
    host="mariadb_1005" if DOCKER_TESTS else "localhost",
    port=3306 if DOCKER_TESTS else 11005,
    password=SecretStr("password-_-12!@#%^&*()/;><.,]}{["),
    db="database-_-12!@#%^&*()/;><.,]}{[",
    user="user-_-12!@#%^&*()/;><.,]}{[",
)
MARIADB_1004 = MariaDBTargetModel(
    env_name="mariadb_1004",
    cron_rule="* * * * *",
    host="mariadb_1004" if DOCKER_TESTS else "localhost",
    port=3306 if DOCKER_TESTS else 11004,
    password=SecretStr("password-_-12!@#%^&*()/;><.,]}{["),
    db="database-_-12!@#%^&*()/;><.,]}{[",
    user="user-_-12!@#%^&*()/;><.,]}{[",
)

DB_VERSION_BY_ENV_VAR: dict[str, str] = {
    "postgresql_db_16": "16.0",
    "postgresql_db_15": "15.4",
    "postgresql_db_14": "14.9",
    "postgresql_db_13": "13.12",
    "postgresql_db_12": "12.16",
    "postgresql_db_11": "11.21",
    "mysql_db_81": "8.1.0",
    "mysql_db_80": "8.0.34",
    "mysql_db_57": "5.7.42",
    "mariadb_1011": "10.11.2",
    "mariadb_1006": "10.6.12",
    "mariadb_1005": "10.5.19",
    "mariadb_1004": "10.4.28",
}
ALL_POSTGRES_DBS_TARGETS: list[PostgreSQLTargetModel] = [
    POSTGRES_11,
    POSTGRES_12,
    POSTGRES_13,
    POSTGRES_14,
    POSTGRES_15,
    POSTGRES_16,
]
ALL_MYSQL_DBS_TARGETS: list[MySQLTargetModel] = [
    MYSQL_57,
    MYSQL_80,
    MYSQL_81,
]
ALL_MARIADB_DBS_TARGETS: list[MariaDBTargetModel] = [
    MARIADB_1011,
    MARIADB_1006,
    MARIADB_1005,
    MARIADB_1004,
]


@pytest.fixture(autouse=True)
def fixed_const_config_setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    backup_folder_path = tmp_path / "pytest_data"
    monkeypatch.setattr(config, "CONST_BACKUP_FOLDER_PATH", backup_folder_path)
    backup_folder_path.mkdir(mode=0o700, parents=True, exist_ok=True)
    config_folder_path = tmp_path / "pytest_config"
    monkeypatch.setattr(config, "CONST_CONFIG_FOLDER_PATH", config_folder_path)
    config_folder_path.mkdir(mode=0o700, parents=True, exist_ok=True)
    options = config.Settings(
        LOG_LEVEL="DEBUG",
        BACKUP_PROVIDER="name=debug",
        ZIP_ARCHIVE_PASSWORD=SecretStr("pass"),
        INSTANCE_NAME="tests",
        ZIP_SKIP_INTEGRITY_CHECK=False,
        SUBPROCESS_TIMEOUT_SECS=5,
        SIGTERM_TIMEOUT_SECS=1,
        ZIP_ARCHIVE_LEVEL=1,
        BACKUP_MAX_NUMBER=2,
        BACKUP_MIN_RETENTION_DAYS=0,
        DISCORD_WEBHOOK_URL=None,
        DISCORD_MAX_MSG_LEN=1500,
        SLACK_WEBHOOK_URL=None,
        SLACK_MAX_MSG_LEN=1500,
        SMTP_HOST="",
        SMTP_PORT=587,
        SMTP_FROM_ADDR="",
        SMTP_PASSWORD=SecretStr(""),
        SMTP_TO_ADDRS="",
    )
    monkeypatch.setattr(config, "options", options)


@pytest.fixture(autouse=True)
def fixed_secrets_token_urlsafe(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_token_urlsafe(nbytes: int) -> str:
        return CONST_TOKEN_URLSAFE

    monkeypatch.setattr(secrets, "token_urlsafe", mock_token_urlsafe)


@pytest.fixture(autouse=True)
def responses_activate_mock_to_prevent_accidential_requests() -> (
    Generator[None, None, None]
):
    r_mock = responses.RequestsMock()
    r_mock.start()
    yield None
    r_mock.stop()
