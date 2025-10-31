# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import argparse
import sys
import threading
import time
from pathlib import Path
from typing import Any, NoReturn
from unittest.mock import Mock

import google.cloud.storage as cloud_storage
import pytest

from ogion import config, core, main
from ogion.models import upload_provider_models
from ogion.notifications.notifications_context import NotificationsContext
from ogion.upload_providers.debug import UploadProviderLocalDebug
from ogion.upload_providers.google_cloud_storage import UploadProviderGCS

from .conftest import (
    ALL_MARIADB_DBS_TARGETS,
    ALL_MYSQL_DBS_TARGETS,
    ALL_POSTGRES_DBS_TARGETS,
    FILE_1,
    FOLDER_1,
)

SECONDS_TIMEOUT = 10


@pytest.fixture(autouse=True)
def mock_google_storage_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cloud_storage, "Client", Mock())


def test_backup_targets(monkeypatch: pytest.MonkeyPatch) -> None:
    models = (
        ALL_MARIADB_DBS_TARGETS
        + ALL_MYSQL_DBS_TARGETS
        + ALL_POSTGRES_DBS_TARGETS
        + [FILE_1, FOLDER_1]
    )
    monkeypatch.setattr(
        core,
        "create_target_models",
        Mock(return_value=models),
    )
    targets = main.backup_targets()
    assert len(targets) == len(models)


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
        config.options,
        "BACKUP_PROVIDER",
        "name=gcs bucket_name=name bucket_upload_path=test "
        "service_account_base64=Z29vZ2xlX3NlcnZpY2VfYWNjb3VudAo=",
    )
    provider = main.backup_provider()
    assert provider.__class__.__name__ == UploadProviderGCS.__name__


def test_main_single(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["main.py", "--single"])
    monkeypatch.setattr(config.options, "BACKUP_PROVIDER", "name=debug")

    def dummy_shutdown() -> NoReturn:
        sys.exit(0)

    monkeypatch.setattr(main, "shutdown", dummy_shutdown)
    models = (
        ALL_MARIADB_DBS_TARGETS
        + ALL_MYSQL_DBS_TARGETS
        + ALL_POSTGRES_DBS_TARGETS
        + [FILE_1, FOLDER_1]
    )
    monkeypatch.setattr(
        core,
        "create_target_models",
        Mock(return_value=models),
    )
    with pytest.raises(SystemExit) as system_exit:
        main.main()
    assert system_exit.type is SystemExit

    target_envs = [model.env_name for model in models]
    count = 0

    timeout: float = 0
    while threading.active_count() > 1 and timeout < SECONDS_TIMEOUT:
        timeout += 0.05
        time.sleep(0.05)

    for dir in config.CONST_DEBUG_FOLDER_PATH.iterdir():
        assert dir.is_dir(), dir
        assert dir.name in target_envs, dir
        assert sum(1 for _ in dir.glob("*.lz.age")) == 1, dir

        count += 1
    assert count == len(target_envs)


def test_main_single_with_target(monkeypatch: pytest.MonkeyPatch) -> None:
    target_name = ALL_POSTGRES_DBS_TARGETS[0].env_name
    monkeypatch.setattr(sys, "argv", ["main.py", "--single", "--target", target_name])
    monkeypatch.setattr(config.options, "BACKUP_PROVIDER", "name=debug")

    def dummy_shutdown() -> NoReturn:
        sys.exit(0)

    monkeypatch.setattr(main, "shutdown", dummy_shutdown)
    models = (
        ALL_MARIADB_DBS_TARGETS
        + ALL_MYSQL_DBS_TARGETS
        + ALL_POSTGRES_DBS_TARGETS
        + [FILE_1, FOLDER_1]
    )
    monkeypatch.setattr(
        core,
        "create_target_models",
        Mock(return_value=models),
    )
    with pytest.raises(SystemExit) as system_exit:
        main.main()
    assert system_exit.type is SystemExit

    timeout: float = 0
    while threading.active_count() > 1 and timeout < SECONDS_TIMEOUT:
        timeout += 0.05
        time.sleep(0.05)

    # Only the specified target should have been backed up
    backup_count = 0
    for dir in config.CONST_DEBUG_FOLDER_PATH.iterdir():
        if dir.is_dir() and dir.name == target_name.lower():
            assert sum(1 for _ in dir.glob("*.lz.age")) == 1, dir
            backup_count += 1
    assert backup_count == 1


def test_main_single_with_nonexistent_target(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["main.py", "--single", "--target", "nonexistent"])
    monkeypatch.setattr(config.options, "BACKUP_PROVIDER", "name=debug")

    models = (
        ALL_MARIADB_DBS_TARGETS
        + ALL_MYSQL_DBS_TARGETS
        + ALL_POSTGRES_DBS_TARGETS
        + [FILE_1, FOLDER_1]
    )
    monkeypatch.setattr(
        core,
        "create_target_models",
        Mock(return_value=models),
    )
    with pytest.raises(SystemExit) as system_exit:
        main.main()
    assert system_exit.value.code == 1


def test_main_debug_notifications(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["main.py", "--debug-notifications"])

    with pytest.raises(SystemExit) as system_exit:
        main.main()
    assert system_exit.type is SystemExit


@pytest.mark.parametrize(
    "make_backup_side_effect,post_save_side_effect,clean_side_effect",
    [
        (ValueError(), None, None),
        (None, ValueError(), None),
        (None, None, ValueError()),
    ],
)
def test_run_backup_notifications_fail_message_is_fired_when_it_fails(
    make_backup_side_effect: Any | None,
    post_save_side_effect: Any | None,
    clean_side_effect: Any | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fail_message_mock = Mock()
    monkeypatch.setattr(NotificationsContext, "create_fail_message", fail_message_mock)
    monkeypatch.setattr(
        core,
        "create_target_models",
        Mock(return_value=[ALL_POSTGRES_DBS_TARGETS[0]]),
    )
    target = main.backup_targets()[0]
    backup_file = Path("/tmp/fake")
    backup_mock = Mock(return_value=backup_file, side_effect=make_backup_side_effect)
    monkeypatch.setattr(target, "backup", backup_mock)
    provider = UploadProviderLocalDebug(upload_provider_models.DebugProviderModel())
    monkeypatch.setattr(provider, "post_save", Mock(side_effect=post_save_side_effect))
    monkeypatch.setattr(provider, "clean", Mock(side_effect=clean_side_effect))
    monkeypatch.setattr(main, "backup_provider", Mock(return_value=provider))

    with pytest.raises(ValueError):
        main.run_backup(target=target)
    fail_message_mock.assert_called_once()


def test_quit(monkeypatch: pytest.MonkeyPatch) -> None:
    exit_mock = Mock()
    monkeypatch.setattr(main, "exit_event", exit_mock)
    main.quit(1, None)
    exit_mock.set.assert_called_once()


@pytest.mark.parametrize(
    "cli_args,expected_attributes",
    [
        (["main.py", "--single"], {"single": True}),
        (
            ["main.py", "--single", "--target", "mytarget"],
            {"single": True, "target": "mytarget"},
        ),
        (["main.py", "--debug-notifications"], {"debug_notifications": True}),
        (
            ["main.py", "--debug-download", "example.log"],
            {"debug_download": "example.log"},
        ),
        (
            ["main.py", "--target", "example_target", "--list"],
            {"target": "example_target", "list": True},
        ),
        (
            ["main.py", "--target", "example_target", "--restore-latest"],
            {"target": "example_target", "restore_latest": True},
        ),
        (["main.py", "--target", "example_target"], {"target": "example_target"}),
        (
            ["main.py", "--target", "example_target", "--restore", "example_restore"],
            {"restore": "example_restore", "target": "example_target"},
        ),
    ],
)
def test_setup_runtime_arguments_parametrized(
    monkeypatch: pytest.MonkeyPatch,
    cli_args: list[str],
    expected_attributes: dict[str, bool | str],
) -> None:
    monkeypatch.setattr("sys.argv", cli_args)

    args: main.RuntimeArgs = main.setup_runtime_arguments()

    assert isinstance(args, main.RuntimeArgs)

    for attribute, expected_value in expected_attributes.items():
        assert getattr(args, attribute) == expected_value


@pytest.mark.parametrize(
    "cli_args,expected_error",
    [
        (
            ["main.py", "--debug-notifications", "--single"],
            "--debug-notifications cannot be combined with other options",
        ),
        (
            ["main.py", "--debug-notifications", "--target", "test"],
            "--debug-notifications cannot be combined with other options",
        ),
        (
            ["main.py", "--single", "--list"],
            "--single can only be combined with --target",
        ),
        (
            ["main.py", "--single", "--restore-latest"],
            "--single can only be combined with --target",
        ),
        (
            ["main.py", "--debug-download", "file.age", "--target", "test"],
            "--debug-download cannot be combined with",
        ),
        (
            ["main.py", "--list"],
            "--list, --restore-latest, and --restore require --target",
        ),
        (
            ["main.py", "--restore-latest"],
            "--list, --restore-latest, and --restore require --target",
        ),
        (
            ["main.py", "--restore", "backup.age"],
            "--list, --restore-latest, and --restore require --target",
        ),
        (
            ["main.py", "--target", "test", "--restore-latest", "--restore", "file"],
            "--restore-latest and --restore cannot be used together",
        ),
        (
            ["main.py", "--target", "test", "--list", "--restore-latest"],
            "--list cannot be combined with --restore-latest or --restore",
        ),
        (
            ["main.py", "--target", "test", "--list", "--restore", "file"],
            "--list cannot be combined with --restore-latest or --restore",
        ),
    ],
)
def test_setup_runtime_arguments_validation_errors(
    monkeypatch: pytest.MonkeyPatch,
    cli_args: list[str],
    expected_error: str,
) -> None:
    monkeypatch.setattr("sys.argv", cli_args)

    with pytest.raises(SystemExit):
        main.setup_runtime_arguments()
    # Note: argparse.error() calls sys.exit(2) and prints to stderr


def test_target_completer(monkeypatch: pytest.MonkeyPatch) -> None:
    models = [ALL_POSTGRES_DBS_TARGETS[0], ALL_MARIADB_DBS_TARGETS[0], FILE_1]
    monkeypatch.setattr(
        core,
        "create_target_models",
        Mock(return_value=models),
    )

    completions = main.target_completer()

    assert isinstance(completions, list)
    assert len(completions) == len(models)
    assert all(model.env_name.lower() in completions for model in models)


def test_target_completer_handles_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        core,
        "create_target_models",
        Mock(side_effect=ValueError("Test error")),
    )

    completions = main.target_completer()

    assert completions == []


def test_backup_file_completer(monkeypatch: pytest.MonkeyPatch) -> None:
    test_backups = ["backup1.sql.lz.age", "backup2.sql.lz.age", "backup3.sql.lz.age"]
    provider_mock = Mock()
    provider_mock.all_target_backups = Mock(return_value=test_backups)
    monkeypatch.setattr(main, "backup_provider", Mock(return_value=provider_mock))

    parsed_args = argparse.Namespace(target="test_target")

    completions = main.backup_file_completer("", parsed_args)

    assert completions == test_backups
    provider_mock.all_target_backups.assert_called_once_with("test_target")


def test_backup_file_completer_no_target(monkeypatch: pytest.MonkeyPatch) -> None:
    parsed_args = argparse.Namespace()

    completions = main.backup_file_completer("", parsed_args)

    assert completions == []


def test_backup_file_completer_handles_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_mock = Mock()
    provider_mock.all_target_backups = Mock(side_effect=ValueError("Test error"))
    monkeypatch.setattr(main, "backup_provider", Mock(return_value=provider_mock))

    parsed_args = argparse.Namespace(target="test_target")

    completions = main.backup_file_completer("", parsed_args)

    assert completions == []
