# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
import hashlib
from pathlib import Path
from unittest.mock import Mock

import pytest
from freezegun import freeze_time

from ogion import config, core, main
from ogion.backup_targets.postgresql import PostgreSQL
from ogion.models.backup_target_models import PostgreSQLTargetModel
from ogion.upload_providers.base_provider import BaseUploadProvider

from .conftest import (
    ALL_POSTGRES_DBS_TARGETS,
    CONST_TOKEN_URLSAFE,
    DB_VERSION_BY_ENV_VAR,
)

TABLE_QUERY = (
    "CREATE TABLE my_table "
    "(id SERIAL PRIMARY KEY, "
    "name VARCHAR (50) UNIQUE NOT NULL, "
    "age INTEGER);"
)
FIRST_ROWS_QUERY = "INSERT INTO my_table (name, age) VALUES ('Geralt z Rivii', 60);"
SECOND_ROWS_QUERY = (
    "INSERT INTO my_table (name, age) VALUES ('Geralt z Rivii', 60),('rafsaf', 24);"
)
FIRST_ROWS_RESULT = (
    " id |      name      | age \n"
    "----+----------------+-----\n"
    "  1 | Geralt z Rivii |  60\n"
    "(1 row)\n\n"
)
SECOND_ROWS_RESULT = (
    " id |      name      | age \n"
    "----+----------------+-----\n"
    "  1 | Geralt z Rivii |  60\n"
    "  2 | rafsaf         |  24\n"
    "(2 rows)\n\n"
)
EXPECTED_PROVIDER_BACKUPS = 2


def _run_psql(conn_uri: str, command: str) -> str:
    return core.run_subprocess(
        [
            "psql",
            "-d",
            conn_uri,
            "-w",
            "--command",
            command,
        ],
    )


def _recreate_database(admin_db: PostgreSQL, db_name: str) -> None:
    _run_psql(admin_db.conn_uri, f"DROP DATABASE IF EXISTS {db_name};")
    _run_psql(admin_db.conn_uri, f"CREATE DATABASE {db_name};")


def _make_test_db(postgres_target: PostgreSQLTargetModel, db_name: str) -> PostgreSQL:
    test_db_target = postgres_target.model_copy(
        update={
            "db": db_name,
            "max_backups": config.options.BACKUP_MAX_NUMBER,
            "min_retention_days": config.options.BACKUP_MIN_RETENTION_DAYS,
        }
    )
    return PostgreSQL(target_model=test_db_target)


def _make_test_db_name(test_name: str) -> str:
    name_hash = hashlib.md5(test_name.encode(), usedforsecurity=False).hexdigest()[:12]
    return f"pg_restore_{name_hash}"


def _assert_table_rows(test_db: PostgreSQL, expected: str) -> None:
    result = _run_psql(test_db.conn_uri, "select * from my_table order by id asc;")
    assert result == expected


def _setup_main_restore_path(
    monkeypatch: pytest.MonkeyPatch,
    provider: BaseUploadProvider,
    test_db: PostgreSQL,
) -> None:
    monkeypatch.setattr(
        main,
        "backup_provider",
        Mock(return_value=provider),
    )
    monkeypatch.setattr(
        main,
        "backup_targets",
        Mock(return_value=[test_db]),
    )


def _create_provider_backups(
    postgres_target: PostgreSQLTargetModel,
    monkeypatch: pytest.MonkeyPatch,
    provider: BaseUploadProvider,
    db_name: str,
) -> tuple[PostgreSQL, list[str]]:
    backup_suffixes = iter(
        [
            ("20221211_0000", "specific"),
            ("20221211_0001", "latest"),
        ]
    )

    def fake_get_new_backup_path(env_name: str, name: str) -> Path:
        timestamp, token = next(backup_suffixes)
        base_dir_path = config.CONST_DATA_FOLDER_PATH / env_name
        base_dir_path.mkdir(mode=0o700, parents=True, exist_ok=True)
        return base_dir_path / f"{env_name}_{timestamp}_{name}_{token}"

    admin_db = PostgreSQL(target_model=postgres_target)
    _recreate_database(admin_db, db_name)
    test_db = _make_test_db(postgres_target, db_name)
    _setup_main_restore_path(monkeypatch, provider, test_db)
    monkeypatch.setattr(core, "get_new_backup_path", fake_get_new_backup_path)

    _run_psql(test_db.conn_uri, TABLE_QUERY)
    _run_psql(test_db.conn_uri, FIRST_ROWS_QUERY)
    main.run_backup(target=test_db)

    _run_psql(test_db.conn_uri, "TRUNCATE TABLE my_table RESTART IDENTITY;")
    _run_psql(test_db.conn_uri, SECOND_ROWS_QUERY)
    main.run_backup(target=test_db)

    return test_db, provider.all_target_backups(test_db.env_name)


@pytest.mark.parametrize("postgres_target", ALL_POSTGRES_DBS_TARGETS)
def test_postgres_connection_success(
    postgres_target: PostgreSQLTargetModel,
) -> None:
    db = PostgreSQL(target_model=postgres_target)
    assert db.db_version.startswith(DB_VERSION_BY_ENV_VAR[postgres_target.env_name])


@pytest.mark.parametrize("postgres_target", ALL_POSTGRES_DBS_TARGETS)
def test_postgres_connection_fail(postgres_target: PostgreSQLTargetModel) -> None:
    with pytest.raises(core.CoreSubprocessError):
        # simulate not existing db port 9999 and connection err
        target_model = postgres_target.model_copy(update={"port": 9999})
        PostgreSQL(target_model=target_model)


@freeze_time("2022-12-11")
@pytest.mark.parametrize("postgres_target", ALL_POSTGRES_DBS_TARGETS)
def test_run_pg_dump(postgres_target: PostgreSQLTargetModel) -> None:
    db = PostgreSQL(target_model=postgres_target)
    out_backup = db.backup()

    escaped_name = "database_12"
    escaped_version = db.db_version.replace(".", "")

    out_file = (
        f"{db.env_name}/"
        f"{db.env_name}_20221211_0000_{escaped_name}_{escaped_version}_{CONST_TOKEN_URLSAFE}.sql"
    )
    out_path = config.CONST_DATA_FOLDER_PATH / out_file
    assert out_backup == out_path


@pytest.mark.parametrize("postgres_target", ALL_POSTGRES_DBS_TARGETS)
def test_end_to_end_successful_restore_after_backup(
    postgres_target: PostgreSQLTargetModel,
) -> None:
    db = PostgreSQL(target_model=postgres_target)
    core.run_subprocess(
        [
            "psql",
            "-d",
            db.conn_uri,
            "-w",
            "--command",
            "DROP DATABASE IF EXISTS test_db;",
        ],
    )
    core.run_subprocess(
        [
            "psql",
            "-d",
            db.conn_uri,
            "-w",
            "--command",
            "CREATE DATABASE test_db;",
        ],
    )

    test_db_target = postgres_target.model_copy(update={"db": "test_db"})
    test_db = PostgreSQL(target_model=test_db_target)

    table_query = (
        "CREATE TABLE my_table "
        "(id SERIAL PRIMARY KEY, "
        "name VARCHAR (50) UNIQUE NOT NULL, "
        "age INTEGER);"
    )
    core.run_subprocess(
        ["psql", "-d", test_db.conn_uri, "-w", "--command", table_query],
    )

    insert_query = (
        "INSERT INTO my_table (name, age) VALUES ('Geralt z Rivii', 60),('rafsaf', 24);"
    )

    core.run_subprocess(
        ["psql", "-d", test_db.conn_uri, "-w", "--command", insert_query],
    )

    test_db_backup = test_db.backup()
    backup_age = core.run_create_age_archive(test_db_backup)
    test_db_backup.unlink()
    test_db_backup = core.run_decrypt_age_archive(backup_age)

    core.run_subprocess(
        ["psql", "-d", db.conn_uri, "-w", "--command", "DROP DATABASE test_db;"],
    )
    core.run_subprocess(
        [
            "psql",
            "-d",
            db.conn_uri,
            "-w",
            "--command",
            "CREATE DATABASE test_db;",
        ],
    )

    test_db.restore(str(test_db_backup))

    result = core.run_subprocess(
        [
            "psql",
            "-d",
            test_db.conn_uri,
            "-w",
            "--command",
            "select * from my_table order by id asc;",
        ],
    )

    assert result == (
        " id |      name      | age \n"
        "----+----------------+-----\n"
        "  1 | Geralt z Rivii |  60\n"
        "  2 | rafsaf         |  24\n"
        "(2 rows)\n\n"
    )

    core.run_subprocess(
        [
            "psql",
            "-d",
            test_db.conn_uri,
            "-w",
            "--command",
            "delete from my_table where id = '2';",
        ],
    )

    test_db.restore(str(test_db_backup))

    result = core.run_subprocess(
        [
            "psql",
            "-d",
            test_db.conn_uri,
            "-w",
            "--command",
            "select * from my_table order by id asc;",
        ],
    )

    assert result == (
        " id |      name      | age \n"
        "----+----------------+-----\n"
        "  1 | Geralt z Rivii |  60\n"
        "  2 | rafsaf         |  24\n"
        "(2 rows)\n\n"
    )


@pytest.mark.parametrize(
    "postgres_target",
    [ALL_POSTGRES_DBS_TARGETS[0]],
    ids=lambda target: target.env_name,
)
def test_end_to_end_restore_specific_stored_backup_via_provider(
    postgres_target: PostgreSQLTargetModel,
    provider: BaseUploadProvider,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    admin_db = PostgreSQL(target_model=postgres_target)
    db_name = _make_test_db_name(f"{request.node.name}_{provider.__class__.__name__}")
    try:
        test_db, backups = _create_provider_backups(
            postgres_target=postgres_target,
            monkeypatch=monkeypatch,
            provider=provider,
            db_name=db_name,
        )

        assert len(backups) == EXPECTED_PROVIDER_BACKUPS

        _run_psql(test_db.conn_uri, "TRUNCATE TABLE my_table RESTART IDENTITY;")

        with pytest.raises(SystemExit) as system_exit:
            main.run_restore(backups[1], test_db.env_name)

        assert system_exit.value.code == 0
        _assert_table_rows(test_db, FIRST_ROWS_RESULT)

        downloaded_backup = config.CONST_DOWNLOADS_FOLDER_PATH / backups[
            1
        ].removeprefix("/")
        assert not downloaded_backup.exists()
    finally:
        _run_psql(admin_db.conn_uri, f"DROP DATABASE IF EXISTS {db_name};")


@pytest.mark.parametrize(
    "postgres_target",
    [ALL_POSTGRES_DBS_TARGETS[0]],
    ids=lambda target: target.env_name,
)
def test_end_to_end_restore_latest_stored_backup_via_provider(
    postgres_target: PostgreSQLTargetModel,
    provider: BaseUploadProvider,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    admin_db = PostgreSQL(target_model=postgres_target)
    db_name = _make_test_db_name(f"{request.node.name}_{provider.__class__.__name__}")
    try:
        test_db, backups = _create_provider_backups(
            postgres_target=postgres_target,
            monkeypatch=monkeypatch,
            provider=provider,
            db_name=db_name,
        )

        assert len(backups) == EXPECTED_PROVIDER_BACKUPS

        _run_psql(test_db.conn_uri, "TRUNCATE TABLE my_table RESTART IDENTITY;")

        with pytest.raises(SystemExit) as system_exit:
            main.run_restore_latest(test_db.env_name)

        assert system_exit.value.code == 0
        _assert_table_rows(test_db, SECOND_ROWS_RESULT)

        downloaded_backup = config.CONST_DOWNLOADS_FOLDER_PATH / backups[
            0
        ].removeprefix("/")
        assert not downloaded_backup.exists()
    finally:
        _run_psql(admin_db.conn_uri, f"DROP DATABASE IF EXISTS {db_name};")
