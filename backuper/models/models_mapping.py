from backuper import config
from backuper.models import backup_target_models, upload_provider_models


def get_target_map() -> dict[str, type[backup_target_models.TargetModel]]:
    return {
        config.BackupTargetEnum.FILE: backup_target_models.SingleFileTargetModel,
        config.BackupTargetEnum.FOLDER: backup_target_models.DirectoryTargetModel,
        config.BackupTargetEnum.MARIADB: backup_target_models.MariaDBTargetModel,
        config.BackupTargetEnum.MYSQL: backup_target_models.MySQLTargetModel,
        config.BackupTargetEnum.POSTGRESQL: backup_target_models.PostgreSQLTargetModel,
    }


def get_provider_map() -> dict[str, type[upload_provider_models.ProviderModel]]:
    return {
        config.UploadProviderEnum.AZURE: upload_provider_models.AzureProviderModel,
        config.UploadProviderEnum.LOCAL_FILES_DEBUG: upload_provider_models.DebugProviderModel,
        config.UploadProviderEnum.GOOGLE_CLOUD_STORAGE: upload_provider_models.GCSProviderModel,
        config.UploadProviderEnum.AWS_S3: upload_provider_models.AWSProviderModel,
    }
