# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import Mock

import pytest
from freezegun import freeze_time

from backuper import config, core
from backuper.backup_targets.mariadb import MariaDB
from backuper.models.backup_target_models import MariaDBTargetModel

from .conftest import (
    ALL_MARIADB_DBS_TARGETS,
    CONST_TOKEN_URLSAFE,
    DB_VERSION_BY_ENV_VAR,
)


@pytest.mark.parametrize("mariadb_target", ALL_MARIADB_DBS_TARGETS)
def test_mariadb_connection_success(mariadb_target: MariaDBTargetModel) -> None:
    db = MariaDB(target_model=mariadb_target)
    assert db.db_version == DB_VERSION_BY_ENV_VAR[mariadb_target.env_name]


@pytest.mark.parametrize("mariadb_target", ALL_MARIADB_DBS_TARGETS)
def test_mariadb_connection_fail(
    mariadb_target: MariaDBTargetModel,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(core.CoreSubprocessError):
        # simulate not existing db port 9999 and connection err
        monkeypatch.setattr(mariadb_target, "port", 9999)
        MariaDB(target_model=mariadb_target)


@freeze_time("2022-12-11")
@pytest.mark.parametrize("mariadb_target", ALL_MARIADB_DBS_TARGETS)
def test_run_mariadb_dump(mariadb_target: MariaDBTargetModel) -> None:
    db = MariaDB(target_model=mariadb_target)
    out_backup = db._backup()

    escaped_name = "database_12"
    escaped_version = db.db_version.replace(".", "")
    out_file = (
        f"{db.env_name}/"
        f"{db.env_name}_20221211_0000_{escaped_name}_{escaped_version}_{CONST_TOKEN_URLSAFE}.sql"
    )
    out_path = config.CONST_BACKUP_FOLDER_PATH / out_file
    assert out_backup == out_path
