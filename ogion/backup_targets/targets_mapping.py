# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from ogion.backup_targets import (
    base_target,
    file,
    folder,
    mariadb,
    mysql,
    postgresql,
)
from ogion.config import BackupTargetEnum


def get_target_cls_map() -> dict[str, type[base_target.BaseBackupTarget]]:
    return {
        BackupTargetEnum.FILE: file.File,
        BackupTargetEnum.FOLDER: folder.Folder,
        BackupTargetEnum.MARIADB: mariadb.MariaDB,
        BackupTargetEnum.POSTGRESQL: postgresql.PostgreSQL,
        BackupTargetEnum.MYSQL: mysql.MySQL,
    }
