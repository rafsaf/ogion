# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)


from pathlib import Path
from unittest.mock import Mock

import pytest
from freezegun import freeze_time

from ogion import config, core, main
from ogion.backup_targets.file import File
from ogion.models.backup_target_models import SingleFileTargetModel
from ogion.upload_providers.base_provider import BaseUploadProvider

from .conftest import CONST_TOKEN_URLSAFE, FILE_1

FIRST_FILE_CONTENT = "first stored version\n"
SECOND_FILE_CONTENT = "second stored version\n"
BROKEN_FILE_CONTENT = "broken local state\n"
EXPECTED_PROVIDER_BACKUPS = 2


def _make_file_target(test_file: Path) -> File:
    test_file.touch()
    return File(
        target_model=SingleFileTargetModel(
            env_name="singlefile_provider_restore",
            cron_rule="* * * * *",
            abs_path=test_file,
            max_backups=config.options.BACKUP_MAX_NUMBER,
            min_retention_days=config.options.BACKUP_MIN_RETENTION_DAYS,
        )
    )


def _setup_main_restore_path(
    monkeypatch: pytest.MonkeyPatch,
    provider: BaseUploadProvider,
    target: File,
) -> None:
    monkeypatch.setattr(main, "backup_provider", Mock(return_value=provider))
    monkeypatch.setattr(main, "backup_targets", Mock(return_value=[target]))


def _create_provider_backups(
    target: File,
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

    target.target_model.abs_path.write_text(FIRST_FILE_CONTENT)
    main.run_backup(target=target)

    target.target_model.abs_path.write_text(SECOND_FILE_CONTENT)
    main.run_backup(target=target)

    return provider.all_target_backups(target.env_name)


@freeze_time("2024-03-14")
def test_run_file_backup_output_file_has_proper_name() -> None:
    file = File(target_model=FILE_1)
    out_backup = file.backup()

    escaped_file_name = FILE_1.abs_path.name.replace(".", "")
    out_file = (
        f"{file.env_name}/"
        f"{file.env_name}_20240314_0000_{escaped_file_name}_{CONST_TOKEN_URLSAFE}"
    )
    out_path = config.CONST_DATA_FOLDER_PATH / out_file

    assert out_path.is_file()
    assert out_backup == out_path


def test_run_file_backup_output_file_has_exact_same_content() -> None:
    file = File(target_model=FILE_1)
    out_backup = file.backup()

    assert out_backup.read_text() == FILE_1.abs_path.read_text()


def test_run_file_backup_output_file_has_same_content_after_restore(
    tmp_path: Path,
) -> None:
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("abcdef")

    file = File(
        target_model=SingleFileTargetModel(
            env_name="singlefile",
            cron_rule="* * * * *",
            abs_path=test_file,
        )
    )

    out_backup = file.backup()

    test_file.unlink()

    file.restore(str(out_backup))

    assert test_file.exists()
    assert test_file.read_text() == "abcdef"


def test_end_to_end_restore_specific_stored_backup_via_provider(
    tmp_path: Path,
    provider: BaseUploadProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_file = tmp_path / "provider_restore_file.txt"
    target = _make_file_target(test_file)

    backups = _create_provider_backups(target, monkeypatch, provider)

    assert len(backups) == EXPECTED_PROVIDER_BACKUPS

    test_file.write_text(BROKEN_FILE_CONTENT)

    with pytest.raises(SystemExit) as system_exit:
        main.run_restore(backups[1], target.env_name)

    assert system_exit.value.code == 0
    assert test_file.read_text() == FIRST_FILE_CONTENT

    downloaded_backup = config.CONST_DOWNLOADS_FOLDER_PATH / backups[1].removeprefix(
        "/"
    )
    assert not downloaded_backup.exists()


def test_end_to_end_restore_latest_stored_backup_via_provider(
    tmp_path: Path,
    provider: BaseUploadProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_file = tmp_path / "provider_restore_latest_file.txt"
    target = _make_file_target(test_file)

    backups = _create_provider_backups(target, monkeypatch, provider)

    assert len(backups) == EXPECTED_PROVIDER_BACKUPS

    test_file.write_text(BROKEN_FILE_CONTENT)

    with pytest.raises(SystemExit) as system_exit:
        main.run_restore_latest(target.env_name)

    assert system_exit.value.code == 0
    assert test_file.read_text() == SECOND_FILE_CONTENT

    downloaded_backup = config.CONST_DOWNLOADS_FOLDER_PATH / backups[0].removeprefix(
        "/"
    )
    assert not downloaded_backup.exists()
