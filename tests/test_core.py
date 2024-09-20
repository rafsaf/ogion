# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import logging
import os
from pathlib import Path
from unittest.mock import Mock

import pytest
from freezegun import freeze_time
from pytest import LogCaptureFixture

from ogion import config, core
from tests.conftest import CONST_UNSAFE_AGE_KEY


@pytest.mark.parametrize(
    "text,result",
    [
        ("asdjklh", "asdjklh"),
        ("asdjklh#$%^&*(*)", "asdjklh"),
        (":'/\\asdjklh#$%^&*(*)", "asdjklh"),
        (":'/\\asdj&^!!!klh#$%^&*(*)", "asdjklh"),
    ],
)
def test_safe_text_version(text: str, result: str) -> None:
    assert core.safe_text_version(text=text) == result


def test_run_subprocess_fail(caplog: LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(core.CoreSubprocessError):
            core.run_subprocess("exit 1")
        assert caplog.messages == [
            "run_subprocess running: 'exit 1'",
            "run_subprocess failed with status 1",
            "run_subprocess stdout: ",
            "run_subprocess stderr: ",
        ]


def test_run_subprocess_success(caplog: LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        core.run_subprocess("echo 'welcome'")
        assert caplog.messages == [
            "run_subprocess running: 'echo 'welcome''",
            "run_subprocess finished with status 0",
            "run_subprocess stdout: welcome\n",
            "run_subprocess stderr: ",
        ]


@freeze_time("2022-12-11")
def test_get_new_backup_path() -> None:
    new_path = core.get_new_backup_path("env_name", "db_string")
    expected_file = "env_name/env_name_20221211_0000_db_string_mock"
    expected_path = config.CONST_BACKUP_FOLDER_PATH / expected_file
    assert str(new_path) == str(expected_path)


def test_run_create_age_archive_out_path_exists(tmp_path: Path) -> None:
    fake_backup_file = tmp_path / "fake_backup"
    with open(fake_backup_file, "w") as f:
        f.write("abcdefghijk\n12345")

    fake_backup_file_out = core.run_create_age_archive(fake_backup_file)
    assert fake_backup_file_out == tmp_path / "fake_backup.age"
    assert fake_backup_file_out.exists()


def test_run_create_age_archive_dir_raise_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        core.run_create_age_archive(tmp_path)


def test_run_create_age_archive_can_be_decrypted(
    tmp_path: Path,
) -> None:
    fake_backup_file = tmp_path / "test_archive"

    with open(fake_backup_file, "w") as f:
        f.write("xxxąć”©#$%")

    archive_file = core.run_create_age_archive(fake_backup_file)
    fake_backup_file.unlink()

    fake_backup_file = core.run_decrypt_age_archive(
        archive_file, debug_secret=CONST_UNSAFE_AGE_KEY
    )

    assert fake_backup_file.exists()
    assert fake_backup_file.read_text() == "xxxąć”©#$%"


test_data = [
    (
        [
            (
                "POSTGRESQL_FIRST_DB",
                "host=localhost port=5432 password=secret cron_rule=* * * * *",
            ),
        ],
        True,
    ),
    (
        [
            (
                "POSTGRESQL_FIRST_DB",
                "host=localhost port=5432 password=secret cron_rule=* * * * *",
            ),
            (
                "MYSQL_FIRST_DB",
                "host=localhost port=3306 password=secret cron_rule=* * * * *",
            ),
        ],
        True,
    ),
    (
        [
            (
                "MYSQL_SECOND_DB",
                "host=10.0.0.1 port=3306 user=foo password=change_me!"
                " db=bar cron_rule=0 5 * * *",
            )
        ],
        True,
    ),
    (
        [
            (
                "MARIADB_THIRD_DB",
                "host=192.168.1.5 port=3306 user=root password=change_me_please! "
                "db=project cron_rule=15 */3 * * * max_backups=20",
            )
        ],
        True,
    ),
    (
        [
            (
                "SINGLEFILE_THIRD",
                f"abs_path={Path(__file__)} cron_rule=15 */3 * * * max_backups=20",
            )
        ],
        True,
    ),
    (
        [
            (
                "DIRECTORY_FIRST",
                f"abs_path={Path(__file__).parent} cron_rule=15 */3 * * * "
                "max_backups=20",
            )
        ],
        True,
    ),
    (
        [
            (
                "POSTGRESQL_FIRST_DB",
                "host=localhostport=5432 password=secret cron_rule=* * * * *",
            ),
        ],
        True,
    ),
    (
        [
            (
                "POSTGRESQL_FIRST_DB",
                "host=localhost port=axxx password=secret cron_rule=* * * * *",
            ),
        ],
        False,
    ),
    (
        [
            (
                "POSTGRESQL_FIRST_DB",
                "host=localhost port=111 passwor=secret cron_rule=* * * * *",
            ),
        ],
        False,
    ),
    (
        [
            (
                "POSTGRESQL_FIRST_DB",
                "host=localhost port=111 password=secret cron_rule=* ** * *",
            ),
        ],
        False,
    ),
    (
        [
            (
                "POSTGRESQL_FIRST_DB",
                "host=localhost port=5432 password=secretcron_rule=* * * * *",
            ),
        ],
        False,
    ),
    (
        [
            (
                "POSTGRESQL_FIRST_DB",
                "host=localhost port5432 password=secret cron_rule=* * * * *",
            ),
        ],
        True,
    ),
]


@pytest.mark.parametrize("env_lst,valid", test_data)
def test_create_backup_targets(
    env_lst: list[tuple[str, str]], valid: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    items_mock = Mock(return_value=env_lst)
    monkeypatch.setattr(os.environ, "items", items_mock)
    if valid:
        assert core.create_target_models()
    else:
        with pytest.raises(Exception):
            core.create_target_models()
