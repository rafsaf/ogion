# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)


import shutil
from pathlib import Path
from unittest.mock import Mock

import pytest
from freezegun import freeze_time

from ogion import config, core, main
from ogion.backup_targets.folder import Folder
from ogion.models.backup_target_models import DirectoryTargetModel
from ogion.upload_providers.base_provider import BaseUploadProvider

from .conftest import CONST_TOKEN_URLSAFE, FOLDER_1

EXPECTED_PROVIDER_BACKUPS = 2


def _make_folder_target(directory: Path) -> Folder:
    directory.mkdir(parents=True, exist_ok=True)
    return Folder(
        target_model=DirectoryTargetModel(
            env_name="directory_provider_restore",
            cron_rule="* * * * *",
            abs_path=directory,
            max_backups=config.options.BACKUP_MAX_NUMBER,
            min_retention_days=config.options.BACKUP_MIN_RETENTION_DAYS,
        )
    )


def _write_folder_state(
    directory: Path, *, content: str, with_nested_file: bool
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "file.txt").write_text(content)
    nested_dir = directory / "nested"
    if with_nested_file:
        nested_dir.mkdir(parents=True, exist_ok=True)
        (nested_dir / "inside.txt").write_text(f"nested:{content}")
    elif nested_dir.exists():
        shutil.rmtree(nested_dir)


def _assert_folder_state(
    directory: Path, *, content: str, with_nested_file: bool
) -> None:
    assert (directory / "file.txt").read_text() == content
    nested_file = directory / "nested" / "inside.txt"
    assert nested_file.exists() is with_nested_file
    if with_nested_file:
        assert nested_file.read_text() == f"nested:{content}"


def _setup_main_restore_path(
    monkeypatch: pytest.MonkeyPatch,
    provider: BaseUploadProvider,
    target: Folder,
) -> None:
    monkeypatch.setattr(main, "backup_provider", Mock(return_value=provider))
    monkeypatch.setattr(main, "backup_targets", Mock(return_value=[target]))


def _create_provider_backups(
    target: Folder,
    monkeypatch: pytest.MonkeyPatch,
    provider: BaseUploadProvider,
) -> list[str]:
    backup_suffixes = iter(
        [
            ("20240314_0000", "specific"),
            ("20240314_0001", "latest"),
        ]
    )

    def fake_get_new_backup_path(env_name: str, name: str) -> Path:
        timestamp, token = next(backup_suffixes)
        base_dir_path = config.CONST_DATA_FOLDER_PATH / env_name
        base_dir_path.mkdir(mode=0o700, parents=True, exist_ok=True)
        return base_dir_path / f"{env_name}_{timestamp}_{name}_{token}"

    _setup_main_restore_path(monkeypatch, provider, target)
    monkeypatch.setattr(core, "get_new_backup_path", fake_get_new_backup_path)

    _write_folder_state(
        target.target_model.abs_path,
        content="first stored version\n",
        with_nested_file=False,
    )
    main.run_backup(target=target)

    _write_folder_state(
        target.target_model.abs_path,
        content="second stored version\n",
        with_nested_file=True,
    )
    main.run_backup(target=target)

    return provider.all_target_backups(target.env_name)


@freeze_time("2024-03-14")
def test_run_folder_backup_output_folder_has_proper_name() -> None:
    folder = Folder(target_model=FOLDER_1)
    out_backup = folder.backup()

    folder_name = FOLDER_1.abs_path.name
    out_file = (
        f"{folder.env_name}/"
        f"{folder.env_name}_20240314_0000_{folder_name}_{CONST_TOKEN_URLSAFE}.tar"
    )
    out_path = config.CONST_DATA_FOLDER_PATH / out_file

    assert out_path.is_file()
    assert out_backup == out_path


def test_run_folder_backup_output_file_in_folder_has_same_content_after_extract(
    tmp_path: Path,
) -> None:
    folder = Folder(target_model=FOLDER_1)
    out_backup = folder.backup()
    out_folder_for_tar = tmp_path / "somewhere"
    out_folder_for_tar.mkdir()

    core.run_subprocess(
        [
            "tar",
            "-xf",
            str(out_backup),
            "-C",
            str(out_folder_for_tar),
            "--strip-components=1",
        ]
    )

    file_in_folder = FOLDER_1.abs_path / "file.txt"

    file_in_out_folder = out_folder_for_tar / "file.txt"

    assert file_in_folder.read_text() == file_in_out_folder.read_text()


def test_run_folder_backup_output_file_in_folder_has_same_content_after_restore(
    tmp_path: Path,
) -> None:
    file_in_folder = FOLDER_1.abs_path / "file.txt"
    original_file_content = file_in_folder.read_text()

    directory = tmp_path / "directory"
    directory.mkdir()

    folder = Folder(
        target_model=DirectoryTargetModel(
            env_name="directory_1",
            cron_rule="* * * * *",
            abs_path=directory,
        )
    )

    new_file = directory / "file.txt"
    new_file.write_text(original_file_content)

    out_backup = folder.backup()

    new_file.unlink()
    directory.rmdir()

    folder.restore(str(out_backup))

    assert new_file.read_text() == original_file_content


def test_end_to_end_restore_specific_stored_backup_via_provider(
    tmp_path: Path,
    provider: BaseUploadProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    directory = tmp_path / "folder_provider_restore"
    target = _make_folder_target(directory)

    backups = _create_provider_backups(target, monkeypatch, provider)

    assert len(backups) == EXPECTED_PROVIDER_BACKUPS

    shutil.rmtree(directory)

    with pytest.raises(SystemExit) as system_exit:
        main.run_restore(backups[1], target.env_name)

    assert system_exit.value.code == 0
    _assert_folder_state(
        directory, content="first stored version\n", with_nested_file=False
    )

    downloaded_backup = config.CONST_DOWNLOADS_FOLDER_PATH / backups[1].removeprefix(
        "/"
    )
    assert not downloaded_backup.exists()


def test_end_to_end_restore_latest_stored_backup_via_provider(
    tmp_path: Path,
    provider: BaseUploadProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    directory = tmp_path / "folder_provider_restore_latest"
    target = _make_folder_target(directory)

    backups = _create_provider_backups(target, monkeypatch, provider)

    assert len(backups) == EXPECTED_PROVIDER_BACKUPS

    shutil.rmtree(directory)

    with pytest.raises(SystemExit) as system_exit:
        main.run_restore_latest(target.env_name)

    assert system_exit.value.code == 0
    _assert_folder_state(
        directory, content="second stored version\n", with_nested_file=True
    )

    downloaded_backup = config.CONST_DOWNLOADS_FOLDER_PATH / backups[0].removeprefix(
        "/"
    )
    assert not downloaded_backup.exists()
