"""
https://discord.com/developers/docs/resources/webhook#execute-webhook
"""
import logging
import traceback
from contextlib import ContextDecorator
from datetime import datetime
from enum import StrEnum
from types import TracebackType

import requests
from pydantic import HttpUrl

from backuper import config

log = logging.getLogger(__name__)

CODE_204 = 204


class PROGRAM_STEP(StrEnum):
    SETUP_PROVIDER = "upload provider setup"
    SETUP_TARGETS = "backup targets setup"
    BACKUP_CREATE = "backup create"
    UPLOAD = "upload to provider"
    CLEANUP = "cleanup old backups"


def _formated_now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S,%f UTC")


def _limit_message(message: str, limit: int) -> str:
    limit = max(100, limit)
    if len(message) <= limit:
        return message

    truncate_text = f"...\n\n(truncated to {limit} chars)"
    truncate_message = message[: limit - len(truncate_text)]
    return truncate_message + truncate_text


class NotificationsContext(ContextDecorator):
    def __init__(
        self,
        step_name: PROGRAM_STEP,
        env_name: str | None = None,
        send_on_success: bool = False,
    ) -> None:
        self.step_name: PROGRAM_STEP = step_name
        self.env_name = env_name
        self.send_on_success = send_on_success

    def _success_message(self) -> str:
        now = _formated_now()
        message_to_send = (
            f"[SUCCESS] {now} target `{self.env_name}` uploaded new backup file "
        )
        return message_to_send

    def _fail_message(
        self,
        exc_type: type[BaseException],
        exc_val: BaseException,
        exc_traceback: TracebackType,
    ) -> str:
        now = _formated_now()
        msg = f"[FAIL] {now}\nStep: {self.step_name}\n"
        if self.env_name:
            msg += f"Target: {self.env_name}\n"
        msg += f"Exception Type: {exc_type}\n"
        msg += f"Exception Value: {exc_val}\n"

        tb = "".join(traceback.format_exception(exc_type, exc_val, exc_traceback))
        msg += f"\n{tb}\n"
        return msg

    def _send_discord(
        self, message: str, webhook_url: str | HttpUrl | None, limit_chars: int
    ) -> None:
        if not webhook_url:
            log.debug("skip sending discord notification, no webhook url")
            return None
        try:
            discord_resp = requests.post(
                str(webhook_url),
                json={"content": _limit_message(message=message, limit=limit_chars)},
                headers={"Content-Type": "application/json"},
                timeout=5,
            )
            if discord_resp.status_code != CODE_204:
                log.error("failed send_discord `%s` to %s", message, webhook_url)
        except Exception as err:
            log.error("fatal error send_discord %s: %s", message, err)

    def __enter__(self) -> None:
        log.debug("start Notifications context: %s, %s", self.step_name, self.env_name)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> None:
        if exc_type and exc_val and exc_traceback:
            log.error("step %s failed, sending notifications", self.step_name)
            fail_message = self._fail_message(
                exc_type=exc_type, exc_val=exc_val, exc_traceback=exc_traceback
            )
            log.debug("fail message: %s", fail_message)
            self._send_discord(
                message=fail_message,
                webhook_url=config.options.DISCORD_FAIL_WEBHOOK_URL,
                limit_chars=config.options.DISCORD_NOTIFICATION_MAX_MSG_LEN,
            )
        elif self.send_on_success:
            sucess_message = self._success_message()
            self._send_discord(
                message=sucess_message,
                webhook_url=config.options.DISCORD_SUCCESS_WEBHOOK_URL,
                limit_chars=config.options.DISCORD_NOTIFICATION_MAX_MSG_LEN,
            )
