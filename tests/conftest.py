import secrets
from pathlib import Path

import pytest
from pytest import FixtureRequest, MonkeyPatch

from pg_dump import config

POSTGRES_DATABASES_PORTS = {
    "postgres_15": "10015",
    "postgres_14": "10014",
    "postgres_13": "10013",
    "postgres_12": "10012",
    "postgres_11": "10011",
}
POSTGRES_VERSION_BY_PORT_AND_HOST: dict[tuple[str, str], str] = {
    ("localhost", "10015"): "15.1",
    ("localhost", "10014"): "14.6",
    ("localhost", "10013"): "13.8",
    ("localhost", "10012"): "12.12",
    ("localhost", "10011"): "11.16",
    ("postgres_15", "5432"): "15.1",
    ("postgres_14", "5432"): "14.6",
    ("postgres_13", "5432"): "13.8",
    ("postgres_12", "5432"): "12.12",
    ("postgres_11", "5432"): "11.16",
}


@pytest.fixture(
    params=["postgres_15", "postgres_14", "postgres_13", "postgres_12", "postgres_11"],
    autouse=True,
)
def config_setup(request: FixtureRequest, tmp_path: Path, monkeypatch: MonkeyPatch):

    if config.POSTGRES_HOST != "localhost":
        # tests running in docker container, use hosts from params
        monkeypatch.setattr(config, "POSTGRES_HOST", request.param)
        monkeypatch.setattr(config, "POSTGRES_PORT", "5432")
    else:
        # tests running locally need ports from docker-compose.yml
        monkeypatch.setattr(
            config, "POSTGRES_PORT", POSTGRES_DATABASES_PORTS[request.param]
        )

    monkeypatch.setattr(config, "SUBPROCESS_TIMEOUT_SECS", 1)
    monkeypatch.setattr(config, "LOG_LEVEL", "DEBUG")
    monkeypatch.setattr(config, "BACKUP_COOLING_SECS", 1)
    monkeypatch.setattr(config, "BACKUP_COOLING_RETRIES", 0)
    monkeypatch.setattr(config, "BACKUP_MAX_NUMBER", 1)
    monkeypatch.setattr(config, "ZIP_ARCHIVE_PASSWORD", "test")
    backup_folder_path = tmp_path / "pytest_data"
    monkeypatch.setattr(config, "BACKUP_FOLDER_PATH", backup_folder_path)
    pgpass_file_path = tmp_path / "pytest_pgpass"
    monkeypatch.setattr(config, "PGPASS_FILE_PATH", pgpass_file_path)
    google_serv_acc_path = tmp_path / "pytest_google_auth"
    monkeypatch.setattr(config, "GOOGLE_SERVICE_ACCOUNT_PATH", google_serv_acc_path)
    monkeypatch.setenv("PGPASSFILE", str(pgpass_file_path))
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(google_serv_acc_path))
    config.runtime_configuration()


@pytest.fixture(autouse=True)
def fixed_secrets_token_urlsafe(monkeypatch: MonkeyPatch):
    def mock_token_urlsafe(nbytes: int):
        return "mocked_random_string"

    monkeypatch.setattr(secrets, "token_urlsafe", mock_token_urlsafe)
