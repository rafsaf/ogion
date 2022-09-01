import os
import pathlib

import pytest

from pg_dump.config import settings

POSTGRES_DATABASES_PORTS = {
    14: "10014",
    13: "10013",
    12: "10012",
    11: "10011",
    10: "10010",
}


@pytest.fixture(params=[13, 14, 12, 11, 10], autouse=True)
def config_setup(request, tmpdir):

    settings.PGDUMP_DATABASE_PORT = POSTGRES_DATABASES_PORTS[request.param]
    settings.PGDUMP_BACKUP_FOLDER_PATH = pathlib.Path(f"{tmpdir}/backup")
    settings.PGDUMP_LOG_FOLDER_PATH = pathlib.Path(f"{tmpdir}/log")
    settings.PGDUMP_PGPASS_FILE_PATH = pathlib.Path(f"{tmpdir}/pgpass")
    settings.PGDUMP_PICKLE_PGDUMP_QUEUE_NAME = pathlib.Path(f"{tmpdir}/queue")

    os.environ["PGPASSFILE"] = str(settings.PGDUMP_PGPASS_FILE_PATH)
    os.makedirs(settings.PGDUMP_BACKUP_FOLDER_PATH, exist_ok=True)
    os.makedirs(settings.PGDUMP_LOG_FOLDER_PATH, exist_ok=True)
