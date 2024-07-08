# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)


from freezegun import freeze_time

from ogion import config
from ogion.backup_targets.file import File

from .conftest import CONST_TOKEN_URLSAFE, FILE_1


@freeze_time("2024-03-14")
def test_run_file_backup_output_file_has_proper_name() -> None:
    file = File(target_model=FILE_1)
    out_backup = file.backup()

    escaped_file_name = FILE_1.abs_path.name.replace(".", "")
    out_file = (
        f"{file.env_name}/"
        f"{file.env_name}_20240314_0000_{escaped_file_name}_{CONST_TOKEN_URLSAFE}"
    )
    out_path = config.CONST_BACKUP_FOLDER_PATH / out_file
    assert out_backup == out_path


def test_run_file_backup_output_file_has_exact_same_content() -> None:
    file = File(target_model=FILE_1)
    out_backup = file.backup()

    assert out_backup.read_text() == FILE_1.abs_path.read_text()
