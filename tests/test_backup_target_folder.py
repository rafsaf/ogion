# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)


from freezegun import freeze_time

from ogion import config
from ogion.backup_targets.folder import Folder

from .conftest import CONST_TOKEN_URLSAFE, FOLDER_1


@freeze_time("2024-03-14")
def test_run_folder_backup_output_folder_has_proper_name() -> None:
    folder = Folder(target_model=FOLDER_1)
    out_backup = folder.make_backup()

    folder_name = FOLDER_1.abs_path.name
    out_file = (
        f"{folder.env_name}/"
        f"{folder.env_name}_20240314_0000_{folder_name}_{CONST_TOKEN_URLSAFE}"
    )
    out_path = config.CONST_BACKUP_FOLDER_PATH / out_file
    assert out_backup == out_path


def test_run_folder_backup_output_file_in_folder_has_exact_same_content() -> None:
    folder = Folder(target_model=FOLDER_1)
    out_backup = folder.make_backup()

    file_in_folder = FOLDER_1.abs_path / "file.txt"
    file_in_out_folder = out_backup / "file.txt"

    assert file_in_folder.read_text() == file_in_out_folder.read_text()
