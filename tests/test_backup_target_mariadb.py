# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)


import pytest
from freezegun import freeze_time
from pydantic import SecretStr

from ogion import config, core
from ogion.backup_targets.mariadb import MariaDB
from ogion.models.backup_target_models import MariaDBTargetModel

from .conftest import (
    ALL_MARIADB_DBS_TARGETS,
    CONST_TOKEN_URLSAFE,
    DB_VERSION_BY_ENV_VAR,
)


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
