import sys
import threading
import time
from pathlib import Path
from unittest.mock import Mock

import google.cloud.storage as storage
import pytest

from backuper import config, core, main, notifications

from .conftest import FILE_1, FOLDER_1, MARIADB_1011, MYSQL_80, POSTGRES_15


@pytest.fixture(autouse=True)
def mock_google_storage_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(storage, "Client", Mock())


def test_backup_targets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        core,
        "create_target_models",
        Mock(return_value=[POSTGRES_15, MYSQL_80, MARIADB_1011, FILE_1, FOLDER_1]),
    )
    targets = main.backup_targets()
    assert len(targets) == 5


def test_empty_backup_targets_raise_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        core,
        "create_target_models",
        Mock(return_value=[]),
    )
    with pytest.raises(RuntimeError):
        main.backup_targets()


def test_backup_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        config,
        "BACKUP_PROVIDER",
        "name=gcs bucket_name=name bucket_upload_path=test service_account_base64=Z29vZ2xlX3NlcnZpY2VfYWNjb3VudAo=",
    )
    provider = main.backup_provider()
    assert provider.NAME == "gcs"


def test_shutdown_gracefully(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "SIGTERM_TIMEOUT_SECS", 0.01)
    with pytest.raises(SystemExit) as system_exit:
        main.shutdown()
    assert system_exit.type == SystemExit
    assert system_exit.value.code == 0


def test_shutdown_not_gracefully(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "SIGTERM_TIMEOUT_SECS", 0.01)

    def sleep_005() -> None:
        time.sleep(0.05)

    dt = threading.Thread(target=sleep_005, daemon=True)
    dt.start()
    dt2 = threading.Thread(target=sleep_005, daemon=True)
    dt2.start()
    with pytest.raises(SystemExit) as system_exit:
        main.shutdown()
    assert system_exit.type == SystemExit
    assert system_exit.value.code == 1
    dt.join()
    dt2.join()


def test_shutdown_gracefully_with_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "SIGTERM_TIMEOUT_SECS", 0.1)

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
    monkeypatch.setattr(config, "BACKUP_PROVIDER", "name=debug")
    monkeypatch.setattr(
        core,
        "create_target_models",
        Mock(return_value=[POSTGRES_15, MYSQL_80, MARIADB_1011, FILE_1, FOLDER_1]),
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
        core,
        "create_target_models",
        Mock(return_value=[POSTGRES_15]),
    )
    target = main.backup_targets()[0]
    monkeypatch.setattr(target, "_backup", Mock(side_effect=ValueError()))
    provider_mock = Mock()
    provider_mock.NAME = "xxx"
    send_fail_message_mock = Mock(return_value=None)
    monkeypatch.setattr(notifications, "send_fail_message", send_fail_message_mock)
    main.run_backup(target=target, provider=provider_mock)
    send_fail_message_mock.assert_called_once_with(
        reason=notifications.FAIL_REASON.BACKUP_CREATE,
        env_name=target.env_name,
        provider_name="xxx",
        backup_file=None,
    )


def test_run_backup_fail_message_when_upload_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        core,
        "create_target_models",
        Mock(return_value=[POSTGRES_15]),
    )
    target = main.backup_targets()[0]
    backup_file = Path("/tmp/fake")
    backup_mock = Mock(return_value=backup_file)
    monkeypatch.setattr(target, "make_backup", backup_mock)
    provider_mock = Mock()
    provider_mock.NAME = "xxx"
    provider_mock.safe_post_save.return_value = None
    send_fail_message_mock = Mock(return_value=None)
    monkeypatch.setattr(notifications, "send_fail_message", send_fail_message_mock)
    main.run_backup(target=target, provider=provider_mock)
    send_fail_message_mock.assert_called_once_with(
        reason=notifications.FAIL_REASON.UPLOAD,
        env_name=target.env_name,
        provider_name="xxx",
        backup_file=backup_file,
    )


def test_quit(monkeypatch: pytest.MonkeyPatch) -> None:
    exit_mock = Mock()
    monkeypatch.setattr(main, "exit_event", exit_mock)
    main.quit(1, None)
    exit_mock.set.assert_called_once()
