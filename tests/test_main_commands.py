# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import Mock

import pytest

from ogion import config, core, main
from ogion.models.backup_target_models import TargetModel
from ogion.upload_providers.base_provider import BaseUploadProvider

from .conftest import (
    ALL_TARGETS,
)


@pytest.fixture
def mock_main_backup_targets() -> None:
    from _pytest.monkeypatch import MonkeyPatch

    monkeypatch = MonkeyPatch()

    monkeypatch.setattr(
        core,
        "create_target_models",
        Mock(return_value=ALL_TARGETS),
    )
    targets = main.backup_targets()
    monkeypatch.setattr(
        main,
        "backup_targets",
        Mock(return_value=targets),
    )


def test_run_download_backup_file(
    monkeypatch: pytest.MonkeyPatch, provider: BaseUploadProvider, provider_prefix: str
) -> None:
    monkeypatch.setattr(
        main,
        "backup_provider",
        Mock(return_value=provider),
    )

    fake_backup_dir_path = config.CONST_BACKUP_FOLDER_PATH / "fake_env_name"
    fake_backup_dir_path.mkdir()

    (fake_backup_dir_path / "file_19990427_0108_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_19990427_0108_dummy_xfcs")

    provider_file = f"{provider_prefix}fake_env_name/file_19990427_0108_dummy_xfcs.age"
    with pytest.raises(SystemExit):
        main.run_download_backup_file(provider_file)

    fake_download_path = config.CONST_DOWNLOADS_FOLDER_PATH / provider_file
    assert fake_download_path.exists()


@pytest.mark.parametrize("target_model", ALL_TARGETS)
def test_run_list_backup_files(
    monkeypatch: pytest.MonkeyPatch,
    provider: BaseUploadProvider,
    provider_prefix: str,
    capsys: pytest.CaptureFixture[str],
    target_model: TargetModel,
    mock_main_backup_targets: None,
) -> None:
    monkeypatch.setattr(
        main,
        "backup_provider",
        Mock(return_value=provider),
    )

    fake_backup_dir_path = config.CONST_BACKUP_FOLDER_PATH / target_model.env_name
    fake_backup_dir_path.mkdir()

    (fake_backup_dir_path / "file_19990427_0108_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_19990427_0108_dummy_xfcs")
    (fake_backup_dir_path / "file_20230427_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230427_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230427_0108_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230427_0108_dummy_xfcs")

    captured = capsys.readouterr()
    with pytest.raises(SystemExit):
        main.run_list_backup_files(target_model.env_name)

    provider_file_1 = (
        f"{provider_prefix}{target_model.env_name}/file_19990427_0108_dummy_xfcs.age"
    )
    provider_file_2 = (
        f"{provider_prefix}{target_model.env_name}/file_20230427_0105_dummy_xfcs.age"
    )
    provider_file_3 = (
        f"{provider_prefix}{target_model.env_name}/file_20230427_0108_dummy_xfcs.age"
    )

    captured = capsys.readouterr()
    assert captured.out == f"{provider_file_3}\n{provider_file_2}\n{provider_file_1}\n"

    with pytest.raises(SystemExit):
        main.run_list_backup_files("random")

    captured = capsys.readouterr()
    assert captured.out == "target 'random' does not exist\n"


@pytest.mark.parametrize("target_model", ALL_TARGETS)
def test_run_restore_latest(
    monkeypatch: pytest.MonkeyPatch,
    provider: BaseUploadProvider,
    provider_prefix: str,
    capsys: pytest.CaptureFixture[str],
    target_model: TargetModel,
    mock_main_backup_targets: None,
) -> None:
    monkeypatch.setattr(
        main,
        "backup_provider",
        Mock(return_value=provider),
    )

    backup_target = [
        target
        for target in main.backup_targets()
        if target.env_name == target_model.env_name
    ][0]

    restore_mock = Mock()
    monkeypatch.setattr(
        backup_target.__class__,
        "restore",
        restore_mock,
    )

    fake_backup_dir_path = config.CONST_BACKUP_FOLDER_PATH / backup_target.env_name
    fake_backup_dir_path.mkdir()

    (fake_backup_dir_path / "file_19990427_0108_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_19990427_0108_dummy_xfcs")
    (fake_backup_dir_path / "file_20230427_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230427_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230427_0108_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230427_0108_dummy_xfcs")

    with pytest.raises(SystemExit):
        main.run_restore_latest(backup_target.env_name)

    provider_file = (
        f"{provider_prefix}{backup_target.env_name}/file_20230427_0108_dummy_xfcs.age"
    )

    provider_file_download = config.CONST_DOWNLOADS_FOLDER_PATH / provider_file

    assert provider_file_download.exists()
    restore_mock.assert_called_once_with(str(provider_file_download.with_suffix("")))

    captured = capsys.readouterr()

    with pytest.raises(SystemExit):
        main.run_restore_latest("random")
    captured = capsys.readouterr()

    assert captured.out == "target 'random' does not exist\n"

    captured = capsys.readouterr()

    other_target_model = [t for t in ALL_TARGETS if t != target_model][0]
    with pytest.raises(SystemExit):
        main.run_restore_latest(other_target_model.env_name)
    captured = capsys.readouterr()

    assert captured.out == f"no backups at all for '{other_target_model.env_name}'\n"


@pytest.mark.parametrize("target_model", ALL_TARGETS)
def test_run_restore(
    monkeypatch: pytest.MonkeyPatch,
    provider: BaseUploadProvider,
    provider_prefix: str,
    capsys: pytest.CaptureFixture[str],
    target_model: TargetModel,
    mock_main_backup_targets: None,
) -> None:
    monkeypatch.setattr(
        main,
        "backup_provider",
        Mock(return_value=provider),
    )

    backup_target = [
        target
        for target in main.backup_targets()
        if target.env_name == target_model.env_name
    ][0]

    restore_mock = Mock()
    monkeypatch.setattr(
        backup_target.__class__,
        "restore",
        restore_mock,
    )

    fake_backup_dir_path = config.CONST_BACKUP_FOLDER_PATH / backup_target.env_name
    fake_backup_dir_path.mkdir()

    (fake_backup_dir_path / "file_19990427_0108_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_19990427_0108_dummy_xfcs")
    (fake_backup_dir_path / "file_20230427_0105_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230427_0105_dummy_xfcs")
    (fake_backup_dir_path / "file_20230427_0108_dummy_xfcs").touch()
    provider.post_save(fake_backup_dir_path / "file_20230427_0108_dummy_xfcs")

    provider_file = (
        f"{provider_prefix}{backup_target.env_name}/file_19990427_0108_dummy_xfcs.age"
    )

    with pytest.raises(SystemExit):
        main.run_restore(backup_name=provider_file, target_name=backup_target.env_name)

    provider_file_download = config.CONST_DOWNLOADS_FOLDER_PATH / provider_file

    assert provider_file_download.exists()
    restore_mock.assert_called_once_with(str(provider_file_download.with_suffix("")))

    captured = capsys.readouterr()

    with pytest.raises(SystemExit):
        main.run_restore("test", "random")
    captured = capsys.readouterr()

    assert captured.out == "target 'random' does not exist\n"

    captured = capsys.readouterr()

    with pytest.raises(SystemExit):
        main.run_restore("test", backup_target.env_name)
    captured = capsys.readouterr()

    assert (
        captured.out
        == f"backup 'test' not exist at all for '{backup_target.env_name}'\n"
    )

    captured = capsys.readouterr()

    other_target_model = [t for t in ALL_TARGETS if t != target_model][0]
    with pytest.raises(SystemExit):
        main.run_restore("test", other_target_model.env_name)
    captured = capsys.readouterr()

    assert captured.out == f"no backups at all for '{other_target_model.env_name}'\n"
