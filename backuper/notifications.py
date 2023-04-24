"""
https://discord.com/developers/docs/resources/webhook#execute-webhook
"""
import logging
from datetime import datetime
from pathlib import Path

import requests

from backuper import config

log = logging.getLogger(__name__)


def send_success_message(provider_name: str, upload_path: str):
    now = datetime.utcnow().isoformat()
    message_to_send = (
        f"[{now}] SUCCESS uploading new backup to provider "
        f"{provider_name} with upload path {upload_path}"
    )
    try:
        if config.DISCORD_SUCCESS_WEBHOOK_URL:
            requests.post(
                config.DISCORD_SUCCESS_WEBHOOK_URL,
                json={"content": message_to_send},
                headers={"Content-Type": "application/json"},
            )
    except Exception as err:
        log.error("error when sending %s: %s", message_to_send, err)


def send_fail_upload_message(provider_name: str, backup_file: Path):
    now = datetime.utcnow().isoformat()
    message_to_send = (
        f"[{now}] FAIL uploading backup file {backup_file} to provider {provider_name}"
    )
    try:
        if config.DISCORD_FAIL_WEBHOOK_URL:
            requests.post(
                config.DISCORD_FAIL_WEBHOOK_URL,
                json={"content": message_to_send},
                headers={"Content-Type": "application/json"},
            )
    except Exception as err:
        log.error("error when sending %s: %s", message_to_send, err)


def send_fail_backup_message(env_name: str):
    now = datetime.utcnow().isoformat()
    message_to_send = f"[{now}] FAIL creating backup for backup target {env_name}"
    try:
        if config.DISCORD_FAIL_WEBHOOK_URL:
            requests.post(
                config.DISCORD_FAIL_WEBHOOK_URL,
                json={"content": message_to_send},
                headers={"Content-Type": "application/json"},
            )
    except Exception as err:
        log.error("error when sending %s: %s", message_to_send, err)
