# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from backuper.config import UploadProviderEnum
from backuper.upload_providers import (
    aws_s3,
    azure,
    base_provider,
    debug,
    google_cloud_storage,
)


def get_provider_cls_map() -> dict[str, type[base_provider.BaseUploadProvider]]:
    return {
        UploadProviderEnum.AWS_S3: aws_s3.UploadProviderAWS,
        UploadProviderEnum.AZURE: azure.UploadProviderAzure,
        UploadProviderEnum.GCS: google_cloud_storage.UploadProviderGCS,
        UploadProviderEnum.LOCAL_FILES_DEBUG: debug.UploadProviderLocalDebug,
    }
