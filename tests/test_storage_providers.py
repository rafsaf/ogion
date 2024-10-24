# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)


from ogion import config
from ogion.upload_providers.base_provider import BaseUploadProvider


def test_gcs_post_save(provider: BaseUploadProvider, provider_prefix: str) -> None:
    fake_backup_dir_path = config.CONST_BACKUP_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_path = fake_backup_dir_path / "fake_backup"
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.age"

    with open(fake_backup_file_path, "w") as f:
        f.write("abcdefghijk\n12345")

    assert (
        provider.post_save(fake_backup_file_path)
        == f"{provider_prefix}fake_env_name/fake_backup.age"
    )
    assert fake_backup_file_age_path.exists()


def test_gcs_clean_local_files(provider: BaseUploadProvider) -> None:
    fake_backup_dir_path = config.CONST_BACKUP_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()

    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup"
    fake_backup_file_age_path.touch()
    fake_backup_file_age_patha = fake_backup_dir_path / "fake_backup.age"
    fake_backup_file_age_patha.touch()

    fake_backup_file_age_path2 = fake_backup_dir_path / "fake_backup2"
    fake_backup_file_age_path2.touch()
    fake_backup_file_age_path2a = fake_backup_dir_path / "fake_backup2.age"
    fake_backup_file_age_path2a.touch()

    provider.clean(fake_backup_file_age_path, 2, 1)

    assert fake_backup_dir_path.exists()
    assert not fake_backup_file_age_path.exists()
    assert not fake_backup_file_age_patha.exists()
    assert not fake_backup_file_age_path2.exists()
    assert not fake_backup_file_age_path2a.exists()


def test_gcs_clean_gcs_files_short(
    provider: BaseUploadProvider, provider_prefix: str
) -> None:
    fake_backup_dir_path = config.CONST_BACKUP_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.age"

    (fake_backup_dir_path / "file_19990427_0108_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_19990427_0108_dummy_xfcs")
    (fake_backup_dir_path / "file_20230427_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230427_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230427_0108_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230427_0108_dummy_xfcs")

    assert provider.all_target_backups("fake_env_name") == [
        f"{provider_prefix}fake_env_name/file_20230427_0108_dummy_xfcs.age",
        f"{provider_prefix}fake_env_name/file_20230427_0105_dummy_xfcs.age",
        f"{provider_prefix}fake_env_name/file_19990427_0108_dummy_xfcs.age",
    ]

    provider.clean(fake_backup_file_age_path, 2, 1)

    assert provider.all_target_backups("fake_env_name") == [
        f"{provider_prefix}fake_env_name/file_20230427_0108_dummy_xfcs.age",
        f"{provider_prefix}fake_env_name/file_20230427_0105_dummy_xfcs.age",
    ]


def test_gcs_clean_gcs_files_long(
    provider: BaseUploadProvider, provider_prefix: str
) -> None:
    fake_backup_dir_path = config.CONST_BACKUP_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.age"

    (fake_backup_dir_path / "file_20230127_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230127_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230227_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230227_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230327_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230327_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230425_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230425_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230426_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230426_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230427_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230427_0105_dummy_xfcs")

    assert provider.all_target_backups("fake_env_name") == [
        f"{provider_prefix}fake_env_name/file_20230427_0105_dummy_xfcs.age",
        f"{provider_prefix}fake_env_name/file_20230426_0105_dummy_xfcs.age",
        f"{provider_prefix}fake_env_name/file_20230425_0105_dummy_xfcs.age",
        f"{provider_prefix}fake_env_name/file_20230327_0105_dummy_xfcs.age",
        f"{provider_prefix}fake_env_name/file_20230227_0105_dummy_xfcs.age",
        f"{provider_prefix}fake_env_name/file_20230127_0105_dummy_xfcs.age",
    ]

    provider.clean(fake_backup_file_age_path, 2, 1)

    assert provider.all_target_backups("fake_env_name") == [
        f"{provider_prefix}fake_env_name/file_20230427_0105_dummy_xfcs.age",
        f"{provider_prefix}fake_env_name/file_20230426_0105_dummy_xfcs.age",
    ]


def test_gcs_clean_respects_max_backups_param_and_not_delete_old_files(
    provider: BaseUploadProvider, provider_prefix: str
) -> None:
    fake_backup_dir_path = config.CONST_BACKUP_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.age"

    (fake_backup_dir_path / "file_20230426_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230426_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230427_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230427_0105_dummy_xfcs")

    assert provider.all_target_backups("fake_env_name") == [
        f"{provider_prefix}fake_env_name/file_20230427_0105_dummy_xfcs.age",
        f"{provider_prefix}fake_env_name/file_20230426_0105_dummy_xfcs.age",
    ]

    provider.clean(fake_backup_file_age_path, 2, 1)

    assert provider.all_target_backups("fake_env_name") == [
        f"{provider_prefix}fake_env_name/file_20230427_0105_dummy_xfcs.age",
        f"{provider_prefix}fake_env_name/file_20230426_0105_dummy_xfcs.age",
    ]


def test_gcs_clean_respects_min_retention_days_param_and_not_delete_any_backup(
    provider: BaseUploadProvider, provider_prefix: str
) -> None:
    fake_backup_dir_path = config.CONST_BACKUP_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.age"

    (fake_backup_dir_path / "file_20230826_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230826_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230825_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230825_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230824_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230824_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230823_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230823_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230729_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230729_0105_dummy_xfcs")

    assert provider.all_target_backups("fake_env_name") == [
        f"{provider_prefix}fake_env_name/file_20230826_0105_dummy_xfcs.age",
        f"{provider_prefix}fake_env_name/file_20230825_0105_dummy_xfcs.age",
        f"{provider_prefix}fake_env_name/file_20230824_0105_dummy_xfcs.age",
        f"{provider_prefix}fake_env_name/file_20230823_0105_dummy_xfcs.age",
        f"{provider_prefix}fake_env_name/file_20230729_0105_dummy_xfcs.age",
    ]

    provider.clean(fake_backup_file_age_path, 2, 300000)

    assert provider.all_target_backups("fake_env_name") == [
        f"{provider_prefix}fake_env_name/file_20230826_0105_dummy_xfcs.age",
        f"{provider_prefix}fake_env_name/file_20230825_0105_dummy_xfcs.age",
        f"{provider_prefix}fake_env_name/file_20230824_0105_dummy_xfcs.age",
        f"{provider_prefix}fake_env_name/file_20230823_0105_dummy_xfcs.age",
        f"{provider_prefix}fake_env_name/file_20230729_0105_dummy_xfcs.age",
    ]


def test_gcs_download_backup(
    provider: BaseUploadProvider, provider_prefix: str
) -> None:
    fake_backup_dir_path = config.CONST_BACKUP_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()

    (fake_backup_dir_path / "file_20230426_0105_dummy_xfcs").write_text("abcdef")
    provider.post_save(fake_backup_dir_path / "file_20230426_0105_dummy_xfcs")

    out = provider.download_backup(
        f"{provider_prefix}fake_env_name/file_20230426_0105_dummy_xfcs.age"
    )

    assert out.is_file()
