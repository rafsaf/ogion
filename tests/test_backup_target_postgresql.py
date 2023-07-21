from unittest.mock import Mock

import pytest
from freezegun import freeze_time

from backuper import config, core
from backuper.backup_targets import PostgreSQL
from backuper.models.target_models import PostgreSQLTargetModel

from .conftest import (
    ALL_POSTGRES_DBS_TARGETS,
    CONST_TOKEN_URLSAFE,
    DB_VERSION_BY_ENV_VAR,
)


@pytest.mark.parametrize("postgres_target", ALL_POSTGRES_DBS_TARGETS)
def test_postgres_connection_success(
    postgres_target: PostgreSQLTargetModel,
) -> None:
    db = PostgreSQL(**postgres_target.model_dump())
    assert db.db_version == DB_VERSION_BY_ENV_VAR[postgres_target.env_name]


@pytest.mark.parametrize("postgres_target", ALL_POSTGRES_DBS_TARGETS)
def test_postgres_connection_fail(
    postgres_target: PostgreSQLTargetModel,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(SystemExit) as system_exit:
        # simulate not existing db port 9999 and connection err
        monkeypatch.setattr(postgres_target, "port", 9999)
        PostgreSQL(**postgres_target.model_dump())
    assert system_exit.type == SystemExit
    assert system_exit.value.code == 1


@freeze_time("2022-12-11")
@pytest.mark.parametrize("postgres_target", ALL_POSTGRES_DBS_TARGETS)
def test_run_pg_dump(
    postgres_target: PostgreSQLTargetModel,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock = Mock(return_value="fixed_dbname")
    monkeypatch.setattr(core, "safe_text_version", mock)

    db = PostgreSQL(**postgres_target.model_dump())
    out_backup = db._backup()

    out_file = f"{db.env_name}/{db.env_name}_20221211_0000_fixed_dbname_{db.db_version}_{CONST_TOKEN_URLSAFE}.sql"
    out_path = config.CONST_BACKUP_FOLDER_PATH / out_file
    assert out_backup == out_path
