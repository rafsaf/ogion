# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import NoReturn
from unittest.mock import Mock

import pytest

from ogion.notifications.notifications_context import (
    PROGRAM_STEP,
    NotificationsContext,
)


@pytest.mark.parametrize(
    "step_name,env_name,exception_text_length",
    [
        (PROGRAM_STEP.BACKUP_CREATE, None, 5),
        (PROGRAM_STEP.DEBUG_NOTIFICATIONS, None, 5),
        (PROGRAM_STEP.SETUP_PROVIDER, "test", 500),
        (PROGRAM_STEP.SETUP_TARGETS, "test", 5000),
    ],
)
def test_notifications_context_send_all_notifications_on_function_fail(
    monkeypatch: pytest.MonkeyPatch,
    step_name: PROGRAM_STEP,
    env_name: str,
    exception_text_length: int,
) -> None:
    send_all = Mock()
    monkeypatch.setattr(NotificationsContext, "send_all", send_all)

    @NotificationsContext(step_name=step_name, env_name=env_name)
    def fail_func_under_tests() -> NoReturn:
        raise ValueError("t" * exception_text_length)

    with pytest.raises(ValueError):
        fail_func_under_tests()

    send_all.assert_called_once()
