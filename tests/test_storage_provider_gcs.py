from pathlib import Path

from backuper.storage_providers import GoogleCloudStorage


def test_gcs_save_and_clean(tmp_path: Path):
    gcs = GoogleCloudStorage()
    fake_backup_dir = tmp_path / "fake_env_name"
    fake_backup_dir.mkdir()
    fake_backup_file = fake_backup_dir / "fake_backup"
    fake_backup_file_zip = fake_backup_dir / "fake_backup.zip"
    with open(fake_backup_file, "w") as f:
        f.write("abcdefghijk\n12345")
    assert gcs._post_save(fake_backup_file)
    gcs.bucket.blob.assert_called_with("test/fake_env_name/fake_backup.zip")

    assert fake_backup_file_zip.exists()
    gcs._clean(fake_backup_file)
    assert not fake_backup_file.exists()
    assert not fake_backup_file_zip.exists()
