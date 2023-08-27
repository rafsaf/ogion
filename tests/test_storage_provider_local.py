from pathlib import Path

import pytest
from freezegun import freeze_time

from backuper.upload_providers import UploadProviderLocalDebug


@pytest.mark.parametrize("method_name", ["_clean", "clean"])
def test_local_debug_clean_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, method_name: str
) -> None:
    local = UploadProviderLocalDebug()

    fake_backup_dir_path = tmp_path / "fake_env_name"
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

    getattr(local, method_name)(fake_backup_file_path4, 2, 1)
    assert fake_backup_dir_path.exists()
    assert not fake_backup_file_path4.exists()
    assert not fake_backup_file_zip_path2.exists()
    assert fake_backup_file_zip_path3.exists()
    assert fake_backup_file_zip_path4.exists()


@pytest.mark.parametrize("method_name", ["_clean", "clean"])
def test_local_debug_clean_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, method_name: str
) -> None:
    local = UploadProviderLocalDebug()

    fake_backup_dir_path = tmp_path / "fake_env_name"
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

    getattr(local, method_name)(fake_backup_file_path4, 2, 1)
    assert fake_backup_dir_path.exists()
    assert not fake_backup_file_path4.exists()
    assert not fake_backup_file_zip_path2.exists()
    assert fake_backup_file_zip_path3.exists()
    assert fake_backup_file_zip_path4.exists()


@freeze_time("2023-08-27")
@pytest.mark.parametrize("method_name", ["_clean", "clean"])
def test_local_debug_respects_min_retention_days_param_and_not_delete_any_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, method_name: str
) -> None:
    local = UploadProviderLocalDebug()

    fake_backup_dir_path = tmp_path / "fake_env_name"
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
    getattr(local, method_name)(fake_backup_file_path, 1, 365 * 30)
    assert fake_backup_dir_path.exists()
    assert not fake_backup_file_path.exists()
    assert fake_backup_file_zip_path.exists()
    assert fake_backup_file_zip2_path.exists()
    assert fake_backup_file_zip3_path.exists()
