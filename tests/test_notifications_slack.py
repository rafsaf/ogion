# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Any

import pytest
import responses

from ogion import config
from ogion.notifications import slack

slack_webhook_url = (
    "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
)


def test_limit_message_full_text_if_below_limit() -> None:
    limited_message = slack.Slack().limit_message(message="short message", limit=200)
    assert limited_message == "short message"


def test_limit_message_limited_text_if_behind_limit() -> None:
    long_text = "a" * 1500
    trunc_text = "...\n\n(truncated to 678 chars)"

    limited_message = slack.Slack().limit_message(message=long_text, limit=678)
    assert limited_message == "a" * (678 - len(trunc_text)) + trunc_text


def test_slack_skip_when_no_webhook_url() -> None:
    assert slack.Slack().send(message="text") is False


@pytest.mark.parametrize(
    "res_kwargs,sent",
    [
        (
            {
                "method": responses.POST,
                "url": slack_webhook_url,
                "status": 200,
                "content_type": "text/plain",
                "body": "",
            },
            True,
        ),
        (
            {
                "method": responses.POST,
                "url": slack_webhook_url,
                "body": Exception("fail"),
            },
            False,
        ),
        (
            {
                "method": responses.POST,
                "url": slack_webhook_url,
                "status": 401,
                "content_type": "text/plain",
                "body": '{"message": "invalid_payload"}',
            },
            False,
        ),
        (
            {
                "method": responses.POST,
                "url": slack_webhook_url,
                "status": 404,
                "content_type": "text/plain",
                "body": '{"message": "user_not_found"}',
            },
            False,
        ),
    ],
)
def test_slack_cases_when_webhook_url_in_config(
    res_kwargs: dict[str, Any], sent: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(**res_kwargs)
        webhook_url = res_kwargs["url"]

        monkeypatch.setattr(config.options, "SLACK_WEBHOOK_URL", webhook_url)
        assert slack.Slack().send(message="text") == sent
