import os
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from backuper import config


@pytest.mark.parametrize(
    "target_cls,target_params,valid",
    [
        (
            config.TargetModel,
            {"env_name": "VALID", "type": "postgresql", "cron_rule": "* * * * *"},
            True,
        ),
        (
            config.TargetModel,
            {"env_name": "VALID", "type": "mysql", "cron_rule": "* * * * *"},
            True,
        ),
        (
            config.TargetModel,
            {"env_name": ":(()", "type": "postgresql", "cron_rule": "* * * * *"},
            False,
        ),
        (
            config.TargetModel,
            {"env_name": "valid", "type": "postgresql", "cron_rule": "* * ** *"},
            False,
        ),
        (
            config.TargetModel,
            {"env_name": "valid", "type": "postgresql", "cron_rule": "!"},
            False,
        ),
        (
            config.PostgreSQLTargetModel,
            {"password": "secret", "env_name": "valid", "cron_rule": "5 5 * * *"},
            True,
        ),
        (
            config.MySQLTargetModel,
            {
                "password": "secret",
                "db": "xxx",
                "env_name": "valid",
                "cron_rule": "5 0 * * *",
            },
            True,
        ),
        (
            config.MariaDBTargetModel,
            {
                "password": "secret",
                "db": "xxx",
                "env_name": "valid",
                "cron_rule": "* 5 * * *",
            },
            True,
        ),
        (
            config.FileTargetModel,
            {
                "abs_path": Path("/tmp/asdasd/not_existing_asd.txt"),
                "env_name": "valid",
                "cron_rule": "5 5 * * *",
            },
            False,
        ),
        (
            config.FileTargetModel,
            {"abs_path": Path(__file__), "env_name": "valid", "cron_rule": "5 5 * * *"},
            True,
        ),
        (
            config.FolderTargetModel,
            {
                "abs_path": Path("/tmp/asdasd/not_existing_asd/folder"),
                "env_name": "valid",
                "cron_rule": "5 5 * * *",
            },
            False,
        ),
        (
            config.FolderTargetModel,
            {
                "abs_path": Path(__file__).parent,
                "env_name": "valid",
                "cron_rule": "5 5 * * *",
            },
            True,
        ),
    ],
)
def test_backup_targets(
    target_cls: type[config.TargetModel],
    target_params: dict[str, Any],
    valid: bool,
) -> None:
    if valid:
        target_cls(**target_params)
    else:
        with pytest.raises(ValidationError):
            target_cls(**target_params)


@pytest.mark.parametrize(
    "env_lst,valid",
    [
        (
            [
                (
                    "POSTGRESQL_FIRST_DB",
                    "host=localhost port=5432 password=secret cron_rule=* * * * *",
                ),
                (
                    "MYSQL_FIRST_DB",
                    "host=localhost port=3306 password=secret cron_rule=* * * * *",
                ),
            ],
            True,
        ),
        (
            [
                (
                    "MYSQL_SECOND_DB",
                    "host=10.0.0.1 port=3306 user=foo password=change_me! db=bar cron_rule=0 5 * * *",
                )
            ],
            True,
        ),
        (
            [
                (
                    "MARIADB_THIRD_DB",
                    "host=192.168.1.5 port=3306 user=root password=change_me_please! db=project cron_rule=15 */3 * * * max_backups=20",
                )
            ],
            True,
        ),
        (
            [
                (
                    "SINGLEFILE_THIRD",
                    f"abs_path={Path(__file__)} cron_rule=15 */3 * * * max_backups=20",
                )
            ],
            True,
        ),
        (
            [
                (
                    "DIRECTORY_FIRST",
                    f"abs_path={Path(__file__).parent} cron_rule=15 */3 * * * max_backups=20",
                )
            ],
            True,
        ),
        (
            [
                (
                    "POSTGRESQL_FIRST_DB",
                    "host=localhostport=5432 password=secret cron_rule=* * * * *",
                ),
            ],
            True,
        ),
        (
            [
                (
                    "POSTGRESQL_FIRST_DB",
                    "host=localhost port=axxx password=secret cron_rule=* * * * *",
                ),
            ],
            False,
        ),
        (
            [
                (
                    "POSTGRESQL_FIRST_DB",
                    "host=localhost port=111 passwor=secret cron_rule=* * * * *",
                ),
            ],
            False,
        ),
        (
            [
                (
                    "POSTGRESQL_FIRST_DB",
                    "host=localhost port=111 password=secret cron_rule=* ** * *",
                ),
            ],
            False,
        ),
        (
            [
                (
                    "POSTGRESQL_FIRST_DB",
                    "host=localhost port=5432 password=secretcron_rule=* * * * *",
                ),
            ],
            False,
        ),
        (
            [
                (
                    "POSTGRESQL_FIRST_DB",
                    "host=localhost port5432 password=secret cron_rule=* * * * *",
                ),
            ],
            True,
        ),
    ],
)
def test_create_backup_targets(
    env_lst: list[tuple[str, str]], valid: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    items_mock = Mock(return_value=env_lst)
    monkeypatch.setattr(os.environ, "items", items_mock)
    if valid:
        assert config.create_target_models()
    else:
        with pytest.raises(Exception):
            config.create_target_models()


def test_runtime_configuration_invalid_log_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "LOG_LEVEL", "XXXXXX")
    with pytest.raises(RuntimeError):
        config.runtime_configuration()


def test_runtime_configuration_invalid_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "ZIP_ARCHIVE_PASSWORD", "XXXXXX")
    monkeypatch.setattr(config, "BACKUP_PROVIDER", "XXXXXX")
    with pytest.raises(RuntimeError):
        config.runtime_configuration()


def test_runtime_configuration_provider_gcs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "ZIP_ARCHIVE_PASSWORD", "XXXXXX")
    monkeypatch.setattr(config, "BACKUP_PROVIDER", "gcs")
    monkeypatch.setattr(config, "GOOGLE_BUCKET_UPLOAD_PATH", "")
    with pytest.raises(RuntimeError):
        config.runtime_configuration()
    monkeypatch.setattr(config, "GOOGLE_BUCKET_NAME", "bucket")
    with pytest.raises(RuntimeError):
        config.runtime_configuration()
    monkeypatch.setattr(config, "GOOGLE_SERVICE_ACCOUNT_BASE64", "base64_fake")
    with pytest.raises(RuntimeError):
        config.runtime_configuration()
    monkeypatch.setattr(config, "GOOGLE_BUCKET_UPLOAD_PATH", "path")
    with pytest.raises(ValueError):
        try:
            config.runtime_configuration()
        except Exception:
            pass
        else:
            raise ValueError()


def test_runtime_configuration_no_7zz(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        config, "CONST_ZIP_BIN_7ZZ_PATH", Path("/tmp/asdasd/not_existing_asd.txt")
    )
    monkeypatch.setattr(config, "BACKUP_PROVIDER", "local")
    with pytest.raises(RuntimeError):
        config.runtime_configuration()
