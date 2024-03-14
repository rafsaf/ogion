# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import os
import secrets
from collections.abc import Generator
from pathlib import Path
from typing import TypeVar

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
from backuper.tools.compose_db_models import ComposeDatabase
from backuper.tools.compose_file_generator import (
    DB_NAME,
    DB_PWD,
    DB_USERNAME,
    db_compose_mariadb_data,
    db_compose_mysql_data,
    db_compose_postgresql_data,
)

TM = TypeVar("TM")


def _to_target_model(
    compose_db: ComposeDatabase,
    model: type[TM],
) -> TM:
    DB_VERSION_BY_ENV_VAR[compose_db.name] = compose_db.version
    return model(  # type: ignore[call-arg]
        env_name=compose_db.name,
        cron_rule="* * * * *",
        host=compose_db.name if DOCKER_TESTS else "localhost",
        port=(
            int(compose_db.ports[0].split(":")[1])
            if DOCKER_TESTS
            else int(compose_db.ports[0].split(":")[0])
        ),
        password=SecretStr(DB_PWD),
        db=DB_NAME,
        user=DB_USERNAME,
    )


DOCKER_TESTS: bool = os.environ.get("DOCKER_TESTS", None) is not None
CONST_TOKEN_URLSAFE = "mock"
DB_VERSION_BY_ENV_VAR: dict[str, str] = {}
ALL_POSTGRES_DBS_TARGETS: list[PostgreSQLTargetModel] = [
    _to_target_model(compose_db, PostgreSQLTargetModel)
    for compose_db in db_compose_postgresql_data()
]
ALL_MYSQL_DBS_TARGETS: list[MySQLTargetModel] = [
    _to_target_model(compose_db, MySQLTargetModel)
    for compose_db in db_compose_mysql_data()
]
ALL_MARIADB_DBS_TARGETS: list[MariaDBTargetModel] = [
    _to_target_model(compose_db, MariaDBTargetModel)
    for compose_db in db_compose_mariadb_data()
]
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
