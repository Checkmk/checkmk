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
from cmk.utils.paths import log_dir


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
            "cert_management",
        ],
    )

    summary: str
    details: Mapping[str, JsonSerializable]
    domain: Domain


@dataclass
class SiteStartStoppedEvent(SecurityEvent):
    """Indicates a site start/stopped"""

    def __init__(self, *, event: Literal["start", "stop", "restart"], daemon: str | None) -> None:
        if event == "start":
            summary = "site started"
        elif event == "stop":
            summary = "site stopped"
        elif event == "restart":
            summary = "site restarted"
        else:
            assert_never(event)

        super().__init__(
            summary,
            {
                "daemon": daemon or "all",
            },
            SecurityEvent.Domain.service,
        )


def log_security_event(event: SecurityEvent) -> None:
    _get_logger().getChild(event.domain.name).info(
        json.dumps(
            {
                "summary": event.summary,
                "details": event.details,
            }
        )
    )


def _get_logger() -> logging.Logger:
    logger = logging.getLogger("cmk_security")
    if not logger.handlers:  # delayed logger initialization
        handler = logging.FileHandler(log_dir / "security.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(name)s %(process)d] %(message)s"))
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        logger.propagate = False
    return logger
