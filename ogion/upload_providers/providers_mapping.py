# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from ogion.config import UploadProviderEnum
from ogion.upload_providers import (
    azure,
    base_provider,
    debug,
    google_cloud_storage,
    s3,
)


def get_provider_cls_map() -> dict[str, type[base_provider.BaseUploadProvider]]:
    return {
        UploadProviderEnum.S3: s3.UploadProviderS3,
        UploadProviderEnum.AZURE: azure.UploadProviderAzure,
        UploadProviderEnum.GCS: google_cloud_storage.UploadProviderGCS,
        UploadProviderEnum.LOCAL_FILES_DEBUG: debug.UploadProviderLocalDebug,
    }
