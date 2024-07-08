# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)


from freezegun import freeze_time

from ogion import config
from ogion.models.upload_provider_models import DebugProviderModel
from ogion.upload_providers.debug import UploadProviderLocalDebug


def get_test_debug() -> UploadProviderLocalDebug:
    return UploadProviderLocalDebug(DebugProviderModel())


def test_local_debug_clean_file() -> None:
    local = get_test_debug()

    fake_backup_dir_path = config.CONST_BACKUP_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_path4 = fake_backup_dir_path / "fake_backup4_20230801_0000_file"
    fake_backup_file_path4.touch()
    fake_backup_file_zip_path4 = (
        fake_backup_dir_path / "fake_backup4_20230801_0000_file.zip"
    )
    fake_backup_file_zip_path4.touch()
    fake_backup_file_zip_path2 = (
        fake_backup_dir_path / "fake_backup2_20230801_0000_file.zip"
    )
    fake_backup_file_zip_path2.touch()
    fake_backup_file_zip_path3 = (
        fake_backup_dir_path / "fake_backup3_20230801_0000_file.zip"
    )
    fake_backup_file_zip_path3.touch()

    local.clean(fake_backup_file_path4, 2, 1)
    assert fake_backup_dir_path.exists()
    assert not fake_backup_file_path4.exists()
    assert not fake_backup_file_zip_path2.exists()
    assert fake_backup_file_zip_path3.exists()
    assert fake_backup_file_zip_path4.exists()


def test_local_debug_clean_folder() -> None:
    local = get_test_debug()

    fake_backup_dir_path = config.CONST_BACKUP_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_path4 = fake_backup_dir_path / "fake_backup4_20230801_0000_file"
    fake_backup_file_path4.mkdir()
    fake_backup_file_zip_path4 = (
        fake_backup_dir_path / "fake_backup4_20230801_0000_file.zip"
    )
    fake_backup_file_zip_path4.mkdir()
    fake_backup_file_zip_path2 = (
        fake_backup_dir_path / "fake_backup2_20230801_0000_file.zip"
    )
    fake_backup_file_zip_path2.mkdir()
    fake_backup_file_zip_path3 = (
        fake_backup_dir_path / "fake_backup3_20230801_0000_file.zip"
    )
    fake_backup_file_zip_path3.mkdir()
    print("xxx")
    print(fake_backup_file_path4)
    local.clean(fake_backup_file_path4, 2, 1)
    assert fake_backup_dir_path.exists()
    assert not fake_backup_file_path4.exists()
    assert not fake_backup_file_zip_path2.exists()
    assert fake_backup_file_zip_path3.exists()
    assert fake_backup_file_zip_path4.exists()


@freeze_time("2023-08-27")
def test_local_debug_respects_min_retention_days_param_and_not_delete_any_file() -> (
    None
):
    local = get_test_debug()

    fake_backup_dir_path = config.CONST_BACKUP_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_path = fake_backup_dir_path / "fake_backup_20230827_0001_file"
    fake_backup_file_path.touch()
    fake_backup_file_zip_path = (
        fake_backup_dir_path / "fake_backup_20230827_0001_file.zip"
    )
    fake_backup_file_zip_path.touch()

    fake_backup_file_zip2_path = (
        fake_backup_dir_path / "fake_backup2_20000501_0000_file.zip"
    )
    fake_backup_file_zip2_path.touch()
    fake_backup_file_zip3_path = (
        fake_backup_dir_path / "fake_backup_20000801_0000_file.zip"
    )
    fake_backup_file_zip3_path.touch()
    local.clean(fake_backup_file_path, 1, 365 * 30)
    assert fake_backup_dir_path.exists()
    assert not fake_backup_file_path.exists()
    assert fake_backup_file_zip_path.exists()
    assert fake_backup_file_zip2_path.exists()
    assert fake_backup_file_zip3_path.exists()
