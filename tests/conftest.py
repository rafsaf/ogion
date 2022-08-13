import os
import pathlib

import pytest
from pytest import MonkeyPatch

from pg_dump import config

POSTGRES_DATABASES_PORTS = {
    14: "10014",
    13: "10013",
    12: "10012",
    11: "10011",
    10: "10010",
}


@pytest.fixture(params=[13, 14, 12, 11, 10], autouse=True)
def config_setup(request, tmpdir, monkeypatch: MonkeyPatch):

    mock_settings = config.Settings()
    mock_settings.PGDUMP_DATABASE_PORT = POSTGRES_DATABASES_PORTS[request.param]
    mock_settings.PGDUMP_BACKUP_FOLDER_PATH = pathlib.Path(f"{tmpdir}/backup")
    mock_settings.PGDUMP_LOG_FOLDER_PATH = pathlib.Path(f"{tmpdir}/log")
    mock_settings.PGDUMP_PGPASS_FILE_PATH = pathlib.Path(f"{tmpdir}/pgpass")
    mock_settings.PGDUMP_PICKLE_PGDUMP_QUEUE_NAME = pathlib.Path(f"{tmpdir}/queue")

    monkeypatch.setattr(config, "settings", mock_settings)

    os.environ["PGPASSFILE"] = str(config.settings.PGDUMP_PGPASS_FILE_PATH)
    os.makedirs(config.settings.PGDUMP_BACKUP_FOLDER_PATH, exist_ok=True)
    os.makedirs(config.settings.PGDUMP_LOG_FOLDER_PATH, exist_ok=True)
