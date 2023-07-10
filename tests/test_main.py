import sys
import threading
import time
from unittest.mock import Mock

import google.cloud.storage as storage
import pytest

from backuper import config, notifications, main

from .conftest import FILE_1, FOLDER_1, MARIADB_1011, MYSQL_80, POSTGRES_15


@pytest.fixture(autouse=True)
def mock_google_storage_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(storage, "Client", Mock())


def test_backup_targets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        config,
        "BACKUP_TARGETS",
        [POSTGRES_15, MYSQL_80, MARIADB_1011, FILE_1, FOLDER_1],
    )
    targets = main.backup_targets()
    assert len(targets) == 5


def test_backup_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "BACKUP_PROVIDER", "gcs")
    provider = main.backup_provider()
    assert provider.NAME == "gcs"


def test_shutdown_gracefully(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "BACKUPER_SIGTERM_TIMEOUT_SECS", 0.01)
    with pytest.raises(SystemExit) as system_exit:
        main.shutdown()
    assert system_exit.type == SystemExit
    assert system_exit.value.code == 0


def test_shutdown_not_gracefully(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "BACKUPER_SIGTERM_TIMEOUT_SECS", 0.01)

    def sleep_005() -> None:
        time.sleep(0.05)

    dt = threading.Thread(target=sleep_005, daemon=True)
    dt.start()
    with pytest.raises(SystemExit) as system_exit:
        main.shutdown()
    assert system_exit.type == SystemExit
    assert system_exit.value.code == 1
    dt.join()


def test_shutdown_gracefully_with_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "BACKUPER_SIGTERM_TIMEOUT_SECS", 0.1)

    def sleep_005() -> None:
        time.sleep(0.05)

    dt = threading.Thread(target=sleep_005, daemon=True)
    dt.start()
    with pytest.raises(SystemExit) as system_exit:
        main.shutdown()
    assert system_exit.type == SystemExit
    assert system_exit.value.code == 0
    dt.join()


def test_main(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["main.py", "--single"])
    monkeypatch.setattr(config, "BACKUP_PROVIDER", "local")
    monkeypatch.setattr(
        config,
        "BACKUP_TARGETS",
        [POSTGRES_15, MYSQL_80, MARIADB_1011, FILE_1, FOLDER_1],
    )
    with pytest.raises(SystemExit) as system_exit:
        main.main()
    assert system_exit.type == SystemExit
    assert system_exit.value.code == 0

    target_envs = [
        "postgresql_db_15",
        "mysql_db_80",
        "mariadb_1011",
        "singlefile_1",
        "directory_1",
    ]
    count = 0
    for dir in config.CONST_BACKUP_FOLDER_PATH.iterdir():
        assert dir.is_dir()
        assert dir.name in target_envs
        count += 1
    assert count == 5


def test_run_backup_fail_message_when_no_backup_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        config,
        "BACKUP_TARGETS",
        [POSTGRES_15],
    )
    target = main.backup_targets()[0]
    target._backup = Mock(side_effect=ValueError())
    provider_mock = Mock()
    send_fail_message_mock = Mock(return_value=None)
    monkeypatch.setattr(notifications, "send_fail_message", send_fail_message_mock)
    assert main.run_backup(target=target, provider=provider_mock) is None
    send_fail_message_mock.assert_called_once()


def test_quit(monkeypatch: pytest.MonkeyPatch):
    exit_mock = Mock()
    monkeypatch.setattr(main, "exit_event", exit_mock)
    assert main.quit(1, None) is None
    exit_mock.set.assert_called_once()
