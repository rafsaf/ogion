# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)


import shlex

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
    assert db.db_version == DB_VERSION_BY_ENV_VAR[mariadb_target.env_name]


@pytest.mark.parametrize("mariadb_target", ALL_MARIADB_DBS_TARGETS)
def test_mariadb_connection_fail(mariadb_target: MariaDBTargetModel) -> None:
    with pytest.raises(core.CoreSubprocessError):
        # simulate not existing db port 9999 and connection err
        target_model = mariadb_target.model_copy(update={"port": 9999})
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
    out_path = config.CONST_BACKUP_FOLDER_PATH / out_file
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
        f"mariadb --defaults-file={db.option_file} {db.db_name} --execute="
        "'DROP DATABASE IF EXISTS test_db;'",
    )
    core.run_subprocess(
        f"mariadb --defaults-file={db.option_file} {db.db_name} --execute="
        "'CREATE DATABASE test_db;'",
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
        f"mariadb --defaults-file={test_db.option_file} {test_db.db_name} "
        f"--execute='{table_query}'",
    )

    insert_query = shlex.quote(
        "INSERT INTO my_table (name, age) "
        "VALUES ('Geralt z Rivii', 60),('rafsaf', 24);"
    )

    core.run_subprocess(
        f"mariadb --defaults-file={test_db.option_file} {test_db.db_name} "
        f"--execute={insert_query}",
    )

    test_db_backup = test_db.backup()
    backup_zip = core.run_create_zip_archive(test_db_backup)
    test_db_backup.unlink()
    test_db_backup = core.run_unzip_zip_archive(backup_zip)

    core.run_subprocess(
        f"mariadb --defaults-file={db.option_file} {db.db_name} --execute="
        "'DROP DATABASE test_db;'",
    )
    core.run_subprocess(
        f"mariadb --defaults-file={db.option_file} {db.db_name} --execute="
        "'CREATE DATABASE test_db;'",
    )

    test_db.restore(str(test_db_backup))

    result = core.run_subprocess(
        f"mariadb --defaults-file={test_db.option_file} {test_db.db_name}"
        " --execute='select * from my_table order by id asc;'",
    )

    assert result == ("id\tname\tage\n" "1\tGeralt z Rivii\t60\n" "2\trafsaf\t24\n")

    result = core.run_subprocess(
        f"mariadb --defaults-file={test_db.option_file} {test_db.db_name}"
        " --execute='delete from my_table where id = '2';'",
    )
    result = core.run_subprocess(
        f"mariadb --defaults-file={test_db.option_file} {test_db.db_name}"
        " --execute='select * from my_table order by id asc;'",
    )

    assert result == ("id\tname\tage\n" "1\tGeralt z Rivii\t60\n")

    test_db.restore(str(test_db_backup))

    result = core.run_subprocess(
        f"mariadb --defaults-file={test_db.option_file} {test_db.db_name}"
        " --execute='select * from my_table order by id asc;'",
    )

    assert result == ("id\tname\tage\n" "1\tGeralt z Rivii\t60\n" "2\trafsaf\t24\n")
