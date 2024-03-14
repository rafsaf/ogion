# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from backuper.models.backup_target_models import (
    DirectoryTargetModel,
    MariaDBTargetModel,
    MySQLTargetModel,
    PostgreSQLTargetModel,
    SingleFileTargetModel,
    TargetModel,
)


@pytest.mark.parametrize(
    "target_cls,target_params,valid",
    [
        (
            TargetModel,
            {"env_name": "VALID", "type": "postgresql", "cron_rule": "* * * * *"},
            True,
        ),
        (
            TargetModel,
            {"env_name": "VALID", "type": "mysql", "cron_rule": "* * * * *"},
            True,
        ),
        (
            TargetModel,
            {"env_name": ":(()", "type": "postgresql", "cron_rule": "* * * * *"},
            False,
        ),
        (
            TargetModel,
            {"env_name": "valid", "type": "postgresql", "cron_rule": "* * ** *"},
            False,
        ),
        (
            TargetModel,
            {"env_name": "valid", "type": "postgresql", "cron_rule": "!"},
            False,
        ),
        (
            PostgreSQLTargetModel,
            {"password": "secret", "env_name": "valid", "cron_rule": "5 5 * * *"},
            True,
        ),
        (
            MySQLTargetModel,
            {
                "password": "secret",
                "db": "xxx",
                "env_name": "valid",
                "cron_rule": "5 0 * * *",
            },
            True,
        ),
        (
            MariaDBTargetModel,
            {
                "password": "secret",
                "db": "xxx",
                "env_name": "valid",
                "cron_rule": "* 5 * * *",
            },
            True,
        ),
        (
            SingleFileTargetModel,
            {
                "abs_path": Path("/tmp/asdasd/not_existing_asd.txt"),
                "env_name": "valid",
                "cron_rule": "5 5 * * *",
            },
            False,
        ),
        (
            SingleFileTargetModel,
            {"abs_path": Path(__file__), "env_name": "valid", "cron_rule": "5 5 * * *"},
            True,
        ),
        (
            DirectoryTargetModel,
            {
                "abs_path": Path("/tmp/asdasd/not_existing_asd/folder"),
                "env_name": "valid",
                "cron_rule": "5 5 * * *",
            },
            False,
        ),
        (
            DirectoryTargetModel,
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
    target_cls: type[TargetModel],
    target_params: dict[str, Any],
    valid: bool,
) -> None:
    if valid:
        target_cls(**target_params)
    else:
        with pytest.raises(ValidationError):
            target_cls(**target_params)
