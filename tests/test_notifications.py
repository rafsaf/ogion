from pathlib import Path
from typing import Any

import pytest
import responses
from freezegun import freeze_time

from backuper import config, notifications

discord_webhook_url = "https://discord.com/api/webhooks/12345/token"


@freeze_time("2023-04-27 21:08:05")
def test_formated_now() -> None:
    assert notifications._formated_now() == "2023-04-27 21:08:05,000000 UTC"


@pytest.mark.parametrize(
    "res_kwargs",
    [
        {
            "method": responses.POST,
            "url": discord_webhook_url,
            "status": 204,
            "content_type": "text/plain",
            "body": "",
        },
        {
            "method": responses.POST,
            "url": discord_webhook_url,
            "status": 401,
            "content_type": "text/plain",
            "body": '{"message": "Invalid Webhook Token", "code": 50027}',
        },
        {
            "method": responses.POST,
            "url": discord_webhook_url,
            "status": 404,
            "content_type": "text/plain",
            "body": '{"message": "Unknown Webhook", "code": 10015}',
        },
    ],
)
def test_notifications_pass(
    res_kwargs: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(**res_kwargs)

        monkeypatch.setattr(config, "DISCORD_SUCCESS_WEBHOOK_URL", discord_webhook_url)
        monkeypatch.setattr(config, "DISCORD_FAIL_WEBHOOK_URL", discord_webhook_url)

        notifications.send_on_success(
            env_name="env_name",
            provider_name="provider_name",
            upload_path="/upload/path",
        )
        notifications.send_fail_message(
            env_name="env_name",
            provider_name="provider_name",
            backup_file=Path("/upload/path"),
            reason=notifications.FAIL_REASON.BACKUP_CREATE,
        )
        notifications.send_fail_message(
            env_name="env_name",
            provider_name="provider_name",
            backup_file=Path("/upload/path"),
            reason=notifications.FAIL_REASON.UPLOAD,
        )
        monkeypatch.setattr(config, "DISCORD_SUCCESS_WEBHOOK_URL", None)
        monkeypatch.setattr(config, "DISCORD_FAIL_WEBHOOK_URL", None)

        notifications.send_on_success(
            env_name="env_name",
            provider_name="provider_name",
            upload_path="/upload/path",
        )
        notifications.send_fail_message(
            env_name="env_name",
            provider_name="provider_name",
            backup_file=Path("/upload/path"),
            reason=notifications.FAIL_REASON.BACKUP_CREATE,
        )
        notifications.send_fail_message(
            env_name="env_name",
            provider_name="provider_name",
            backup_file=Path("/upload/path"),
            reason=notifications.FAIL_REASON.UPLOAD,
        )


def test_notifications_pass_on_connection_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "DISCORD_SUCCESS_WEBHOOK_URL", discord_webhook_url)
    monkeypatch.setattr(config, "DISCORD_FAIL_WEBHOOK_URL", discord_webhook_url)

    notifications.send_on_success(
        env_name="env_name",
        provider_name="provider_name",
        upload_path="/upload/path",
    )
    notifications.send_fail_message(
        env_name="env_name",
        provider_name="provider_name",
        backup_file=Path("/upload/path"),
        reason=notifications.FAIL_REASON.BACKUP_CREATE,
    )
    notifications.send_fail_message(
        env_name="env_name",
        provider_name="provider_name",
        backup_file=Path("/upload/path"),
        reason=notifications.FAIL_REASON.UPLOAD,
    )
