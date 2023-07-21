import base64

from pydantic import BaseModel, field_validator

from backuper import config


class ProviderModel(BaseModel):
    name: config.BackupProviderEnum


class LocalProviderModel(ProviderModel):
    pass


class GCSProviderModel(ProviderModel):
    bucket_name: str
    bucket_upload_path: str | None = None
    service_account_base64: str

    @field_validator("service_account_base64")
    def process_service_account_base64(cls, service_account_base64: str) -> str:
        base64.b64decode(service_account_base64)
        return service_account_base64
