from backuper.backup_targets import (
    base_target,
    file,
    folder,
    mariadb,
    mysql,
    postgresql,
)
from backuper.config import BackupTargetEnum


def get_target_cls_map() -> dict[str, type[base_target.BaseBackupTarget]]:
    return {
        BackupTargetEnum.FILE: file.File,
        BackupTargetEnum.FOLDER: folder.Folder,
        BackupTargetEnum.MARIADB: mariadb.MariaDB,
        BackupTargetEnum.POSTGRESQL: postgresql.PostgreSQL,
        BackupTargetEnum.MYSQL: mysql.MySQL,
    }
