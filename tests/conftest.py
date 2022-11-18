import pytest

POSTGRES_DATABASES_PORTS = {
    14: "10014",
    13: "10013",
    12: "10012",
    11: "10011",
    10: "10010",
}


@pytest.fixture(params=[13, 14, 12, 11, 10], autouse=True)
def config_setup(request, tmpdir):
    pass
    # settings.PD_DATABASE_PORT = POSTGRES_DATABASES_PORTS[request.param]
    # settings.BACKUP_FOLDER_PATH = pathlib.Path(f"{tmpdir}/backup")
    # settings.PD_LOG_FOLDER_PATH = pathlib.Path(f"{tmpdir}/log")
    # settings.PGPASS_FILE_PATH = pathlib.Path(f"{tmpdir}/pgpass")
    # settings.PD_PICKLE_PD_QUEUE_NAME = pathlib.Path(f"{tmpdir}/queue")

    # os.environ["PGPASSFILE"] = str(settings.PGPASS_FILE_PATH)
    # os.makedirs(settings.BACKUP_FOLDER_PATH, exist_ok=True)
    # os.makedirs(settings.PD_LOG_FOLDER_PATH, exist_ok=True)
