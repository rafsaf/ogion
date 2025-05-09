# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)


from pathlib import Path

from freezegun import freeze_time

from ogion import config, core
from ogion.backup_targets.folder import Folder
from ogion.models.backup_target_models import DirectoryTargetModel

from .conftest import CONST_TOKEN_URLSAFE, FOLDER_1


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
        f"tar -xf {out_backup} -C {out_folder_for_tar} --strip-components=1"
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
