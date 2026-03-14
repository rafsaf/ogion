# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)


import hashlib
from pathlib import Path
from unittest.mock import Mock

import pytest
from freezegun import freeze_time
from pydantic import SecretStr

from ogion import config, core, main
from ogion.backup_targets.mariadb import MariaDB
from ogion.models.backup_target_models import MariaDBTargetModel
from ogion.upload_providers.base_provider import BaseUploadProvider

from .conftest import (
    ALL_MARIADB_DBS_TARGETS,
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
FIRST_ROWS_RESULT = "id\tname\tage\n1\tGeralt z Rivii\t60\n"
SECOND_ROWS_RESULT = "id\tname\tage\n1\tGeralt z Rivii\t60\n2\trafsaf\t24\n"
EXPECTED_PROVIDER_BACKUPS = 2


def _make_root_target(mariadb_target: MariaDBTargetModel) -> MariaDBTargetModel:
    return mariadb_target.model_copy(
        update={
            "user": "root",
            "password": SecretStr(f"root-{mariadb_target.password.get_secret_value()}"),
        }
    )


def _run_mariadb(db: MariaDB, command: str) -> str:
    return core.run_subprocess(
        [
            "mariadb",
            f"--defaults-file={db.option_file}",
            db.target_model.db,
            f"--execute={command}",
        ],
    )


def _make_test_db_name(test_name: str) -> str:
    name_hash = hashlib.md5(test_name.encode(), usedforsecurity=False).hexdigest()[:12]
    return f"mariadb_restore_{name_hash}"


def _make_test_db(root_target: MariaDBTargetModel, db_name: str) -> MariaDB:
    test_db_target = root_target.model_copy(
        update={
            "db": db_name,
            "max_backups": config.options.BACKUP_MAX_NUMBER,
            "min_retention_days": config.options.BACKUP_MIN_RETENTION_DAYS,
        }
    )
    return MariaDB(target_model=test_db_target)


def _assert_table_rows(test_db: MariaDB, expected: str) -> None:
    result = _run_mariadb(test_db, "select * from my_table order by id asc;")
    assert result == expected


def _setup_main_restore_path(
    monkeypatch: pytest.MonkeyPatch,
    provider: BaseUploadProvider,
    test_db: MariaDB,
) -> None:
    monkeypatch.setattr(main, "backup_provider", Mock(return_value=provider))
    monkeypatch.setattr(main, "backup_targets", Mock(return_value=[test_db]))


def _create_provider_backups(
    mariadb_target: MariaDBTargetModel,
    monkeypatch: pytest.MonkeyPatch,
    provider: BaseUploadProvider,
    db_name: str,
) -> tuple[MariaDB, list[str]]:
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

    root_target = _make_root_target(mariadb_target)
    admin_db = MariaDB(target_model=root_target)
    _run_mariadb(admin_db, f"DROP DATABASE IF EXISTS {db_name};")
    _run_mariadb(admin_db, f"CREATE DATABASE {db_name};")

    test_db = _make_test_db(root_target, db_name)
    _setup_main_restore_path(monkeypatch, provider, test_db)
    monkeypatch.setattr(core, "get_new_backup_path", fake_get_new_backup_path)

    _run_mariadb(test_db, TABLE_QUERY)
    _run_mariadb(test_db, FIRST_ROWS_QUERY)
    main.run_backup(target=test_db)

    _run_mariadb(test_db, "TRUNCATE TABLE my_table;")
    _run_mariadb(test_db, SECOND_ROWS_QUERY)
    main.run_backup(target=test_db)

    return test_db, provider.all_target_backups(test_db.env_name)


@pytest.mark.parametrize("mariadb_target", ALL_MARIADB_DBS_TARGETS)
def test_mariadb_connection_success(mariadb_target: MariaDBTargetModel) -> None:
    db = MariaDB(target_model=mariadb_target)
    assert db.db_version.startswith(DB_VERSION_BY_ENV_VAR[mariadb_target.env_name])


@pytest.mark.parametrize("mariadb_target", ALL_MARIADB_DBS_TARGETS)
def test_mariadb_connection_fail(mariadb_target: MariaDBTargetModel) -> None:
    with pytest.raises(core.CoreSubprocessError):
        # simulate not existing db port 9999 and connection err
        target_model = mariadb_target.model_copy(update={"port": 9999})
        MariaDB(target_model=target_model)


def test_mariadb_option_file_rejects_newlines_in_client_option(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(MariaDB, "_mariadb_connection", lambda self: "11.4.2")

    target_model = MariaDBTargetModel.model_validate(
        {
            "env_name": "mariadb_newline_client",
            "cron_rule": "* * * * *",
            "host": "localhost",
            "port": 3306,
            "db": "mariadb",
            "user": "root",
            "password": SecretStr("secret"),
            "client_tee": "safe\nunsafe=true",
        }
    )

    with pytest.raises(ValueError, match="must not contain newlines"):
        MariaDB(target_model=target_model)


def test_mariadb_option_file_accepts_valid_client_option(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(MariaDB, "_mariadb_connection", lambda self: "11.4.2")

    target_model = MariaDBTargetModel.model_validate(
        {
            "env_name": "mariadb_valid_client",
            "cron_rule": "* * * * *",
            "host": "localhost",
            "port": 3306,
            "db": "mariadb",
            "user": "root",
            "password": SecretStr("secret"),
            "client_tee": "safe-option",
        }
    )

    db = MariaDB(target_model=target_model)

    assert "tee=safe-option\n" in db.option_file.read_text()


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("host", "localhost\nunsafe=true"),
        ("host", "localhost\runsafe=true"),
        ("user", "root\nunsafe=true"),
        ("password", SecretStr("secret\nunsafe=true")),
    ],
)
def test_mariadb_option_file_rejects_newlines_in_credentials(
    monkeypatch: pytest.MonkeyPatch,
    field_name: str,
    field_value: str | SecretStr,
) -> None:
    monkeypatch.setattr(MariaDB, "_mariadb_connection", lambda self: "11.4.2")

    target_kwargs: dict[str, str | int | SecretStr] = {
        "env_name": "mariadb_newline_user",
        "cron_rule": "* * * * *",
        "host": "localhost",
        "port": 3306,
        "db": "mariadb",
        "user": "root",
        "password": SecretStr("secret"),
    }
    target_kwargs[field_name] = field_value

    target_model = MariaDBTargetModel.model_validate(target_kwargs)

    with pytest.raises(ValueError, match="must not contain newlines"):
        MariaDB(target_model=target_model)


@freeze_time("2022-12-11")
@pytest.mark.parametrize("mariadb_target", ALL_MARIADB_DBS_TARGETS)
def test_run_mariadb_dump(mariadb_target: MariaDBTargetModel) -> None:
    db = MariaDB(target_model=mariadb_target)
    out_backup = db.backup()

    escaped_name = "database_12"
    escaped_version = db.db_version.replace(".", "")
    out_file = (
        f"{db.env_name}/"
        f"{db.env_name}_20221211_0000_{escaped_name}_{escaped_version}_{CONST_TOKEN_URLSAFE}.sql"
    )
    out_path = config.CONST_DATA_FOLDER_PATH / out_file
    assert out_backup == out_path


@pytest.mark.parametrize("mariadb_target", ALL_MARIADB_DBS_TARGETS)
def test_end_to_end_successful_restore_after_backup(
    mariadb_target: MariaDBTargetModel,
) -> None:
    root_target_model = mariadb_target.model_copy(
        update={
            "user": "root",
            "password": SecretStr(f"root-{mariadb_target.password.get_secret_value()}"),
        }
    )

    db = MariaDB(target_model=root_target_model)
    core.run_subprocess(
        [
            "mariadb",
            f"--defaults-file={db.option_file}",
            db.target_model.db,
            "--execute=DROP DATABASE IF EXISTS test_db;",
        ],
    )
    core.run_subprocess(
        [
            "mariadb",
            f"--defaults-file={db.option_file}",
            db.target_model.db,
            "--execute=CREATE DATABASE test_db;",
        ],
    )

    test_db_target = root_target_model.model_copy(update={"db": "test_db"})
    test_db = MariaDB(target_model=test_db_target)

    table_query = (
        "CREATE TABLE my_table "
        "(id SERIAL PRIMARY KEY, "
        "name VARCHAR (50) UNIQUE NOT NULL, "
        "age INTEGER);"
    )
    core.run_subprocess(
        [
            "mariadb",
            f"--defaults-file={test_db.option_file}",
            test_db.target_model.db,
            f"--execute={table_query}",
        ],
    )

    insert_query = (
        "INSERT INTO my_table (name, age) VALUES ('Geralt z Rivii', 60),('rafsaf', 24);"
    )

    core.run_subprocess(
        [
            "mariadb",
            f"--defaults-file={test_db.option_file}",
            test_db.target_model.db,
            f"--execute={insert_query}",
        ],
    )

    test_db_backup = test_db.backup()
    backup_age = core.run_create_age_archive(test_db_backup)
    test_db_backup.unlink()
    test_db_backup = core.run_decrypt_age_archive(backup_age)

    core.run_subprocess(
        [
            "mariadb",
            f"--defaults-file={db.option_file}",
            db.target_model.db,
            "--execute=DROP DATABASE test_db;",
        ],
    )
    core.run_subprocess(
        [
            "mariadb",
            f"--defaults-file={db.option_file}",
            db.target_model.db,
            "--execute=CREATE DATABASE test_db;",
        ],
    )

    test_db.restore(str(test_db_backup))

    result = core.run_subprocess(
        [
            "mariadb",
            f"--defaults-file={test_db.option_file}",
            test_db.target_model.db,
            "--execute=select * from my_table order by id asc;",
        ],
    )

    assert result == ("id\tname\tage\n1\tGeralt z Rivii\t60\n2\trafsaf\t24\n")

    result = core.run_subprocess(
        [
            "mariadb",
            f"--defaults-file={test_db.option_file}",
            test_db.target_model.db,
            "--execute=delete from my_table where id = '2';",
        ],
    )
    result = core.run_subprocess(
        [
            "mariadb",
            f"--defaults-file={test_db.option_file}",
            test_db.target_model.db,
            "--execute=select * from my_table order by id asc;",
        ],
    )

    assert result == ("id\tname\tage\n1\tGeralt z Rivii\t60\n")

    test_db.restore(str(test_db_backup))

    result = core.run_subprocess(
        [
            "mariadb",
            f"--defaults-file={test_db.option_file}",
            test_db.target_model.db,
            "--execute=select * from my_table order by id asc;",
        ],
    )

    assert result == ("id\tname\tage\n1\tGeralt z Rivii\t60\n2\trafsaf\t24\n")


@pytest.mark.parametrize(
    "mariadb_target",
    [ALL_MARIADB_DBS_TARGETS[0]],
    ids=lambda target: target.env_name,
)
def test_end_to_end_restore_specific_stored_backup_via_provider(
    mariadb_target: MariaDBTargetModel,
    provider: BaseUploadProvider,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    root_target = _make_root_target(mariadb_target)
    admin_db = MariaDB(target_model=root_target)
    db_name = _make_test_db_name(f"{request.node.name}_{provider.__class__.__name__}")
    try:
        test_db, backups = _create_provider_backups(
            mariadb_target=mariadb_target,
            monkeypatch=monkeypatch,
            provider=provider,
            db_name=db_name,
        )

        assert len(backups) == EXPECTED_PROVIDER_BACKUPS

        _run_mariadb(test_db, "TRUNCATE TABLE my_table;")

        with pytest.raises(SystemExit) as system_exit:
            main.run_restore(backups[1], test_db.env_name)

        assert system_exit.value.code == 0
        _assert_table_rows(test_db, FIRST_ROWS_RESULT)

        downloaded_backup = config.CONST_DOWNLOADS_FOLDER_PATH / backups[
            1
        ].removeprefix("/")
        assert not downloaded_backup.exists()
    finally:
        _run_mariadb(admin_db, f"DROP DATABASE IF EXISTS {db_name};")


@pytest.mark.parametrize(
    "mariadb_target",
    [ALL_MARIADB_DBS_TARGETS[0]],
    ids=lambda target: target.env_name,
)
def test_end_to_end_restore_latest_stored_backup_via_provider(
    mariadb_target: MariaDBTargetModel,
    provider: BaseUploadProvider,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    root_target = _make_root_target(mariadb_target)
    admin_db = MariaDB(target_model=root_target)
    db_name = _make_test_db_name(f"{request.node.name}_{provider.__class__.__name__}")
    try:
        test_db, backups = _create_provider_backups(
            mariadb_target=mariadb_target,
            monkeypatch=monkeypatch,
            provider=provider,
            db_name=db_name,
        )

        assert len(backups) == EXPECTED_PROVIDER_BACKUPS

        _run_mariadb(test_db, "TRUNCATE TABLE my_table;")

        with pytest.raises(SystemExit) as system_exit:
            main.run_restore_latest(test_db.env_name)

        assert system_exit.value.code == 0
        _assert_table_rows(test_db, SECOND_ROWS_RESULT)

        downloaded_backup = config.CONST_DOWNLOADS_FOLDER_PATH / backups[
            0
        ].removeprefix("/")
        assert not downloaded_backup.exists()
    finally:
        _run_mariadb(admin_db, f"DROP DATABASE IF EXISTS {db_name};")
