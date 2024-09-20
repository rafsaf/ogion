# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)


import shlex

import pytest
from freezegun import freeze_time
from pydantic import SecretStr

from ogion import config, core
from ogion.backup_targets.mysql import MySQL
from ogion.models.backup_target_models import MySQLTargetModel

from .conftest import (
    ALL_MYSQL_DBS_TARGETS,
    CONST_TOKEN_URLSAFE,
    CONST_UNSAFE_AGE_KEY,
    DB_VERSION_BY_ENV_VAR,
)


@pytest.mark.parametrize("mysql_target", ALL_MYSQL_DBS_TARGETS)
def test_mysql_connection_success(mysql_target: MySQLTargetModel) -> None:
    db = MySQL(target_model=mysql_target)
    assert db.db_version == DB_VERSION_BY_ENV_VAR[mysql_target.env_name]


@pytest.mark.parametrize("mysql_target", ALL_MYSQL_DBS_TARGETS)
def test_mysql_connection_fail(mysql_target: MySQLTargetModel) -> None:
    with pytest.raises(core.CoreSubprocessError):
        # simulate not existing db port 9999 and connection err
        target_model = mysql_target.model_copy(update={"port": 9999})
        MySQL(target_model=target_model)


@freeze_time("2022-12-11")
@pytest.mark.parametrize("mysql_target", ALL_MYSQL_DBS_TARGETS)
def test_run_mysqldump(mysql_target: MySQLTargetModel) -> None:
    db = MySQL(target_model=mysql_target)
    out_backup = db.backup()

    escaped_name = "database_12"
    escaped_version = db.db_version.replace(".", "")

    out_file = (
        f"{db.env_name}/"
        f"{db.env_name}_20221211_0000_{escaped_name}_{escaped_version}_{CONST_TOKEN_URLSAFE}.sql"
    )
    out_path = config.CONST_BACKUP_FOLDER_PATH / out_file
    assert out_backup == out_path


@pytest.mark.parametrize("mysql_target", ALL_MYSQL_DBS_TARGETS)
def test_end_to_end_successful_restore_after_backup(
    mysql_target: MySQLTargetModel,
) -> None:
    root_target_model = mysql_target.model_copy(
        update={
            "user": "root",
            "password": SecretStr(f"root-{mysql_target.password.get_secret_value()}"),
        }
    )

    db = MySQL(target_model=root_target_model)
    core.run_subprocess(
        f"mariadb --defaults-file={db.option_file} {db.db_name} --execute="
        "'DROP DATABASE IF EXISTS test_db;'",
    )
    core.run_subprocess(
        f"mariadb --defaults-file={db.option_file} {db.db_name} --execute="
        "'CREATE DATABASE test_db;'",
    )

    test_db_target = root_target_model.model_copy(update={"db": "test_db"})
    test_db = MySQL(target_model=test_db_target)

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
    backup_zip = core.run_create_age_archive(test_db_backup)
    test_db_backup.unlink()
    test_db_backup = core.run_decrypt_age_archive(
        backup_zip, debug_secret=CONST_UNSAFE_AGE_KEY
    )

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
