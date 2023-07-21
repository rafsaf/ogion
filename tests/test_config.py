from pathlib import Path

import pytest

from backuper import config


def test_runtime_configuration_invalid_log_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "LOG_LEVEL", "XXXXXX")
    with pytest.raises(RuntimeError):
        config.runtime_configuration()


def test_runtime_configuration_invalid_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "ZIP_ARCHIVE_PASSWORD", "XXXXXX")
    monkeypatch.setattr(config, "BACKUP_PROVIDER", "XXXXXX")
    with pytest.raises(RuntimeError):
        config.runtime_configuration()


def test_runtime_configuration_provider_gcs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "ZIP_ARCHIVE_PASSWORD", "XXXXXX")
    monkeypatch.setattr(config, "BACKUP_PROVIDER", "gcs")
    monkeypatch.setattr(config, "GOOGLE_BUCKET_UPLOAD_PATH", "")
    with pytest.raises(RuntimeError):
        config.runtime_configuration()
    monkeypatch.setattr(config, "GOOGLE_BUCKET_NAME", "bucket")
    with pytest.raises(RuntimeError):
        config.runtime_configuration()
    monkeypatch.setattr(config, "GOOGLE_SERVICE_ACCOUNT_BASE64", "base64_fake")
    with pytest.raises(RuntimeError):
        config.runtime_configuration()
    monkeypatch.setattr(config, "GOOGLE_BUCKET_UPLOAD_PATH", "path")
    with pytest.raises(ValueError):
        try:
            config.runtime_configuration()
        except Exception:
            pass
        else:
            raise ValueError()


def test_runtime_configuration_no_7zz(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        config, "CONST_ZIP_BIN_7ZZ_PATH", Path("/tmp/asdasd/not_existing_asd.txt")
    )
    monkeypatch.setattr(config, "BACKUP_PROVIDER", "local")
    with pytest.raises(RuntimeError):
        config.runtime_configuration()
