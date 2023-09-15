import logging

import requests
from requests.adapters import HTTPAdapter, Retry

from backuper import config
from backuper.notifications.base_notification_system import NotificationSystem

log = logging.getLogger(__name__)


STATUS_CODE_204 = 204


class Discord(NotificationSystem):
    def _send(self, message: str) -> bool:
        if not config.options.DISCORD_WEBHOOK_URL:
            log.info("skip sending discord notification, no setup")
            return False

        log.info("sending discord notification")

        content = self.limit_message(
            message=message, limit=config.options.DISCORD_MAX_MSG_LEN
        )

        with requests.session() as session:
            retry = Retry(
                total=4,
                backoff_factor=0.5,
                status_forcelist=[500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry)
            session.mount("", adapter=adapter)

            discord_resp = session.post(
                str(config.options.DISCORD_WEBHOOK_URL),
                json={"content": content},
                headers={"Content-Type": "application/json"},
                timeout=3,
            )

            if discord_resp.status_code != STATUS_CODE_204:
                log.error(
                    "failed send_discord `%s` to %s with status code %s and resp: %s",
                    message,
                    config.options.DISCORD_WEBHOOK_URL,
                    discord_resp.status_code,
                    discord_resp.content,
                )
                return False
            return True
