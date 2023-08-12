from typing import Any, NoReturn
from unittest.mock import Mock

import pytest
import responses
from freezegun import freeze_time

from backuper import config
from backuper.notifications import (
    PROGRAM_STEP,
    NotificationsContext,
    _formated_now,
    _limit_message,
)

discord_webhook_url = "https://discord.com/api/webhooks/12345/token"


@freeze_time("2023-04-27 21:08:05")
def test_formated_now() -> None:
    assert _formated_now() == "2023-04-27 21:08:05,000000 UTC"


def test_limit_message_full_text_if_below_limit() -> None:
    assert _limit_message(message="short message", limit=200) == "short message"


def test_limit_message_limited_text_if_behind_limit() -> None:
    long_text = "a" * 1500
    trunc_text = "...\n\n(truncated to 678 chars)"
    assert (
        _limit_message(message=long_text, limit=678)
        == "a" * (678 - len(trunc_text)) + trunc_text
    )


@pytest.mark.parametrize(
    "res_kwargs",
    [
        None,
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
            "body": Exception("fail"),
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
def test_send_discord_always_none_without_exceptions(
    res_kwargs: dict[str, Any]
) -> None:
    with responses.RequestsMock() as rsps:
        if res_kwargs:
            rsps.add(**res_kwargs)
            webhook_url = res_kwargs["url"]
        else:
            webhook_url = ""
        nc = NotificationsContext(step_name=PROGRAM_STEP.SETUP_PROVIDER)
        nc._send_discord("text", webhook_url, limit_chars=150)


@pytest.mark.parametrize(
    "step_name,env_name,send_on_success,exception_text_length",
    [
        (PROGRAM_STEP.BACKUP_CREATE, None, True, 5),
        (PROGRAM_STEP.BACKUP_CREATE, None, False, 5),
        (PROGRAM_STEP.SETUP_PROVIDER, "test", False, 500),
        (PROGRAM_STEP.SETUP_TARGETS, "test", True, 5000),
    ],
)
def test_notifications_context_send_valid_notifications_on_function_fail(
    monkeypatch: pytest.MonkeyPatch,
    step_name: PROGRAM_STEP,
    env_name: str,
    send_on_success: bool,
    exception_text_length: int,
) -> None:
    send_discord_mock = Mock(return_value=None)
    monkeypatch.setattr(config, "DISCORD_FAIL_WEBHOOK_URL", "https://fail")
    monkeypatch.setattr(config, "DISCORD_SUCCESS_WEBHOOK_URL", "https://success")
    monkeypatch.setattr(NotificationsContext, "_send_discord", send_discord_mock)

    @NotificationsContext(
        step_name=step_name, env_name=env_name, send_on_success=send_on_success
    )
    def fail_func_under_tests() -> NoReturn:
        raise ValueError("t" * exception_text_length)

    with pytest.raises(ValueError):
        fail_func_under_tests()

    send_discord_mock.assert_called_once()
    assert send_discord_mock.call_args.kwargs["webhook_url"] == "https://fail"
    assert "ValueError" in send_discord_mock.call_args.kwargs["message"]


@pytest.mark.parametrize(
    "step_name,env_name",
    [
        (PROGRAM_STEP.BACKUP_CREATE, None),
        (PROGRAM_STEP.BACKUP_CREATE, None),
        (PROGRAM_STEP.SETUP_PROVIDER, "test"),
        (PROGRAM_STEP.SETUP_TARGETS, "test"),
    ],
)
def test_notifications_context_send_valid_notifications_on_function_success(
    monkeypatch: pytest.MonkeyPatch,
    step_name: PROGRAM_STEP,
    env_name: str,
) -> None:
    send_discord_mock = Mock(return_value=None)
    monkeypatch.setattr(config, "DISCORD_NOTIFICATION_MAX_MSG_LEN", 150)
    monkeypatch.setattr(config, "DISCORD_FAIL_WEBHOOK_URL", "https://fail")
    monkeypatch.setattr(config, "DISCORD_SUCCESS_WEBHOOK_URL", "https://success")
    monkeypatch.setattr(NotificationsContext, "_send_discord", send_discord_mock)

    @NotificationsContext(step_name=step_name, env_name=env_name, send_on_success=True)
    def success_func_under_tests() -> None:
        return None

    success_func_under_tests()

    send_discord_mock.assert_called_once()
    assert send_discord_mock.call_args.kwargs["webhook_url"] == "https://success"
    assert "[SUCCESS]" in send_discord_mock.call_args.kwargs["message"]
