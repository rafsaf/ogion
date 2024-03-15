# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import sys
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
    assert system_exit.type == SystemExit

    target_envs = [model.env_name for model in models]
    count = 0
    for dir in config.CONST_BACKUP_FOLDER_PATH.iterdir():
        assert dir.is_dir()
        assert dir.name in target_envs
        count += 1
    assert count == len(target_envs)


def test_main_debug_notifications(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["main.py", "--debug-notifications"])

    with pytest.raises(SystemExit) as system_exit:
        main.main()
    assert system_exit.type == SystemExit


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
    monkeypatch.setattr(target, "_backup", backup_mock)
    provider = UploadProviderLocalDebug(upload_provider_models.DebugProviderModel())
    monkeypatch.setattr(provider, "_post_save", Mock(side_effect=post_save_side_effect))
    monkeypatch.setattr(provider, "_clean", Mock(side_effect=clean_side_effect))

    with pytest.raises(ValueError):
        main.run_backup(target=target, provider=provider)
    fail_message_mock.assert_called_once()


def test_quit(monkeypatch: pytest.MonkeyPatch) -> None:
    exit_mock = Mock()
    monkeypatch.setattr(main, "exit_event", exit_mock)
    main.quit(1, None)
    exit_mock.set.assert_called_once()
