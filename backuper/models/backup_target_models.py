from functools import cached_property
from pathlib import Path
from typing import Self

from croniter import croniter
from pydantic import (
    BaseModel,
    Field,
    SecretStr,
    computed_field,
    field_validator,
    model_validator,
)

from backuper import config


class TargetModel(BaseModel):
    env_name: str
    cron_rule: str
    max_backups: int = Field(ge=1, le=998)
    settings: config.Settings

    @field_validator("cron_rule")
    def cron_rule_is_valid(cls, cron_rule: str) -> str:
        if not croniter.is_valid(cron_rule):
            raise ValueError(
                f"Error in cron_rule expression: `{cron_rule}` is not valid"
            )
        return cron_rule

    @field_validator("env_name")
    def env_name_is_valid(cls, env_name: str) -> str:
        if not config.CONST_ENV_NAME_REGEX.match(env_name):
            raise ValueError(
                f"Env variable does not match regex {config.CONST_ENV_NAME_REGEX}: `{env_name}`"
            )
        return env_name

    @computed_field()  # type: ignore
    @cached_property
    def target_type(self) -> config.BackupTargetEnum:
        cls_name = self.__class__.__name__.lower()
        target_name = cls_name.removesuffix("targetmodel")
        return config.BackupTargetEnum(target_name)


class PostgreSQLTargetModel(TargetModel):
    user: str = "postgres"
    host: str = "localhost"
    port: int = 5432
    db: str = "postgres"
    password: SecretStr


class MySQLTargetModel(TargetModel):
    user: str = "root"
    host: str = "localhost"
    port: int = 3306
    db: str = "mysql"
    password: SecretStr


class MariaDBTargetModel(TargetModel):
    user: str = "root"
    host: str = "localhost"
    port: int = 3306
    db: str = "mariadb"
    password: SecretStr


class SingleFileTargetModel(TargetModel):
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
    abs_path: Path

    @model_validator(mode="after")
    def abs_path_is_valid(self) -> Self:
        if not self.abs_path.is_dir() or not self.abs_path.exists():
            raise ValueError(
                f"Path {self.abs_path} is not a dir or does not exist\n "
                f"Error validating environment variable: {self.env_name}"
            )
        return self
