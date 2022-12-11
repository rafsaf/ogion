from pathlib import Path

import pytest
from freezegun import freeze_time
from pytest import LogCaptureFixture, MonkeyPatch

from pg_dump import config, core

from .conftest import POSTGRES_VERSION_BY_PORT_AND_HOST


def test_run_subprocess_fail(caplog: LogCaptureFixture):
    with pytest.raises(core.CoreSubprocessError):
        core.run_subprocess("exit 1")
    assert caplog.messages == [
        "run_subprocess running: 'exit 1'",
        "run_subprocess failed with status 1",
        "run_subprocess stdout: ",
        "run_subprocess stderr: ",
    ]


def test_run_subprocess_success(caplog: LogCaptureFixture):
    core.run_subprocess("echo 'welcome'")
    assert caplog.messages == [
        "run_subprocess running: 'echo 'welcome''",
        "run_subprocess finished with status 0",
        "run_subprocess stdout: welcome\n",
        "run_subprocess stderr: ",
    ]


@freeze_time("2022-12-11")
def test_get_new_backup_path(caplog: LogCaptureFixture):
    new_path = core.get_new_backup_path("db_string")

    assert (
        new_path
        == f"{config.BACKUP_FOLDER_PATH}/20221211_0000_postgres_db_string_mocked_random_string"
    )
    assert caplog.messages == []


def test_run_create_zip_archive(tmp_path: Path, caplog: LogCaptureFixture):
    fake_backup_file = tmp_path / "fake_backup.sql"
    fake_backup_file.touch()
    fake_backup_file_path = str(fake_backup_file)
    core.run_create_zip_archive(str(fake_backup_file))
    out = tmp_path / "fake_backup.sql.zip"
    assert out.exists()
    assert (
        caplog.messages[0]
        == f"run_create_zip_archive start in subprocess: {fake_backup_file_path}"
    )
    assert "run_subprocess running:" in caplog.messages[1]
    assert caplog.messages[2] == "run_subprocess finished with status 0"
    assert f"Creating archive: {fake_backup_file_path}.zip" in caplog.messages[3]
    assert "Everything is Ok" in caplog.messages[3]
    assert caplog.messages[4] == "run_subprocess stderr: "
    assert (
        caplog.messages[5]
        == f"run_create_zip_archive finished, output: {fake_backup_file_path}.zip"
    )


@freeze_time("2022-12-11")
def test_run_pg_dump(caplog: LogCaptureFixture):
    core.init_pgpass_file()
    out_backup = core.run_pg_dump("test_version")
    out_path = f"{config.BACKUP_FOLDER_PATH}/20221211_0000_postgres_test_version_mocked_random_string"
    assert (
        f"run_pg_dump start pg_dump in subprocess: pg_dump -v -O -Fc -U postgres -p {config.POSTGRES_PORT} -h {config.POSTGRES_HOST} postgres -f {out_path}"
        == caplog.messages[0]
    )
    assert (
        f"run_subprocess running: 'pg_dump -v -O -Fc -U postgres -p {config.POSTGRES_PORT} -h {config.POSTGRES_HOST} postgres -f {out_path}'"
        == caplog.messages[1]
    )
    assert "run_subprocess finished with status 0" == caplog.messages[2]
    assert "run_subprocess stdout: " == caplog.messages[3]
    assert "pg_dump: reading extensions" in caplog.messages[4]
    assert "pg_dump: reading user-defined tables" in caplog.messages[4]
    assert "pg_dump: saving database definition" in caplog.messages[4]
    assert f"run_pg_dump finished pg_dump, output: {out_path}" == caplog.messages[5]
    assert out_backup == out_path


def test_postgres_connection_success(caplog: LogCaptureFixture):
    core.init_pgpass_file()
    db_version = core.postgres_connection()
    expected_version = POSTGRES_VERSION_BY_PORT_AND_HOST[
        (config.POSTGRES_HOST, config.POSTGRES_PORT)
    ]
    assert db_version == expected_version
    assert "postgres_connection start postgres connection" == caplog.messages[0]
    assert "run_subprocess finished with status 0" == caplog.messages[2]
    assert f"PostgreSQL {expected_version}" in caplog.messages[3]
    assert "version" in caplog.messages[3]
    assert "(1 row)" in caplog.messages[3]
    assert "run_subprocess stderr: " == caplog.messages[4]
    assert (
        f"postgres_connection calculated version: {expected_version}"
        == caplog.messages[5]
    )


def test_postgres_connection_fail_conn(
    caplog: LogCaptureFixture, monkeypatch: MonkeyPatch
):
    # simulate not existing db port 9999 and connection err
    monkeypatch.setattr(config, "POSTGRES_PORT", "9999")
    core.init_pgpass_file()
    with pytest.raises(SystemExit) as system_exit:
        core.postgres_connection()
    assert system_exit.type == SystemExit
    assert system_exit.value.code == 1
    assert "postgres_connection start postgres connection" == caplog.messages[0]
    assert (
        f"run_subprocess running: 'psql -U postgres -p 9999 -h {config.POSTGRES_HOST} postgres -w --command 'SELECT version();''"
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
