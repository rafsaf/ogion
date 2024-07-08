# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from datetime import UTC, datetime
from pathlib import Path
from typing import override

from freezegun import freeze_time

from ogion.backup_targets.base_target import BaseBackupTarget
from ogion.models.backup_target_models import TargetModel


@freeze_time("2023-05-03 17:58")
def test_base_backup_target_next_backup() -> None:
    class MyTargetModel(BaseBackupTarget):
        @override
        def backup(self) -> Path:
            return Path(__file__)

        @override
        def restore(self, path: str) -> None:
            return None

    target = MyTargetModel(
        target_model=TargetModel(
            cron_rule="* * * * *", env_name="env", max_backups=1, min_retention_days=1
        )
    )
    assert target.cron_rule == "* * * * *"
    assert target.env_name == "env"
    assert target.last_backup_time == datetime(2023, 5, 3, 17, 58, tzinfo=UTC)
    assert target.next_backup_time == datetime(2023, 5, 3, 17, 59, tzinfo=UTC)
    assert not target.next_backup()
    assert target.last_backup_time == datetime(2023, 5, 3, 17, 58, tzinfo=UTC)
    assert target.next_backup_time == datetime(2023, 5, 3, 17, 59, tzinfo=UTC)
    with freeze_time("2023-05-03 17:59:02"):
        assert target.next_backup()
        assert target.last_backup_time == datetime(2023, 5, 3, 17, 59, tzinfo=UTC)
        assert target.next_backup_time == datetime(2023, 5, 3, 18, 0, tzinfo=UTC)
