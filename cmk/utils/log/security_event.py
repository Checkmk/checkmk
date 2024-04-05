#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import assert_never, Literal

from cmk.utils.jsontype import JsonSerializable
from cmk.utils.log import init_dedicated_logging


@dataclass
class SecurityEvent:
    """A security event that can be logged"""

    Domain = Enum(
        "Domain",
        [
            "application_errors",
            "auth",
            "service",
            "user_management",
        ],
    )

    summary: str
    details: Mapping[str, JsonSerializable]
    domain: Domain


@dataclass
class SiteStartStoppedEvent(SecurityEvent):
    """Indicates a site start/stopped"""

    def __init__(self, *, event: Literal["start", "stop", "restart"]) -> None:
        if event == "start":
            summary = "site started"
        elif event == "stop":
            summary = "site stopped"
        elif event == "restart":
            summary = "site restarted"
        else:
            assert_never(event)

        super().__init__(summary, {}, SecurityEvent.Domain.service)


def log_security_event(event: SecurityEvent) -> None:
    """Log a security event"""

    # initialize if not already initialized
    if not _root_logger().handlers:
        init_dedicated_logging(
            logging.INFO,
            target_logger=_root_logger(),
            log_file_name="security.log",
            formatter=logging.Formatter("%(asctime)s [%(name)s %(process)d] %(message)s"),
        )

    _root_logger().getChild(event.domain.name).info(
        json.dumps(
            {
                "summary": event.summary,
                "details": event.details,
            }
        )
    )


def _root_logger() -> logging.Logger:
    return logging.getLogger("cmk_security")
