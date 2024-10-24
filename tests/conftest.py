# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import os
import secrets
import time
from pathlib import Path
from typing import TypeVar

import google.cloud.storage as storage_client
import pytest
from google.auth.credentials import AnonymousCredentials
from pydantic import SecretStr

from ogion import config
from ogion.models.backup_target_models import (
    DirectoryTargetModel,
    MariaDBTargetModel,
    PostgreSQLTargetModel,
    SingleFileTargetModel,
)
from ogion.models.upload_provider_models import (
    AzureProviderModel,
    DebugProviderModel,
    GCSProviderModel,
    S3ProviderModel,
)
from ogion.tools.compose_db_models import ComposeDatabase
from ogion.tools.compose_file_generator import (
    DB_NAME,
    DB_PWD,
    DB_USERNAME,
    db_compose_mariadb_data,
    db_compose_mysql_data,
    db_compose_postgresql_data,
)
from ogion.upload_providers.azure import UploadProviderAzure
from ogion.upload_providers.base_provider import BaseUploadProvider
from ogion.upload_providers.debug import UploadProviderLocalDebug
from ogion.upload_providers.google_cloud_storage import UploadProviderGCS
from ogion.upload_providers.s3 import UploadProviderS3

TM = TypeVar("TM", MariaDBTargetModel, PostgreSQLTargetModel)


def _to_target_model(
    compose_db: ComposeDatabase,
    model: type[TM],
) -> TM:
    DB_VERSION_BY_ENV_VAR[compose_db.name] = compose_db.version
    return model(
        env_name=compose_db.name,
        cron_rule="* * * * *",
        host=compose_db.name if DOCKER_TESTS else "localhost",
        port=(
            int(compose_db.ports[0].split(":")[1])
            if DOCKER_TESTS
            else int(compose_db.ports[0].split(":")[0])
        ),
        password=SecretStr(DB_PWD),
        db=DB_NAME,
        user=DB_USERNAME,
    )


DOCKER_TESTS: bool = os.environ.get("DOCKER_TESTS", None) is not None
CONST_TOKEN_URLSAFE = "mock"
CONST_UNSAFE_AGE_PUBLIC_KEY = (
    "age1q5g88krfjgty48thtctz22h5ja85grufdm0jly3wll6pr9f30qsszmxzm2"
)
CONST_UNSAFE_AGE_SECRET_KEY = (
    "AGE-SECRET-KEY-12L9ETSAZJXK2XLGQRU503VMJ59NGXASGXKAUH05KJ4TDC6UKTAJQGMSN3L"
)
DB_VERSION_BY_ENV_VAR: dict[str, str] = {}
ALL_POSTGRES_DBS_TARGETS: list[PostgreSQLTargetModel] = [
    _to_target_model(compose_db, PostgreSQLTargetModel)
    for compose_db in db_compose_postgresql_data()
]
ALL_MYSQL_DBS_TARGETS: list[MariaDBTargetModel] = [
    _to_target_model(compose_db, MariaDBTargetModel)
    for compose_db in db_compose_mysql_data()
]
ALL_MARIADB_DBS_TARGETS: list[MariaDBTargetModel] = [
    _to_target_model(compose_db, MariaDBTargetModel)
    for compose_db in db_compose_mariadb_data()
]
FILE_1 = SingleFileTargetModel(
    env_name="singlefile_1",
    cron_rule="* * * * *",
    abs_path=Path(__file__).absolute().parent / "const/testfile.txt",
)
FOLDER_1 = DirectoryTargetModel(
    env_name="directory_1",
    cron_rule="* * * * *",
    abs_path=Path(__file__).absolute().parent / "const/testfolder",
)
ALL_TARGETS = (
    ALL_POSTGRES_DBS_TARGETS
    + ALL_MYSQL_DBS_TARGETS
    + ALL_MARIADB_DBS_TARGETS
    + [FILE_1, FOLDER_1]
)


@pytest.fixture(autouse=True)
def fixed_const_config_setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    backup_folder_path = tmp_path / "pytest_data"
    monkeypatch.setattr(config, "CONST_BACKUP_FOLDER_PATH", backup_folder_path)
    backup_folder_path.mkdir(mode=0o700, parents=True, exist_ok=True)
    config_folder_path = tmp_path / "pytest_config"
    monkeypatch.setattr(config, "CONST_CONFIG_FOLDER_PATH", config_folder_path)
    config_folder_path.mkdir(mode=0o700, parents=True, exist_ok=True)
    download_folder_path = tmp_path / "pytest_download"
    monkeypatch.setattr(config, "CONST_DOWNLOADS_FOLDER_PATH", download_folder_path)
    download_folder_path.mkdir(mode=0o700, parents=True, exist_ok=True)
    debug_folder_path = tmp_path / "pytest_data_debug"
    monkeypatch.setattr(config, "CONST_DEBUG_FOLDER_PATH", debug_folder_path)
    debug_folder_path.mkdir(mode=0o700, parents=True, exist_ok=True)
    options = config.Settings(
        LOG_LEVEL="DEBUG",
        BACKUP_PROVIDER="name=debug",
        INSTANCE_NAME="tests",
        SUBPROCESS_TIMEOUT_SECS=10,
        SIGTERM_TIMEOUT_SECS=1,
        BACKUP_MAX_NUMBER=2,
        BACKUP_MIN_RETENTION_DAYS=0,
        DISCORD_WEBHOOK_URL=None,
        DISCORD_MAX_MSG_LEN=1500,
        SLACK_WEBHOOK_URL=None,
        SLACK_MAX_MSG_LEN=1500,
        SMTP_HOST="",
        SMTP_PORT=587,
        SMTP_FROM_ADDR="",
        SMTP_PASSWORD=SecretStr(""),
        SMTP_TO_ADDRS="",
        AGE_RECIPIENTS=CONST_UNSAFE_AGE_PUBLIC_KEY,
        DEBUG_AGE_SECRET_KEY=CONST_UNSAFE_AGE_SECRET_KEY,
    )
    monkeypatch.setattr(config, "options", options)


@pytest.fixture(autouse=True)
def fixed_secrets_token_urlsafe(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_token_urlsafe(nbytes: int) -> str:
        return CONST_TOKEN_URLSAFE

    monkeypatch.setattr(secrets, "token_urlsafe", mock_token_urlsafe)


@pytest.fixture(params=["gcs", "s3", "azure", "debug"])
def provider(request: pytest.FixtureRequest) -> BaseUploadProvider:
    if request.param == "gcs":
        bucket = storage_client.Client(
            credentials=AnonymousCredentials()  # type: ignore[no-untyped-call]
        ).create_bucket(str(time.time_ns()))
        return UploadProviderGCS(
            GCSProviderModel(
                bucket_name=bucket.name or "",
                bucket_upload_path="test",
                service_account_base64=SecretStr("Z29vZ2xlX3NlcnZpY2VfYWNjb3VudAo="),
                chunk_size_mb=100,
                chunk_timeout_secs=100,
            )
        )

    elif request.param == "s3":
        bucket = str(time.time_ns())
        provider_s3 = UploadProviderS3(
            S3ProviderModel(
                endpoint="localhost:9000",
                bucket_name=bucket,
                access_key="minioadmin",
                secret_key=SecretStr("minioadmin"),
                bucket_upload_path="test",
                secure=False,
            )
        )
        provider_s3.client.make_bucket(bucket)
        return provider_s3

    elif request.param == "azure":
        provider_azure = UploadProviderAzure(
            # https://github.com/Azure/Azurite?tab=readme-ov-file#connection-strings
            AzureProviderModel(
                container_name=str(time.time_ns()),
                connect_string=SecretStr(
                    "DefaultEndpointsProtocol=http;"
                    "AccountName=devstoreaccount1;"
                    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
                    "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
                    "QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;"
                    "TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
                ),
            )
        )
        provider_azure.container_client.create_container()
        return provider_azure
    elif request.param == "debug":
        return UploadProviderLocalDebug(DebugProviderModel())
    else:
        raise ValueError("unknown")


@pytest.fixture
def provider_prefix(provider: BaseUploadProvider) -> str:
    if provider.__class__ == UploadProviderAzure:
        return ""
    elif provider.__class__ == UploadProviderLocalDebug:
        return f"{config.CONST_DEBUG_FOLDER_PATH}/"
    return "test/"
