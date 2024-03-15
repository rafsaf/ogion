# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import base64

from pydantic import BaseModel, ConfigDict, SecretStr, field_validator

from ogion import config


class ProviderModel(BaseModel):
    name: str

    model_config = ConfigDict(frozen=True)


class DebugProviderModel(ProviderModel):
    name: str = config.UploadProviderEnum.LOCAL_FILES_DEBUG


class GCSProviderModel(ProviderModel):
    name: str = config.UploadProviderEnum.GCS
    bucket_name: str
    bucket_upload_path: str
    service_account_base64: SecretStr
    chunk_size_mb: int = 100
    chunk_timeout_secs: int = 60

    @field_validator("service_account_base64")
    def process_service_account_base64(
        cls, service_account_base64: SecretStr
    ) -> SecretStr:
        base64.b64decode(service_account_base64.get_secret_value())
        return service_account_base64


class AWSProviderModel(ProviderModel):
    name: str = config.UploadProviderEnum.AWS_S3
    bucket_name: str
    bucket_upload_path: str
    key_id: str
    key_secret: SecretStr
    region: str
    max_bandwidth: int | None = None


class AzureProviderModel(ProviderModel):
    name: str = config.UploadProviderEnum.AZURE
    container_name: str
    connect_string: SecretStr
