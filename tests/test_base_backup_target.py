from datetime import UTC, datetime
from pathlib import Path

from freezegun import freeze_time

from backuper import config
from backuper.backup_targets.base_target import BaseBackupTarget


@freeze_time("2023-05-03 17:58")
def test_base_backup_target_next_backup() -> None:
    class TargetModel(BaseBackupTarget, target_model_name=config.BackupTargetEnum.TEST):
        def _backup(self) -> Path:
            return Path(__file__)

    target = TargetModel(
        cron_rule="* * * * *", env_name="env", max_backups=1, min_retention_days=1
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
