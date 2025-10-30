# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)


from ogion import config
from ogion.upload_providers.base_provider import BaseUploadProvider


def test_gcs_post_save(provider: BaseUploadProvider, provider_prefix: str) -> None:
    fake_backup_dir_path = config.CONST_DATA_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_path = fake_backup_dir_path / "fake_backup"
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.lz.age"

    with open(fake_backup_file_path, "w") as f:
        f.write("abcdefghijk\n12345")

    assert (
        provider.post_save(fake_backup_file_path)
        == f"{provider_prefix}fake_env_name/fake_backup.lz.age"
    )
    assert fake_backup_file_age_path.exists()


def test_gcs_clean_local_files(provider: BaseUploadProvider) -> None:
    fake_backup_dir_path = config.CONST_DATA_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()

    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup"
    fake_backup_file_age_path.touch()
    fake_backup_file_age_patha = fake_backup_dir_path / "fake_backup.lz.age"
    fake_backup_file_age_patha.touch()

    fake_backup_file_age_path2 = fake_backup_dir_path / "fake_backup2"
    fake_backup_file_age_path2.touch()
    fake_backup_file_age_path2a = fake_backup_dir_path / "fake_backup2.lz.age"
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
    fake_backup_dir_path = config.CONST_DATA_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.lz.age"

    (fake_backup_dir_path / "file_19990427_0108_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_19990427_0108_dummy_xfcs")
    (fake_backup_dir_path / "file_20230427_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230427_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230427_0108_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230427_0108_dummy_xfcs")

    assert provider.all_target_backups("fake_env_name") == [
        f"{provider_prefix}fake_env_name/file_20230427_0108_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230427_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_19990427_0108_dummy_xfcs.lz.age",
    ]

    provider.clean(fake_backup_file_age_path, 2, 1)

    assert provider.all_target_backups("fake_env_name") == [
        f"{provider_prefix}fake_env_name/file_20230427_0108_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230427_0105_dummy_xfcs.lz.age",
    ]


def test_gcs_clean_gcs_files_long(
    provider: BaseUploadProvider, provider_prefix: str
) -> None:
    fake_backup_dir_path = config.CONST_DATA_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.lz.age"

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
        f"{provider_prefix}fake_env_name/file_20230427_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230426_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230425_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230327_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230227_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230127_0105_dummy_xfcs.lz.age",
    ]

    provider.clean(fake_backup_file_age_path, 2, 1)

    assert provider.all_target_backups("fake_env_name") == [
        f"{provider_prefix}fake_env_name/file_20230427_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230426_0105_dummy_xfcs.lz.age",
    ]


def test_gcs_clean_respects_max_backups_param_and_not_delete_old_files(
    provider: BaseUploadProvider, provider_prefix: str
) -> None:
    fake_backup_dir_path = config.CONST_DATA_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.lz.age"

    (fake_backup_dir_path / "file_20230426_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230426_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230427_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230427_0105_dummy_xfcs")

    assert provider.all_target_backups("fake_env_name") == [
        f"{provider_prefix}fake_env_name/file_20230427_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230426_0105_dummy_xfcs.lz.age",
    ]

    provider.clean(fake_backup_file_age_path, 2, 1)

    assert provider.all_target_backups("fake_env_name") == [
        f"{provider_prefix}fake_env_name/file_20230427_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230426_0105_dummy_xfcs.lz.age",
    ]


def test_gcs_clean_respects_min_retention_days_param_and_not_delete_any_backup(
    provider: BaseUploadProvider, provider_prefix: str
) -> None:
    fake_backup_dir_path = config.CONST_DATA_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()
    fake_backup_file_age_path = fake_backup_dir_path / "fake_backup.lz.age"

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
        f"{provider_prefix}fake_env_name/file_20230826_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230825_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230824_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230823_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230729_0105_dummy_xfcs.lz.age",
    ]

    provider.clean(fake_backup_file_age_path, 2, 300000)

    assert provider.all_target_backups("fake_env_name") == [
        f"{provider_prefix}fake_env_name/file_20230826_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230825_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230824_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230823_0105_dummy_xfcs.lz.age",
        f"{provider_prefix}fake_env_name/file_20230729_0105_dummy_xfcs.lz.age",
    ]


def test_gcs_download_backup(
    provider: BaseUploadProvider, provider_prefix: str
) -> None:
    fake_backup_dir_path = config.CONST_DATA_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()

    (fake_backup_dir_path / "file_20230426_0105_dummy_xfcs").write_text("abcdef")
    provider.post_save(fake_backup_dir_path / "file_20230426_0105_dummy_xfcs")

    out = provider.download_backup(
        f"{provider_prefix}fake_env_name/file_20230426_0105_dummy_xfcs.lz.age"
    )

    assert out.is_file()


def test_all_target_backups_edge_cases_with_similar_names(
    provider: BaseUploadProvider, provider_prefix: str
) -> None:
    """Test various edge cases with similar env_names to ensure exact matching.

    Covers cases like:
    - 'db' and 'db_2'
    - 'app' and 'application'
    - 'test' and 'test_env' and 'testing'
    """

    env_names = [
        "db",
        "db_2",
        "db_backup",
        "app",
        "application",
        "test",
        "test_env",
        "testing",
    ]

    for env_name in env_names:
        backup_dir = config.CONST_DATA_FOLDER_PATH / env_name
        backup_dir.mkdir()
        backup_file = backup_dir / f"backup_20230427_0105_{env_name}"
        backup_file.touch()
        provider.post_save(backup_file)

    expected_backup_count = 1
    for env_name in env_names:
        backups = provider.all_target_backups(env_name)
        assert len(backups) == expected_backup_count, (
            f"Expected {expected_backup_count} backup for {env_name}, "
            f"got {len(backups)}: {backups}"
        )
        assert env_name in backups[0], (
            f"Backup path {backups[0]} doesn't contain {env_name}"
        )

        expected_prefix = f"{provider_prefix}{env_name}/"
        assert backups[0].startswith(expected_prefix), (
            f"Backup {backups[0]} doesn't start with expected prefix {expected_prefix}"
        )
