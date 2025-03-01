# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)


import shlex

import pytest
from freezegun import freeze_time

from ogion import config, core
from ogion.backup_targets.postgresql import PostgreSQL
from ogion.models.backup_target_models import PostgreSQLTargetModel

from .conftest import (
    ALL_POSTGRES_DBS_TARGETS,
    CONST_TOKEN_URLSAFE,
    DB_VERSION_BY_ENV_VAR,
)


@pytest.mark.parametrize("postgres_target", ALL_POSTGRES_DBS_TARGETS)
def test_postgres_connection_success(
    postgres_target: PostgreSQLTargetModel,
) -> None:
    db = PostgreSQL(target_model=postgres_target)
    assert db.db_version == DB_VERSION_BY_ENV_VAR[postgres_target.env_name]


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
    out_path = config.CONST_BACKUP_FOLDER_PATH / out_file
    assert out_backup == out_path


@pytest.mark.parametrize("postgres_target", ALL_POSTGRES_DBS_TARGETS)
def test_end_to_end_successful_restore_after_backup(
    postgres_target: PostgreSQLTargetModel,
) -> None:
    db = PostgreSQL(target_model=postgres_target)
    core.run_subprocess(
        f"psql -d {db.escaped_conn_uri} -w --command "
        "'DROP DATABASE IF EXISTS test_db;'",
    )
    core.run_subprocess(
        f"psql -d {db.escaped_conn_uri} -w --command 'CREATE DATABASE test_db;'",
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
        f"psql -d {test_db.escaped_conn_uri} -w --command '{table_query}'",
    )

    insert_query = shlex.quote(
        "INSERT INTO my_table (name, age) VALUES ('Geralt z Rivii', 60),('rafsaf', 24);"
    )

    core.run_subprocess(
        f"psql -d {test_db.escaped_conn_uri} -w --command {insert_query}",
    )

    test_db_backup = test_db.backup()
    backup_age = core.run_create_age_archive(test_db_backup)
    test_db_backup.unlink()
    test_db_backup = core.run_decrypt_age_archive(backup_age)

    core.run_subprocess(
        f"psql -d {db.escaped_conn_uri} -w --command 'DROP DATABASE test_db;'",
    )
    core.run_subprocess(
        f"psql -d {db.escaped_conn_uri} -w --command 'CREATE DATABASE test_db;'",
    )

    test_db.restore(str(test_db_backup))

    result = core.run_subprocess(
        f"psql -d {test_db.escaped_conn_uri} -w --command "
        "'select * from my_table order by id asc;'",
    )

    assert result == (
        " id |      name      | age \n"
        "----+----------------+-----\n"
        "  1 | Geralt z Rivii |  60\n"
        "  2 | rafsaf         |  24\n"
        "(2 rows)\n\n"
    )

    core.run_subprocess(
        f"psql -d {test_db.escaped_conn_uri} -w --command "
        "'delete from my_table where id = '2';'",
    )

    test_db.restore(str(test_db_backup))

    result = core.run_subprocess(
        f"psql -d {test_db.escaped_conn_uri} -w --command "
        "'select * from my_table order by id asc;'",
    )

    assert result == (
        " id |      name      | age \n"
        "----+----------------+-----\n"
        "  1 | Geralt z Rivii |  60\n"
        "  2 | rafsaf         |  24\n"
        "(2 rows)\n\n"
    )
