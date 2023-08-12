from pathlib import Path

import pytest

from backuper.upload_providers import UploadProviderLocalDebug


@pytest.mark.parametrize("method_name", ["_clean", "safe_clean"])
def test_gcs_clean_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, method_name: str
) -> None:
    local = UploadProviderLocalDebug()

    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_path4 = fake_backup_dir_path / "fake_backup4"
    fake_backup_file_path4.touch()
    fake_backup_file_zip_path4 = fake_backup_dir_path / "fake_backup4.zip"
    fake_backup_file_zip_path4.touch()
    fake_backup_file_zip_path2 = fake_backup_dir_path / "fake_backup2.zip"
    fake_backup_file_zip_path2.touch()
    fake_backup_file_zip_path3 = fake_backup_dir_path / "fake_backup3.zip"
    fake_backup_file_zip_path3.touch()

    getattr(local, method_name)(fake_backup_file_path4, 2)
    assert fake_backup_dir_path.exists()
    assert not fake_backup_file_path4.exists()
    assert not fake_backup_file_zip_path2.exists()
    assert fake_backup_file_zip_path3.exists()
    assert fake_backup_file_zip_path4.exists()


@pytest.mark.parametrize("method_name", ["_clean", "safe_clean"])
def test_gcs_clean_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, method_name: str
) -> None:
    local = UploadProviderLocalDebug()

    fake_backup_dir_path = tmp_path / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_path4 = fake_backup_dir_path / "fake_backup4"
    fake_backup_file_path4.mkdir()
    fake_backup_file_zip_path4 = fake_backup_dir_path / "fake_backup4.zip"
    fake_backup_file_zip_path4.mkdir()
    fake_backup_file_zip_path2 = fake_backup_dir_path / "fake_backup2.zip"
    fake_backup_file_zip_path2.mkdir()
    fake_backup_file_zip_path3 = fake_backup_dir_path / "fake_backup3.zip"
    fake_backup_file_zip_path3.mkdir()

    getattr(local, method_name)(fake_backup_file_path4, 2)
    assert fake_backup_dir_path.exists()
    assert not fake_backup_file_path4.exists()
    assert not fake_backup_file_zip_path2.exists()
    assert fake_backup_file_zip_path3.exists()
    assert fake_backup_file_zip_path4.exists()
