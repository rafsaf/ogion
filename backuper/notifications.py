"""
https://discord.com/developers/docs/resources/webhook#execute-webhook
"""
import logging
from datetime import datetime
from enum import StrEnum
from pathlib import Path

import requests

from backuper import config


class FAIL_REASON(StrEnum):
    BACKUP_CREATE = "backup_create"
    UPLOAD = "upload"


log = logging.getLogger(__name__)


def _formated_now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S,%f UTC")


def send_success_message(env_name: str, provider_name: str, upload_path: str) -> None:
    now = _formated_now()
    message_to_send = (
        f"{now} [SUCCESS] target `{env_name}` uploading new backup file "
        f"to provider {provider_name} with upload path {upload_path}"
    )
    try:
        if config.DISCORD_SUCCESS_WEBHOOK_URL:
            discord_success_res = requests.post(
                config.DISCORD_SUCCESS_WEBHOOK_URL,
                json={"content": message_to_send},
                headers={"Content-Type": "application/json"},
                timeout=5,
            )
            if discord_success_res.status_code != 204:
                log.error(
                    "Sent fail message `%s` to DISCORD_SUCCESS_WEBHOOK_URL",
                    message_to_send,
                )
    except Exception as err:
        log.error("fatal error when sending %s: %s", message_to_send, err)


def send_fail_message(
    env_name: str,
    provider_name: str,
    reason: FAIL_REASON,
    backup_file: Path | None = None,
) -> None:
    now = _formated_now()
    if reason == FAIL_REASON.BACKUP_CREATE:
        message_to_send = (
            f"{now} [FAIL] target `{env_name}` uploading backup file "
            f"{backup_file} to provider {provider_name}"
        )
    elif reason == FAIL_REASON.UPLOAD:
        message_to_send = f"{now} [FAIL] target `{env_name}` creating new backup file"
    else:  # pragma: no cover
        raise RuntimeError("panic!!! unexpected reason", reason)

    try:
        if config.DISCORD_FAIL_WEBHOOK_URL:
            discord_fail_res = requests.post(
                config.DISCORD_FAIL_WEBHOOK_URL,
                json={"content": message_to_send},
                headers={"Content-Type": "application/json"},
                timeout=5,
            )
            if discord_fail_res.status_code != 204:
                log.error(
                    "Sent fail message `%s` to DISCORD_FAIL_WEBHOOK_URL",
                    message_to_send,
                )
    except Exception as err:
        log.error("fatal error when sending %s: %s", message_to_send, err)
