#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

import cmk.utils.paths
from cmk.utils.jsontype import JsonSerializable


@dataclass
class SecurityEvent:
    """A security event that can be logged"""

    Domain = Enum("Domain", ["auth"])

    summary: str
    details: Mapping[str, JsonSerializable]
    domain: Domain


def log_security_event(event: SecurityEvent) -> None:
    """Log a security event"""

    logger = _init_security_logging(event.domain.name)
    logger.info(
        json.dumps(
            {
                "summary": event.summary,
                "details": event.details,
            }
        )
    )


def _root_logger() -> logging.Logger:
    return logging.getLogger("cmk_security")


def _init_security_logging(name: str) -> logging.Logger:
    """Return the logger with the appropriate handler attached"""

    root_logger = _root_logger()

    # initialize if not already initialized
    if not root_logger.handlers:
        handler = logging.FileHandler(cmk.utils.paths.security_log_file, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(name)s %(process)d] %(message)s"))

        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(handler)

    return root_logger.getChild(name)
