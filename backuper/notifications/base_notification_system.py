# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import logging
from abc import ABC, abstractmethod
from typing import final

log = logging.getLogger(__name__)


class NotificationSystem(ABC):
    @abstractmethod
    def _send(self, message: str) -> bool:  # pragma: no cover
        pass

    @final
    def send(self, message: str) -> bool:
        try:
            return self._send(message=message)
        except Exception as err:
            log.error(
                "fatal error when sending notification to '%s': %s",
                self.__class__.__name__,
                err,
            )
            return False

    @final
    def limit_message(self, message: str, limit: int) -> str:
        limit = max(100, limit)
        if len(message) <= limit:
            return message

        last_chars = f"...\n\n(truncated to {limit} chars)"
        truncated_message = message[: limit - len(last_chars)]
        return f"{truncated_message}{last_chars}"
