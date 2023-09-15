import smtplib
from unittest.mock import Mock

import pytest
from pydantic import SecretStr

from backuper import config
from backuper.notifications import smtp


def test_smtp_skip_when_no_webhook_url() -> None:
    assert smtp.SMTP().send(message="text") is False


def test_smtp_work_on_smtp_client_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    smtp_mock = Mock()
    smtp_mock.return_value.__enter__ = Mock()
    smtp_mock.return_value.__exit__ = Mock()
    monkeypatch.setattr(smtplib, "SMTP", smtp_mock)
    monkeypatch.setattr(config.options, "SMTP_HOST", "xxxx11231453.com")
    monkeypatch.setattr(config.options, "SMTP_FROM_ADDR", "example@example.com")
    monkeypatch.setattr(config.options, "SMTP_PORT", 587)
    monkeypatch.setattr(config.options, "SMTP_PASSWORD", SecretStr("secret"))
    monkeypatch.setattr(
        config.options, "SMTP_TO_ADDRS", "example2@example.com,example3@example.com"
    )

    assert smtp.SMTP().send(message="text")
