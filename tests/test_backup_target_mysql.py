from unittest.mock import Mock

import pytest
from freezegun import freeze_time

from backuper import config, core
from backuper.backup_targets import MySQL

from .conftest import ALL_MYSQL_DBS_TARGETS, CONST_TOKEN_URLSAFE, DB_VERSION_BY_ENV_VAR


@pytest.mark.parametrize("mysql_target", ALL_MYSQL_DBS_TARGETS)
def test_mysql_connection_success(mysql_target: config.MySQLBackupTarget) -> None:
    db = MySQL(**mysql_target.dict())
    assert db.db_version == DB_VERSION_BY_ENV_VAR[mysql_target.env_name]


@pytest.mark.parametrize("mysql_target", ALL_MYSQL_DBS_TARGETS)
def test_mysql_connection_fail(
    mysql_target: config.MySQLBackupTarget,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(SystemExit) as system_exit:
        # simulate not existing db port 9999 and connection err
        monkeypatch.setattr(mysql_target, "port", 9999)
        MySQL(**mysql_target.dict())
    assert system_exit.type == SystemExit
    assert system_exit.value.code == 1


@freeze_time("2022-12-11")
@pytest.mark.parametrize("mysql_target", ALL_MYSQL_DBS_TARGETS)
def test_run_mysqldump(
    mysql_target: config.MySQLBackupTarget,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock = Mock(return_value="fixed_dbname")
    monkeypatch.setattr(core, "safe_text_version", mock)

    db = MySQL(**mysql_target.dict())
    out_backup = db._backup()

    out_file = f"{db.env_name}/{db.env_name}_20221211_0000_fixed_dbname_{db.db_version}_{CONST_TOKEN_URLSAFE}.sql"
    out_path = config.CONST_BACKUP_FOLDER_PATH / out_file
    assert out_backup == out_path
