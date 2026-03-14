# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import logging
import os
import subprocess
from pathlib import Path, PosixPath
from typing import Any
from unittest.mock import Mock

import pytest
import tenacity
from freezegun import freeze_time
from pydantic import SecretStr
from pytest import LogCaptureFixture

from ogion import config, core


@pytest.mark.parametrize(
    "text,result",
    [
        ("asdjklh", "asdjklh"),
        ("asdjklh#$%^&*(*)", "asdjklh"),
        (":'/\\asdjklh#$%^&*(*)", "asdjklh"),
        (":'/\\asdj&^!!!klh#$%^&*(*)", "asdjklh"),
    ],
)
def test_safe_text_version(text: str, result: str) -> None:
    assert core.safe_text_version(text=text) == result


def test_run_subprocess_fail(caplog: LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(core.CoreSubprocessError):
            core.run_subprocess(["false"])
        assert caplog.messages == [
            "run_subprocess running: 'false'",
            "run_subprocess failed with status 1",
            "run_subprocess stdout: ",
            "run_subprocess stderr: ",
        ]


def test_run_subprocess_success(caplog: LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        core.run_subprocess(["echo", "welcome"])
        assert caplog.messages == [
            "run_subprocess running: 'echo welcome'",
            "run_subprocess finished with status 0",
            "run_subprocess stdout: welcome\n",
            "run_subprocess stderr: ",
        ]


def test_run_subprocess_with_args_list(caplog: LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        result = core.run_subprocess(["echo", "welcome"])

    assert result == "welcome\n"
    assert caplog.messages == [
        "run_subprocess running: 'echo welcome'",
        "run_subprocess finished with status 0",
        "run_subprocess stdout: welcome\n",
        "run_subprocess stderr: ",
    ]


def test_run_subprocess_with_stdin_path(tmp_path: Path) -> None:
    stdin_file = tmp_path / "stdin.txt"
    stdin_file.write_text("welcome")

    result = core.run_subprocess(["cat"], stdin_path=stdin_file)

    assert result == "welcome"


def test_run_subprocess_opens_stdin_path_in_binary_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stdin_file = tmp_path / "stdin.txt"
    stdin_file.write_bytes(b"welcome\xff")

    def mock_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        del args
        assert kwargs["stdin"] is not None
        assert kwargs["stdin"].mode == "rb"
        return subprocess.CompletedProcess([], 0, stdout="ok", stderr="")

    monkeypatch.setattr(core.subprocess, "run", mock_run)

    result = core.run_subprocess(["cat"], stdin_path=stdin_file)

    assert result == "ok"


def test_run_subprocess_missing_executable(caplog: LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(core.CoreSubprocessError, match="No such file or directory"):
            core.run_subprocess(["definitely-not-a-real-command-ogion"])

    assert any(
        message.startswith("run_subprocess executable not found:")
        for message in caplog.messages
    )


def test_run_subprocess_timeout_is_wrapped(
    monkeypatch: pytest.MonkeyPatch, caplog: LogCaptureFixture
) -> None:
    timeout_error = subprocess.TimeoutExpired(
        cmd=["sleep", "1"], timeout=0.01, output="", stderr=""
    )
    run_mock = Mock(side_effect=timeout_error)
    monkeypatch.setattr(core.subprocess, "run", run_mock)

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(core.CoreSubprocessError, match="Command timed out"):
            core.run_subprocess(["sleep", "1"])

    assert "run_subprocess timed out after 0.01 seconds" in caplog.messages


@freeze_time("2022-12-11")
def test_get_new_backup_path() -> None:
    new_path = core.get_new_backup_path("env_name", "db_string")
    expected_file = "env_name/env_name_20221211_0000_db_string_mock"
    expected_path = config.CONST_DATA_FOLDER_PATH / expected_file
    assert str(new_path) == str(expected_path)


def test_run_create_age_archive_out_path_exists(tmp_path: Path) -> None:
    fake_backup_file = tmp_path / "fake_backup"
    with open(fake_backup_file, "w") as f:
        f.write("abcdefghijk\n12345")

    fake_backup_file_out = core.run_create_age_archive(fake_backup_file)
    assert fake_backup_file_out == tmp_path / "fake_backup.lz.age"
    assert fake_backup_file_out.exists()
    # Verify intermediate .lz file was cleaned up
    assert not (tmp_path / "fake_backup.lz").exists()


def test_run_create_age_archive_dir_raise_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        core.run_create_age_archive(tmp_path)


def test_run_lzip_decrypt_not_encrypted(tmp_path: Path) -> None:
    fake_backup_file = tmp_path / "fake_backup"
    fake_backup_file.touch()

    p = core.run_lzip_decrypt(fake_backup_file)
    assert p == fake_backup_file


def test_lzip_works_with_encrypt_and_decrypt(tmp_path: Path) -> None:
    init_fake_backup_file = tmp_path / "fake_backup_file"
    init_fake_backup_file.write_text("something")

    p = core.run_lzip_compression(init_fake_backup_file)

    assert p == init_fake_backup_file.with_suffix(".lz")
    assert p.exists()
    init_fake_backup_file.unlink()

    fake_backup_file = core.run_lzip_decrypt(p)
    assert fake_backup_file == init_fake_backup_file
    assert fake_backup_file.exists()
    assert fake_backup_file.read_text() == "something"


def test_lzip_compression_with_threads_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config.options, "LZIP_THREADS", None)
    monkeypatch.setattr(config.options, "LZIP_LEVEL", 0)

    init_fake_backup_file = tmp_path / "fake_backup_file"
    init_fake_backup_file.write_text("test data")

    run_subprocess_mock = Mock(return_value="")
    monkeypatch.setattr(core, "run_subprocess", run_subprocess_mock)
    size_mock = Mock(return_value="0.0 MB")
    monkeypatch.setattr(core, "size", size_mock)

    result = core.run_lzip_compression(init_fake_backup_file)

    run_subprocess_mock.assert_called_once()
    called_command = run_subprocess_mock.call_args[0][0]
    assert "-n" not in called_command
    expected = [
        "plzip",
        "-0",
        "-o",
        str(tmp_path / "fake_backup_file.lz"),
        str(init_fake_backup_file),
    ]
    assert expected == called_command
    assert result == tmp_path / "fake_backup_file.lz"


def test_lzip_compression_with_threads_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config.options, "LZIP_THREADS", 4)
    monkeypatch.setattr(config.options, "LZIP_LEVEL", 0)

    init_fake_backup_file = tmp_path / "fake_backup_file"
    init_fake_backup_file.write_text("test data")

    run_subprocess_mock = Mock(return_value="")
    monkeypatch.setattr(core, "run_subprocess", run_subprocess_mock)
    size_mock = Mock(return_value="0.0 MB")
    monkeypatch.setattr(core, "size", size_mock)

    result = core.run_lzip_compression(init_fake_backup_file)

    run_subprocess_mock.assert_called_once()
    called_command = run_subprocess_mock.call_args[0][0]
    assert called_command[2:4] == ["-n", "4"]
    expected = [
        "plzip",
        "-0",
        "-n",
        "4",
        "-o",
        str(tmp_path / "fake_backup_file.lz"),
        str(init_fake_backup_file),
    ]
    assert expected == called_command
    assert result == tmp_path / "fake_backup_file.lz"


def test_lzip_decompression_with_threads_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config.options, "LZIP_THREADS", None)

    fake_backup_file = tmp_path / "fake_backup_file.lz"
    fake_backup_file.write_text("compressed data")

    run_subprocess_mock = Mock(return_value="")
    monkeypatch.setattr(core, "run_subprocess", run_subprocess_mock)
    size_mock = Mock(return_value="0.0 MB")
    monkeypatch.setattr(core, "size", size_mock)

    result = core.run_lzip_decrypt(fake_backup_file)

    run_subprocess_mock.assert_called_once()
    called_command = run_subprocess_mock.call_args[0][0]
    assert "-n" not in called_command
    expected = [
        "plzip",
        "-d",
        "-o",
        str(tmp_path / "fake_backup_file"),
        str(fake_backup_file),
    ]
    assert expected == called_command
    assert result == tmp_path / "fake_backup_file"


def test_lzip_decompression_with_threads_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config.options, "LZIP_THREADS", 8)

    fake_backup_file = tmp_path / "fake_backup_file.lz"
    fake_backup_file.write_text("compressed data")

    run_subprocess_mock = Mock(return_value="")
    monkeypatch.setattr(core, "run_subprocess", run_subprocess_mock)
    size_mock = Mock(return_value="0.0 MB")
    monkeypatch.setattr(core, "size", size_mock)

    result = core.run_lzip_decrypt(fake_backup_file)

    run_subprocess_mock.assert_called_once()
    called_command = run_subprocess_mock.call_args[0][0]
    assert called_command[2:4] == ["-n", "8"]
    expected = [
        "plzip",
        "-d",
        "-n",
        "8",
        "-o",
        str(tmp_path / "fake_backup_file"),
        str(fake_backup_file),
    ]
    assert expected == called_command
    assert result == tmp_path / "fake_backup_file"


def test_get_safe_download_path() -> None:
    path = core.get_safe_download_path("folder/backup.lz.age")

    assert path == config.CONST_DOWNLOADS_FOLDER_PATH / "folder/backup.lz.age"


@pytest.mark.parametrize("path", ["", "../backup", "folder/../backup", "./x"])
def test_get_safe_download_path_rejects_unsafe_paths(path: str) -> None:
    with pytest.raises(ValueError):
        core.get_safe_download_path(path)


def test_get_safe_debug_download_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    debug_root = tmp_path / "debug"
    debug_root.mkdir()
    monkeypatch.setattr(config, "CONST_DEBUG_FOLDER_PATH", debug_root)

    source = debug_root / "env" / "backup.lz.age"
    source.parent.mkdir()
    source.touch()

    safe_source, safe_destination = core.get_safe_debug_download_paths(str(source))

    assert safe_source == source
    assert safe_destination == config.CONST_DOWNLOADS_FOLDER_PATH / str(
        source
    ).removeprefix("/")


def test_get_safe_debug_download_paths_rejects_outside_paths(tmp_path: Path) -> None:
    outside = tmp_path / "outside.lz.age"
    outside.touch()

    with pytest.raises(ValueError):
        core.get_safe_debug_download_paths(str(outside))


def test_retry_on_network_errors_only_retries_network_errors() -> None:
    expected_network_attempts = 2
    expected_non_network_attempts = 1
    attempts_network = 0
    attempts_non_network = 0

    def no_sleep(seconds: float) -> None:
        del seconds

    retry_network = core.retry_on_network_errors(expected_network_attempts)
    retry_non_network = core.retry_on_network_errors(expected_network_attempts)

    @retry_network
    def fail_network() -> None:
        nonlocal attempts_network
        attempts_network += 1
        raise core.CoreSubprocessError("Connection refused")

    @retry_non_network
    def fail_non_network() -> None:
        nonlocal attempts_non_network
        attempts_non_network += 1
        raise core.CoreSubprocessError("permission denied")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(tenacity.nap, "sleep", no_sleep)

        with pytest.raises(core.CoreSubprocessError):
            fail_network()

        with pytest.raises(core.CoreSubprocessError):
            fail_non_network()

    assert attempts_network == expected_network_attempts
    assert attempts_non_network == expected_non_network_attempts


def test_run_create_age_archive_can_be_decrypted(
    tmp_path: Path,
) -> None:
    fake_backup_file = tmp_path / "test_archive"

    with open(fake_backup_file, "w") as f:
        f.write("xxxąć”©#$%")

    archive_file = core.run_create_age_archive(fake_backup_file)
    fake_backup_file.unlink()

    fake_backup_file = core.run_decrypt_age_archive(archive_file)

    assert fake_backup_file.exists()
    assert fake_backup_file.read_text() == "xxxąć”©#$%"


test_data = [
    (
        [
            (
                "POSTGRESQL_FIRST_DB",
                "host=localhost port=5432 password=secret cron_rule=* * * * *",
            ),
        ],
        True,
        [
            {
                "cron_rule": "* * * * *",
                "db": "postgres",
                "env_name": "postgresql_first_db",
                "host": "localhost",
                "max_backups": config.options.BACKUP_MAX_NUMBER,
                "min_retention_days": config.options.BACKUP_MIN_RETENTION_DAYS,
                "name": config.BackupTargetEnum.POSTGRESQL,
                "password": SecretStr("secret"),
                "port": 5432,
                "user": "postgres",
            },
        ],
    ),
    (
        [
            (
                "POSTGRESQL_FIRST_OF_TWO_DB",
                "host=localhost port=5432 password=secret cron_rule=* * * * *",
            ),
            (
                "MARIADB_SECOND_OF_TWO_DB",
                "host=localhost port=3306 password=secret cron_rule=* * * * *",
            ),
        ],
        True,
        [
            {
                "cron_rule": "* * * * *",
                "db": "postgres",
                "env_name": "postgresql_first_of_two_db",
                "host": "localhost",
                "max_backups": config.options.BACKUP_MAX_NUMBER,
                "min_retention_days": config.options.BACKUP_MIN_RETENTION_DAYS,
                "name": config.BackupTargetEnum.POSTGRESQL,
                "password": SecretStr("secret"),
                "port": 5432,
                "user": "postgres",
            },
            {
                "cron_rule": "* * * * *",
                "db": "mariadb",
                "env_name": "mariadb_second_of_two_db",
                "host": "localhost",
                "max_backups": config.options.BACKUP_MAX_NUMBER,
                "min_retention_days": config.options.BACKUP_MIN_RETENTION_DAYS,
                "name": config.BackupTargetEnum.MARIADB,
                "password": SecretStr("secret"),
                "port": 3306,
                "user": "root",
            },
        ],
    ),
    (
        [
            (
                "MARIADB_THIRD_DB",
                "host=192.168.1.5 port=3308 user=root password=change_me_please! "
                "db=project cron_rule=15 */3 * * * max_backups=15 min_retention_days=5",
            )
        ],
        True,
        [
            {
                "cron_rule": "15 */3 * * *",
                "db": "project",
                "env_name": "mariadb_third_db",
                "host": "192.168.1.5",
                "max_backups": 15,
                "min_retention_days": 5,
                "name": config.BackupTargetEnum.MARIADB,
                "password": SecretStr("change_me_please!"),
                "port": 3308,
                "user": "root",
            },
        ],
    ),
    (
        [
            (
                "SINGLEFILE_THIRD",
                f"abs_path={Path(__file__)} cron_rule=15 */3 * * * max_backups=20",
            )
        ],
        True,
        [
            {
                "abs_path": PosixPath(Path(__file__)),
                "cron_rule": "15 */3 * * *",
                "env_name": "singlefile_third",
                "max_backups": 20,
                "min_retention_days": config.options.BACKUP_MIN_RETENTION_DAYS,
                "name": config.BackupTargetEnum.FILE,
            },
        ],
    ),
    (
        [
            (
                "DIRECTORY_FIRST",
                f"abs_path={Path(__file__).parent} cron_rule=15 */3 * * * "
                "max_backups=20",
            )
        ],
        True,
        [
            {
                "abs_path": PosixPath(Path(__file__).parent),
                "cron_rule": "15 */3 * * *",
                "env_name": "directory_first",
                "max_backups": 20,
                "min_retention_days": config.options.BACKUP_MIN_RETENTION_DAYS,
                "name": config.BackupTargetEnum.FOLDER,
            },
        ],
    ),
    (
        [
            (
                "POSTGRESQL_FIRST_DB",
                "host=localhostport=5432 password=secret cron_rule=* * * * *",
            ),
        ],
        True,
        [
            {
                "cron_rule": "* * * * *",
                "db": "postgres",
                "env_name": "postgresql_first_db",
                "host": "localhostport=5432",
                "max_backups": config.options.BACKUP_MAX_NUMBER,
                "min_retention_days": config.options.BACKUP_MIN_RETENTION_DAYS,
                "name": config.BackupTargetEnum.POSTGRESQL,
                "password": SecretStr("secret"),
                "port": 5432,
                "user": "postgres",
            },
        ],
    ),
    (
        [
            (
                "POSTGRESQL_FIRST_DB",
                "host=localhost port=axxx password=secret cron_rule=* * * * *",
            ),
        ],
        False,
        [],
    ),
    (
        [
            (
                "POSTGRESQL_FIRST_DB",
                "host=localhost port=111 passwor=secret cron_rule=* * * * *",
            ),
        ],
        False,
        [],
    ),
    (
        [
            (
                "POSTGRESQL_FIRST_DB",
                "host=localhost port=111 password=secret cron_rule=* ** * *",
            ),
        ],
        False,
        [],
    ),
    (
        [
            (
                "POSTGRESQL_FIRST_DB",
                "host=localhost port=5432 password=secretcron_rule=* * * * *",
            ),
        ],
        False,
        [],
    ),
    (
        [
            (
                "POSTGRESQL_FIRST_DB",
                "garbage host=localhost port=5432 password=secret cron_rule=* * * * *",
            ),
        ],
        False,
        [],
    ),
    (
        [
            (
                "POSTGRESQL_FIRST_DB",
                "host=localhost host=127.0.0.1 port=5432 "
                "password=secret cron_rule=* * * * *",
            ),
        ],
        False,
        [],
    ),
    (
        [
            (
                "POSTGRESQL_FIRST_DB",
                "host=localhost port5432 password=secret cron_rule=* * * * *",
            ),
        ],
        True,
        [
            {
                "cron_rule": "* * * * *",
                "db": "postgres",
                "env_name": "postgresql_first_db",
                "host": "localhost port5432",
                "max_backups": config.options.BACKUP_MAX_NUMBER,
                "min_retention_days": config.options.BACKUP_MIN_RETENTION_DAYS,
                "name": config.BackupTargetEnum.POSTGRESQL,
                "password": SecretStr("secret"),
                "port": 5432,
                "user": "postgres",
            },
        ],
    ),
    (
        [
            (
                "POSTGRESQL_FIRST_DB",
                "host=localhost port5432 password=secret "
                "cron_rule=* * * * * ssl_mode=require",
            ),
        ],
        True,
        [
            {
                "cron_rule": "* * * * *",
                "db": "postgres",
                "env_name": "postgresql_first_db",
                "host": "localhost port5432",
                "max_backups": config.options.BACKUP_MAX_NUMBER,
                "min_retention_days": config.options.BACKUP_MIN_RETENTION_DAYS,
                "name": config.BackupTargetEnum.POSTGRESQL,
                "password": SecretStr("secret"),
                "port": 5432,
                "ssl_mode": "require",
                "user": "postgres",
            },
        ],
    ),
    (
        [
            (
                "MARIADB_DB",
                "host=localhost client_skip-ssl=true client_ssl=false port=12011 "
                "client_tee=name password=password cron_rule=* * * * * "
                "client_ssl-verify-server-cert=true",
            ),
        ],
        True,
        [
            {
                "client_skip-ssl": "true",
                "client_ssl": "false",
                "client_ssl-verify-server-cert": "true",
                "client_tee": "name",
                "cron_rule": "* * * * *",
                "db": "mariadb",
                "env_name": "mariadb_db",
                "host": "localhost",
                "max_backups": config.options.BACKUP_MAX_NUMBER,
                "min_retention_days": config.options.BACKUP_MIN_RETENTION_DAYS,
                "name": config.BackupTargetEnum.MARIADB,
                "password": SecretStr("password"),
                "port": 12011,
                "user": "root",
            },
        ],
    ),
]


@pytest.mark.parametrize("env_lst,valid,result_lst", test_data)
def test_create_backup_targets(
    env_lst: list[tuple[str, str]],
    valid: bool,
    result_lst: list[dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    items_mock = Mock(return_value=env_lst)
    monkeypatch.setattr(os.environ, "items", items_mock)
    if valid:
        targets = core.create_target_models()

        assert [target.model_dump() for target in targets] == result_lst
    else:
        with pytest.raises(Exception):
            core.create_target_models()


def test_create_backup_targets_ignores_non_delimited_prefixes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    items_mock = Mock(
        return_value=[
            (
                "POSTGRESQLISH_DB",
                "host=localhost port=5432 password=secret cron_rule=* * * * *",
            )
        ]
    )
    monkeypatch.setattr(os.environ, "items", items_mock)

    assert core.create_target_models() == []


def test_create_provider_model() -> None:
    provider = core.create_provider_model()

    assert provider.model_dump() == {
        "name": config.UploadProviderEnum.LOCAL_FILES_DEBUG
    }


def test_create_provider_model_does_not_log_provider_secrets(
    monkeypatch: pytest.MonkeyPatch, caplog: LogCaptureFixture
) -> None:
    provider_config = (
        "name=s3 bucket_name=test bucket_upload_path=backups "
        "access_key=user secret_key=supersecret"
    )
    monkeypatch.setattr(config.options, "BACKUP_PROVIDER", provider_config)

    with caplog.at_level(logging.DEBUG):
        provider = core.create_provider_model()

    assert provider.name == config.UploadProviderEnum.S3
    assert "supersecret" not in "\n".join(caplog.messages)


@pytest.mark.parametrize(
    "provider_config",
    [
        "debug",
        "garbage name=debug",
        "name=debug name=debug",
    ],
)
def test_create_provider_model_invalid_config(
    provider_config: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config.options, "BACKUP_PROVIDER", provider_config)

    with pytest.raises(Exception):
        core.create_provider_model()


def test_remove_path_file_exists(tmp_path: Path) -> None:
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("test content")
    assert test_file.exists()

    core.remove_path(test_file)
    assert not test_file.exists()


def test_remove_path_file_not_found(tmp_path: Path) -> None:
    """Test that remove_path handles FileNotFoundError gracefully."""
    non_existent_file = tmp_path / "non_existent_file.txt"
    assert not non_existent_file.exists()

    # Should not raise an exception
    core.remove_path(non_existent_file)
    assert not non_existent_file.exists()


@freeze_time("2026-03-14 12:00:00")
def test_file_before_retention_period_ends() -> None:
    assert core.file_before_retention_period_ends(
        "backup_20260314_1159_payload_token.lz.age", min_retention_days=1
    )


@freeze_time("2026-03-14 12:00:00")
def test_file_before_retention_period_ends_uses_file_name_only() -> None:
    assert not core.file_before_retention_period_ends(
        "/tmp/20200101_0000/backup_20260313_1100_payload_token.lz.age",
        min_retention_days=0,
    )


def test_file_before_retention_period_ends_rejects_ambiguous_datetime() -> None:
    with pytest.raises(ValueError, match="expected exactly one datetime segment"):
        core.file_before_retention_period_ends(
            "backup_20260314_1200_payload_20260315_1201_token.lz.age",
            min_retention_days=1,
        )


@pytest.mark.parametrize(
    "exception,expected",
    [
        (core.CoreSubprocessError("Temporary failure in name resolution"), True),
        (core.CoreSubprocessError("Can't connect to server on 'host' (115)"), True),
        (core.CoreSubprocessError("Connection refused"), True),
        (core.CoreSubprocessError("Network is unreachable"), True),
        (core.CoreSubprocessError("Host is unreachable"), True),
        (core.CoreSubprocessError("Timeout occurred"), True),
        (core.CoreSubprocessError("Some other error"), False),
        (ValueError("Temporary failure in name resolution"), False),
        (RuntimeError("Can't connect to server"), False),
        (Exception("Network is unreachable"), False),
    ],
)
def test_is_network_error(exception: Exception, expected: bool) -> None:
    assert core.is_network_error(exception) == expected
