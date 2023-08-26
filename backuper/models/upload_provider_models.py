import base64

from pydantic import BaseModel, field_validator

from backuper import config


class ProviderModel(BaseModel):
    name: config.UploadProviderEnum
    settings: config.Settings


class DebugProviderModel(ProviderModel):
    pass


class GCSProviderModel(ProviderModel):
    bucket_name: str
    bucket_upload_path: str
    service_account_base64: str
    chunk_size_mb: int = 100
    chunk_timeout_secs: int = 60

    @field_validator("service_account_base64")
    def process_service_account_base64(cls, service_account_base64: str) -> str:
        base64.b64decode(service_account_base64)
        return service_account_base64


class AWSProviderModel(ProviderModel):
    bucket_name: str
    bucket_upload_path: str
    key_id: str
    key_secret: str
    region: str
    max_bandwidth: int | None = None
