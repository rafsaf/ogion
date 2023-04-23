from pathlib import Path

import pytest
from freezegun import freeze_time
from pytest import LogCaptureFixture

from backuper import config, core


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
    new_path = core.get_new_backup_path("env_name", "db_string")
    expected_file = "env_name/20221211_0000_db_string_mock"
    expected_path = config.CONST_BACKUP_FOLDER_PATH / expected_file
    assert str(new_path) == str(expected_path)
    assert caplog.messages == []


def test_run_create_zip_archive(tmp_path: Path, caplog: LogCaptureFixture):
    fake_backup_file = tmp_path / "fake_backup"
    with open(fake_backup_file, "w") as f:
        f.write("abcdefghijk\n12345")

    fake_backup_file_out = core.run_create_zip_archive(fake_backup_file)
    assert fake_backup_file_out == tmp_path / "fake_backup.zip"
    assert fake_backup_file_out.exists()
    assert (
        caplog.messages[0]
        == f"run_create_zip_archive start creating in subprocess: {fake_backup_file}"
    )
    assert "run_subprocess running:" in caplog.messages[1]
    assert caplog.messages[2] == "run_subprocess finished with status 0"
    assert f"Creating archive: {fake_backup_file}.zip" in caplog.messages[3]
    assert "Everything is Ok" in caplog.messages[3]
    assert caplog.messages[4] == "run_subprocess stderr: "
    assert (
        caplog.messages[5]
        == f"run_create_zip_archive finished, output: {fake_backup_file_out}"
    )
    assert (
        caplog.messages[6]
        == f"run_create_zip_archive start integriy test in subprocess: {fake_backup_file_out}"
    )
    assert "run_subprocess running:" in caplog.messages[7]
    assert "run_subprocess finished with status 0" in caplog.messages[8]
    assert f"Testing archive: {fake_backup_file_out}" in caplog.messages[9]
    assert "Everything is Ok" in caplog.messages[9]
    assert "run_subprocess stderr:" in caplog.messages[10]
    assert (
        f"run_create_zip_archive finish integriy test in subprocess: {fake_backup_file_out}"
        == caplog.messages[11]
    )
