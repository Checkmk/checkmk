#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from dataclasses import dataclass

import cmk.utils.log
import cmk.utils.paths
from cmk.utils.log.security_event import SecurityEvent

logger = logging.getLogger("cmk.web")


def init_logging() -> None:
    handler = logging.FileHandler("%s/web.log" % cmk.utils.paths.log_dir, encoding="UTF-8")
    handler.setFormatter(cmk.utils.log.get_formatter())
    root = logging.getLogger()
    del root.handlers[:]  # Remove all previously existing handlers
    root.addHandler(handler)


def set_log_levels(log_levels: dict[str, int]) -> None:
    for name, level in _augmented_log_levels(log_levels).items():
        logging.getLogger(name).setLevel(level)


# To see log entries from libraries and non-GUI code, reuse cmk.web's level.
def _augmented_log_levels(log_levels: dict[str, int]) -> dict[str, int]:
    root_level = log_levels.get("cmk.web")
    all_levels = {} if root_level is None else {"": root_level, "cmk": root_level}
    all_levels.update(log_levels)
    return all_levels


@dataclass
class AuthenticationFailureEvent(SecurityEvent):
    """Indicates a failed authentication attempt"""

    def __init__(
        self, *, user_error: str, auth_method: str, username: str | None, remote_ip: str | None
    ) -> None:
        super().__init__(
            "authentication failed",
            {
                "user_error": user_error,  # Note: may be localized
                "method": auth_method,
                "user": username,
                "remote_ip": remote_ip,
            },
            SecurityEvent.Domain.auth,
        )


@dataclass
class AuthenticationSuccessEvent(SecurityEvent):
    """Indicates a successful authentication"""

    def __init__(self, *, auth_method: str, username: str, remote_ip: str | None) -> None:
        super().__init__(
            "authentication succeeded",
            {"method": auth_method, "user": username, "remote_ip": remote_ip},
            SecurityEvent.Domain.auth,
        )
