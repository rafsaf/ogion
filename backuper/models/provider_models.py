import base64
import os

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
        service_account_bytes = base64.b64decode(service_account_base64)
        with open(config.CONST_GOOGLE_SERVICE_ACCOUNT_PATH, "wb") as f:
            f.write(service_account_bytes)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(
            config.CONST_GOOGLE_SERVICE_ACCOUNT_PATH
        )
        return service_account_base64
