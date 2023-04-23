import pytest
from freezegun import freeze_time
from pytest import LogCaptureFixture, MonkeyPatch

from backuper import config
from backuper.backup_targets import MySQL

from .conftest import ALL_MYSQL_DBS_TARGETS, CONST_TOKEN_URLSAFE, DB_VERSION_BY_ENV_VAR


@pytest.mark.parametrize("mysql_target", ALL_MYSQL_DBS_TARGETS)
def test_mysql_connection_success(
    caplog: LogCaptureFixture, mysql_target: config.MySQLBackupTarget
):
    db = MySQL(**mysql_target.dict())
    assert db.db_version == DB_VERSION_BY_ENV_VAR[mysql_target.env_name]


@pytest.mark.parametrize("mysql_target", ALL_MYSQL_DBS_TARGETS)
def test_mysql_connection_fail(
    caplog: LogCaptureFixture,
    mysql_target: config.MySQLBackupTarget,
    monkeypatch: MonkeyPatch,
):
    with pytest.raises(SystemExit) as system_exit:
        # simulate not existing db port 9999 and connection err
        monkeypatch.setattr(mysql_target, "port", 9999)
        MySQL(**mysql_target.dict())
    assert system_exit.type == SystemExit
    assert system_exit.value.code == 1


@freeze_time("2022-12-11")
@pytest.mark.parametrize("mysql_target", ALL_MYSQL_DBS_TARGETS)
def test_run_mysqldump(
    caplog: LogCaptureFixture, mysql_target: config.MySQLBackupTarget
):
    db = MySQL(**mysql_target.dict())
    out_backup = db._backup()
    out_file = (
        f"{db.env_name}/20221211_0000_database_{db.db_version}_{CONST_TOKEN_URLSAFE}"
    )
    out_path = config.CONST_BACKUP_FOLDER_PATH / out_file
    assert out_backup == out_path
