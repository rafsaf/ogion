# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from pathlib import Path
from typing import Self

from croniter import croniter
from pydantic import (
    BaseModel,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

from backuper import config


class TargetModel(BaseModel):
    name: str = "test"
    env_name: str = Field(pattern=r"^[A-Za-z_0-9]{1,}$")
    cron_rule: str
    max_backups: int = Field(ge=1, le=998, default=config.options.BACKUP_MAX_NUMBER)
    min_retention_days: int = Field(
        ge=0, le=36600, default=config.options.BACKUP_MIN_RETENTION_DAYS
    )

    @field_validator("cron_rule")
    def cron_rule_is_valid(cls, cron_rule: str) -> str:
        if not croniter.is_valid(cron_rule):
            raise ValueError(
                f"Error in cron_rule expression: `{cron_rule}` is not valid"
            )
        return cron_rule


class PostgreSQLTargetModel(TargetModel):
    name: config.BackupTargetEnum = config.BackupTargetEnum.POSTGRESQL
    user: str = "postgres"
    host: str = "localhost"
    port: int = 5432
    db: str = "postgres"
    password: SecretStr


class MySQLTargetModel(TargetModel):
    name: config.BackupTargetEnum = config.BackupTargetEnum.MYSQL
    user: str = "root"
    host: str = "localhost"
    port: int = 3306
    db: str = "mysql"
    password: SecretStr


class MariaDBTargetModel(TargetModel):
    name: config.BackupTargetEnum = config.BackupTargetEnum.MARIADB
    user: str = "root"
    host: str = "localhost"
    port: int = 3306
    db: str = "mariadb"
    password: SecretStr


class SingleFileTargetModel(TargetModel):
    name: config.BackupTargetEnum = config.BackupTargetEnum.FILE
    abs_path: Path

    @model_validator(mode="after")
    def abs_path_is_valid(self) -> Self:
        if not self.abs_path.is_file() or not self.abs_path.exists():
            raise ValueError(
                f"Path {self.abs_path} is not a file or does not exist\n "
                f"Error validating environment variable: {self.env_name}"
            )
        return self


class DirectoryTargetModel(TargetModel):
    name: config.BackupTargetEnum = config.BackupTargetEnum.FOLDER
    abs_path: Path

    @model_validator(mode="after")
    def abs_path_is_valid(self) -> Self:
        if not self.abs_path.is_dir() or not self.abs_path.exists():
            raise ValueError(
                f"Path {self.abs_path} is not a dir or does not exist\n "
                f"Error validating environment variable: {self.env_name}"
            )
        return self
