import pytest
from freezegun import freeze_time
from pytest import LogCaptureFixture, MonkeyPatch

from backuper import config
from backuper.backup_targets import PostgreSQL

from .conftest import (
    ALL_POSTGRES_DBS_TARGETS,
    CONST_TOKEN_URLSAFE,
    POSTGRES_VERSION_BY_ENV,
)


@pytest.mark.parametrize("postgres_target", ALL_POSTGRES_DBS_TARGETS)
def test_postgres_connection_success(
    caplog: LogCaptureFixture, postgres_target: config.PostgreSQLBackupTarget
):
    db = PostgreSQL(**postgres_target.dict())
    assert db.db_version == POSTGRES_VERSION_BY_ENV[postgres_target.env_name]
    assert "postgres_connection start postgres connection" == caplog.messages[0]
    assert "run_subprocess finished with status 0" == caplog.messages[2]
    assert f"PostgreSQL {db.db_version}" in caplog.messages[3]
    assert "version" in caplog.messages[3]
    assert "(1 row)" in caplog.messages[3]
    assert "run_subprocess stderr: " == caplog.messages[4]
    assert (
        f"postgres_connection calculated version: {db.db_version}" == caplog.messages[5]
    )


@pytest.mark.parametrize("postgres_target", ALL_POSTGRES_DBS_TARGETS)
def test_postgres_connection_fail(
    caplog: LogCaptureFixture,
    postgres_target: config.PostgreSQLBackupTarget,
    monkeypatch: MonkeyPatch,
):
    with pytest.raises(SystemExit) as system_exit:
        # simulate not existing db port 9999 and connection err
        monkeypatch.setattr(postgres_target, "port", 9999)
        PostgreSQL(**postgres_target.dict())
    assert system_exit.type == SystemExit
    assert system_exit.value.code == 1
    assert "postgres_connection start postgres connection" == caplog.messages[0]
    assert (
        f"run_subprocess running: 'psql -U postgres -p 9999 -h {postgres_target.host} postgres -w --command 'SELECT version();''"
        == caplog.messages[1]
    )
    assert "run_subprocess failed with status 2" == caplog.messages[2]
    assert "run_subprocess stdout: " == caplog.messages[3]
    assert "port 9999 failed: Connection refused" in caplog.messages[4]
    assert (
        "Is the server running on that host and accepting TCP/IP connections?"
        in caplog.messages[4]
    )
    assert "" == caplog.messages[5]
    assert (
        "postgres_connection unable to connect to database, exiting"
        == caplog.messages[6]
    )


@freeze_time("2022-12-11")
@pytest.mark.parametrize("postgres_target", ALL_POSTGRES_DBS_TARGETS)
def test_run_pg_dump(
    caplog: LogCaptureFixture, postgres_target: config.PostgreSQLBackupTarget
):
    db = PostgreSQL(**postgres_target.dict())
    out_backup = db._backup()
    out_file = (
        f"{db.env_name}/20221211_0000_postgres_{db.db_version}_{CONST_TOKEN_URLSAFE}"
    )
    out_path = config.CONST_BACKUP_FOLDER_PATH / out_file

    assert "postgres_connection start postgres connection" == caplog.messages[0]
    assert "run_subprocess finished with status 0" == caplog.messages[2]
    assert f"PostgreSQL {db.db_version}" in caplog.messages[3]
    assert "version" in caplog.messages[3]
    assert "(1 row)" in caplog.messages[3]
    assert "run_subprocess stderr: " == caplog.messages[4]
    assert (
        f"postgres_connection calculated version: {db.db_version}" == caplog.messages[5]
    )
    assert (
        f"start pg_dump in subprocess: pg_dump -v -O -Fc -U postgres -p {db.port} -h {db.host} postgres -f {out_path}"
        == caplog.messages[6]
    )
    assert (
        f"run_subprocess running: 'pg_dump -v -O -Fc -U postgres -p {db.port} -h {db.host} postgres -f {out_path}'"
        == caplog.messages[7]
    )
    assert "run_subprocess finished with status 0" == caplog.messages[8]
    assert "run_subprocess stdout: " == caplog.messages[9]
    assert "pg_dump: reading extensions" in caplog.messages[10], caplog.messages[10]
    assert f"finished pg_dump, output: {out_path}" == caplog.messages[11]
    assert out_backup == out_path
